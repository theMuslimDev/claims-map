# Agent prompts and JSON formats

## Contents
- Extractor
- Section agent
- Unclaimed strong statements
- Orchestrator notes

## Extractor
One agent (or one per front file if they are long). Give it the snapshot `resolved/` paths of the `role: front`
files and the config's `claim_type_overrides`. Prompt core:

> Extract every claim the paper makes about itself in these files: what the method does, how it performs, why,
> what it is compared with, what is in or out of scope, how a quantity is defined, what a cited work established.
> Do not gather evidence, do not read other sections, do not judge truth, do not propose wording. Split sentences
> that carry separable claims. Copy `sentence` verbatim (at most about 250 characters). Types: numeric,
> comparative, causal, scope, definition, citation. Never edit a span or drop its citation commands; pick a
> shorter verbatim span instead. Write the JSON array to `<output_dir>/claims.json` and check that every sentence
> occurs in its file (whitespace-normalised).

Format of `claims.json`: `[{"id":"C01","sentence":"...","file":"sections/00_abstract.tex","location":"abstract, sentence 3","type":"numeric"}]`

## Section agent
One per `role: body` section, parallel, each given only `claims.json` and its own `resolved/` file. Prompt core:

> For every claim say what this section says about it: anchored, partial, differs, absent or external.
> Except for absent, give a verbatim quote from this section (one sentence or clause, at most 250 characters) as
> anchor. Report only; never propose fixes or wording, never say whether a claim is right or wrong. Raise
> `differs` for a different term only under these terminology rules: <config terminology>. For every `anchored`
> verdict add `basis`: `shown` if the section derives, proves or measures the claim here, or `assumed` if it only
> states it as an assumption or relies on it without showing it. Describe what the text does, not whether it is
> right. Also list unclaimed
> strong statements (below). Write the JSON to `<output_dir>/verdicts/<id>.json`, then reply in two sentences.

Format:
```json
{"section": "s04",
 "verdicts": [{"claim": "C01", "verdict": "anchored", "basis": "shown", "anchor": {"quote": "..."}, "note": "optional, one plain sentence"}],
 "unclaimed": [{"type": "numeric", "quote": "..."}]}
```
One verdict per claim id. `absent` carries no anchor. `basis` is optional and applies to `anchored` only; a
citation is covered by `external`, so there is no `cited` basis. An `anchored` verdict without `basis` is counted as
`shown` by `build_map.py`, and the ledger says "basis not given".

## Unclaimed strong statements
Each section agent also lists strong statements in its section that match no claim, limited to numeric, comparative
and causal types, at most about 15 to 25 per section. They are a prompt to look, not a defect list.

## Orchestrator notes
- Pass `model` from the config's `agent_model` (default Sonnet 5.5) on every Agent call.
- Never show a section agent another section or another agent's output.
- Let agents write their own JSON files (claims.json, verdicts/<id>.json) rather than retyping their messages: copying by hand is where trimmed or mistyped claims came from in the pilot.
- If a cell comes back `invalid-anchor` or `missing`, re-run that section agent; do not repair quotes by hand.
