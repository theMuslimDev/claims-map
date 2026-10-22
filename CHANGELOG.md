# Changelog

## Unreleased
- Fixed: `numcheck.sections: []` (the template default) scanned 0 numbers; empty now means all sections, and a zero-number run prints a hint.
- `snapshot.py` warns which files differ from the commit and which number-macro keys are unresolved (comment lines ignored); `--ref HEAD` snapshots the committed content. The map header names modified files.

## v0.0.1 (experimental)
- Workflow: snapshot, extractor agent, one section agent per body section, number check, markdown map with the anchor rule enforced by script, HTML render.
- Input: LaTeX folders (`init_config.py` drafts the config from `main.tex`) and PDF, DOCX, Markdown or text files (`ingest.py` extracts the text and splits it into sections by heading).
- Weak-anchor flag when a claim and its quote share no content word; citation claims listed apart from the headline "absent from every section" list.
- Plugin and marketplace manifests, so it installs with `claude plugin install`.
- 37 tests (a toy-paper fixture, a generated PDF fixture, unit tests, failure paths) and a manual acceptance example on a real CC BY arXiv paper (`examples/arxiv-2610.24343/`).
- Piloted on two LaTeX papers with Sonnet 5.5. PDF input has not been run through the full agent workflow yet.
