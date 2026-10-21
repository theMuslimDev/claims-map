# Acceptance test on a real paper (manual)

Unlike `tests/test_pipeline.py`, this needs model agents, so it is run by hand with Claude Code.

1. `python scripts/snapshot.py examples/arxiv-2610.24343/claims-map.config.md`
2. Run the extractor and the three section agents (setup, results, appendix) as in `SKILL.md`.
3. `python scripts/numcheck.py ...`, `python scripts/build_map.py ...`, `python scripts/render_html.py ...`

What to check (not what the paper should say):
- the pipeline runs on a single-file ICML-style paper split into sections, with no number macros and an empty terminology list;
- `build_map.py` reports 0 `invalid-anchor` cells and 0 `missing` cells;
- claims that appear only in the abstract or introduction show up in the absent-everywhere lists;
- the number check lists rounding pairs only where the same quantity is stated twice.
