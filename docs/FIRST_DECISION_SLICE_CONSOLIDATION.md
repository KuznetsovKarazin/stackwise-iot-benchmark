# Stage 6A — First Decision-Slice Consolidation

Version: **v0.1.46**

## Purpose

Stage 6A is the consolidation gate between evidence engineering and decision experiments. It does not add new protocol detail, new datasets, weights, rankings or imputed target values. It combines the frozen Stage-4 hard-feasibility result with the completed Stage-5 evidence, transfer, lifecycle-cost and transport-accounting work and asks a narrower question:

> Which feasible candidate/criterion pairs are now usable by a decision engine, which are only contextual robustness evidence, and which remain blocked?

The Stage-4 matrix remains frozen at **21 feasible / 39 infeasible / 3 unresolved**.

## First soft-decision slice

The first soft slice retains only two mandatory targets:

1. `expected_device_energy_per_application_report_j`;
2. `lifecycle_cost_eur`.

Latency and feasible-link/coverage remain upstream hard/contextual dimensions and are not scored again. Delivery probability remains deferred until an attempted-transmission denominator is identified. This avoids compensating a hard requirement with preference weights and avoids double counting.

## Updated readiness semantics

Stage 6 distinguishes target readiness from evidence usefulness:

- `READY_PROBABILISTIC` — target identified at the decision boundary with an admissible probability-bearing uncertainty representation;
- `READY_ROBUSTNESS_FAMILY` — target identified as an explicit unweighted epistemic/scenario family;
- `CONTEXT_ONLY` — evidence is informative but does not identify the required target in a scoreable form;
- `HARD_SCREEN_ONLY` — dimension remains upstream in non-compensatory feasibility;
- `DEFERRED` — optional target is excluded from the first soft slice;
- `BLOCKED` — required target is not decision-usable.

A `CONTEXT_ONLY` quantity is not silently promoted to an MCDA score.

## Consolidated checkpoint

Across the 21 feasible candidates and five canonical targets:

- criterion rows: **105**;
- mandatory soft-target rows: **42**;
- mandatory rows ready: **0**;
- mandatory rows with context-only evidence: **10**;
- mandatory rows blocked: **32**;
- feasible candidates with both mandatory soft targets ready: **0/21**.

Candidate-boundary report energy remains blocked for all 21 feasible candidates. The ten feasible IP-cellular incidences have the strongest progress: they have dated module/SIM/tariff evidence and Stage-5N raw-volume robustness context, but not a canonical EUR lifecycle-cost uncertainty representation.

For those ten IP-cellular candidates, the profile-level tariff-volume context is:

- **4** candidates robustly within the nominal raw 500-MB allowance across the compact Stage-5 sensitivity family (the four smart-meter IP candidates);
- **3** candidates robustly above the nominal raw allowance (the three MQTT/TLS tracking candidates);
- **3** candidates protocol-envelope-sensitive (the three CoAP/DTLS tracking candidates).

These are raw deterministic robustness classes, not exact billed-volume or TopUp results.

## Preferred development benchmark

Stage 6A selects the four-candidate IP-cellular subset in `asset_tracking_periodic_cross_cell` for **development and gap closure only**:

- NB-IoT + CoAP/DTLS/LwM2M;
- LTE-M + CoAP/DTLS/LwM2M;
- NB-IoT + MQTT/TLS/LwM2M;
- LTE-M + MQTT/TLS/LwM2M.

The subset is attractive because it is a common 60-s / 64-B operating profile, forms a 2×2 access/binding comparison, and its tariff-volume robustness is non-degenerate: MQTT is robust-exceed while CoAP is envelope-sensitive.

This subset is **not** the optimum over the full benchmark scenario. Two Non-IP cellular candidates also remain feasible in the frozen Stage-4 matrix but are excluded from this development subset because matched energy and operator-service cost evidence are missing.

## Stage 6B gate

Two gaps now separate the preferred development subset from the first decision experiment:

1. **matched cellular-IP whole-device energy/report** at the candidate boundary, without scaling the 1-KB Vomhoff source component to 64/200 B;
2. **EUR lifecycle-cost robustness family** built from dated price evidence plus the tariff-volume envelope, with tariff billing aggregation resolved or explicitly bracketed and without invented probabilities.

Further transport-detail expansion is frozen unless a material methodological error is found. Publication MCDA and fleet optimisation remain unauthorised at v0.1.46.
