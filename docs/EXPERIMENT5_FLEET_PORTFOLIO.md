# Experiment 5 — fleet portfolio feasibility and simplification penalty

Status: **implemented in v0.1.57**. Benchmark input: **STACKWISE Empirical Evidence Benchmark v1.0.0**.

## Question

How much scenario-class serviceability is lost when a heterogeneous IoT fleet is forced to use one stack, one access technology, or one broad access family rather than the minimum heterogeneous portfolio permitted by the frozen hard-feasibility matrix?

## Primary analysis

The primary universe contains only benchmark scenarios with at least one `feasible` candidate. `unresolved` cells are not promoted to feasibility. This produces five strictly serviceable scenario classes from the seven benchmark scenarios.

Portfolio optimisation is a deterministic set-cover problem. It maximises the number of strictly serviceable scenario classes covered by a portfolio and then identifies the minimum cardinality required for complete coverage. It uses no device-count weights, lifecycle-cost values, soft scores, empirical-energy imputation, or stakeholder weights.

## Headline strict-feasibility result

- total benchmark scenarios: 7;
- scenarios with at least one strictly feasible candidate: 5;
- unresolved-only scenarios: 2;
- best single stack: 4/5 serviceable scenario classes;
- best single access technology: 4/5;
- best single access family: 4/5;
- single-option structural serviceability loss: 1/5 = 20%;
- minimum complete strict portfolio: 2 stacks / 2 access technologies / 2 access families;
- minimum two-stack portfolios: 6;
- minimum technology portfolios: 2 — `LTE-M + LoRaWAN-LoRa` or `LTE-M + LoRaWAN-LR-FHSS`;
- unique minimum family portfolio: `cellular + lorawan`.

The best single stack is `ltem_nonip_lwm2m`; it covers smart metering, urban non-IP dual access, periodic cross-cell tracking, and connected-handover tracking, but cannot serve the private-LoRaWAN environmental scenario. Hence a LoRaWAN option is structurally necessary for complete strict serviceability across the five currently resolvable scenario classes.

## Unresolved-closure sensitivity

A secondary, explicitly optimistic sensitivity treats `unresolved` as potentially coverable solely to ask what portfolio would be required if every unresolved predicate later closed positively. This is **not** a feasibility claim.

Under that sensitivity:

- one portfolio element covers at most 4/7 classes;
- two cover at most 6/7;
- three are required for 7/7;
- complete technology/family coverage adds Thread because the industrial low-latency scenario is currently unresolved only for the Thread stack.

## Interpretation boundaries

The result is a fleet-level **structural serviceability** optimisation under hard feasibility. It is not a device-count-weighted fleet design, not a lifecycle-cost optimum, not a global stack ranking, and not a probability distribution over deployments. The legacy smoke optimiser in `src/stackwise/optimizer.py` remains non-publication evidence unless its configured prices are independently validated.
