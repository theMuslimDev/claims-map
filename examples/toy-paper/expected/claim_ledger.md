# Claim ledger: Toy paper

Consistency, not correctness. A status says where the paper's own text backs a
claim, with a quote. It never says a claim is true: Established means the paper
shows it, not that it is true. References are external and unverified.

Snapshot `snapshot_<UTC>`. Body sections checked: methods, results.

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

6 claims: 2 established, 1 conflicting, 1 narrower, 1 cited, 1 unsupported, 0
assumed.

## Ledger (worst first)

| id | status | claim | where claimed | evidence |
| --- | --- | --- | --- | --- |
| T06 | Unsupported | This paper learns the mapping instead. | introduction, sentence 2 | none: absent from methods and results |
| T05 | Conflicting | We train the classifier in three stages. | abstract, sentence 4 | results differs: "Phase 2 is evaluated second." |
| T03 | Narrower | It beats the baseline. | abstract, sentence 3 | results partial: "The method is twice as fast as the older design." |
| T04 | Cited | Prior work uses Kalman filters \cite{smith2020}. | intro, sentence 1 | support is the cited work; not read |
| T01 | Established | The method reaches 95\% accuracy on the test set. | abstract, sentence 1 | results anchored (basis: shown): "The classifier reaches 95.2\% accuracy on the test set."; not counted: invalid-anchor in methods |
| T02 | Established | It runs in 1.39 ms per frame. | abstract, sentence 2 | results anchored (basis: shown): "Latency is 1.388 ms per frame." |

## Detail

### T06 · Unsupported

> This paper learns the mapping instead.

- introduction, sentence 2 (`sections/01_intro.tex`)
- methods: absent. results: absent.

### T05 · Conflicting

> We train the classifier in three stages.

- abstract, sentence 4 (`sections/00_abstract.tex`)
- methods, `sections/02_methods.tex:1`, anchored (basis: shown): "We train a
  classifier in three stages, each starting from the previous weights."
- results, `sections/03_results.tex:2`, differs: "Phase 2 is evaluated second."
  Weak anchor: no shared content word with the claim.

### T03 · Narrower

> It beats the baseline.

- abstract, sentence 3 (`sections/00_abstract.tex`)
- methods: absent.
- results, `sections/03_results.tex:2`, partial: "The method is twice as fast as
  the older design." Weak anchor: no shared content word with the claim.

### T04 · Cited

> Prior work uses Kalman filters \cite{smith2020}.

- intro, sentence 1 (`sections/01_intro.tex`)
- methods: absent. results: absent.

### T01 · Established

> The method reaches 95\% accuracy on the test set.

- abstract, sentence 1 (`sections/00_abstract.tex`)
- methods: not counted; the agent said partial but its quote was not found in
  the snapshot.
- results, `sections/03_results.tex:1`, anchored (basis: shown): "The classifier
  reaches 95.2\% accuracy on the test set."

### T02 · Established

> It runs in 1.39 ms per frame.

- abstract, sentence 2 (`sections/00_abstract.tex`)
- methods: absent.
- results, `sections/03_results.tex:1`, anchored (basis: shown): "Latency is
  1.388 ms per frame."
