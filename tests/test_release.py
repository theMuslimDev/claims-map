"""release.py in a temporary git repo: dry run, refusals, bump, changelog, --check."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
CHANGELOG = "# Changelog\n\n## Unreleased\n- Fixed a thing.\n\n## v0.0.1 (experimental)\n- First.\n"


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

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, data):
        (self.repo / rel).write_text(json.dumps(data, indent=2) + "\n")

    def read(self, rel):
        return json.loads((self.repo / rel).read_text())

    def run_release(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              capture_output=True, text=True)

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
        self.assertEqual(self.run_release("--check").returncode, 0)

    def test_check_flags_ref_mismatch(self):
        self.write(".claude-plugin/plugin.json", {"name": "p", "version": "0.0.2"})
        r = self.run_release("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MISMATCH", r.stdout)
        self.assertIn("v0.0.2", r.stdout)
        self.assertIn("tag v0.0.2 does not exist", r.stdout)


if __name__ == "__main__":
    unittest.main()
