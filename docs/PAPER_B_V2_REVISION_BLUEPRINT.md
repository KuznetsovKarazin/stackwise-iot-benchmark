# STACKWISE Paper B v2 — Revision Blueprint

## Central thesis

STACKWISE is not another IoT ranking algorithm. It is an evidence-readiness layer placed before simulation or MCDA. Its role is to determine whether a candidate is structurally feasible and whether available empirical evidence is admissible for the exact decision targets and accounting boundaries before preference aggregation is allowed.

## Contributions to claim in v2

1. A unified decision-readiness algorithm with explicit states: `INFEASIBLE`, `UNRESOLVED`, `FEASIBLE_BUT_EVIDENCE_INCOMPLETE`, `DECISION_READY`.
2. A target-specific admissibility contract (`C0/C1/C2/E0`) that separates source provenance from inferential applicability.
3. Internal stress tests showing that preference-before-feasibility can contaminate top sets across multiple preference operators.
4. Held-out evidence validation showing prospective gap closure only when measurement boundaries support the target, plus a preregistered negative control for delivery probability.
5. External scenario stress validation showing conservative abstention when independently authored use cases exceed the frozen ontology.
6. Source-specific uncertainty contracts and broad accounting-boundary robustness.
7. Independent blind audit by four independent expert groups, establishing moderate semantic reproducibility and identifying disputed bridge boundaries.

## Claims to demote or remove

- Do not present hard-feasibility-before-ranking as novel by itself; HINTS already performs pre-selection.
- Do not claim full external decision portability to the five external cases.
- Do not claim universal heterogeneous fleet necessity; keep the portfolio result as benchmark-specific secondary analysis.
- Do not call HINTS/Vannieuwenborg cases IID replicates.
- Do not change the frozen admissibility labels using expert feedback in confirmatory analyses.

## Proposed manuscript structure

1. Introduction and problem statement
2. Related work and explicit comparison with HINTS/Vannieuwenborg
3. Unified STACKWISE Decision-Readiness Algorithm
4. Frozen benchmark and preregistered validation design
5. Internal methodological stress tests
   - feasibility vs preference ordering
   - admissibility inflation
   - uncertainty contracts
   - accounting-boundary robustness
6. External validation
   - external use-case ontology portability and abstention
   - held-out evidence gap closure
   - preregistered LoRaWAN negative control
   - independent blind expert audit
7. Secondary portfolio analysis and sensitivity
8. Threats to validity
9. Discussion
10. Reproducibility and data/code availability
11. Conclusions

## Figures recommended

- Fig. 1: Unified STACKWISE decision-readiness pipeline vs conventional evaluation/ranking pipeline.
- Fig. 2: Comparative positioning table/diagram vs HINTS and related methods.
- Fig. 3: Internal feasibility-ordering robustness across three preference operators.
- Fig. 4: External scenario portability + decision-state outcomes.
- Fig. 5: Held-out evidence transitions and negative control.
- Fig. 6: Accounting factorial robustness.
- Optional Fig. 7: Expert-audit agreement/disagreement map; otherwise keep as a table.

## Main quantitative results for abstract

Prefer only four quantitative anchors:

- 77.1–85.1% top-set contamination across three preference operators among cases with feasible alternatives;
- 38/45 external case–candidate assessments remain `UNRESOLVED` and 7/45 `INFEASIBLE`, with no forced `DECISION_READY` result;
- 83.3% of 1,350 workload/tariff regimes contain at least one payload-only billing misclassification across 388,800 deterministic states;
- 4 independent expert groups: Fleiss' kappa 0.537; 3/4-or-better consensus on 32/35 items, matching the frozen classifier on 27/32 (84.4%).

## Required threat-to-validity statements

- External scenarios are published case studies, not new physical deployments.
- The frozen STACKWISE ontology under-represents many HINTS/Vannieuwenborg requirements; this is a finding, not hidden missingness.
- Admissibility classes involve semantic judgment and show moderate, not perfect, independent expert reproducibility.
- The benchmark's technology universe is limited and is not exhaustive of current IoT connectivity options.
- Accounting sensitivity is deterministic state-space coverage, not a probability distribution over real deployments.
- External held-out sources test evidence-boundary behavior, not end-to-end winner accuracy.
