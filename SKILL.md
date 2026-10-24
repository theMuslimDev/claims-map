---
name: claims-map
description: Maps a paper's claims across its sections and reports, for each claim, whether each body section states it, narrows it, names it differently or never mentions it, each with a quoted anchor. Checks consistency only, never correctness. Use when the user asks for a claims map, a cross-section consistency check of a paper (abstract, introduction, body, conclusion), or where a claim is supported in the text.
---

# claims-map

A map, not a judge. Every claim from the abstract, introduction, conclusion and
contributions list is checked against each body section. The result shows where
the text agrees with itself. It never says a claim is right or wrong, never
proposes wording, and never reads cited papers (those cells read "external,
unverified"). The author decides the story.

Requires Python 3.9+ with PyYAML (`pip install pyyaml`). Works on LaTeX folders,
PDF, DOCX, Markdown and text files.

## Rules

1. **No anchor, no verdict.** An anchor is a file location plus the quoted
   sentence. `build_map.py` rejects any quote that is not in the snapshot (the
   cell becomes `invalid-anchor`).
2. Agents **report**. No fixes, no wording, no framing advice, no
   "correct/incorrect".
3. **Section agents are independent.** Each sees only the claims table and its
   own section.
4. **Terminology and framing rules come from the config**, never from this
   skill.
5. **Read the snapshot, never the live tree.** Another session may be editing
   the paper.
6. Write nothing tracked: output goes to the config's `output_dir`, which should
   be gitignored. Run on demand only.

## Verdicts

| verdict | meaning |
| --- | --- |
| anchored | the section states the same thing |
| partial | narrower or conditioned version |
| differs | different number or term for the same thing |
| absent | no anchor in this section; absent from every body section is the headline finding |
| external | support is a citation; marked "external, unverified" |

An `anchored` verdict may carry `basis`: `shown` (the paper derives, proves or
measures it there) or `assumed` (stated as an assumption or relied on without
being shown).

## Statuses

`build_map.py` gives each claim one status, first match wins: **Conflicting**
(any body `differs`), **Established** (some `anchored` with basis shown; no
basis counts as shown), **Assumed**, **Narrower** (only `partial`), **Cited**
(only `external`, or a citation claim with no body anchor), **Unsupported**
(absent everywhere). Established means the paper shows it, not that it is true.
Cells that are `invalid-anchor`, `invalid-verdict` or `missing` never count as
support.

## Starting

The input is a config file (`CFG`) describing the paper. Build it from what the
user gives:

- **A PDF, DOCX, Markdown or text file:** run `python scripts/ingest.py <file>`.
  It extracts the text, splits it into sections by heading, and writes `<file
  stem>_claims_map/claims-map.config.md`. PDF needs `pdftotext` (poppler) or
  `pypdf`. Anchors then point at lines of the extracted text, not PDF pages;
  equations may be garbled.
- **A LaTeX folder:** run `python scripts/init_config.py <folder>`. It reads the
  section order from the main `.tex` file and writes
  `<folder>/claims_map/claims-map.config.md`. LaTeX gives the cleanest results.
- **A config path:** use it.
- **Nothing:** ask which paper; do not pick one. `examples/toy-paper/` is a safe
  demo.

Either helper guesses roles from headings or file names. Show the user the
section list and roles, let them fix any, ask for their terminology rules, and
remind them to gitignore the output folder.

## Workflow

Copy this checklist and tick it off. `CFG` is the paper's config, copied from
[claims-map.config.template.md](claims-map.config.template.md). Scripts are in
`scripts/`.

```text
- [ ] 1. python scripts/snapshot.py CFG
- [ ] 2. Extractor agent -> <output_dir>/claims.json
- [ ] 3. One section agent per body section, in parallel -> <output_dir>/verdicts/<id>.json
- [ ] 4. python scripts/numcheck.py CFG
- [ ] 5. python scripts/build_map.py CFG
      (fix or re-run agents until no invalid-anchor / missing cells remain)
- [ ] 6. python scripts/render_html.py <output_dir>/claims_map.md
```

1. **Snapshot** copies the configured files (from the working tree; add `--ref
   HEAD` to snapshot the committed content instead, which ignores uncommitted
   edits, and tell the user when the tree is dirty), writes a macro-expanded
   `resolved/` copy (agents read this one), and records sha256 per file, the git
   commit and a dirty-tree flag. Git is only queried, never changed.
2. **Extractor** reads the `role: front` files and gathers no evidence.
3. **Section agents** each see the claims table and one section. Prompts, JSON
   formats and the unclaimed-statements flag:
   [reference/agent-prompts.md](reference/agent-prompts.md).
4. **Number check** compares numbers with the same unit and shared context
   across sections (equal, rounding, conflict). It lists; a human decides.
5. **Build** validates anchors, applies the config's terminology lint and writes
   the markdown map, the source of truth, plus `claim_ledger.md` (one status per
   claim, worst first) and `briefing.md`, both from the anchor-checked cells
   only. Output layout and the status rule:
   [reference/output-format.md](reference/output-format.md).
6. **Render** produces one self-contained HTML matrix from the markdown
   (optional).

## Agent model

Sub-agents default to **Sonnet 5.5** (`claude-sonnet-5-5`). Set `agent_model` in
the config to override (for example `haiku`, `opus`); pass that value as the
`model` of every Agent call.

## Reporting to the user

Calm and plain. Lead with `briefing.md`: the counts per status, then the
Unsupported, Conflicting, Narrower, Assumed and Cited claims, each with its
quote, then unclaimed strong statements, number check hits and lint hits. Point
to `claim_ledger.md` for the full table. Say where a rule was ambiguous and how
many cells were not counted. State findings only: never say how to support,
reword or reframe a claim, and never call a claim true or false.

## Limits

Consistency is not correctness: two sections can agree and both be wrong. Agent
verdicts are judgement calls, which is why each carries a quote to check. The
number check is a heuristic. Claims that live only in figures, tables or
captions are visible only if those files are sections or `support_files` that an
agent is given.
