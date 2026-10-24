"""Claim ledger and briefing: one status per claim, computed from anchor-checked cells only.

Used by build_map.py. A cell is a dict as built there: {"verdict": ..., "file", "line", "quote", "weak", "basis"}.
Cells whose verdict is invalid-anchor, invalid-verdict or missing never count as support.

Status precedence (first match wins):
  Conflicting  any body section is `differs`
  Established  some `anchored` cell with basis shown (an anchored cell with no basis counts as shown)
  Assumed      `anchored` cells, all with basis assumed
  Narrower     some `partial` cell and nothing stronger
  Cited        some `external` cell, or a citation-type claim, and nothing stronger
  Unsupported  everything else (absent from every body section)
"""
import textwrap

from cm_common import norm_ws

BASES = {"shown", "assumed"}
UNCOUNTED = {"invalid-anchor", "invalid-verdict", "missing"}
STATUSES = ["Unsupported", "Conflicting", "Narrower", "Assumed", "Cited", "Established"]  # worst first
RULES = [
    ("Conflicting", "any body section says `differs`"),
    ("Established", "some body section is `anchored` with `basis: shown`"),
    ("Assumed", "`anchored` only with `basis: assumed`"),
    ("Narrower", "only `partial` in the body: the body backs a weaker version"),
    ("Cited", "only `external`, or a citation-type claim with no body anchor"),
    ("Unsupported", "`absent` from every body section"),
]
WIDTH = 80
TABLE_QUOTE = 80


def classify(claim, cells):
    """Return (status, supporting cells) for one claim; cells is a list of (section id, cell)."""
    def pick(pred):
        return [(s, c) for s, c in cells if pred(c)]

    differs = pick(lambda c: c["verdict"] == "differs")
    if differs:
        return "Conflicting", differs
    anchored = pick(lambda c: c["verdict"] == "anchored")
    shown = [(s, c) for s, c in anchored if c.get("basis") in (None, "shown")]
    if shown:
        return "Established", shown
    if anchored:
        return "Assumed", anchored
    partial = pick(lambda c: c["verdict"] == "partial")
    if partial:
        return "Narrower", partial
    external = pick(lambda c: c["verdict"] == "external")
    if external or claim["type"] == "citation":
        return "Cited", external
    return "Unsupported", []


def build_entries(claims, body, cells):
    out = []
    for c in claims:
        row = [(s["id"], cells[(c["id"], s["id"])]) for s in body]
        status, support = classify(c, row)
        out.append({"claim": c, "status": status, "support": support, "cells": row,
                    "uncounted": [(s, v["verdict"]) for s, v in row if v["verdict"] in UNCOUNTED]})
    return out


def counts(entries):
    n = {s: 0 for s in STATUSES}
    for e in entries:
        n[e["status"]] += 1
    return n


def worst_first(entries):
    return sorted(entries, key=lambda e: STATUSES.index(e["status"]))  # stable: claim order within a status


def wrap(text, first="", rest=""):
    return textwrap.wrap(text, WIDTH, initial_indent=first, subsequent_indent=rest,
                         break_long_words=False, break_on_hyphens=False) or [first.rstrip()]


def cell_label(v):
    if v["verdict"] == "anchored":
        return f"anchored (basis: {v.get('basis') or 'not given'})"
    return v["verdict"] if v["verdict"] != "external" else "external, unverified"


def short(q, n=TABLE_QUOTE):
    q = norm_ws(q)
    return q if len(q) <= n else q[:n - 3].rstrip() + "..."


def cell_text(s):
    return norm_ws(s).replace("|", "/")


def evidence(e, body_ids):
    note = ""
    if e["uncounted"]:
        note = "; not counted: " + ", ".join(f"{v} in {s}" for s, v in e["uncounted"])
    if e["status"] == "Unsupported":
        return f"none: absent from {' and '.join(body_ids) if len(body_ids) < 3 else ', '.join(body_ids)}" + note
    if e["status"] == "Cited" and not e["support"]:
        return "support is the cited work; not read" + note
    parts = [f"{s} {cell_label(v)}: \"{short(v['quote'])}\"" for s, v in e["support"]]
    return "; ".join(parts) + note


def cell_bullet(section, v):
    if v["verdict"] == "absent":
        return f"{section}: absent."
    if v["verdict"] == "missing":
        return f"{section}: no answer from the agent; not counted."
    if v["verdict"] == "invalid-anchor":
        return (f"{section}: not counted; the agent said {v['claimed']} but its quote was not found in the "
                "snapshot.")
    if v["verdict"] == "invalid-verdict":
        return f"{section}: not counted; \"{v['note']}\" is not a verdict word."
    weak = " Weak anchor: no shared content word with the claim." if v.get("weak") else ""
    return f"{section}, `{v['file']}:{v['line']}`, {cell_label(v)}: \"{v['quote']}\"{weak}"


