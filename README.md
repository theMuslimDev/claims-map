# claims-map

A Claude Code skill that maps a paper's claims across its sections. For every
claim made in the abstract, introduction, conclusion and contributions list, it
shows what each body section says about it, with a quoted anchor: **anchored**,
**partial**, **differs**, **absent**, or **external, unverified** (support is a
citation).

It checks **consistency, not correctness**. It never says a claim is right or
wrong, never proposes wording, and never reads cited papers. The author decides
the story; the map shows where the text agrees with itself.

> **Status: v0.0.1, experimental.** Piloted on two LaTeX papers (one private,
> one CC BY arXiv paper) with Sonnet 5.5. Expect rough edges; see
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

## Install

Clone into your Claude Code skills folder:

```bash
git clone https://github.com/theMuslimDev/claims-map.git ~/.claude/skills/claims-map
pip install pyyaml
```

Copy `claims-map.config.template.md` next to your paper, fill in the YAML block,
then ask Claude Code for a claims map of your paper (the skill triggers on that
wording). Sub-agents default to Sonnet 5.5; set `agent_model` in the config to
override.

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

## Usage

**1. Give it your paper.** A PDF, DOCX, Markdown or text file, or a LaTeX
folder:

```text
/claims-map:claims-map /path/to/paper.pdf
/claims-map:claims-map /path/to/latex-folder
```

Claude prepares the paper and writes a draft config:

- **PDF, DOCX, Markdown, text:** `scripts/ingest.py` extracts the text and
  splits it into sections by heading. PDFs need `pdftotext` (poppler: `brew
  install poppler`) or `pip install pypdf`.
- **LaTeX folder:** `scripts/init_config.py` reads the section order from
  `main.tex`.

Either way, Claude shows you the sections it found and which are `front`
(abstract, introduction, conclusion: the claims come from these) and `body`
(checked against the claims). Fix any wrong role, and tell it your terminology
rules (for example "never write Phase"). Add the output folder to `.gitignore`.

LaTeX gives the cleanest results. For a PDF, anchors point at lines of the
extracted text, not at PDF pages, and equations can come out garbled, so number
checks and quotes around maths are less reliable.

You can run the helpers yourself and then pass the finished config:

```bash
python scripts/ingest.py /path/to/paper.pdf
python scripts/init_config.py /path/to/latex-folder
```

```text
/claims-map:claims-map /path/to/paper_claims_map/claims-map.config.md
```

For every option, see `claims-map.config.template.md`. To see it work first, ask
for `examples/toy-paper`.

**2. Ask in plain words if you prefer.** "Run a claims map on /path/to/my-paper"
works too. If you give no path, Claude asks which paper.

**3. Wait for the agents.** Claude takes a snapshot of your files, runs one
agent to extract the claims, then one agent per body section in parallel, then
the scripts. It makes several model calls, so expect a few minutes and some
usage on a real paper. Your files are never modified; everything goes to
`output_dir`.

**4. Read the briefing and the ledger.** `briefing.md` is a short findings list.
`claim_ledger.md` has one row per claim, worst first, with the quoted evidence,
and a detail section per claim. Each claim gets one status, computed by
`build_map.py` in this order (the first rule that matches wins):

| status | meaning |
| --- | --- |
| Conflicting | a body section says `differs`: a different number or term for the same thing |
| Established | a body section is `anchored` and shows it: it derives, proves or measures the claim there |
| Assumed | the body only states it as an assumption, or relies on it without showing it |
| Narrower | the body states only a narrower or conditioned version (`partial`) |
| Cited | the support is a cited work, which the skill does not read (or a citation claim with no body anchor) |
| Unsupported | no body section states it |

**Established means the paper shows it, not that it is true.** A section can
show something wrong, and two sections can agree and both be wrong. An anchored
cell with no `basis` from the agent counts as shown, and the ledger says "basis
not given". A cell whose quote is not found in the snapshot (`invalid-anchor`),
has an invalid verdict, or got no answer never counts as support.

`claims_map.md` (and `claims_map.html`, rendered from it) keeps the
claim-by-section matrix, with the per-section cells (anchored, partial, differs,
absent, external) behind the statuses. Beyond the ledger, check the unclaimed
statements, the number check and the terminology lint. The output shows where
your text agrees with itself. It does not say whether any claim is true, and it
never suggests wording.

**Uncommitted edits.** By default the snapshot copies your files as they are on
disk, so unsaved-to-git edits are included. The script warns which files differ
from the commit and the map header says so. To map exactly what is committed,
run `python scripts/snapshot.py CONFIG --ref HEAD`.

**5. Re-run after edits.** Each run takes a fresh snapshot, so re-run whenever
the paper changes.

## Try the toy paper and run the tests

```bash
python -m unittest discover -s tests
```

79 tests: an end-to-end run on `examples/toy-paper/` with fixed claims and
verdicts (no model calls), plus unit tests for the helpers and failure paths. A
manual acceptance test on a real CC BY arXiv paper is in
`examples/arxiv-2610.24343/` (needs model agents; see its README).

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

## Licence

See [LICENSE](LICENSE).
