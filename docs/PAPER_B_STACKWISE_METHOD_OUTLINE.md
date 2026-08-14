# Paper B — STACKWISE methodology and results

Working title: **STACKWISE: Feasibility-, Evidence- and Uncertainty-Aware Selection of IoT Communication Stacks**

Central research question: **What decision errors and structural conclusions arise when IoT stack selection explicitly respects hard feasibility, evidence admissibility, heterogeneous uncertainty, full accounting boundaries and fleet heterogeneity?**

## Scope boundary

Benchmark v1.0.0 is a frozen external input artifact and is described only briefly. The paper must not repeat the data-paper harmonisation narrative or reproduce its dataset validation section.

## Proposed structure

1. **Introduction** — stack-selection problem; why score-first, evidence flattening and accounting simplification are unsafe; contributions.
2. **Related work** — IoT technology selection/MCDA, empirical benchmarking, uncertainty-aware decision methods and fleet/network heterogeneity; precise gap.
3. **STACKWISE framework** — layer-aware stack representation; hard feasibility before preference; evidence admissibility; uncertainty/dependence semantics; accounting boundaries; fleet portfolio layer.
4. **Benchmark input and experimental protocol** — short description of Benchmark v1.0.0; frozen 7×9 matrix; no global stochastic ranking; deterministic grids/robustness families are not probability distributions.
5. **Experiment 1: feasibility-first versus score-first** — 142/175 evaluable rows contaminated by hard-infeasible top sets; 70/70 no-feasible rows where score-first still returns a top set.
6. **Experiment 2: evidence admissibility ablation** — Grade A does not imply decision-ready; 0 direct / 5 bridgeable / 1 conditional / 14 missing; candidate-space inflation 0→10→21 under relaxed assumptions.
7. **Experiment 3: uncertainty-aware treatment** — Vomhoff precision, LoED block-model sensitivity, paired lifecycle-cost state analysis; preserve dependence and avoid pooled epistemic probability.
8. **Experiment 4: accounting/cost simplification** — 252/288 payload-only false-within classifications; median €50 and maximum €100/device/5y underestimation in retained family.
9. **Experiment 5: fleet portfolio feasibility** — best single option 4/5 strict-serviceable scenarios; two-element minimum strict portfolio; unique family-level cellular+LoRaWAN result; unresolved sensitivity adds Thread only conditionally.
10. **Discussion** — what each experiment establishes; interaction between feasibility, evidence, uncertainty and accounting; practical implications.
11. **Limitations and future validation** — no publication-grade global stochastic ranking; no matched whole-device cellular energy/report comparison; no device-count-weighted lifecycle-cost fleet optimisation.
12. **Conclusion**.

## Main figure/table budget

Use the existing final consolidation plan: six main figures and three main tables. Move full preference grids, raw ablation tables, 288/576-state details and complete portfolio enumerations to supplementary material.

## Claims explicitly prohibited

Do not claim a universal best IoT stack, probabilistic superiority across epistemic states, a complete global SMAA ranking or an experimentally matched four-candidate cellular energy comparison.
