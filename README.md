# claims-map

A Claude Code skill that maps a paper's claims across its sections. For every claim made in the abstract,
introduction, conclusion and contributions list, it shows what each body section says about it, with a quoted
anchor: **anchored**, **partial**, **differs**, **absent**, or **external, unverified** (support is a citation).

It checks **consistency, not correctness**. It never says a claim is right or wrong, never proposes wording, and
never reads cited papers. The author decides the story; the map shows where the text agrees with itself.

> **Status: v0.0.1, experimental.** Piloted on two LaTeX papers (one private, one CC BY arXiv paper) with Sonnet 5.5.
> Expect rough edges; see
> [CHANGELOG.md](CHANGELOG.md) and the known limits below.

This skill and its scripts were written with Claude (Anthropic's AI model) in Claude Code. The agents it runs are
LLM agents too, which is why every verdict must carry a quote you can check.

## How it works
1. **Snapshot** the section files (sha256, git commit, dirty-tree flag). All agents read the snapshot, never the live tree.
2. **Extractor agent** writes a claims table from the front matter. It gathers no evidence.
3. **One section agent per body section**, in parallel. Each sees only the claims table and its own section.
4. **Number check** (a script) compares numbers for the same quantity across sections: equal, rounding, conflict.
5. **Build** the markdown map (the source of truth), enforcing the anchor rule mechanically, plus a terminology
   lint from your config.
6. **Render** a self-contained HTML matrix.

Hard rules: no anchor, no verdict; agents report and never fix; section agents are independent; terminology
and framing rules come from your per-paper config, not the skill.

## Install
Clone into your Claude Code skills folder:
```bash
git clone https://github.com/theMuslimDev/claims-map.git ~/.claude/skills/claims-map
pip install pyyaml
```
Copy `claims-map.config.template.md` next to your paper, fill in the YAML block, then ask Claude Code for a claims map
of your paper (the skill triggers on that wording). Sub-agents default to Sonnet 5.5; set `agent_model` in the config
to override.

### As a plugin (experimental)
```bash
claude plugin marketplace add theMuslimDev/claims-map
claude plugin install claims-map@claims-map-marketplace
```
The repo root is the plugin, so a plugin install and a manual clone give the same files.

## Usage

**1. Give it your paper.** A PDF, DOCX, Markdown or text file, or a LaTeX folder:
```text
/claims-map:claims-map /path/to/paper.pdf
/claims-map:claims-map /path/to/latex-folder
```
Claude prepares the paper and writes a draft config:
- **PDF, DOCX, Markdown, text:** `scripts/ingest.py` extracts the text and splits it into sections by heading.
  PDFs need `pdftotext` (poppler: `brew install poppler`) or `pip install pypdf`.
- **LaTeX folder:** `scripts/init_config.py` reads the section order from `main.tex`.

Either way, Claude shows you the sections it found and which are `front` (abstract, introduction, conclusion: the
claims come from these) and `body` (checked against the claims). Fix any wrong role, and tell it your terminology
rules (for example "never write Phase"). Add the output folder to `.gitignore`.

LaTeX gives the cleanest results. For a PDF, anchors point at lines of the extracted text, not at PDF pages, and
equations can come out garbled, so number checks and quotes around maths are less reliable.

You can run the helpers yourself and then pass the finished config:
```bash
python scripts/ingest.py /path/to/paper.pdf
python scripts/init_config.py /path/to/latex-folder
```
```text
/claims-map:claims-map /path/to/paper_claims_map/claims-map.config.md
```
For every option, see `claims-map.config.template.md`. To see it work first, ask for `examples/toy-paper`.

**2. Ask in plain words if you prefer.** "Run a claims map on /path/to/my-paper" works too. If you give no path,
Claude asks which paper.

**3. Wait for the agents.** Claude takes a snapshot of your files, runs one agent to extract the claims, then one
agent per body section in parallel, then the scripts. It makes several model calls, so expect a few minutes and
some usage on a real paper. Your files are never modified; everything goes to `output_dir`.

**4. Read the map.** Open `claims_map.html` in a browser (or `claims_map.md`). Each row is a claim; each column is a
body section; each cell is one of:

| cell | meaning |
|---|---|
| anchored | the section says the same thing (click for the quoted sentence) |
| partial | narrower or conditioned |
| differs | different number or term for the same thing |
| absent | not in that section |
| external, unverified | support is a citation; the skill does not read it |

Start with "Claims absent from every body section", then the `partial` and `differs` cells, the unclaimed
statements, the number check and the terminology lint. The map shows where your text agrees with itself. It does
not say whether any claim is true, and it never suggests wording.

**5. Re-run after edits.** Each run takes a fresh snapshot, so re-run whenever the paper changes.

## Try the toy paper and run the tests
```bash
python -m unittest discover -s tests
```
25 tests: an end-to-end run on `examples/toy-paper/` with fixed claims and verdicts (no model calls), plus unit tests for the helpers and failure paths. A manual acceptance test on a real
CC BY arXiv paper is in `examples/arxiv-2610.24343/` (needs model agents; see its README).

## Known limits
- PDF input is new: text extraction, section splitting and the config were tested on a toy PDF and one real IEEE-style paper, but the full agent workflow has not been run on a PDF yet.
- Consistency only: two sections can agree and both be wrong.
- The anchor check proves a quote exists; a weak-anchor flag warns when claim and quote share no content word, but
  relevance is still a judgement.
- The number check is a heuristic and can pair unrelated numbers.
- Figures, tables and captions are visible only if listed as sections or support files.
- Best on LaTeX. PDF input depends on text extraction: two-column layouts, equations, tables and figures can come out garbled, and anchors point at the extracted text, not PDF pages.

## Licence
See [LICENSE](LICENSE).
