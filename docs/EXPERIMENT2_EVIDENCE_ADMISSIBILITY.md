# Experiment 2 — evidence-grade and admissibility ablation

## Question

Does high source/provenance quality imply that evidence is decision-ready for the canonical STACKWISE criteria, and how much apparent decision space is created when admissibility requirements are progressively relaxed?

## Frozen inputs

- STACKWISE Empirical Evidence Benchmark v1.0.0 scientific state;
- Stage-2 core-four evidence summary and source→decision-target gap matrix;
- Stage-6A feasible-candidate criterion-readiness matrix;
- Stage-6C lifecycle-cost robustness family for the four periodic-tracking IP-cellular candidates.

No new empirical values are introduced. No missing energy, cost, reliability, latency or coverage values are imputed.

## Two separate quality axes

The experiment explicitly preserves the Stage-2 decision that `source_grade` is a provenance/accessibility grade, not a substitute for inferential strength or target compatibility.

### Source-grade ladder

`A only → A+B → A+B+C → A+B+C+D`

All four core sources are Grade A. Therefore every rung retains all 4 core datasets and all 398 canonical evidence records. This is a deliberate negative result: source-grade ablation alone cannot distinguish decision admissibility in the frozen core-four benchmark.

### Source→target admissibility ladder

Across 4 datasets × 5 canonical decision targets = 20 relations:

- C0 direct: 0;
- C1 bridgeable: 5;
- C2 conditional: 1;
- missing: 14.

Counting bridgeable or conditional evidence as 'available' increases apparent target coverage, but does not authorise a score. A Grade-A-only rule that ignores relation class would count all 20 source×target cells despite 14 being explicitly missing.

## Candidate-level first-slice ablation

The first publication slice requires energy/report and lifecycle cost for each of the 21 feasible candidate incidences, giving 42 candidate×criterion cells.

After overlaying the validated Stage-6C cost family:

- 4/42 are `READY_ROBUSTNESS_FAMILY`;
- 6/42 are context-only cost evidence;
- 10/42 have structural energy-transfer support but no canonical energy target;
- 22/42 remain otherwise blocked.

The admissibility ladder is:

1. **D0 canonical ready only** — 4 cells counted, 0 complete candidates;
2. **D1 ready + context** — 10 cells counted, still 0 complete candidates;
3. **D2 context + structural transfer, counterfactual** — 20 cells counted and 10 candidates in 3 scenarios appear complete, but this is not scientifically authorised because structural transfer is not a canonical energy target;
4. **D3 explicit assumption-prior counterfactual** — all 42 cells and all 21 candidates appear complete by construction; this is included only to quantify assumption-driven decision-space inflation.

No D2/D3 result is a candidate ranking or a publication MCDA result.

## Interpretation

The core result is that **Grade-A provenance is not equivalent to decision-ready evidence**. All 398 records can come from excellent, open, well-documented empirical sources while the canonical decision targets remain largely unidentified at the required boundary. Apparent decision coverage expands rapidly when bridgeable/contextual/assumption evidence is treated as if it were score-ready, but that expansion is methodological rather than empirical.
