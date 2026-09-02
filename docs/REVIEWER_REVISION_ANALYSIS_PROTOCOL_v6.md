# STACKWISE reviewer-revision analysis protocol v6

Date fixed: 2026-09-02
Baseline: public research release v0.1.62; frozen benchmark v1.0.0.
Purpose: answer Array reviewers without changing the confirmatory external campaign or tuning the frozen admissibility classifier.

## R6-A — construct-validity diagnostics for C0/C1/C2/E0

Inputs: the four independent anonymized primary rater labels for 35 audit items and the frozen algorithmic labels.

Report:
1. 4x4 confusion matrix pooling 140 expert votes against frozen labels.
2. Per-frozen-class exact vote agreement and item-level >=3/4 consensus agreement.
3. Fleiss kappa and item-bootstrap 95% CI (20,000 resamples; seed 20260816).
4. A pre-specified operational collapse: {C0_DIRECT,C1_BRIDGEABLE} = `NO_EXTERNAL_ASSUMPTION`; {C2_CONDITIONAL,E0_MISSING} = `ASSUMPTION_OR_MISSING`. Report agreement and Fleiss kappa on this coarser boundary. This does not replace the four-class primary audit.

## R6-B — expert-consensus downstream sensitivity

Three label schemes are compared:
- `FROZEN`: original algorithmic labels.
- `MAJORITY_SUBSTITUTION`: replace an item only where >=3 of 4 independent raters agree on a valid class; retain the frozen label for 2:2 ties or 2:1:1 plurality.
- `CONSERVATIVE_MAJORITY`: apply only >=3/4 majority substitutions that are more conservative than the frozen label under C0 > C1 > C2 > E0; ignore majority upgrades.

No frozen result is overwritten. Sensitivity is post-review and non-confirmatory.

Outcomes:
1. Internal 20 source-target relation distribution and the A0-A3 admissibility ladder under all schemes.
2. External 15 held-out source-target relation distribution under all schemes.
3. Candidate-target transition table for the 8 held-out transitions. A changed held-out relation may only alter a candidate transition if it changes the best available relation after preserving the pre-held-out class and candidate-specific boundary restrictions.
4. External scenario x candidate readiness states (45 rows): verify whether any final readiness state changes. These states are driven by frozen scenario ontology/feasibility blockers; source-target relabeling cannot silently resolve unmapped hard requirements.
5. Internal first-slice candidate-level readiness (42 energy/cost criterion rows): verify whether source-target relabeling alone changes any candidate support state or the number of complete two-criterion candidates. Generic source-target upgrades are not allowed to override candidate-specific transfer/boundary blockers.
6. Negative-control conclusion under all schemes.

## R6-C — uncertainty/readiness structural invariance audit

The current Stage-5E readiness implementation uses uncertainty contracts to preserve/propagate precision and model-form semantics after evidence admissibility, but contains no probabilistic readiness threshold. To verify this implementation property, compare readiness statuses under:
- baseline uncertainty metadata;
- an all-pessimistic uncertainty label substitution;
- an all-optimistic uncertainty label substitution;
while keeping feasibility, evidence relations, profiles, and bridge-materialization states fixed.

Expected interpretation regardless of outcome: this is an implementation/contract sensitivity audit, not evidence that uncertainty is unimportant. If readiness is invariant, the manuscript must state that uncertainty would affect readiness only when a future target contract includes an explicit uncertainty/precision threshold.

## R6-D — reproducibility checks

Run the full regression test suite and the public-repository audit after adding revision scripts/results. Record all generated-file SHA-256 values. No third-party raw data or identifiable expert files are to be added to the public package.
