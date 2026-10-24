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

For every option, see `claims-map.config.template.md`. To see it work first, ask
for `examples/toy-paper`.

**2. Wait for the agents.** Claude snapshots your files, runs one agent to
extract the claims, then one agent per body section in parallel, then the
scripts. It makes several model calls, so expect a few minutes and some usage on
a real paper. Your files are never modified; everything goes to `output_dir`.

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
absent, external) behind the statuses. Beyond the ledger, check the unclaimed
statements, the number check and the terminology lint. The output shows where
your text agrees with itself. It does not say whether any claim is true, and it
never suggests wording.

**Uncommitted edits.** By default the snapshot copies your files as they are on
disk, so unsaved-to-git edits are included. The script warns which files differ
from the commit and the map header says so. To map exactly what is committed,
run `python scripts/snapshot.py CONFIG --ref HEAD`.

**4. Re-run after edits.** Each run takes a fresh snapshot, so re-run whenever
the paper changes.
