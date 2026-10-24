# Using claims-map

The full walkthrough: from giving the skill your paper to reading the map. For
what the skill is and a worked example, see [README.md](README.md).

**1. Give it your paper.** A PDF, DOCX, Markdown or text file, or a LaTeX
folder. If you give no path, Claude asks which paper.

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

Claude then shows you the sections it found and which are `front` (abstract,
introduction, conclusion: the claims come from these) and `body` (checked
against the claims). Fix any wrong role, and tell it your terminology rules (for
example "never write Phase"). Add the output folder to `.gitignore`.

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

`ingest.py` prints the draft config's section list with the roles it guessed
(shown here on a small LaTeX file):

<!-- usage-ingest:start -->
```text
wrote /path/to/paper/toy-paper_claims_map/claims-map.config.md
5 sections found:
{id: front_matter, file: ingested/00_front_matter.txt, role: front}
{id: introduction, file: ingested/01_introduction.txt, role: front}
{id: methods, file: ingested/02_methods.txt, role: body}
{id: results, file: ingested/03_results.txt, role: body}
{id: conclusion, file: ingested/04_conclusion.txt, role: front}
Check that the roles are right (front = abstract, introduction, conclusion; body
  = the rest).
```
<!-- usage-ingest:end -->

For every option, see `claims-map.config.template.md`. To see it work first, ask
for `examples/toy-paper`. The sample output on this page is the real output of
the scripts on that paper, with temp paths, timestamps and commit hashes
replaced and long lines wrapped.

**2. Wait for the agents.** Claude snapshots your files, runs one agent to
extract the claims, then one agent per body section in parallel, then the
scripts. It makes several model calls, so expect a few minutes and some usage on
a real paper. Your files are never modified; everything goes to `output_dir`.

The first script run is `snapshot.py`. Here a section had an edit not yet
committed, so it warns (the map header says the tree is dirty too):

<!-- usage-snapshot_dirty:start -->
```text
/path/to/paper/out/snapshot_<timestamp>
warning: snapshot taken from the working tree; these files differ from the
  commit: sections/03_results.tex. Use --ref HEAD to snapshot the committed
  content instead.
```
<!-- usage-snapshot_dirty:end -->

`numcheck.py` then compares numbers for the same quantity across sections:

<!-- usage-numcheck:start -->
```text
scanned 5 numbers; equal pairs 0; rounding 2; conflict 0
```
<!-- usage-numcheck:end -->

After the agents have written their verdicts, `build_map.py` checks every
anchor, writes the map, the ledger and the briefing, and prints one summary
line:

<!-- usage-build_map:start -->
```text
wrote /path/to/paper/out/claims_map.md: 6 claims, absent-everywhere 1 (+1
  citation), weak anchors 2, invalid anchors 1, unclaimed 1, lint hits 1
wrote /path/to/paper/out/claim_ledger.md and /path/to/paper/out/briefing.md
```
<!-- usage-build_map:end -->

The output folder then holds:

<!-- usage-listing:start -->
```text
out/
  briefing.md
  claim_ledger.md
  claims.json
  claims_map.md
  numcheck.json
  snapshot_<timestamp>/
  verdicts/
```
<!-- usage-listing:end -->

**3. Read the briefing and the ledger.** `briefing.md` is a short findings list.
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
absent, external) behind the statuses. Its Summary starts like this:

<!-- usage-summary:start -->
```text
- claims extracted: 6; body sections checked: methods, results
- cells by verdict: absent 6, anchored 3, differs 1, invalid-anchor 1, partial 1
- claims absent from every body section: **1**
- citation claims with no body anchor (listed separately, expected for
  literature review): 1
- unclaimed strong statements: 1
- anchors sharing no content word with their claim (check relevance): 2
- cells rejected because the quoted anchor was not found in the snapshot: 1
```
<!-- usage-summary:end -->

and the matrix rows (one claim per row, one column per body section):

<!-- usage-matrix:start -->
| id | type | where claimed | claim | methods | results |
| --- | --- | --- | --- | --- | --- |
| T01 | numeric | abstract, sentence 1 | The method reaches 95\% accuracy on the test set. | invalid-anchor | anchored |
| T02 | numeric | abstract, sentence 2 | It runs in 1.39 ms per frame. | absent | anchored |
| T03 | comparative | abstract, sentence 3 | It beats the baseline. | absent | partial (weak anchor) |
| T04 | citation | intro, sentence 1 | Prior work uses Kalman filters \cite{smith2020}. | absent | absent |
| T05 | definition | abstract, sentence 4 | We train the classifier in three stages. | anchored | differs (weak anchor) |
| T06 | scope | introduction, sentence 2 | This paper learns the mapping instead. | absent | absent |
<!-- usage-matrix:end -->

For the ledger and the briefing of the same paper, see the Example in
[README.md](README.md#example). Beyond the ledger, check the unclaimed
statements, the number check and the terminology lint. The output shows where
your text agrees with itself. It does not say whether any claim is true, and it
never suggests wording.

**Uncommitted edits.** By default the snapshot copies your files as they are on
disk, so unsaved-to-git edits are included. The script warns which files differ
from the commit and the map header says so. To map exactly what is committed,
run `python scripts/snapshot.py CONFIG --ref HEAD`.

**4. Re-run after edits.** Each run takes a fresh snapshot, so re-run whenever
the paper changes.
