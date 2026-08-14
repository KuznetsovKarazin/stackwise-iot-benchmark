# Stage 6D — Synthetic Nested Decision/Robustness Engine Dry Run

Version: `v0.1.49`

## Purpose

Stage 6D validates the decision software before matched cellular whole-device energy measurements exist. It does **not** create scientific rankings. The only real decision input used is the frozen Stage-6C lifecycle-cost robustness family; energy is supplied by explicitly synthetic paired fixtures that are prohibited from publication results.

## Nested uncertainty semantics

The engine keeps three layers separate:

1. **Lifecycle-cost states:** 144 aligned Stage-6C protocol/serialization/session-control/billing/procurement states. They are epistemic/deployment sensitivities and receive no probabilities.
2. **Stakeholder preferences:** 21 deterministic energy-vs-cost weight anchors from 0/1 to 1/0. They are sensitivity points and receive no probabilities.
3. **Energy draws:** three synthetic paired fixtures with 64 common-block draws each. They exist only to exercise the conditional ranking code and have no scientific probability interpretation.

Rank acceptability is therefore computed only conditionally on a declared cost state and weight anchor. Across cost states and weights the engine reports envelopes and possible ranks; it never averages them into a global probability.

## Value functions

Stage 6D uses fixed external linear anchors (`0–6 J` for synthetic energy and `0–160 EUR` for lifecycle cost) solely for software validation. Alternative-set min/max normalisation is prohibited because it can induce rank changes when alternatives are added or removed. These anchors must be replaced/frozen on substantive grounds before a real decision experiment.

## Tie handling

Exact utility ties are not broken randomly. A tied group receives fractional mass across the integer ranks it occupies. The implementation checks both candidate-wise and rank-wise mass conservation and is invariant to candidate ordering.

## Synthetic fixtures

- `F0_ltem_energy_advantage`: LTE-M has lower synthetic report energy within both bindings.
- `F1_binding_tradeoff_rat_symmetry`: NB-IoT and LTE-M are exactly tied within each binding; MQTT has lower synthetic energy while the real Stage-6C cost family can favour CoAP.
- `F2_nbiot_energy_advantage`: NB-IoT has lower synthetic report energy within both bindings.

The opposite F0/F2 orderings verify that the engine does not encode an RAT preference. F1 verifies exact-tie handling and weight sensitivity.

## Current result

The dry run aligns 4 candidates, 144 cost states, 3 synthetic energy fixtures, 64 paired draws per fixture and 21 deterministic weight anchors. This yields 9,072 conditional cost-state × weight × fixture evaluations. The compact output contains 252 weight-sensitivity envelope rows and 12 fixture-level rank-envelope rows. All 13 invariants pass.

## Publication restriction

No Stage-6D synthetic utility or rank may be presented as evidence about NB-IoT, LTE-M, CoAP or MQTT. Real ranking remains blocked until Stage-6B matched whole-device report-energy data pass boundary, replication and quality checks.
