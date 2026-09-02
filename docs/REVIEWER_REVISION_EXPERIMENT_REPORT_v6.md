# STACKWISE — Array reviewer-revision experiment report v6

**Date:** 2026-09-02  
**Baseline:** public research release v0.1.62; frozen STACKWISE Empirical Evidence Benchmark v1.0.0  
**Purpose:** answer the methodological requests from Array reviewers before any manuscript rewriting.  
**Guardrail:** no confirmatory external-campaign result or frozen admissibility label was overwritten. All R6 sensitivity analyses are post-review/non-confirmatory.

## 1. Baseline reconstruction and reproducibility

The working tree was reconstructed at content level from the last full project archive, the public v0.1.62 overlay, and the public-repository hygiene changes. The frozen benchmark remains v1.0.0.

During fresh replay, one reproducibility defect was found in the v0.1.62 public overlay: `scripts/run_external_validation.py` imports `stackwise.external_validation`, but that module was absent from the public source tree. A minimal module was reconstructed from the frozen implementation semantics and validated by exact replay tests against the public v0.1.62 result artefacts. The replay reproduces the frozen external mapping, candidate readiness, held-out transitions, and MR1 preference-robustness tables exactly.

Full regression status after the revision additions: **336 passed, 11 skipped**. Public-repository audit: **OK, 0 errors / 0 warnings**.

## 2. R6-A — construct validity of C0/C1/C2/E0

### 2.1 Four-class primary audit

Four independent expert-group raters assessed 35 relations, giving 140 expert votes.

- Fleiss' kappa: **0.5367**.
- Observed pairwise agreement: **79.52%**.
- Item-bootstrap 95% CI for Fleiss' kappa: **[0.4076, 0.6297]**.
- Bootstrap: 20,000 item-level resamples, seed 20260816.
- Frozen label distribution: C0=0, C1=8, C2=3, E0=24.

### 2.2 Confusion matrix: frozen classifier vs all expert votes

| Frozen class | Expert C0 | Expert C1 | Expert C2 | Expert E0 |
|---|---:|---:|---:|---:|
| C0_DIRECT | 0 | 0 | 0 | 0 |
| C1_BRIDGEABLE | 7 | 14 | 10 | 1 |
| C2_CONDITIONAL | 0 | 0 | 3 | 9 |
| E0_MISSING | 0 | 3 | 1 | 92 |

### 2.3 Class-specific agreement

| Frozen class | Items | Exact expert-vote agreement | >=3/4 item consensus matching frozen | Unanimous items matching frozen |
|---|---:|---:|---:|---:|
| C0_DIRECT | 0 | not estimable | not estimable | 0 |
| C1_BRIDGEABLE | 8 | **43.75%** | **25.0%** | 0 |
| C2_CONDITIONAL | 3 | **25.0%** | **33.3%** | 0 |
| E0_MISSING | 24 | **95.83%** | **100%** | 20 |

Interpretation: the four-class taxonomy is highly reproducible for `E0_MISSING`, while the principal ambiguity is the severity of admissible bridges (C0/C1/C2), exactly where the manuscript already identified semantic discretion. No C0 item was present in the frozen primary audit, so C0 class-specific performance cannot be estimated from this audit.

### 2.4 Pre-specified operational boundary collapse

For an operational gate, classes were also collapsed without replacing the primary four-class analysis:

- `{C0_DIRECT, C1_BRIDGEABLE}` -> `NO_EXTERNAL_ASSUMPTION`
- `{C2_CONDITIONAL, E0_MISSING}` -> `ASSUMPTION_OR_MISSING`

Results:

- Expert Fleiss' kappa: **0.6312**.
- Expert observed pairwise agreement: **89.52%**.
- Frozen algorithm vs all 140 expert votes exact agreement on this binary operational boundary: **90.0%**.

This is supplementary evidence that the practically important boundary "can proceed without an external assumption" is more reproducible than the finer four-class severity labels. It does not replace the primary four-class audit.

## 3. R6-B — expert-consensus downstream sensitivity

Three schemes were compared:

1. `FROZEN`: original algorithmic labels.
2. `MAJORITY_SUBSTITUTION`: substitute only >=3/4 expert consensus; ties/pluralities keep the frozen class.
3. `CONSERVATIVE_MAJORITY`: apply only >=3/4 changes that are more conservative than the frozen class.

The main expert-consensus changes were:

- I02: C2 -> E0 (4/4).
- I14: C1 -> C2 (3/4).
- I12: C1 -> C0 (3/4; upgrade, therefore excluded in conservative scheme).
- E06: C2 -> E0 (4/4).
- E09: C1 -> C2 (3/4).

### 3.1 Relation-level distributions

Internal 20 relations:

- Frozen: E0=14, C1=5, C2=1, C0=0.
- Majority substitution: E0=15, C1=3, C2=1, C0=1.
- Conservative majority: E0=15, C1=4, C2=1, C0=0.

External held-out 15 relations:

- Frozen: E0=10, C1=3, C2=2.
- Majority/conservative: E0=11, C1=2, C2=2.

### 3.2 Primary downstream conclusions

- Held-out candidate-target transition rows changed: **0/8**.
- External scenario x candidate readiness states changed: **0/45**.
- Internal first-slice candidate-criterion states changed: **0/42**.
- Canonically complete two-criterion candidates: **0** under all three schemes.
- Povalac negative-control class becomes *more conservative*: C2 -> E0; it never becomes C0.

### 3.3 Full Stage-5E follow-up sensitivity

A broader 120 candidate-target-row follow-up was also evaluated to localize any effect beyond the primary summaries:

- Majority substitution: **3/120** status categories change.
- Conservative majority: **3/120** status categories change.
- All three changes are `ROBUSTNESS_ONLY -> MISSING` for the classical-LoRa delivery target in three scenarios.
- Ready target rows remain **0**.
- Feasible first-slice fully-ready candidates remain **0**.
- Therefore, the candidate-level `DECISION_READY` conclusion is unchanged.

Interpretation: expert disagreement affects the *severity label* of three non-ready LoRaWAN delivery rows but does not create or remove a decision-ready candidate and does not alter the primary external-abstention conclusion.

## 4. R6-C — uncertainty/readiness structural invariance

The current Stage-5E implementation was evaluated under three uncertainty metadata variants while keeping feasibility, source-target admissibility, profiles and bridge-materialization states fixed:

- baseline uncertainty metadata;
- all-pessimistic uncertainty labels;
- all-optimistic uncertainty labels.

For each variant, **120 candidate-target rows** were evaluated. Readiness status changes relative to baseline: **0/120** for both alternative variants.

This is an implementation-property result, not a claim that uncertainty is unimportant. In the current Stage-5E contract there is no probabilistic precision threshold, so uncertainty metadata is preserved/propagated after admissibility but cannot by itself upgrade E0/C2 evidence or override hard feasibility. A future target contract such as `P(latency < L) >= 0.95` could make uncertainty directly decision-gating.

## 5. R6-D — computational-overhead sanity check

The actual Stage-5E readiness builder was benchmarked over 3,000 iterations after warm-up, with 120 candidate-target rows per iteration (24 non-infeasible scenario-candidate pairs x 5 targets).

Environment: Linux / Python 3.13.5.

- median: **0.236 ms** per 120-row readiness evaluation;
- p95: **0.387 ms**;
- mean: **0.267 ms**.

This is an illustrative implementation sanity check only, not a cross-hardware performance claim. It supports the narrower statement that readiness bookkeeping is computationally negligible relative to measurement or network simulation in this implementation.

## 6. Reviewer questions now closed experimentally

The following reviewer requests are now directly supported by new/re-expressed results:

- class-specific admissibility agreement: **done**;
- four-class confusion matrix: **done**;
- uncertainty around kappa: **done**;
- expert-consensus impact on downstream readiness: **done**;
- conservative alternative-label envelope: **done**;
- uncertainty-assumption effect on the current readiness implementation: **done**;
- computational-overhead sanity check: **done**;
- frozen public-result replay: **done**.

## 7. Experiments deliberately not added

No new experiment is recommended before rewriting the manuscript for the following reviewer suggestions:

1. **Real multi-operator invoices / billing records.** The current accounting claim is boundary sensitivity, not market prevalence. Invoice-calibrated multi-operator validation is a future external-economic-validation study, not required to support the existing scoped claim.
2. **New prospective external deployments / third use-case family.** This would constitute a new prospective validation campaign and materially expand the study. It should be future work rather than post-review accommodation.
3. **New or balanced expert audit.** A post-hoc second audit designed after observing the C1/C2 disagreements risks tuning the construct validation. The requested class-specific diagnostics and downstream sensitivity are now available from the frozen audit.
4. **New continuous-criterion MCDA campaign.** The preference experiment is explicitly a deterministic four-feature structural stress test; it should be scoped as such rather than generalized to empirical MCDA-failure prevalence.
5. **External winner accuracy / unnecessary-abstention rate.** These require independently labelled ground truth that the present evidence does not contain. The revision should distinguish evidence-readiness correctness from downstream decision correctness rather than invent a proxy ground truth.

## 8. Reproducibility action before manuscript resubmission

Recommended public revision release: **v0.1.63** after the manuscript response is finalized. It should include the new scripts, tests, anonymized derived audit tables and reviewer-revision results. A DOI-backed archival software/research-compendium snapshot should then be deposited (e.g. Zenodo), as explicitly requested by Reviewer 1.

