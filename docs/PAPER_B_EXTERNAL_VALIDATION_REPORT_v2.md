# STACKWISE Paper B — External Validation Campaign Report v1

Status: **OUTCOME ANALYSIS COMPLETE UNDER PRE-DATA FREEZE**  
Target manuscript: Paper B / Elsevier *Internet of Things*  
Frozen benchmark input: STACKWISE Empirical Evidence Benchmark v1.0.0  
Protocol freeze: `2026-08-16T11:33:49.808703+00:00`

## 1. Executive assessment

The external-validation campaign materially strengthens Paper B, but it does so in a deliberately asymmetric way.

The strongest positive findings are:

1. the feasibility-ordering failure persists across three preference operators and remains visible under leave-one-feature-out sensitivity, so it is not a weighted-sum artefact;
2. held-out NB-IoT operational evidence closes three previously missing link-support relations to `C1_BRIDGEABLE` without being promoted to direct serviceability probability;
3. the pre-registered LoRaWAN sniffer negative control passes: observed receptions are not promoted to direct delivery probability in the absence of an attempted-transmission denominator;
4. a held-out NB-IoT power dataset adds independent energy-component support without erasing whole-device/report-boundary gaps;
5. the accounting-boundary conclusion persists over a 388,800-state factorial expansion rather than only at the original tariff point, and the generalized implementation reproduces all 288 original accounting states exactly at the frozen original point.

The main limiting finding is equally important: the frozen STACKWISE scenario ontology does not fully represent the independently authored HINTS and Vannieuwenborg use cases. Only 21 of 46 hard requirements map as `exact` or `interpretable`; 25 are unavailable and 6 source conflicts are retained. Consequently, none of the five external use cases passes the pre-registered Tier-C threshold, and external portfolio/set-cover analysis is withheld rather than extending the ontology after seeing the data.

This outcome should be presented as **external stress validation of conservative decision-readiness semantics**, not as evidence that the frozen STACKWISE ontology already generalises completely to arbitrary IoT applications.

## 2. Pre-data integrity

The external-validation protocol was frozen before outcome-producing analyses. The frozen manifest pins:

- the external-validation protocol;
- five external use-case definitions;
- three held-out empirical sources and their selected files;
- the canonical evidence-boundary taxonomy;
- the evidence metric catalogue;
- candidate-stack and component catalogues;
- the Benchmark v1.0.0 hard-feasibility matrix;
- HINTS source-document artefacts and the pre-outcome discrepancy ledger.

The frozen policy prohibits post-outcome creation of new admissibility classes, silent imputation of missing external requirements, post-hoc hard-constraint relaxation, or canonical-schema extension for the primary validation.

## 3. External use-case portability

Five independently authored use cases were transcribed before outcomes:

- HINTS smart building;
- HINTS event video-surveillance;
- HINTS precision agriculture;
- Vannieuwenborg smart shipping containers;
- Vannieuwenborg smart parking.

Across 46 hard requirements:

| Mapping status | Count |
|---|---:|
| Exact | 10 |
| Interpretable | 11 |
| Unavailable in frozen ontology | 25 |
| Recorded source conflicts | 6 |

Per-case hard-requirement mapping fractions were 0.500, 0.583, 0.462, 0.200 and 0.250, respectively. All five cases remain valid Tier-A ontology-portability cases and Tier-B readiness stress cases, but **zero** satisfy the Tier-C portfolio threshold.

The HINTS source inspection itself exposed several published/companion inconsistencies that were recorded before outcome analysis rather than silently reconciled. Examples include smart-building scope (100 m in narrative vs 50 m in the summary table), event-surveillance scope (60 m vs 30 m), and precision-agriculture delivery/battery targets with conflicting values across narrative and tables. These conflicts are retained as unresolved source semantics.

## 4. External decision-readiness behavior

The five external cases were crossed with the nine frozen candidate stacks, yielding 45 case-candidate assessments:

