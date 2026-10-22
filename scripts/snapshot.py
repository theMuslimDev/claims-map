#!/usr/bin/env python
"""Step 1 of claims-map: copy the paper's files to a scratch snapshot and record provenance.

Usage: snapshot.py CONFIG.md [--ref REF]
Writes <output_dir>/snapshot_<UTC>/{raw,resolved}/ and MANIFEST.json. Read-only on the paper:
git is queried with --no-optional-locks, nothing in the working tree is touched.
By default the files are copied from the working tree, so uncommitted edits are included; files that differ
from the commit are listed as a warning and marked in the map. `--ref REF` (for example HEAD) copies the
committed content instead, read-only through `git show`, and ignores uncommitted edits.
raw/       byte-exact copies (hashed)
resolved/  same files with number macros expanded (so agents and scripts see the numbers); line
           numbers match raw/ because only inline text is substituted.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys

from cm_common import load_config


def git(paper, *args):
    r = subprocess.run(["git", "--no-optional-locks", "-C", str(paper), *args],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def main(cfg_path, ref=None):
    cfg = load_config(cfg_path)
    paper = cfg["_paper"]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap = cfg["_out"] / f"snapshot_{stamp}"
    (snap / "raw").mkdir(parents=True)
    (snap / "resolved").mkdir()

    macros = {}
    nm = cfg.get("number_macros")
    if nm:
        defs = (paper / nm["definitions_file"]).read_text(encoding="utf-8")
        macros = {k: v for k, v in re.findall(nm["definition_regex"], defs)}
    files = [s["file"] for s in cfg["sections"]] + list(cfg.get("support_files", []))
    manifest_files = []
    for rel in files:
        if not (paper / rel).is_file():
            sys.exit(f"configured file not found: {paper / rel}")
        if ref:
            r = subprocess.run(["git", "--no-optional-locks", "-C", str(paper), "show", f"{ref}:./{rel}"], capture_output=True)
            if r.returncode != 0:
                sys.exit(f"{rel} is not in {ref}: {r.stderr.decode(errors='replace').strip()}")
            data = r.stdout
        else:
            data = (paper / rel).read_bytes()
        dst = snap / "raw" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        text = data.decode("utf-8")
        missing = []
        if nm:
            def sub(m):
                key = m.group(1)
                if key not in macros:
                    missing.append(key)
                    return m.group(0)
                return macros[key]
            text = "\n".join(
                ln if ln.lstrip().startswith("%") else re.sub(r"\\" + nm["macro"] + r"\{([^}]*)\}", sub, ln)
                for ln in text.split("\n"))
        for name in cfg.get("unwrap_macros", []):
            text = re.sub(r"\\" + name + r"\{([^{}]*)\}", r"\1", text)
        dst2 = snap / "resolved" / rel
        dst2.parent.mkdir(parents=True, exist_ok=True)
        dst2.write_text(text, encoding="utf-8")
        state = "" if ref else git(paper, "status", "--porcelain", "--", rel)
        manifest_files.append({
            "file": rel, "sha256": hashlib.sha256(data).hexdigest(),
            "git_status": state[:2] if state else "clean", "unresolved_macros": missing,
        })
    status = "" if ref else git(paper, "status", "--porcelain", "--", ".")
    modified = [f["file"] for f in manifest_files if f["git_status"] != "clean"]
    if modified:
        print("warning: snapshot taken from the working tree; these files differ from the commit: " + ", ".join(modified)
              + ". Use --ref HEAD to snapshot the committed content instead.", file=sys.stderr)
    for f in manifest_files:
        if f["unresolved_macros"]:
            print(f"warning: {f['file']}: number macro keys not found in the definitions file: "
                  + ", ".join(f["unresolved_macros"][:5]) + " (check number_macros in the config)", file=sys.stderr)
    manifest = {
        "created_utc": stamp, "paper_dir": str(paper), "config": cfg["_config_path"],
        "commit": git(paper, "rev-parse", "HEAD"), "branch": git(paper, "rev-parse", "--abbrev-ref", "HEAD"),
        "ref": ref, "dirty_tree": bool(status), "dirty_entries_under_paper_dir": len(status.splitlines()),
        "files": manifest_files,
    }
    (snap / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(snap)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config")
    ap.add_argument("--ref", help="snapshot the committed content at this git ref (e.g. HEAD) instead of the working tree")
    a = ap.parse_args()
    main(a.config, a.ref)
