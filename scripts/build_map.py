#!/usr/bin/env python
"""Assemble the claims map (markdown, source of truth) from agent outputs, and enforce the anchor rule.

Usage: build_map.py CONFIG.md [SNAPSHOT_DIR]
Inputs in <output_dir>/ : claims.json, verdicts/<section-id>.json, numcheck.json (optional)
Output: <output_dir>/claims_map.md

Mechanical checks (no agent judgement involved):
  * every claim sentence must occur in the snapshot at the stated file;
  * every non-absent verdict needs an anchor whose quote occurs, whitespace-normalised, in that
    section's snapshot file. Otherwise the cell becomes `invalid-anchor` (not accepted as a verdict).
    The line number printed is computed here from the quote, not trusted from the agent.
  * claims an agent did not answer become `missing`.
  * terminology rules from the config are applied to every snapshot file (lint).
"""
import json
import re
import sys
from pathlib import Path

from cm_common import latest_snapshot, load_config, norm_ws, strip_tex_comment, tex_to_text

VERDICTS = {"anchored", "partial", "differs", "absent", "external"}


class Doc:
    """Whitespace-normalised text of a snapshot file with a char-to-line map."""

    def __init__(self, path):
        chars, lines, prev_space = [], [], True
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for ch in line + "\n":
                if ch.isspace():
                    if prev_space:
                        continue
                    ch, prev_space = " ", True
                else:
                    prev_space = False
                chars.append(ch)
                lines.append(ln)
        self.text, self.lines = "".join(chars), lines

    def find(self, quote):
        q = norm_ws(quote)
        i = self.text.find(q) if q else -1
        return self.lines[i] if i >= 0 else None


STOP = set("the a an of and or to in on for with by is are was were be as at from that this it its we our which than "
           "then not no each per into over under using can may also has have had one two all any both such their these those".split())
STEM = 4  # words are compared on their first 4 letters, so "leaks"/"leakage" match; lenient on purpose, since this only flags


def content_stems(text):
    """Content tokens of a claim or quote: words, acronyms (also inside \\ac{..}), numbers, math symbol names.

    TeX comments, citation and reference commands are dropped; other macro names are kept as words, so
    \\sigma and \\max count as content (they name the quantity). \\ac{zf} becomes the token ZF.
    """
    t = strip_tex_comment(text)
    t = re.sub(r"\\(?:cite|ref|eqref|label|cref|Cref)\w*\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\\ac[a-z]*\{([^}]*)\}", lambda m: " " + m.group(1).upper() + " ", t)
    toks = re.findall(r"[A-Z]{2,}|[A-Za-z]{3,}|\d+(?:\.\d+)?", t)
    return {x.lower()[:STEM] for x in toks if x.lower() not in STOP and x.lower() not in TEX_NOISE}


# macro names that carry no meaning for relevance (formatting, math scaffolding)
TEX_NOISE = set("mathbf mathcal mathrm mathsf mathbb frac left right begin end text textbf emph quad qquad dots cdot ldots "
                "tilde hat star label item section subsection paragraph".split())


def weak_anchor(claim_sentence, quote):
    """True when claim and anchor share no content token: the quote exists but may be irrelevant."""
    return not (content_stems(claim_sentence) & content_stems(quote))


def cell_md(v):
    return v["verdict"] if v["verdict"] != "external" else "external, unverified"


