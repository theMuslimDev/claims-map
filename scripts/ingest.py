#!/usr/bin/env python
"""Turn a paper file (PDF, DOCX, Markdown, plain text, or a single .tex) into section text files plus a draft config.

Usage: ingest.py FILE [--out DIR]

Writes DIR/ingested/NN_<name>.txt (one per top-level section) and DIR/claims-map.config.md. DIR defaults to
<FILE's folder>/<FILE stem>_claims_map. Anchors in the final map point at lines of these extracted text files,
not at PDF pages. PDF extraction needs `pdftotext` (poppler) or the `pypdf` package. Section detection is by
heading shape, so check the section list and roles in the config before running the skill.
"""
import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from init_config import FRONT, SKIP, make_id

KNOWN = (r"abstract|introduction|related work|background|preliminaries|methods?|methodology|approach|"
         r"experiments?|experimental setup|results?|evaluation|discussion|limitations|conclusions?|"
         r"acknowledge?ments?|references|bibliography|appendix(?: [A-Z])?")
HEADING = [
    re.compile(rf"^(?:\d+\.?|[IVX]+\.)?\s*({KNOWN})\s*$", re.I),                 # "Introduction", "1 Introduction", "II. METHODS"
    re.compile(r"^(\d{1,2})\.?\s+([A-Z][A-Za-z0-9 ,:&\-–']{2,70})$"),        # "3 Experimental Setup" (top level only)
    re.compile(r"^([IVX]{1,4})\.\s+([A-Z][A-Za-z0-9 ,:&\-']{2,70})$"),            # "IV. SIMULATION RESULTS"
]
LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "­": ""}


def clean(text):
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    return text.replace("\r", "").replace("\f", "\n")


def read_pdf(path):
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"pdftotext failed: {r.stderr.strip()}")
        return r.stdout
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("PDF input needs `pdftotext` (poppler: brew install poppler / apt install poppler-utils) or `pip install pypdf`.")
    return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)


def read_docx(path):
    """Paragraph text from word/document.xml; Heading styles become '# ' lines. Standard library only."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(f"{{{ns['w']}}}p"):
        style = p.find("w:pPr/w:pStyle", ns)
        sid = style.get(f"{{{ns['w']}}}val", "") if style is not None else ""
        text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t"))
        out.append(("# " if re.match(r"(?i)heading\s*1$|title$", sid) else "") + text)
    return "\n".join(out)


def read_any(path):
    suf = path.suffix.lower()
    if suf == ".pdf":
        return read_pdf(path)
    if suf == ".docx":
        return read_docx(path)
    if suf in (".md", ".markdown", ".txt", ".text", ".tex", ".rst"):
        return path.read_text(encoding="utf-8", errors="replace")
    sys.exit(f"unsupported file type {suf!r}: use .pdf, .docx, .md, .txt or .tex")


def heading_of(line):
    s = line.strip()
    if not s or len(s) > 80:
        return None
    if s.startswith("# "):
        return s[2:].strip()
    if re.match(r"^\\section\*?\{", s):
        return re.sub(r"^\\section\*?\{(.*?)\}.*$", r"\1", s)
    for rx in HEADING:
        m = rx.match(s)
        if m:
            return s
    return None


def tidy_title(title):
    """Undo small-caps extraction ("I NTRODUCTION" -> "INTRODUCTION") and strip the section number."""
    title = re.sub(r"^(?:\d+\.?|[IVX]+\.)\s*", "", title.strip())
    title = re.sub(r"\b([A-Z]) (?=[A-Z]{2,}\b)", r"\1", title)
    return title.title() if title.isupper() else title


def split_sections(text):
    """[(title, [lines])]; text before the first heading is the front matter."""
    sections, cur = [], ("front_matter", [])
    for line in clean(text).split("\n"):
        h = heading_of(line)
        if h:
            sections.append(cur)
            cur = (tidy_title(h) or h, [line])
        else:
            cur[1].append(line)
    sections.append(cur)
    return [(t, ls) for t, ls in sections if "".join(ls).strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--out")
    a = ap.parse_args()
    src = Path(a.file).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"not a file: {src}")
    out = Path(a.out).expanduser().resolve() if a.out else src.parent / f"{src.stem}_claims_map"
    secs = split_sections(read_any(src))
    if len(secs) < 3:
        sys.exit(f"found only {len(secs)} section(s) in {src.name}: headings were not recognised. "
                 "Convert to Markdown or LaTeX with clear headings, or split the sections by hand.")
    (out / "ingested").mkdir(parents=True, exist_ok=True)
    used, rows, after_refs = set(), [], False
    for i, (title, lines) in enumerate(secs):
        name = f"{i:02d}_{make_id(title, used)}.txt"
        (out / "ingested" / name).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        ident = Path(name).stem.split("_", 1)[1]
        is_refs = bool(re.search(r"(?i)references|bibliograph", title))
        after_refs = after_refs or is_refs
        if is_refs or SKIP.search(title):
            role = "skip"
        elif i == 0 or FRONT.search(title) or title == "front_matter":
            role = "front"
        else:
            role = "body"
        rows.append(f"  - {{id: {ident}, file: ingested/{name}, role: {role}}}")
    cfg = out / "claims-map.config.md"
    cfg.write_text(f"""# claims-map config (draft written by ingest.py from {src.name})

Sections were split by heading shape; check the list and the roles before running. front = claims are extracted
from it; body = checked against the claims; skip = ignored. Anchors point at lines of the extracted text files in
`ingested/`, not at pages of the original file. Add terminology rules under `terminology`.

```yaml
title: "{src.stem}"
paper_dir: .
output_dir: out
sections:
{chr(10).join(rows)}
terminology: []
```
""", encoding="utf-8")
    print(f"wrote {cfg}\n{len(secs)} sections found:")
    print("\n".join(r.strip("- ") for r in rows))
    print("Check that the roles are right (front = abstract, introduction, conclusion; body = the rest).")


if __name__ == "__main__":
    main()
