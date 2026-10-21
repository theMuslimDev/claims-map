# Output layout

## Contents
- Directory
- claims_map.md
- Rendering

## Directory
`<output_dir>/` holds `snapshot_<UTC>/` (`raw/`, `resolved/`, `MANIFEST.json`), `claims.json`, `verdicts/<id>.json`,
`numcheck.json`, `claims_map.md`, `claims_map.html`.

## claims_map.md
Header (snapshot name, git commit, dirty-tree flag, table of sha256 per file), Summary, Claims absent from every
body section, Matrix (claims by body sections, one verdict word per cell), Claim detail (per claim, per section:
verdict, `file:line`, quote; the line is computed from the quote by `build_map.py`), Unclaimed strong statements,
Number check, Terminology lint. Extra cell values from the checker: `invalid-anchor` (quote not in the snapshot),
`missing` (agent gave no answer), `invalid-verdict`.

## Rendering
`render_html.py` reads only this markdown, so the markdown stays the source of truth and diffs cleanly in git.