| Final state | Count |
|---|---:|
| `INFEASIBLE` | 7 |
| `UNRESOLVED` | 38 |
| `FEASIBLE_BUT_EVIDENCE_INCOMPLETE` | 0 |
| `DECISION_READY` | 0 |

The seven `INFEASIBLE` outcomes occur where an externally specified technology restriction is structurally incompatible with a candidate. The remaining 38 assessments stay `UNRESOLVED` because one or more hard requirements are unmapped/conflicting or because the frozen structural/evidence substrate lacks a verified capability needed to assert readiness.

This is not positive full-ontology portability. It is, however, a direct test of the framework's advertised no-forced-decision property: independent use cases do not receive invented values or forced winners when the frozen representation is insufficient.

## 5. Held-out empirical evidence validation

### EV-E1: Kousias operational NB-IoT measurements

The selected held-out file contains 281,481 passive NB-IoT radio/network observations across 80 campaign labels and 249 serving-cell identities. It contains RSRP/RSRQ/SINR-type link evidence but no device-energy measurement and no complete attempted-transmission denominator.

For each of the three NB-IoT candidate stacks, the link-support target transitions from `E0_MISSING` to `C1_BRIDGEABLE`. The held-out source therefore closes a genuine evidence gap while remaining correctly below `C0_DIRECT` because signal measurements do not directly identify a link-serviceability probability estimand.

### EV-E2: Povalac & Kral LoRaWAN sniffer dataset

The selected archive contains 62 non-empty CSV files across seven dataset prefixes. The source boundary is observed LoRaWAN sniffer packet receptions. The pre-registered negative control required that such receptions must not become direct delivery probability without an attempted-transmission denominator.

The negative control passes. Delivery remains `C2_CONDITIONAL`; link context remains `C1_BRIDGEABLE`. No inappropriate `C0_DIRECT` transition occurs.

### EV-E3: Leenders & Callebaut NB-IoT power measurements

Thirteen usable payload traces were reproduced from the selected measurement family for payloads from 10 to 390 bytes. The source provides independent NB-IoT energy-component evidence and accompanying link context.

For the two NB-IoT IP stacks, energy remains `C1_BRIDGEABLE` but gains independent measured component support. For the non-IP NB-IoT stack, energy moves from `E0_MISSING` to `C2_CONDITIONAL`, because the measurement context does not identify the target non-IP application-report boundary.

Across all 15 held-out source-target relations the frozen classifier returns:

- 0 `C0_DIRECT`;
- 3 `C1_BRIDGEABLE`;
- 2 `C2_CONDITIONAL`;
- 10 `E0_MISSING`.

This is a useful result rather than a failure: independent datasets add evidence where their measurement boundaries justify it, while unrelated estimands remain missing.

## 6. MR1 — preference-operator and feature sensitivity

For the full four-feature structural representation and the pre-registered simplex grid, among the 175 evaluations with at least one feasible candidate:

| Preference operator | Any infeasible at top | All top infeasible | Unique infeasible winner |
|---|---:|---:|---:|
| Weighted sum | 81.14% | 65.71% | 40.00% |
| TOPSIS | 77.14% | 61.71% | 34.29% |
| Weighted Chebyshev | 85.14% | 51.43% | 25.71% |

Thus the original ordering problem is not specific to weighted-sum scoring and is not explained only by ties. However, leave-one-feature-out analysis shows that the unique-infeasible-winner rate can collapse for some feature subsets, so the robust claim should concern **top-set contamination and ordering**, not a universal unique-winner rate.

## 7. MR3 — uncertainty contracts

The revised method treats uncertainty as three explicit contracts rather than one generic probabilistic layer:

- `U1`: physical-run nonparametric bootstrap for Vomhoff, 10,000 replicates, seed 20260811, marginal 2.5/97.5 percentiles, preserving shared-run dependence;
- `U2`: LoED temporal model-form robustness using 3-, 7- and 14-day non-circular overlapping source-day blocks, 5,000 resamples per campaign/block length, seed 20260811, without assigning probabilities to block-length alternatives;
- `U3`: deterministic aligned finite-state lifecycle-cost enumeration, with paired state comparison and no bootstrap/probability interpretation.

