"""Regenerate the sample output shown in USAGE.md from a throwaway copy of the toy paper.

`python tests/usage_samples.py` rewrites the golden files in examples/toy-paper/expected/usage/.
Volatile parts (temp paths, snapshot timestamps, commit hashes) are replaced deterministically.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TOY = ROOT / "examples" / "toy-paper"
GOLDEN = TOY / "expected" / "usage"
NAMES = ["ingest", "snapshot_dirty", "numcheck", "build_map", "listing", "summary", "matrix"]
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def run(cmd, cwd, both=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=GIT_ENV)
    assert r.returncode == 0, f"{cmd} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout + r.stderr if both else r.stdout


def script(name, *args, cwd, both=False):
    return run([sys.executable, str(SCRIPTS / name), *map(str, args)], cwd, both)


def git_repo(path, files):
    for cmd in (["init", "-q", "-b", "main"], ["add", *files], ["commit", "-qm", "init"]):
        run(["git", *cmd], path)


def clean(text, *roots):
    for root in roots:
        text = text.replace(str(root.resolve()), "/path/to/paper").replace(str(root), "/path/to/paper")
    text = re.sub(r"snapshot_\d{8}T\d{6}Z", "snapshot_<timestamp>", text)
    text = re.sub(r"`[0-9a-f]{10}` on", "`<commit>` on", text)
    return text.strip("\n") + "\n"


def wrap(text, width=80):
    """Wrap long lines for display (markdownlint line length); continuation lines are indented."""
    lines = [textwrap.fill(ln, width, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)
             if len(ln) > width else ln for ln in text.split("\n")]
    return "\n".join(lines)


def table(text):
    """The matrix is shown as a rendered table; markdownlint wants `| --- |` separators."""
    return re.sub(r"^\|(?:-+\|)+$", lambda m: "| " + " | ".join("---" for _ in m.group(0).strip("|").split("|")) + " |",
                  text, flags=re.M)


def section(text, heading):
    m = re.search(rf"^## {heading}\n\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
    return m.group(1).strip("\n") + "\n"


def generate():
    """Return {name: snippet text} for every sample in USAGE.md."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # ingest: a plain LaTeX file in, a draft config out
        ing = tmp / "ingest"
        ing.mkdir()
        shutil.copy(ROOT / "tests" / "fixtures" / "toy-paper.tex", ing)
        out["ingest"] = clean(script("ingest.py", ing / "toy-paper.tex", cwd=ing), ing)
        # snapshot of a tree with an uncommitted edit
        dirty = tmp / "dirty"
        shutil.copytree(TOY, dirty, ignore=shutil.ignore_patterns("expected", "out", "ledger.example.md"))
        git_repo(dirty, ["."])
        with open(dirty / "sections" / "03_results.tex", "a", encoding="utf-8") as f:
            f.write("\n")
        out["snapshot_dirty"] = clean(script("snapshot.py", dirty / "claims-map.config.md", cwd=dirty, both=True), dirty)
        # the full scripted run on a clean copy
        paper = tmp / "paper"
        shutil.copytree(TOY, paper, ignore=shutil.ignore_patterns("expected", "out", "ledger.example.md"))
        (paper / ".gitignore").write_text("out/\n")
        git_repo(paper, ["."])
        cfg = paper / "claims-map.config.md"
        snap = Path(script("snapshot.py", cfg, cwd=paper).strip())
        shutil.copy(TOY / "claims.json", snap.parent / "claims.json")
        shutil.copytree(TOY / "verdicts", snap.parent / "verdicts")
        out["numcheck"] = clean(script("numcheck.py", cfg, cwd=paper), paper)
        out["build_map"] = clean(script("build_map.py", cfg, cwd=paper), paper)
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in snap.parent.iterdir())
        names = [n if not n.startswith("snapshot_") else "snapshot_<timestamp>/" for n in names]
        out["listing"] = "out/\n" + "".join(f"  {n}\n" for n in names)
        md = (snap.parent / "claims_map.md").read_text(encoding="utf-8")
        out["summary"] = clean(section(md, "Summary"))
        out["matrix"] = table(clean(section(md, "Matrix")))
    return {k: v if k == "matrix" else wrap(v.rstrip("\n")) + "\n" for k, v in out.items()}


if __name__ == "__main__":
    GOLDEN.mkdir(parents=True, exist_ok=True)
    for name, text in generate().items():
        (GOLDEN / f"{name}.txt").write_text(text, encoding="utf-8")
        print("wrote", GOLDEN / f"{name}.txt")
