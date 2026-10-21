#!/usr/bin/env python
"""Render claims_map.md to one self-contained HTML file (matrix coloured by verdict, anchors on click).

Usage: render_html.py CLAIMS_MAP.md [OUT.html]
Reads only the markdown produced by build_map.py; the markdown stays the source of truth.
"""
import html
import re
import sys
from pathlib import Path

COLOURS = {  # colour is paired with the word, never alone
    "anchored": ("#d8efdc", "#1b5e2a"), "partial": ("#fff1cc", "#7a5200"), "differs": ("#fbd9d3", "#8a2a1b"),
    "absent": ("#e6e6ea", "#444"), "weak": ("#fff1cc", "#7a5200"), "external, unverified": ("#dbe8fb", "#1d4e89"),
    "invalid-anchor": ("#f3c6f0", "#6d1a69"), "missing": ("#f3c6f0", "#6d1a69"), "invalid-verdict": ("#f3c6f0", "#6d1a69"),
}


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    lines = src.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip()
    # sections by "## " heading
    secs, cur = {}, None
    head = []
    for ln in lines[1:]:
        if ln.startswith("## "):
            cur = ln[3:].strip()
            secs[cur] = []
        elif cur is None:
            head.append(ln)
        else:
            secs[cur].append(ln)

    def table(block):
        rows = [split_row(text) for text in block if text.startswith("|")]
        return (rows[0], rows[2:]) if len(rows) >= 2 else (None, [])

    # claim details: "### id · type · loc" then bullets
    detail = {}
    cid = None
    for ln in secs.get("Claim detail", []):
        if ln.startswith("### "):
            cid = ln[4:].split(" · ")[0]
            detail[cid] = []
        elif cid and ln.startswith("- "):
            detail[cid].append(ln[2:])
    hdr, rows = table(secs.get("Matrix", []))
    o = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>",
         ":root{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#d9d9de}@media(prefers-color-scheme:dark){:root{--bg:#161618;--fg:#eee;--mut:#9a9aa0;--line:#38383c}}",
         "body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1200px;padding:16px}",
         "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top;font-size:.9rem}",
         ".wrap{overflow-x:auto}code{font-size:.85em}.cell{font-weight:600;white-space:nowrap}details{margin:4px 0}summary{cursor:pointer}.mut{color:var(--mut)}",
         ".legend span{display:inline-block;padding:2px 8px;margin:2px 6px 2px 0;border-radius:4px;font-size:.85rem}li{margin:3px 0}",
         "@media(prefers-color-scheme:dark){.cell,.legend span{filter:brightness(.8)}}</style></head><body>",
         f"<h1>{html.escape(title)}</h1>"]
    o.append("".join(f"<p>{inline(text)}</p>" for text in head if text.strip() and not text.startswith("|") and not text.startswith("- ")))
    o.append("<ul>" + "".join(f"<li>{inline(text[2:])}</li>" for text in head if text.startswith("- ")) + "</ul>")
    h2, r2 = table(head)
    if h2:
        o.append("<details><summary>Snapshot files and hashes</summary><div class='wrap'><table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in h2) + "</tr>" +
                 "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in r2) + "</table></div></details>")
    o.append("<h2>Summary</h2><ul>" + "".join(f"<li>{inline(text[2:])}</li>" for text in secs.get("Summary", []) if text.startswith("- ")) + "</ul>")
    o.append("<h2>Claims absent from every body section</h2><ul>" + "".join(f"<li>{inline(text[2:])}</li>" for text in secs.get("Claims absent from every body section", []) if text.startswith("- ")) + "</ul>")
    o.append("<h2>Citation claims with no body anchor</h2><ul>" + "".join(f"<li>{inline(text[2:])}</li>" for text in secs.get("Citation claims with no body anchor", []) if text.startswith("- ")) + "</ul>")
    o.append("<h2>Matrix</h2><p class='mut'>Click a claim id for the anchors. Colour is always paired with the verdict word.</p><div class='legend'>" +
             "".join(f"<span style='background:{bg};color:{fg}'>{k}</span>" for k, (bg, fg) in COLOURS.items() if k in ("anchored", "partial", "differs", "absent", "external, unverified")) + "</div>")
    if hdr:
        o.append("<div class='wrap'><table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hdr) + "</tr>")
        for r in rows:
            o.append("<tr>")
            for i, c in enumerate(r):
                if i == 0:
                    items = "".join(f"<li>{inline(d)}</li>" for d in detail.get(c, []))
                    o.append(f"<td><details><summary><b>{html.escape(c)}</b></summary><ul style='min-width:380px'>{items}</ul></details></td>")
                elif i >= 4:
                    bg, fg = COLOURS.get(c.replace(" (weak anchor)", ""), ("#eee", "#222"))
                    o.append(f"<td class='cell' style='background:{bg};color:{fg}'>{html.escape(c)}</td>")
                else:
                    o.append(f"<td>{inline(c)}</td>")
            o.append("</tr>")
        o.append("</table></div>")
    for name in ("Unclaimed strong statements", "Number check", "Terminology lint"):
        o.append(f"<h2>{name}</h2>")
        block = secs.get(name, [])
        o.append("".join(f"<p>{inline(text)}</p>" for text in block if text.strip() and not text.startswith("|")))
        h, rr = table(block)
        if h:
            o.append("<div class='wrap'><table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in h) + "</tr>" +
                     "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rr) + "</table></div>")
    o.append("</body></html>")
    dst.write_text("\n".join(o), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()
