#!/usr/bin/env python
"""Write a first-draft claims-map config for a LaTeX paper folder.

Usage: init_config.py PAPER_DIR [--out CONFIG.md]

Finds the main .tex file (the one with \\documentclass), reads the order of its \\input / \\include
files, and guesses roles from file names: abstract, introduction, conclusion -> front; acronyms,
biography, bibliography, numbers, captions -> skip; everything else -> body. Review the draft before
running the skill: the guess is by file name only. The config goes to PAPER_DIR/claims_map/ by
default (add that folder to .gitignore; it also receives the snapshots and the map).
"""
import argparse
import re
import sys
from pathlib import Path

FRONT = re.compile(r"abstract|intro|conclu|summary", re.I)
SKIP = re.compile(r"acronym|biograph|bibliograph|reference|macro|number|caption|preamble|notation|glossary|title", re.I)


def input_order(main):
    """Files named by \\input{..} / \\include{..} in the main file, in order, comments removed."""
    text = "\n".join(re.sub(r"(?<!\\)%.*$", "", ln) for ln in main.read_text(encoding="utf-8", errors="replace").splitlines())
    names = re.findall(r"\\(?:input|include)\{([^}]+)\}", text)
    return [n if n.endswith(".tex") else n + ".tex" for n in names]


def make_id(path, used):
    stem = re.sub(r"^[\d_\-\s]+", "", Path(path).stem) or Path(path).stem
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()[:24] or "section"
    base, n = stem, 2
    while stem in used:
        stem, n = f"{base}{n}", n + 1
    used.add(stem)
    return stem


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paper_dir")
    ap.add_argument("--out", help="config path (default PAPER_DIR/claims_map/claims-map.config.md)")
    args = ap.parse_args()
    paper = Path(args.paper_dir).expanduser().resolve()
    if not paper.is_dir():
        sys.exit(f"not a folder: {paper}")
    mains = [p for p in sorted(paper.glob("*.tex")) if "\\documentclass" in p.read_text(encoding="utf-8", errors="replace")]
    if mains:
        order = [n for n in input_order(mains[0]) if (paper / n).is_file()]
        note = f"order read from {mains[0].name}"
    else:
        order, note = [], "no main .tex with \\documentclass found; using sorted file names"
    if not order:
        order = [str(p.relative_to(paper)) for p in sorted(paper.rglob("*.tex"))
                 if "claims_map" not in p.parts and "out" not in p.parts]
    if not order:
        sys.exit(f"no .tex files found under {paper}")
    used, rows = set(), []
    for rel in order:
        role = "skip" if SKIP.search(Path(rel).name) else "front" if FRONT.search(Path(rel).name) else "body"
        rows.append(f"  - {{id: {make_id(rel, used)}, file: {rel}, role: {role}}}")
    cfg = Path(args.out).expanduser() if args.out else paper / "claims_map" / "claims-map.config.md"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    rel_paper = Path(__import__("os").path.relpath(paper, cfg.parent.resolve())).as_posix()
    cfg.write_text(f"""# claims-map config (draft written by init_config.py; {note})

Review the roles below before running. front = claims are extracted from it; body = checked against the
claims; skip = ignored. Add your terminology rules under `terminology` (see claims-map.config.template.md).

```yaml
title: "{paper.name}"
paper_dir: {rel_paper}
output_dir: {cfg.parent.relative_to(paper).as_posix() if cfg.parent.resolve().is_relative_to(paper) else cfg.parent}
sections:
{chr(10).join(rows)}
terminology: []
```
""", encoding="utf-8")
    print(f"wrote {cfg}\n{note}\nroles guessed from file names; open the file and fix any that are wrong.")
    print("Add the output folder to .gitignore so snapshots and the map are not committed.")


if __name__ == "__main__":
    main()