This makes explicit that the three analyses answer different uncertainty questions and should not be pooled into one confidence statement.

## 8. MR4 — accounting robustness beyond one tariff point

A factorial expansion covers:

- payloads: 32, 64, 128, 256, 512, 1024 bytes;
- reporting intervals: 300, 900, 3600, 21600, 86400 s;
- nominal allowances: 50, 100, 250, 500, 1000 MB;
- billing increments: 50, 100, 500 MB;
- horizons: 1, 3, 5 years;
- the same 288 standards/session/billing states per workload/tariff setting.

This yields 1,350 workload/tariff regimes and 388,800 deterministic state rows.

Results:

- payload-only top-up/tariff-class differs from billing-aware accounting in **17.21% of all expanded states**;
- **83.33% of workload/tariff regimes** contain at least one classification error;
- **17.11% of regimes** have errors in a majority of their deterministic protocol/billing states;
- relative billed-volume undercount has median **74.4%**, 5th percentile **20.62%**, 95th percentile **97.20%**.

These are deterministic state-space coverage fractions, not deployment probabilities.

A dedicated reproduction diagnostic evaluates the generalized engine at the exact original Experiment-4 point (64-byte payload, 60-s reporting interval, five-year horizon, 500-MB allowance and 500-MB increment). All 288 states match the frozen original L0-L4 byte totals **exactly**, with maximum absolute difference 0 bytes at every level.

## 9. MR5 — portfolio robustness and required claim downgrade

The frozen internal five-scenario strict universe requires two access families (`cellular|lorawan`). Leave-one-scenario-out analysis gives:

- four of five omissions: minimum remains two families;
- omitting `environmental_private_lorawan`: minimum collapses to one family (`cellular`).

Therefore the internal portfolio result is not universally robust to scenario composition. It is specifically dependent on retaining at least one scenario with a genuinely LoRaWAN-exclusive structural requirement.

Because no external use case passed the pre-registered Tier-C mapping threshold, external and combined set-cover analyses are **withheld**. Paper B should no longer present heterogeneous portfolio necessity as a general external conclusion. It can remain as a benchmark-specific structural result and sensitivity example.

## 10. Implications for Paper B v2

### Promote to central contribution

1. Evidence provenance and target admissibility are distinct decision properties.
2. The framework can preserve no-decision/unresolved states under independently authored cases rather than manufacturing completeness.
3. Held-out datasets close only boundary-compatible evidence gaps; a pre-registered negative control confirms that receive-side observations are not promoted to direct delivery probability.
4. Feasibility-before-preference is robust to multiple preference operators and persists under feature sensitivity, although it is not claimed as a novel principle by itself.
5. Accounting-boundary error remains material across a broad workload/tariff grid rather than a single chosen threshold.

### Demote/narrow

1. Do not claim that the frozen STACKWISE scenario ontology fully generalises to the five external cases.
2. Do not claim external decision winners for HINTS/Vannieuwenborg cases.
3. Do not retain fleet heterogeneity as a universal headline; report it as an internal scenario-universe result whose sensitivity is quantified.
4. Do not treat the five external cases as IID statistical replicates.

### Manuscript structure recommended

1. Problem and positioning relative to HINTS.
2. Unified STACKWISE Decision-Readiness Algorithm.
3. Frozen benchmark and pre-registered external-validation design.
4. Internal stress tests (condensed RQ1-RQ4; fleet as secondary).
5. External scenario portability and no-forced-decision test.
6. Held-out evidence gap-closure and negative-control experiment.
7. Robustness analyses (preference operators, uncertainty contracts, accounting factorial).
8. Threats to validity.
9. Discussion and scope guardrails.

## 11. Independent blind admissibility audit

The remaining semantic-validation item was completed after the external-validation outcomes were frozen. Four independent expert groups, anonymised as Raters A--D, classified the same 35 blinded source--target relations without access to the STACKWISE algorithmic labels.

