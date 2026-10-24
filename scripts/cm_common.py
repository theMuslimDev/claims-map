"""Shared helpers for the claims-map scripts: config loading and light TeX text handling."""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


def load_config(path):
    """Read the first ```yaml fenced block of a claims-map config markdown file."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(.*?)\n```", text, re.S)
    if not m:
        sys.exit(f"no ```yaml block in {path}")
    cfg = yaml.safe_load(m.group(1))
    missing = [k for k in ("paper_dir", "output_dir", "sections") if k not in cfg]
    if missing:
        sys.exit(f"config {path} is missing required keys: {', '.join(missing)}")
    cfg["_config_path"] = str(Path(path).resolve())
    paper = Path(cfg["paper_dir"]).expanduser()
    if not paper.is_absolute():
        paper = (Path(path).resolve().parent / paper).resolve()
    cfg["_paper"] = paper
    out = Path(cfg["output_dir"]).expanduser()
    cfg["_out"] = out if out.is_absolute() else (paper / out)
    return cfg


def latest_snapshot(cfg):
    snaps = sorted(p for p in cfg["_out"].glob("snapshot_*") if p.is_dir())
    if not snaps:
        sys.exit("no snapshot yet: run snapshot.py first")
    return snaps[-1]


def strip_tex_comment(line):
    """Drop an unescaped % comment from one line."""
    return re.sub(r"(?<!\\)%.*$", "", line)


def tex_to_text(line):
    """Crude TeX-to-text for number and keyword scanning (not for display)."""
    s = strip_tex_comment(line)
    s = re.sub(r"\\(?:cite|ref|eqref|label|cref|Cref|autoref)\w*\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", s)
    s = re.sub(r"\\(?:ac|acp|acs|acl|acf)\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", s)
    s = s.replace("~", " ").replace("\\%", "%").replace("\\,", " ")
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = re.sub(r"[{}$]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()
