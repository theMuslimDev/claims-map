"""release.py in a temporary git repo: dry run, refusals, bump, changelog, --check, --publish."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
CHANGELOG = "# Changelog\n\n## Unreleased\n- Fixed a thing.\n\n## v0.0.1 (experimental)\n- First.\n"


FAKE_GH = """#!%s
import json, os, sys
state = os.environ["FAKE_GH_STATE"]
args = sys.argv[1:]
rel = os.path.join(state, "releases.json")
releases = json.load(open(rel)) if os.path.exists(rel) else {}
if args[:2] == ["auth", "status"]:
    sys.exit(0 if os.environ.get("FAKE_GH_LOGGED_IN", "1") == "1" else 1)
if args[:2] == ["release", "view"]:
    sys.exit(0 if args[2] in releases else 1)
if args[:2] == ["release", "create"]:
    notes = open(args[args.index("--notes-file") + 1]).read()
    releases[args[2]] = {"args": args, "notes": notes}
    json.dump(releases, open(rel, "w"))
    print("https://example.invalid/" + args[2])
    sys.exit(0)
sys.exit(2)
""" % sys.executable


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".claude-plugin").mkdir()
        self.write(".claude-plugin/plugin.json", {"name": "p", "version": "0.0.1"})
        self.write(".claude-plugin/marketplace.json", {"plugins": [
            {"name": "p", "source": {"source": "github", "repo": "o/p", "ref": "v0.0.1"}}]})
        (self.repo / "CHANGELOG.md").write_text(CHANGELOG)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        git(self.repo, "tag", "-a", "v0.0.1", "-m", "v0.0.1")
        self.origin = self.repo.parent / (self.repo.name + "-origin.git")
        git(self.repo, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(self.repo, "remote", "add", "origin", str(self.origin))
        git(self.repo, "push", "-q", "origin", "main", "v0.0.1")
        # fake gh on PATH, plus a PATH with git only for the "no gh" case
        self.bin = self.repo.parent / (self.repo.name + "-bin")
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.gitonly = self.repo.parent / (self.repo.name + "-gitonly")
        self.gitonly.mkdir()
        (self.gitonly / "git").symlink_to(shutil.which("git"))
        self.state = self.repo.parent / (self.repo.name + "-state")
        self.state.mkdir()

    def tearDown(self):
        self._tmp.cleanup()
        for d in (self.origin, self.bin, self.gitonly, self.state):
            shutil.rmtree(d, ignore_errors=True)

    def releases(self):
        f = self.state / "releases.json"
        return json.loads(f.read_text()) if f.exists() else {}

    def env(self, gh=True, logged_in=True):
        path = str(self.bin if gh else self.gitonly) + os.pathsep + (os.environ["PATH"] if gh else "")
        return dict(os.environ, PATH=path, FAKE_GH_STATE=str(self.state),
                    FAKE_GH_LOGGED_IN="1" if logged_in else "0")

    def write(self, rel, data):
        (self.repo / rel).write_text(json.dumps(data, indent=2) + "\n")

    def read(self, rel):
        return json.loads((self.repo / rel).read_text())

    def run_release(self, *args, **envopts):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              capture_output=True, text=True, env=self.env(**envopts))

    def test_dry_run_changes_nothing(self):
        before = git(self.repo, "rev-parse", "HEAD")
        r = self.run_release("0.1.0", "--skip-checks", "--tag")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would set plugin.json version to 0.1.0", r.stdout)
        self.assertIn("would create the tag v0.1.0", r.stdout)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(self.read(".claude-plugin/plugin.json")["version"], "0.0.1")
        self.assertEqual(git(self.repo, "tag"), "v0.0.1")

    def test_dirty_tree_refused(self):
        (self.repo / "stray.txt").write_text("x")
        r = self.run_release("0.1.0", "--skip-checks", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not clean", r.stderr)

    def test_wrong_branch_refused(self):
        git(self.repo, "checkout", "-q", "-b", "feature")
        r = self.run_release("0.1.0", "--skip-checks", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not on branch main", r.stderr)

    def test_apply_bumps_version_pin_and_changelog(self):
        r = self.run_release("0.1.0", "--skip-checks", "--apply", "--trailer", "Co-Authored-By: T <t@example.com>")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read(".claude-plugin/plugin.json")["version"], "0.1.0")
        self.assertEqual(self.read(".claude-plugin/marketplace.json")["plugins"][0]["source"]["ref"], "v0.1.0")
        text = (self.repo / "CHANGELOG.md").read_text()
        self.assertRegex(text, r"## Unreleased\n\n## v0\.1\.0 \(\d{4}-\d\d-\d\d\)\n- Fixed a thing\.")
        self.assertEqual(git(self.repo, "log", "--format=%s", "-1"), "release: v0.1.0")
        self.assertIn("Co-Authored-By", git(self.repo, "log", "--format=%b", "-1"))
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD"), "2")
        self.assertEqual(git(self.repo, "tag"), "v0.0.1")  # no --tag, no tag
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_apply_with_tag_then_check_passes(self):
        self.assertEqual(self.run_release("0.1.0", "--skip-checks", "--apply", "--tag").returncode, 0)
        self.assertIn("v0.1.0", git(self.repo, "tag").split())
        self.releases_add("v0.1.0")
        r = self.run_release("--check")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_empty_unreleased_refused(self):
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n## v0.0.1\n- x\n")
        git(self.repo, "commit", "-qam", "empty")
        r = self.run_release("0.1.0", "--skip-checks", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("empty", r.stderr)

    def test_version_must_increase(self):
        r = self.run_release("0.0.1", "--skip-checks", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stderr, re.compile("not greater"))

    def test_check_passes_on_consistent_repo(self):
        self.releases_add("v0.0.1")
        r = self.run_release("--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("GitHub Release exists", r.stdout)

    def releases_add(self, tag):
        (self.state / "releases.json").write_text(json.dumps({tag: {}}))

    def test_check_flags_missing_github_release(self):
        r = self.run_release("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MISMATCH: no GitHub Release for v0.0.1", r.stdout)

    def test_check_skips_release_without_gh(self):
        r = self.run_release("--check", gh=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("GitHub Release check skipped: gh is not installed", r.stdout)
        self.assertNotIn("MISMATCH", r.stdout)

    def test_check_skips_release_when_not_logged_in(self):
        r = self.run_release("--check", logged_in=False)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("skipped: gh is not logged in", r.stdout)

    def test_publish_dry_run_creates_nothing(self):
        r = self.run_release("--publish")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would create the GitHub Release v0.0.1", r.stdout)
        self.assertIn("dry run", r.stdout)
        self.assertEqual(self.releases(), {})

    def test_publish_creates_release_from_changelog_section(self):
        r = self.run_release("--publish", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        made = self.releases()["v0.0.1"]
        self.assertEqual(made["notes"], "- First.\n")
        args = made["args"]
        for flag in ("--verify-tag", "--latest"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--title") + 1], "v0.0.1 (experimental)")
        self.assertEqual(self.run_release("--check").returncode, 0)

    def test_publish_explicit_version(self):
        r = self.run_release("--publish", "0.0.1", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v0.0.1", self.releases())

    def test_publish_refused_when_tag_not_on_origin(self):
        git(self.repo, "tag", "-a", "v0.0.2", "-m", "v0.0.2")
        (self.repo / "CHANGELOG.md").write_text(CHANGELOG + "\n## v0.0.2 (x)\n- Two.\n")
        r = self.run_release("--publish", "0.0.2", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not on origin", r.stderr)
        self.assertEqual(self.releases(), {})

    def test_publish_refused_when_tag_missing_locally(self):
        r = self.run_release("--publish", "0.0.9", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not exist locally", r.stderr)

    def test_publish_refused_when_release_exists(self):
        self.releases_add("v0.0.1")
        r = self.run_release("--publish", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists", r.stderr)

    def test_publish_refused_without_changelog_section(self):
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n- x\n")
        r = self.run_release("--publish", "--apply")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no non-empty '## v0.0.1' section", r.stderr)
        self.assertEqual(self.releases(), {})

    def test_publish_refused_without_gh(self):
        r = self.run_release("--publish", "--apply", gh=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("gh is not installed", r.stderr)
        r = self.run_release("--publish", "--apply", logged_in=False)
        self.assertIn("not logged in", r.stderr)

    def test_check_flags_ref_mismatch(self):
        self.write(".claude-plugin/plugin.json", {"name": "p", "version": "0.0.2"})
        r = self.run_release("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MISMATCH", r.stdout)
        self.assertIn("v0.0.2", r.stdout)
        self.assertIn("tag v0.0.2 does not exist", r.stdout)


if __name__ == "__main__":
    unittest.main()
