# claims-map

A Claude Code skill that maps a paper's claims across its sections. For every
claim made in the abstract, introduction, conclusion and contributions list, it
shows what each body section says about it, with a quoted anchor: **anchored**,
**partial**, **differs**, **absent**, or **external, unverified** (support is a
citation).

It checks **consistency, not correctness**. It never says a claim is right or
wrong, never proposes wording, and never reads cited papers. The author decides
the story; the map shows where the text agrees with itself.

> **Status: experimental.** Piloted on two LaTeX papers (one a CC BY
> arXiv paper) with Sonnet 5.5. Expect rough edges; see
> [CHANGELOG.md](CHANGELOG.md) and the known limits below.

This skill and its scripts were written with Claude (Anthropic's AI model) in
Claude Code. The agents it runs are LLM agents too, which is why every verdict
must carry a quote you can check.

## Example

This is the real output for the toy paper in `examples/toy-paper/`. The
briefing, `briefing.md`:

<!-- example-briefing:start -->

```text
# Briefing: Toy paper

6 claims in Toy paper: 2 established, 1 conflicting, 1 narrower, 1 cited, 1
unsupported.

- **T06, unsupported.** "This paper learns the mapping instead." Claimed in
  introduction, sentence 2; no body section states it.
- **T05, conflicting.** "We train the classifier in three stages." (abstract,
  sentence 4). A body section differs. results: "Phase 2 is evaluated second."
- **T03, narrower.** "It beats the baseline." (abstract, sentence 3). The body
  states a narrower version. results: "The method is twice as fast as the older
  design."
- **T04, cited.** "Prior work uses Kalman filters \cite{smith2020}." (intro,
  sentence 1). The support is a cited work, which was not read.
- **T01 and T02, established.** A body section shows each of them; the quotes
  are in the ledger.

Nothing here says whether any claim is true. It shows where the text agrees with
itself.
```

<!-- example-briefing:end -->

The top of the claim ledger, `claim_ledger.md`, worst first:

<!-- example-ledger:start -->

| id | status | claim | where claimed | evidence |
| --- | --- | --- | --- | --- |
| T06 | Unsupported | This paper learns the mapping instead. | introduction, sentence 2 | none: absent from methods and results |
| T05 | Conflicting | We train the classifier in three stages. | abstract, sentence 4 | results differs: "Phase 2 is evaluated second." |
| T03 | Narrower | It beats the baseline. | abstract, sentence 3 | results partial: "The method is twice as fast as the older design." |

<!-- example-ledger:end -->

Each claim gets one status: Conflicting, Established, Assumed, Narrower, Cited
or Unsupported. Every verdict is backed by a quote, and the ledger's detail
section gives the file and line it came from. Established means the paper
shows the claim, not that the claim is true. Nothing here is advice: the map
reports where the text agrees with itself and never says what to change.

## Install

Clone into your Claude Code skills folder:

```bash
git clone https://github.com/theMuslimDev/claims-map.git ~/.claude/skills/claims-map
pip install pyyaml
```

Copy `claims-map.config.template.md` next to your paper, fill in the YAML block,
then ask Claude Code for a claims map of your paper (the skill triggers on that
wording). Sub-agents default to Sonnet 5.5; set `agent_model` in the config to
override. Next steps are in [USAGE.md](USAGE.md).

### As a plugin (experimental)

```bash
claude plugin marketplace add theMuslimDev/claims-map
claude plugin install claims-map@claims-map-marketplace
```

The repo root is the plugin, so a plugin install and a manual clone give the
same files.

### Versions

Installs from the plugin marketplace follow the pinned release (the `ref` in
`.claude-plugin/marketplace.json`) and stay on it until the next release ships.
Cloning the repository follows `main`, which moves ahead of the last release.
Releases are listed in [CHANGELOG.md](CHANGELOG.md).

## Quick start

After [installing](#install), ask Claude Code for a claims map:

```text
/claims-map:claims-map /path/to/paper.pdf
```

Give it a PDF, DOCX, Markdown or text file, or a LaTeX folder. Claude drafts a
config, you confirm the sections, and it writes `briefing.md` and
`claim_ledger.md` (plus `claims_map.md`, and an optional HTML matrix) to the
output folder, leaving your files untouched.

Full walkthrough: [USAGE.md](USAGE.md).

## How it works

1. **Snapshot** the section files (sha256, git commit, dirty-tree flag). All
   agents read the snapshot, never the live tree.
2. **Extractor agent** writes a claims table from the front matter. It gathers
   no evidence.
3. **One section agent per body section**, in parallel. Each sees only the
   claims table and its own section.
4. **Number check** (a script) compares numbers for the same quantity across
   sections: equal, rounding, conflict.
5. **Build** the markdown map (the source of truth), enforcing the anchor rule
   mechanically, plus a terminology lint from your config. From the same checked
   cells it writes the **claim ledger** (`claim_ledger.md`, one status per
   claim, worst first) and a plain-text **briefing** (`briefing.md`), the main
   outputs.
6. **Render** a self-contained HTML matrix (optional).

Hard rules: no anchor, no verdict; agents report and never fix; section agents
are independent; terminology and framing rules come from your per-paper config,
not the skill.

## Known limits

- PDF input is new: text extraction, section splitting and the config were
  tested on a toy PDF and one real IEEE-style paper, but the full agent workflow
  has not been run on a PDF yet.
- Consistency only: two sections can agree and both be wrong.
- The anchor check proves a quote exists; a weak-anchor flag warns when claim
  and quote share no content word, but relevance is still a judgement.
- The number check is a heuristic and can pair unrelated numbers.
- Figures, tables and captions are visible only if listed as sections or support
  files.
- Best on LaTeX. PDF input depends on text extraction: two-column layouts,
  equations, tables and figures can come out garbled, and anchors point at the
  extracted text, not PDF pages.

## Tests

```bash
python -m unittest discover -s tests
```

81 tests, none needing a model: an end-to-end run on `examples/toy-paper/`
(whose golden output is the Example above), plus unit tests. A manual acceptance
test on a real CC BY arXiv paper is in `examples/arxiv-2610.24343/` (needs model
agents; see its README).

## Licence

See [LICENSE](LICENSE).
