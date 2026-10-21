# claims-map config (template)

Copy this file next to the paper (or into its notes folder), fill in the YAML block, and pass it to the
scripts. Everything paper-specific lives here; the skill itself has no built-in terminology or framing rules.
Paths are relative to `paper_dir`, and `paper_dir` is relative to this config file unless absolute.

```yaml
title: "Short paper title"
agent_model: sonnet-5.5     # model for all sub-agents; default Sonnet 5.5, override with e.g. haiku or opus
paper_dir: ../..                 # directory that holds the section files
output_dir: notes/claims_map     # relative to paper_dir; should be gitignored. Snapshots, claims, map land here

# Section files in reading order. role: front (claims are extracted from it), body (one section agent
# each, checked against the claims), skip (listed in the snapshot, ignored by agents).
sections:
  - {id: abstract, file: sections/00_abstract.tex,     role: front}
  - {id: intro,    file: sections/01_intro.tex,        role: front}
  - {id: s02,      file: sections/02_model.tex,        role: body}
  - {id: s03,      file: sections/03_method.tex,       role: body}
  - {id: s04,      file: sections/04_results.tex,      role: body}
  - {id: conclusion, file: sections/05_conclusion.tex, role: front}

# Files copied into the snapshot but not treated as sections (number files, caption macros, tables).
support_files: []

# Optional. If numbers are typed through a macro (e.g. \rn{key}), the snapshot writes a `resolved/` copy
# with the values substituted, so agents and the number check see the real numbers.
# number_macros:
#   macro: rn                              # \rn{key}
#   definitions_file: sections/numbers.tex
#   definition_regex: '\\csname rn@(.*?)\\endcsname\{(.*?)\}'   # group 1 = key, group 2 = value
unwrap_macros: []                # macros whose argument is kept as is, e.g. [prov]

# Terminology rules. Applied as a mechanical lint to every snapshot file, and given to the agents so
# "differs" can be raised when two sections name the same thing differently. pattern is a regex run on
# comment-stripped text (labels, refs, cites removed). raw: true runs it on the line with TeX commands intact.
terminology:
  - {id: banned-term, pattern: '\bBannedWord\b', message: 'use "preferred word" instead'}
  - {id: em-dash, pattern: '—', message: 'no em dashes', raw: true}
words_to_avoid: []               # soft list for the agents; they report hits as unclaimed or differs, never as fixes
spelling: British                # documentation for the agents; enforce through terminology patterns if you want a lint

# Claim types the extractor uses: numeric, comparative, causal, scope, definition, citation.
# Overrides add paper-specific guidance, e.g. what counts as a scope claim here.
claim_type_overrides:
  scope: "statements about what is NOT claimed, held fixed or excluded count as scope claims"

# Number check tuning (optional).
numcheck:
  sections: []                   # empty = all sections
  min_shared_words: 2            # content words two contexts must share to count as the same quantity
  conflict_rel_tol: 0.5          # pairs further apart than this relative gap are treated as unrelated
```

Notes
- Keep the config out of the paper's tracked files unless you want it versioned; the output directory
  should be gitignored so the pilot never touches the working tree.
- Every agent receives the `terminology`, `words_to_avoid` and `claim_type_overrides` entries verbatim.
