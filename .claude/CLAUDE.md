# claims-map: project instructions

A Claude Code skill and plugin that maps a paper's claims across its sections. It checks consistency only, never
correctness. Public repo (MIT): github.com/theMuslimDev/claims-map. Read README.md, SKILL.md and CHANGELOG.md first.

## Layout
- `SKILL.md`, `reference/`: the skill instructions and agent prompts (keep SKILL.md under 500 lines; one level of links).
- `scripts/`: `snapshot.py`, `numcheck.py`, `build_map.py`, `ledger.py` (claim statuses, ledger and briefing text), `render_html.py`, `init_config.py`, `ingest.py`, shared `cm_common.py`.
- `examples/`: `toy-paper` (fixed claims and verdicts for tests), `arxiv-2610.24343` (CC BY, manual acceptance test).
- `tests/`: unittest suite with fixtures. `.claude-plugin/`: plugin and marketplace manifests (the repo root is the plugin).
- Sub-agents default to Sonnet 5.5; the config key `agent_model` overrides it.

## Before every commit
```
python -m unittest discover -s tests
ruff check scripts tests
claude plugin validate .
```
Needs Python 3.9+ and PyYAML. PDF input needs `pdftotext` (poppler) or `pypdf`.

## Rules
- Small logical commits, one concern each. Work on a branch; fast-forward merge to `main` only when the maintainer says so.
- Commit trailer: `Co-Authored-By: Claude <model name> <noreply@anthropic.com>`. AI attribution is intentional in this repo.
- Never tag, release or force-push without being asked in that turn. History was rewritten once (2026-10-21); do not rewrite again.
- State the plan before a batch of edits or a commit and push. Keep the repo free of personal data and of anything from the maintainer's own papers.
- The skill's hard rules stay: no anchor, no verdict; agents report and never fix or advise; section agents are independent; terminology comes from the paper's config.
- Test plugin installs only in a throwaway config: `CLAUDE_CONFIG_DIR=$(mktemp -d) claude plugin ...`. A nested `claude -p` cannot authenticate inside a session.
- Do not commit generated output (`out/`, `claims_map/`); they are gitignored.

## Versioning (decided, not yet implemented)
Users stay on a released version until the next one ships, while `main` keeps moving. Keep `version` in `plugin.json`
and pin the marketplace entry to the release tag through the git source `ref` (verify the syntax in the plugin
marketplace docs and prove it in a throwaway config first). A release is: bump `version`, tag, update `ref`. Add a release
script and a CI check (tests, ruff, validate, and that `ref` matches `version`). v0.0.1 is the only tag.

## Open work (suggested order)
1. Friendly error when PyYAML is missing (one line with the pip command, no traceback).
2. `build_map.py` prints the `render_html.py` command at the end, or renders HTML by default (`--no-html` to skip).
3. Keep each run's results under its snapshot folder so a second run does not overwrite the first.
4. Compare two runs: match claims by sentence text (ids change between runs) and report verdict changes.
5. HTML: a "supported in" column per claim; grey out or collapse absent cells; keep the absent-everywhere list prominent.
6. Number check false positives: ignore numbers inside "for example" clauses, require more shared context.
7. Run the full workflow on a PDF and on another real paper. The anchor check proves a quote exists, not that it is relevant.
