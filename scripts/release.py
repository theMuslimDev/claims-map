#!/usr/bin/env python3
"""Cut a release: bump the version, date the changelog, pin the marketplace.

Dry run by default. `--apply` makes the release commit, `--tag` (with
`--apply`) also creates the annotated tag. Nothing is ever pushed.
`--check` verifies that plugin.json, the marketplace pin and the tag agree.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = ".claude-plugin/plugin.json"
MARKET = ".claude-plugin/marketplace.json"
CHANGELOG = "CHANGELOG.md"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class Refuse(Exception):
    pass


def git(root, *args, check=True):
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if check and p.returncode:
        raise Refuse("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def load(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def pinned_entry(market, name):
    for plugin in market.get("plugins", []):
        if plugin.get("name") == name:
            return plugin
    raise Refuse("no plugin named %r in %s" % (name, MARKET))


def tag_exists(root, tag):
    return subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/" + tag],
                          cwd=root, capture_output=True).returncode == 0


def check(root):
    """Return a list of problems; empty means plugin.json, pin and tag agree."""
    plugin = load(root, PLUGIN)
    version = plugin["version"]
    source = pinned_entry(load(root, MARKET), plugin["name"]).get("source")
    ref = source.get("ref") if isinstance(source, dict) else None
    problems = []
    if ref != "v" + version:
        problems.append("marketplace ref is %r but plugin.json version is %s (want v%s)"
                        % (ref, version, version))
    if not tag_exists(root, "v" + version):
        problems.append("tag v%s does not exist" % version)
    return problems


def bump_changelog(text, version, today):
    m = re.search(r"^## Unreleased[ \t]*\n", text, re.M)
    if not m:
        raise Refuse("CHANGELOG.md has no '## Unreleased' heading")
    body = text[m.end():]
    nxt = re.search(r"^## ", body, re.M)
    if not (body[:nxt.start()] if nxt else body).strip():
        raise Refuse("the Unreleased section of CHANGELOG.md is empty")
    return (text[:m.start()] + "## Unreleased\n\n## v%s (%s)\n" % (version, today)
            + text[m.end():])


def preflight(root, version):
    if not VERSION_RE.match(version):
        raise Refuse("version must look like 1.2.3, got %r" % version)
    if git(root, "rev-parse", "--abbrev-ref", "HEAD") != "main":
        raise Refuse("not on branch main")
    if git(root, "status", "--porcelain"):
        raise Refuse("working tree is not clean")
    current = load(root, PLUGIN)["version"]
    if tuple(map(int, version.split("."))) <= tuple(map(int, current.split("."))):
        raise Refuse("version %s is not greater than the current %s" % (version, current))
    if tag_exists(root, "v" + version):
        raise Refuse("tag v%s already exists" % version)
    bump_changelog((root / CHANGELOG).read_text(encoding="utf-8"), version, "x")


def run_checks(root):
    steps = [
        ("unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]),
        ("ruff", ["ruff", "check", "scripts", "tests"]),
        ("plugin validate", ["claude", "plugin", "validate", "."]),
    ]
    mdl = shutil.which("markdownlint-cli2")
    if mdl:
        files = git(root, "ls-files", "*.md").split("\n")
        steps.append(("markdownlint", [mdl, *files]))
    else:
        print("note: markdownlint-cli2 not found, skipping markdownlint")
    for name, cmd in steps:
        print("check: %s" % name)
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        except FileNotFoundError:
            raise Refuse("%s is not installed" % cmd[0])
        if p.returncode:
            raise Refuse("check failed: %s\n%s%s" % (name, p.stdout, p.stderr))


def release(root, version, apply, tag, skip_checks, trailer):
    preflight(root, version)
    today = datetime.date.today().isoformat()
    verb = "" if apply else "would "
    if skip_checks:
        print("note: checks skipped")
    else:
        run_checks(root)
    print("%sset plugin.json version to %s" % (verb, version))
    print("%sset the marketplace ref to v%s" % (verb, version))
    print("%srename '## Unreleased' to '## v%s (%s)' and add a new empty Unreleased"
          % (verb, version, today))
    print("%smake one commit: release: v%s" % (verb, version))
    if tag:
        print("%screate the tag v%s" % (verb, version))
    else:
        print("not creating a tag (add --tag)")
    print("never pushes")
    if not apply:
        print("dry run: nothing changed (use --apply to do it)")
        return
    path = root / PLUGIN
    path.write_text(json.dumps(dict(load(root, PLUGIN), version=version), indent=2) + "\n",
                    encoding="utf-8")
    market = load(root, MARKET)
    name = load(root, PLUGIN)["name"]
    source = pinned_entry(market, name)["source"]
    if not isinstance(source, dict):
        raise Refuse("marketplace source is not a git source object; cannot set ref")
    source["ref"] = "v" + version
    (root / MARKET).write_text(json.dumps(market, indent=2) + "\n", encoding="utf-8")
    cl = root / CHANGELOG
    cl.write_text(bump_changelog(cl.read_text(encoding="utf-8"), version, today),
                  encoding="utf-8")
    message = "release: v" + version + ("\n\n" + trailer if trailer else "")
    git(root, "add", PLUGIN, MARKET, CHANGELOG)
    git(root, "commit", "-q", "-m", message)
    print("committed release: v%s" % version)
    if tag:
        git(root, "tag", "-a", "v" + version, "-m", "claims-map v" + version)
        print("tagged v%s" % version)
    print("not pushed: push main and the tag yourself when asked")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("version", nargs="?", help="new version, e.g. 0.1.0")
    ap.add_argument("--apply", action="store_true", help="make the release commit (default is a dry run)")
    ap.add_argument("--tag", action="store_true", help="also create the tag (needs --apply to take effect)")
    ap.add_argument("--check", action="store_true", help="verify plugin.json version, marketplace ref and tag agree")
    ap.add_argument("--skip-checks", action="store_true", help="skip unittest, ruff, validate and markdownlint (for tests)")
    ap.add_argument("--trailer", help="trailer line to append to the release commit message")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = Path(args.repo)
    try:
        if args.check:
            problems = check(root)
            for p in problems:
                print("MISMATCH: " + p)
            if not problems:
                print("ok: plugin.json, marketplace ref and tag agree")
            return 1 if problems else 0
        if not args.version:
            ap.error("version is required (or use --check)")
        release(root, args.version, args.apply, args.tag, args.skip_checks, args.trailer)
    except Refuse as e:
        print("refused: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
