# Experiment 1 — Feasibility-First vs Score-First

## Purpose

Experiment 1 tests one of the central STACKWISE methodological claims: hard feasibility must be applied before preference scoring. The experiment is deliberately designed so that it does **not** require missing energy, lifecycle-cost, latency, delivery-probability or coverage values.

The input is frozen `STACKWISE Empirical Evidence Benchmark v1.0.0` only.

## Inputs

Three benchmark tables are used:

1. `candidate_stack_catalog.csv` — the 9 frozen candidate stacks;
2. `component_catalog.csv` — verified structural component roles/capabilities;
3. `refined_hard_feasibility_matrix.csv` — the complete 7×9 matrix with 21 feasible, 39 infeasible and 3 unresolved scenario–stack pairs.

No raw external dataset, Stage-6B synthetic energy fixture, smoke price or missing empirical metric enters this experiment.

## Score-first baseline

The score-first baseline is not presented as a recommended MCDA model or a stakeholder probability model. It is a **generic structural preference-envelope stress test** over four attributes that are fully observed for every candidate:

- `stack_parsimony`: mean inverse min–max component count and binding count;
- `explicit_transport_security`: presence of a verified end-to-end security component (TLS/DTLS);
- `operator_independence`: primary access does not require operator-managed access;
- `ip_interoperability`: the stack exposes an IP packet service.

All attributes lie in [0,1]. The four weights are enumerated on a deterministic simplex grid with step 0.25, producing 35 anchors. Anchor frequency has **no probability interpretation**.

For each of 7 scenarios and 35 anchors:

- **score-first** ranks all 9 candidates without considering hard feasibility;
- **feasibility-first** first retains `status == feasible`, then applies the identical soft score;
- if no feasible candidate exists, feasibility-first returns `NO_FEASIBLE_DECISION` rather than forcing a ranking;
- exact ties are retained as top sets instead of broken arbitrarily.

This gives 245 scenario×anchor evaluations for the primary grid. A grid-resolution sensitivity repeats the same experiment at simplex steps 0.5, 0.25, 0.2 and 0.1. Across these grids, the score-first top set contains a hard-infeasible alternative in approximately 78.6–82.9% of all deterministic anchors and 81.1–83.5% of anchors in scenarios with at least one feasible candidate. These are geometric grid-coverage diagnostics, not preference probabilities.

## Results

Frozen Benchmark v1.0.0 produces:

- score-first top set contains at least one hard-infeasible candidate in **193/245** evaluations;
- score-first top set is entirely hard-infeasible in **159/245** evaluations;
- among the 175 evaluations belonging to the five scenarios with at least one feasible candidate, hard-infeasible candidates contaminate the score-first top set in **142/175**, and the top set is entirely infeasible in **115/175**;
- the remaining two scenarios have no feasible candidate. Score-first nevertheless returns a top set in **70/70** anchor evaluations, whereas feasibility-first returns `NO_FEASIBLE_DECISION` in all 70;
- feasibility-first never forces a decision when the feasible set is empty;
- among evaluable scenarios the median soft-score concession required by feasibility filtering is **0.25** on the normalized structural-preference scale. This concession is descriptive over the deterministic grid, not a utility-loss probability.

## Interpretation

The experiment does not claim that the four structural criteria are the final STACKWISE MCDA criteria or that the 35 anchors approximate a population of stakeholder preferences. Its narrower claim is algorithmic:

> whenever hard constraints and soft preferences coexist, scoring all candidates first can produce top-ranked alternatives that are infeasible, and can create false decisiveness when no feasible alternative exists.

The result is robust over a declared deterministic preference envelope and is obtained without imputing missing empirical performance values.

## Publication scope

Experiment 1 supports the `feasibility before preference` contribution and is suitable for the main paper as an ordering/ablation experiment. It does **not** authorise a real performance ranking of the 9 candidate stacks.

## Reproduction

```powershell
python .\scripts\run_experiment1_feasibility_first.py
```

Outputs are written to:

`results/experiments/experiment1_feasibility_first/`

including the full scenario×anchor table, scenario summary, feature matrix, deterministic weight grid, figures, summary JSON and run manifest.
