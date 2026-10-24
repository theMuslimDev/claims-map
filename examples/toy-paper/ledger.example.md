# Claim ledger: Toy paper (format draft, hand-written)

Consistency, not correctness. A status says where the paper's own text backs a
claim, with a quote. It never says a claim is true. References are external and
unverified.

Built from the verdicts in `out/` plus a made-up `basis` per anchored cell (the
section agents do not emit `basis` yet).

## Status rule (computed by the script, in this order)

| status | rule |
| --- | --- |
| Conflicting | any body section says `differs` |
| Established | some body section is `anchored` with `basis: shown` |
| Assumed | `anchored` only with `basis: assumed` |
| Narrower | only `partial` in the body: the body backs a weaker version |
| Cited | only `external`, or a citation-type claim with no body anchor |
| Unsupported | `absent` from every body section |

## Summary

6 claims: 2 established, 1 conflicting, 1 narrower, 1 cited, 1 unsupported,
0 assumed.

## Ledger (worst first)

| id | status | claim | where claimed | evidence |
| --- | --- | --- | --- | --- |
| C06 | Unsupported | This paper learns the mapping instead. | introduction, sentence 2 | none: absent from methods and results |
| C04 | Conflicting | We train the classifier in three stages. | abstract, sentence 4 | methods says "stages"; results says "Phase" |
| C03 | Narrower | It beats the baseline. | abstract, sentence 3 | results compares speed only, against an "older design" |
| C05 | Cited | Prior work uses Kalman filters \cite{smith2020}. | introduction, sentence 1 | support is the cited work; not read |
| C01 | Established | The method reaches 95\% accuracy on the test set. | abstract, sentence 1 | results gives 95.2%; rounds to the claim |
| C02 | Established | It runs in 1.39 ms per frame. | abstract, sentence 2 | results gives 1.388 ms; rounds to the claim |

## Detail

### C06 · Unsupported

> This paper learns the mapping instead.

- introduction, sentence 2 (`sections/01_intro.tex`)
- methods: absent. results: absent.

### C04 · Conflicting

> We train the classifier in three stages.

- abstract, sentence 4 (`sections/00_abstract.tex`)
- methods, `sections/02_methods.tex:1`, anchored (basis: shown): "We train a
  classifier in three stages, each starting from the previous weights."
- results, `sections/03_results.tex:2`, differs: "Phase 2 is evaluated
  second." (terminology rule: no "Phase")

### C03 · Narrower

> It beats the baseline.

- abstract, sentence 3 (`sections/00_abstract.tex`)
- methods: absent.
- results, `sections/03_results.tex:2`, partial: "The method is twice as fast
  as the older design." Speed only, and an "older design" rather than "the
  baseline". Weak anchor: no shared content word with the claim.

### C05 · Cited

> Prior work uses Kalman filters \cite{smith2020}.

- introduction, sentence 1 (`sections/01_intro.tex`)
- No body section anchors it. The support is the citation, which this skill
  does not read.

### C01 · Established

> The method reaches 95\% accuracy on the test set.

- results, `sections/03_results.tex:1`, anchored (basis: shown): "The
  classifier reaches 95.2\% accuracy on the test set."
- Number check: 95% vs 95.2% (rounding).

### C02 · Established

> It runs in 1.39 ms per frame.

- results, `sections/03_results.tex:1`, anchored (basis: shown): "Latency is
  1.388 ms per frame."
- Number check: 1.39 ms vs 1.388 ms (rounding).

## Row format for Assumed (illustration, not in the toy paper)

| id | status | claim | where claimed | evidence |
| --- | --- | --- | --- | --- |
| C0X | Assumed | Works for any channel. | abstract, sentence 2 | methods: "we assume a Gaussian channel" (basis: assumed) |

## Briefing (written from the ledger)

6 claims in the toy paper: 2 established, 1 conflicting, 1 narrower, 1 cited,
1 unsupported.

- **C06, unsupported.** "This paper learns the mapping instead." It appears in
  the introduction and in no body section.
- **C04, conflicting.** The abstract says "three stages". Methods uses
  "stages" ("We train a classifier in three stages, each starting from the
  previous weights."). Results uses "Phase" ("Phase 2 is evaluated second."),
  which the terminology rule forbids.
- **C03, narrower.** The abstract says "It beats the baseline." Results
  compares speed against an "older design" ("The method is twice as fast as the
  older design."). It does not mention accuracy or "the baseline".
- **C05, cited.** "Prior work uses Kalman filters." The support is smith2020,
  which was not read.
- **C01 and C02, established.** Results reports 95.2% accuracy and 1.388 ms per
  frame, which round to the abstract's 95% and 1.39 ms.

Nothing here says whether any claim is true. It shows where the text agrees with
itself.
