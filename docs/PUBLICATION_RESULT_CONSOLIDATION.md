# Publication-result consolidation — Experiments 1–4

Status: **closed in v0.1.56**. Benchmark input: **STACKWISE Empirical Evidence Benchmark v1.0.0**.

This consolidation freezes the four completed publication experiments and separates claims that are directly supported from claims that remain open. It does not create a new ranking, impute blocked criteria, or reopen transport/accounting details.

## Closed publication results

1. **Feasibility-first:** score-first top sets contain hard-infeasible stacks in 142/175 evaluable scenario–preference-anchor rows, and score-first still returns a top set in all 70 rows from scenarios with no feasible alternative.
2. **Evidence admissibility:** all 398 canonical evidence records come from Grade-A sources, yet the 20 source×target relations contain 0 direct, 5 bridgeable, 1 conditional and 14 missing relations. Canonical energy+cost completeness remains 0 candidates; inadmissible relaxation inflates it to 10 or 21.
3. **Uncertainty semantics:** Vomhoff uncertainty confirms the source-level point ordering while quantifying unequal precision; LoED temporal model choice changes uncertainty scale by about 1.39–1.70×; paired lifecycle-cost states produce 172 CoAP-cheaper rows, 116 ties and 0 MQTT-cheaper reversals despite overlapping marginal ranges.
4. **Accounting simplification:** payload-only accounting produces 252/288 false-within tariff classifications relative to billing-aware accounting and understates five-year connectivity cost by a median €50 and up to €100/device in the retained sensitivity family.

Counts over deterministic preference, robustness or sensitivity states are **not probabilities of deployment or stakeholder preference**.

## Publication claims

Strong and authorised claims:

- release of a harmonised, provenance-preserving empirical evidence benchmark;
- layer-aware end-to-end stack modelling with hard feasibility before preference;
- explicit separation of source quality from decision-target admissibility;
- preservation of heterogeneous uncertainty semantics and dependence;
- quantified tariff/cost error caused by simplified protocol/accounting boundaries.

Claims that must not be made in the current article without additional evidence:

- a publication-grade global stochastic ranking of all candidate stacks;
- absolute matched whole-device energy/report ranking of the four IP-cellular candidates;
- fleet-level simplification/portfolio penalty, unless one final fleet feasibility experiment is added.

## Recommended article scope

A narrower article is already supportable if the fleet claim and global stochastic ranking are dropped. To retain the original heterogeneous-fleet story, add one final experiment based only on the frozen hard-feasibility matrix: minimum stack/technology portfolio cardinality and serviceability loss under single-technology / at-most-two-technology restrictions. This experiment must not introduce synthetic energy or price values.

## Figure plan

Keep the main paper compact: one framework workflow figure; the main feasibility-first figure; candidate decision-space inflation; one three-panel uncertainty figure; the accounting misclassification figure; and lifecycle-cost underestimation. Move redundant or technical-detail figures to supplementary material.

Machine-readable outputs are under `results/publication/result_consolidation/`.
