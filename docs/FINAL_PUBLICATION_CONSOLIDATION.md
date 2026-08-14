# Final publication consolidation — Experiments 1–5

Status: **finalised in v0.1.58**. Benchmark input: **STACKWISE Empirical Evidence Benchmark v1.0.0**.

The experimental programme is closed after five publication-oriented experiments. No Experiment 6 is planned. The benchmark content remains frozen.

## Final authorised methodology claims

1. **Feasibility before preference.** Score-first top sets contain hard-infeasible stacks in 142/175 evaluable scenario–preference-anchor rows; score-first still returns a top set in all 70 rows from the two no-feasible scenarios.
2. **Evidence quality is not decision admissibility.** All 398 canonical records are Grade A, yet source×target relations are 0 direct, 5 bridgeable, 1 conditional and 14 missing; inadmissible relaxation inflates complete candidate count from 0 to 10 or 21.
3. **Uncertainty semantics and dependence matter.** Vomhoff uncertainty confirms ordering with unequal precision; LoED block-model choice changes uncertainty scale; aligned lifecycle-cost states show 172 CoAP-cheaper, 116 ties and 0 MQTT-cheaper reversals despite overlapping marginal ranges.
4. **Accounting simplification has measurable cost.** Payload-only accounting gives 252/288 false-within tariff classifications and understates five-year connectivity cost by a median €50 and up to €100/device in the retained family.
5. **Fleet heterogeneity is structurally required.** The best single stack/technology/family covers only 4/5 strictly serviceable scenario classes. Complete strict coverage requires two elements; cellular + LoRaWAN is the unique minimum family-level portfolio. Treating unresolved feasibility only as an optimistic sensitivity increases the minimum to three elements and adds Thread.

The Benchmark v1.0.0 resource claim is also strong, but it is assigned primarily to the separate data paper.

## Claims that remain explicitly blocked

- no publication-grade global stochastic ranking of all candidate stacks;
- no matched whole-device energy/report comparison across the four cellular IP candidates.

These are scope limitations/future work, not blockers for the two recommended manuscripts.

## Publication strategy

Use two manuscripts with distinct research questions.

### Data/benchmark paper

Research question: **How can heterogeneous public IoT measurements be transformed into a traceable, layer-aware and uncertainty-aware empirical benchmark without erasing statistical units, accounting boundaries or provenance?**

Primary content: four upstream sources and licences; harmonisation; canonical records; schemas; statistical/independence units; measurement boundaries; uncertainty/dependence metadata; benchmark scenarios/stacks as dataset definitions; technical validation; release QA; reproducibility and FAIR packaging. Experiments 1–5 are excluded.

### STACKWISE methodology/results paper

Research question: **What decision errors and structural conclusions arise when IoT stack selection explicitly respects hard feasibility, evidence admissibility, heterogeneous uncertainty, full accounting boundaries and fleet heterogeneity?**

Primary content: framework plus Experiments 1–5. The Benchmark v1.0.0 is cited as the frozen input artifact and described only briefly.

Machine-readable outputs are under `results/publication/final_consolidation/`.
