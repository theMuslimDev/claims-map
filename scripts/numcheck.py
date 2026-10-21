#!/usr/bin/env python
"""Number check (a script, not an agent): compare numbers for the same quantity across sections.

Usage: numcheck.py CONFIG.md [SNAPSHOT_DIR]
Reads snapshot/resolved/*, writes <snapshot>/../numcheck.json.
Two numbers are treated as the same quantity when they have the same unit and their surrounding
words share at least `min_shared_words` content words (unitless numbers are paired only when within 5%; one shared word is enough
when the values are within 5%, since a near-miss with the same unit is worth listing on its own).
Context is the sentence containing the number. Classes:
  equal     identical value
  rounding  differs but agrees once the more precise one is rounded to the precision of the other
  conflict  differs by more than rounding
Only rounding and conflict pairs are listed; a human decides what they mean. Heuristic: it can
miss quantities whose context words differ, and can pair unrelated numbers that share words.
"""
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path

from cm_common import latest_snapshot, load_config, strip_tex_comment, tex_to_text

# Constants: NEAR is the relative gap under which two same-unit numbers are suspicious on their own
# (a 5% gap covers rounding and small edits); CONTEXT_CHARS is how much sentence text is kept per hit.
NEAR = Decimal("0.05")
CONTEXT_CHARS = 200
UNITS = r"(ms|us|dB|dBi|dBm|GHz|MHz|%|deg|degrees|x|times|s|W|mW)"
NUM = re.compile(r"(?<![\w.\\])(\d+(?:\.\d+)?)(?:\s*(?:\^\\circ|\^\{\\circ\}|\\circ))?\s*" + UNITS + r"?(?![\w])")
STOP = set("the a an of and or to in on for with by is are was were be as at from that this it its we our "
           "which than then not no each per into over under using use used can may also has have had one two "
           "all any both such their these those only more less most least between across while when where".split())


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def rounds_to(fine, coarse):
    q = Decimal(1).scaleb(-decimals(coarse))
    return Decimal(fine).quantize(q, rounding=ROUND_HALF_UP) == Decimal(coarse)


def sentences(path):
    """Yield (sentence_text, [(start, end, line)...]) with sentence text built from TeX-stripped lines."""
    text, line_of = [], []
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        t = tex_to_text(line) if strip_tex_comment(line).strip() else ""
        if not t:
            text.append("\n")
            line_of.extend([ln])
            continue
        text.append(t + " ")
        line_of.extend([ln] * (len(t) + 1))
    joined = "".join(text)
    pos = 0
    for para in re.split(r"\n+", joined):
        base = joined.index(para, pos) if para else pos
        pos = base + len(para)
        start = 0
        for m in list(re.finditer(r"(?<=[.!?])\s+(?=[A-Z])", para)) + [None]:
            end = m.start() if m else len(para)
            if para[start:end].strip():
                yield para[start:end], base + start, line_of
            start = m.end() if m else len(para)


def collect(snap, cfg, scope):
    items = []
    for sec in cfg["sections"]:
        if sec["id"] not in scope:
            continue
        for sent, off, line_of in sentences(snap / "resolved" / sec["file"]):
            words = sorted({w for w in re.findall(r"[a-z]{3,}", sent.lower()) if w not in STOP})
            for m in NUM.finditer(sent):
                num, unit = m.group(1), m.group(2) or ""
                if not unit and len(num) < 2 and "." not in num:
                    continue  # lone digits are mostly counts, indices, equation labels
                items.append({"section": sec["id"], "file": sec["file"], "line": line_of[min(off + m.start(), len(line_of) - 1)],
                              "number": num, "unit": unit, "words": words, "context": sent[:CONTEXT_CHARS]})
    return items


def main():
    cfg = load_config(sys.argv[1])
    snap = Path(sys.argv[2]) if len(sys.argv) > 2 else latest_snapshot(cfg)
    nc = cfg.get("numcheck", {})
    scope = set(nc.get("sections", [s["id"] for s in cfg["sections"]]))
    min_shared = nc.get("min_shared_words", 2)
    tol = Decimal(str(nc.get("conflict_rel_tol", 0.5)))  # farther apart than this: treated as unrelated
    items = collect(snap, cfg, scope)
    out, equal, seen = [], 0, set()
    for a, b in combinations(items, 2):
        if a["section"] == b["section"] or a["unit"] != b["unit"]:
            continue
        shared = sorted(set(a["words"]) & set(b["words"]))
        x, y = Decimal(a["number"]), Decimal(b["number"])
        near = x != 0 and y != 0 and abs(x - y) / max(abs(x), abs(y)) <= NEAR
        if not a["unit"] and not near:
            continue  # unitless numbers are only paired when they are near-misses
        need = 1 if near and a["unit"] else (min_shared if a["unit"] else min_shared + 1)
        if len(shared) < need:
            continue
        if x == y:
            equal += 1
            continue
        if x == 0 or y == 0 or abs(x - y) / max(abs(x), abs(y)) > tol:
            continue
        fine, coarse = (a, b) if decimals(a["number"]) >= decimals(b["number"]) else (b, a)
        cls = "rounding" if rounds_to(fine["number"], coarse["number"]) else "conflict"
        keep = ("section", "file", "line", "number", "unit", "context")
        key = (cls, a["file"], a["line"], a["number"], b["file"], b["line"], b["number"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"class": cls, "shared_words": shared[:6],
                    "a": {k: a[k] for k in keep}, "b": {k: b[k] for k in keep}})
    res = {"numbers_scanned": len(items), "equal_pairs": equal, "findings": out}
    (snap.parent / "numcheck.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"scanned {len(items)} numbers; equal pairs {equal}; "
          f"rounding {sum(f['class'] == 'rounding' for f in out)}; conflict {sum(f['class'] == 'conflict' for f in out)}")


if __name__ == "__main__":
    main()