def main():
    cfg = load_config(sys.argv[1])
    snap = Path(sys.argv[2]) if len(sys.argv) > 2 else latest_snapshot(cfg)
    out = snap.parent
    man = json.loads((snap / "MANIFEST.json").read_text())
    docs = {s["file"]: Doc(snap / "resolved" / s["file"]) for s in cfg["sections"]}
    body = [s for s in cfg["sections"] if s.get("role") == "body"]
    if not (out / "claims.json").exists():
        sys.exit(f"{out / 'claims.json'} not found: run the extractor agent first")
    claims = json.loads((out / "claims.json").read_text())

    # claim validation
    for c in claims:
        d = docs.get(c.get("file"))
        line = d.find(c["sentence"]) if d else None
        c["line"] = line
        c["sentence_ok"] = line is not None

    # verdict validation
    cells, unclaimed, invalid = {}, [], []
    for s in body:
        vp = out / "verdicts" / f"{s['id']}.json"
        data = json.loads(vp.read_text()) if vp.exists() else {"verdicts": [], "unclaimed": []}
        got = {v["claim"]: v for v in data["verdicts"]}
        for c in claims:
            v = got.get(c["id"])
            if v is None:
                cells[(c["id"], s["id"])] = {"verdict": "missing"}
                continue
            if v["verdict"] not in VERDICTS:
                cells[(c["id"], s["id"])] = {"verdict": "invalid-verdict", "note": v["verdict"]}
                continue
            if v["verdict"] == "absent":
                cells[(c["id"], s["id"])] = {"verdict": "absent"}
                continue
            a = v.get("anchor") or {}
            line = docs[s["file"]].find(a.get("quote", ""))
            if line is None:
                cells[(c["id"], s["id"])] = {"verdict": "invalid-anchor", "claimed": v["verdict"], "quote": a.get("quote", "")}
                invalid.append((c["id"], s["id"]))
            else:
                cells[(c["id"], s["id"])] = {"verdict": v["verdict"], "file": s["file"], "line": line, "quote": norm_ws(a["quote"]),
                                             "weak": weak_anchor(c["sentence"], a["quote"])}
        for u in data.get("unclaimed", []):
            line = docs[s["file"]].find(u.get("quote", ""))
            u = dict(u, section=s["id"], file=s["file"], line=line, quote_ok=line is not None)
            unclaimed.append(u)

    # lint
    lint = []
    for rule in cfg.get("terminology", []):
        rx = re.compile(rule["pattern"], 0 if rule.get("case_sensitive", True) else re.I)
        for s in cfg["sections"]:
            if s.get("role") == "skip":
                continue
            for ln, line in enumerate((snap / "resolved" / s["file"]).read_text().splitlines(), 1):
                t = tex_to_text(line) if not rule.get("raw") else strip_tex_comment(line)
                for m in rx.finditer(t):
                    lint.append({"rule": rule["id"], "message": rule["message"], "file": s["file"], "line": ln, "hit": m.group(0)})

    nc = json.loads((out / "numcheck.json").read_text()) if (out / "numcheck.json").exists() else None

    L = []
    w = L.append
    w(f"# Claims map: {cfg.get('title', 'paper')}")
    w("")
    w("This is a consistency map, not a correctness check. A cell says whether a section states the same thing as a claim, with a quoted anchor. It never says a claim is right or wrong. References are external and unverified.")
    w("")
    w(f"- snapshot: `{snap.name}`")
    w(f"- git commit: `{man['commit'][:10]}` on `{man['branch']}`; dirty tree: **{'yes' if man['dirty_tree'] else 'no'}** ({man['dirty_entries_under_paper_dir']} entries under the paper directory)")
    w("")
    w("| file | role | sha256 (first 12) | git state |")
    w("|---|---|---|---|")
    role = {s["file"]: s.get("role", "") for s in cfg["sections"]}
    for f in man["files"]:
        w(f"| `{f['file']}` | {role.get(f['file'], 'support')} | `{f['sha256'][:12]}` | {f['git_status']} |")
    w("")

    def row_cells(c):
        return [cells[(c["id"], s["id"])] for s in body]

    absent_every = [c for c in claims if all(v["verdict"] == "absent" for v in row_cells(c))]
    # citation claims are supported by their reference, so a body section is not expected to restate them
    absent_all = [c for c in absent_every if c["type"] != "citation"]
    absent_cites = [c for c in absent_every if c["type"] == "citation"]
    weak = [(c["id"], s["id"]) for c in claims for s in body if cells[(c["id"], s["id"])].get("weak")]
    counts = {}
    for v in cells.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    w("## Summary")
    w("")
    w(f"- claims extracted: {len(claims)}; body sections checked: {', '.join(s['id'] for s in body)}")
    w("- cells by verdict: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())))
    w(f"- claims absent from every body section: **{len(absent_all)}**")
    w(f"- citation claims with no body anchor (listed separately, expected for literature review): {len(absent_cites)}")
    w(f"- unclaimed strong statements: {len(unclaimed)}")
    if weak:
        w(f"- anchors sharing no content word with their claim (check relevance): {len(weak)}")
    if invalid:
        w(f"- cells rejected because the quoted anchor was not found in the snapshot: {len(invalid)}")
    w("")
    w("## Claims absent from every body section")
    w("")
    if absent_all:
        for c in absent_all:
            w(f"- **{c['id']}** ({c['type']}, {c['location']}): {norm_ws(c['sentence'])}")
    else:
        w("None.")
    w("")
    w("## Citation claims with no body anchor")
    w("")
    w("The support for these is a cited work, which this skill cannot read. Listed apart so they do not bury the headline list.")
    w("")
    for c in absent_cites:
        w(f"- **{c['id']}** ({c['location']}): {norm_ws(c['sentence'])}")
    if not absent_cites:
        w("None.")
    w("")
    w("## Matrix")
    w("")
    w("| id | type | where claimed | claim | " + " | ".join(s["id"] for s in body) + " |")
    w("|---|---|---|---|" + "---|" * len(body))
    for c in claims:
        short = norm_ws(c["sentence"])
        short = short if len(short) <= 110 else short[:107] + "..."
        flag = "" if c["sentence_ok"] else " (sentence not found in snapshot)"
        w(f"| {c['id']} | {c['type']} | {c['location']} | {short.replace('|', '/')}{flag} | " + " | ".join(cell_md(v) + (" (weak anchor)" if v.get("weak") else "") for v in row_cells(c)) + " |")
    w("")
    w("## Claim detail")
    w("")
    for c in claims:
        w(f"### {c['id']} · {c['type']} · {c['location']}")
        w("")
        w(f"> {norm_ws(c['sentence'])}")
        w("")
        for s in body:
            v = cells[(c["id"], s["id"])]
            if v["verdict"] in ("absent", "missing"):
                w(f"- `{s['id']}` **{v['verdict']}**: no anchor in this section" if v["verdict"] == "absent" else f"- `{s['id']}` **missing**: agent gave no answer")
            elif v["verdict"] == "invalid-anchor":
                w(f"- `{s['id']}` **invalid-anchor** (agent said {v['claimed']}): quote not found in snapshot: \"{v['quote']}\"")
            elif v["verdict"] == "invalid-verdict":
                w(f"- `{s['id']}` **invalid-verdict**: {v['note']}")
            else:
                mark = " · **weak anchor: no shared content word with the claim**" if v.get("weak") else ""
                w(f"- `{s['id']}` **{cell_md(v)}** · `{v['file']}:{v['line']}` · \"{v['quote']}\"{mark}")
        w("")
    w("## Unclaimed strong statements")
    w("")
    w("Numeric, comparative or causal statements in a body section that match no extracted claim. A prompt to look, not a defect list.")
    w("")
    if unclaimed:
        w("| section | type | location | quote |")
        w("|---|---|---|---|")
        for u in unclaimed:
            loc = f"`{u['file']}:{u['line']}`" if u["quote_ok"] else "quote not found in snapshot"
            w(f"| {u['section']} | {u.get('type', '')} | {loc} | {norm_ws(u.get('quote', '')).replace('|', '/')} |")
    else:
        w("None.")
    w("")
    w("## Number check")
    w("")
    if nc is None:
        w("Not run.")
    else:
        w(f"Numbers scanned: {nc['numbers_scanned']}. Equal pairs across sections: {nc['equal_pairs']}. Listed below: pairs with the same unit and shared context words whose values differ. `rounding` means they agree at the coarser precision; `conflict` means they do not.")
        w("")
        if nc["findings"]:
            w("| class | a | b | shared words |")
            w("|---|---|---|---|")
            for f in nc["findings"]:
                a, b = f["a"], f["b"]
                w(f"| {f['class']} | `{a['file']}:{a['line']}` {a['number']}{a['unit']} | `{b['file']}:{b['line']}` {b['number']}{b['unit']} | {', '.join(f['shared_words'])} |")
        else:
            w("No differing pairs.")
    w("")
    w("## Terminology lint")
    w("")
    w("Rules from the config, applied to every snapshot file.")
    w("")
    if lint:
        w("| rule | location | hit |")
        w("|---|---|---|")
        for h in lint:
            w(f"| {h['rule']} | `{h['file']}:{h['line']}` | `{h['hit']}` |")
    else:
        w("No hits.")
    w("")
    (out / "claims_map.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out / 'claims_map.md'}: {len(claims)} claims, absent-everywhere {len(absent_all)} (+{len(absent_cites)} citation), weak anchors {len(weak)}, invalid anchors {len(invalid)}, unclaimed {len(unclaimed)}, lint hits {len(lint)}")


if __name__ == "__main__":
    main()