def ledger_md(cfg, snap_name, claims, body, entries):
    ids = [s["id"] for s in body]
    n = counts(entries)
    L = []
    w = L.append
    w(f"# Claim ledger: {cfg.get('title', 'paper')}")
    w("")
    L.extend(wrap("Consistency, not correctness. A status says where the paper's own text backs a claim, with a "
                  "quote. It never says a claim is true: Established means the paper shows it, not that it is "
                  "true. References are external and unverified."))
    w("")
    w(f"Snapshot `{snap_name}`. Body sections checked: {', '.join(ids)}.")
    w("")
    w("## Status rule (computed by the script, in this order)")
    w("")
    w("| status | rule |")
    w("| --- | --- |")
    for s, r in RULES:
        w(f"| {s} | {r} |")
    w("")
    w("## Summary")
    w("")
    summary = [f"{n[s]} {s.lower()}" for s in ("Established", "Conflicting", "Narrower", "Cited", "Unsupported",
                                                "Assumed")]
    L.extend(wrap(f"{len(claims)} claims: " + ", ".join(summary) + "."))
    w("")
    ordered = worst_first(entries)
    w("## Ledger (worst first)")
    w("")
    w("| id | status | claim | where claimed | evidence |")
    w("| --- | --- | --- | --- | --- |")
    for e in ordered:
        c = e["claim"]
        w(f"| {c['id']} | {e['status']} | {cell_text(c['sentence'])} | {cell_text(c['location'])} | "
          f"{cell_text(evidence(e, ids))} |")
    w("")
    w("## Detail")
    w("")
    for e in ordered:
        c = e["claim"]
        w(f"### {c['id']} · {e['status']}")
        w("")
        L.extend(wrap(norm_ws(c["sentence"]), "> ", "> "))
        w("")
        flag = "" if c["sentence_ok"] else " (sentence not found in snapshot)"
        L.extend(wrap(f"{c['location']} (`{c['file']}`){flag}", "- ", "  "))
        cs = e["cells"]
        if all(v["verdict"] == "absent" for _, v in cs):
            L.extend(wrap(" ".join(f"{s}: absent." for s, _ in cs), "- ", "  "))
        else:
            for s, v in cs:
                L.extend(wrap(cell_bullet(s, v), "- ", "  "))
        w("")
    return "\n".join(L).rstrip("\n") + "\n"


def briefing_md(cfg, entries):
    n = counts(entries)
    title = cfg.get("title", "paper")
    L = []
    w = L.append
    w(f"# Briefing: {title}")
    w("")
    parts = [f"{n[s]} {s.lower()}" for s in ("Established", "Assumed", "Conflicting", "Narrower", "Cited",
                                              "Unsupported") if n[s]]
    L.extend(wrap(f"{len(entries)} claims in {title}: " + ", ".join(parts) + "."))
    w("")
    for e in worst_first(entries):
        if e["status"] == "Established":
            continue
        c = e["claim"]
        q = norm_ws(c["sentence"])
        head = f"**{c['id']}, {e['status'].lower()}.**"
        sup = "; ".join(f"{s}: \"{norm_ws(v['quote'])}\"" for s, v in e["support"])
        if e["status"] == "Unsupported":
            body = f"\"{q}\" Claimed in {c['location']}; no body section states it."
        elif e["status"] == "Conflicting":
            body = f"\"{q}\" ({c['location']}). A body section differs. {sup}"
        elif e["status"] == "Narrower":
            body = f"\"{q}\" ({c['location']}). The body states a narrower version. {sup}"
        elif e["status"] == "Assumed":
            body = f"\"{q}\" ({c['location']}). The body relies on it as an assumption. {sup}"
        else:
            body = f"\"{q}\" ({c['location']}). The support is a cited work, which was not read."
        if e["uncounted"]:
            body += " Not counted: " + ", ".join(f"{v} in {s}" for s, v in e["uncounted"]) + "."
        L.extend(wrap(f"{head} {body}", "- ", "  "))
    est = [e["claim"]["id"] for e in entries if e["status"] == "Established"]
    if est:
        who = est[0] if len(est) == 1 else ", ".join(est[:-1]) + " and " + est[-1]
        L.extend(wrap(f"**{who}, established.** A body section shows "
                      f"{'it' if len(est) == 1 else 'each of them'}; the quotes are in the ledger.", "- ", "  "))
    w("")
    L.extend(wrap("Nothing here says whether any claim is true. It shows where the text agrees with itself."))
    return "\n".join(L).rstrip("\n") + "\n"
