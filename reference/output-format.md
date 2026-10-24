# Output layout

## Contents

- Directory
- claims_map.md
- claim_ledger.md and briefing.md
- Rendering

## Directory

`<output_dir>/` holds `snapshot_<UTC>/` (`raw/`, `resolved/`, `MANIFEST.json`),
`claims.json`, `verdicts/<id>.json`, `numcheck.json`, `claims_map.md`,
`claim_ledger.md`, `briefing.md`, `claims_map.html`.

## claims_map.md

Header (snapshot name, git commit, dirty-tree flag, table of sha256 per file),
Summary, Claims absent from every body section, Matrix (claims by body sections,
one verdict word per cell), Claim detail (per claim, per section: verdict,
`file:line`, quote; the line is computed from the quote by `build_map.py`),
Unclaimed strong statements, Number check, Terminology lint. Extra cell values
from the checker: `invalid-anchor` (quote not in the snapshot), `missing` (agent
gave no answer), `invalid-verdict`.

## claim_ledger.md and briefing.md

Both are written by `build_map.py` next to `claims_map.md`, from the same
anchor-checked cells. Cells with an `invalid-anchor`, `invalid-verdict` or
`missing` result never count as support.

`claim_ledger.md` gives one status per claim, worst first, with a summary count,
a table, and per-claim detail with the quoted anchors. The status is computed in
this order, first match wins:

| status | rule |
| --- | --- |
| Conflicting | any body section is `differs` |
| Established | some body section is `anchored` with `basis` `shown` (no `basis` counts as shown) |
| Assumed | `anchored` only with `basis` `assumed` |
| Narrower | only `partial` in the body |
| Cited | only `external`, or a citation-type claim with no body anchor |
| Unsupported | `absent` from every body section |

Established means the paper shows it, not that it is true.

`briefing.md` is a short plain-text findings list written from the ledger: one
bullet per claim that is not established, then one line for the established
ones. It states findings only and gives no advice.

## Rendering

`render_html.py` reads only this markdown, so the markdown stays the source of
truth and diffs cleanly in git.