The audit comprises 20 internal frozen-benchmark relations and 15 held-out external-source relations. The frozen algorithmic class distribution is imbalanced: 24 `E0_MISSING`, 8 `C1_BRIDGEABLE`, 3 `C2_CONDITIONAL`, and 0 `C0_DIRECT`. Raw agreement is therefore reported together with kappa statistics.

| Independent group representative | Agreement with frozen classifier | Cohen's kappa | Internal agreement | Held-out agreement |
|---|---:|---:|---:|---:|
| Rater A | 80.0% (28/35) | 0.558 | 80.0% | 80.0% |
| Rater B | 80.0% (28/35) | 0.543 | 80.0% | 80.0% |
| Rater C | 65.7% (23/35) | 0.332 | 65.0% | 66.7% |
| Rater D | 85.7% (30/35) | 0.685 | 80.0% | 93.3% |

Across the four independent groups, Fleiss' kappa is **0.537** overall, **0.497** for the internal relations, and **0.587** for the held-out relations. Unanimous 4/4 agreement occurs for **22/35 (62.9%)** items. At least 3/4 groups agree on the same class for **32/35 (91.4%)** items; two items are 2:2 ties and one is a 2:1:1 plurality. Among the 32 items with 3/4 or 4/4 consensus, the consensus matches the pre-specified frozen classifier in **27/32 (84.4%)** cases.

The strongest disagreements are not random. Two relations are unanimously judged more conservatively than the frozen classifier:

- `I02` (LoED → delivery probability): frozen `C2_CONDITIONAL`, experts 4/4 `E0_MISSING`;
- `E06` (Povalac LoRaWAN sniffer → delivery probability): frozen `C2_CONDITIONAL`, experts 4/4 `E0_MISSING`.

Two further relations show 3/4 expert preference for `C2_CONDITIONAL` over frozen `C1_BRIDGEABLE` (`I14` and `E09`, both feasible-link targets), while `I12` shows 3/4 expert preference for `C0_DIRECT` over frozen `C1_BRIDGEABLE` for a whole-device energy/report relation. These disagreements identify the bridge-severity boundaries as the main construct-validity uncertainty.

Crucially, the expert audit does **not** justify post-hoc relabelling of the primary results. The pre-specified frozen classifier remains unchanged. The audit is reported as an independent reproducibility assessment and as evidence that the four-class contract is useful but not perfectly observer-independent.


## 12. Final campaign-level conclusion

The external-validation campaign is now complete. It changes the evidential status of Paper B in five important ways:

1. **External scenarios stress the ontology rather than merely confirming it.** Five independently authored HINTS/Vannieuwenborg cases expose substantial unmapped requirements, so STACKWISE abstains instead of manufacturing decision readiness.
2. **Held-out datasets test prospective evidence behavior.** Independent NB-IoT operational and energy datasets close only boundary-compatible gaps, while unrelated targets remain missing or conditional.
3. **The pre-specified negative control passes.** LoRaWAN reception/sniffer data are not promoted to direct delivery probability without an attempted-transmission denominator.
4. **Core internal conclusions survive methodological variation.** Feasibility-ordering failure persists across weighted sum, TOPSIS and weighted Chebyshev; accounting-boundary error persists over 388,800 deterministic states.
5. **Independent human audit provides external semantic validation.** Four independent expert groups show moderate multi-rater agreement and 84.4% classifier agreement among items with 3/4 or 4/4 consensus, while exposing a small set of interpretable bridge-boundary disagreements.

The appropriate Paper-B claim is therefore not that STACKWISE always produces a correct winner. The stronger and more defensible claim is that STACKWISE provides an **evidence-readiness layer before simulation/MCDA** that (i) separates structural feasibility from preference, (ii) distinguishes provenance quality from target admissibility, (iii) preserves source-specific uncertainty and accounting boundaries, and (iv) can abstain when independently authored requirements or held-out evidence do not justify a complete decision.
