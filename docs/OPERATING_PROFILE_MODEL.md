# Operating-profile and bridge contracts (Stage 5A)

Stage 4 closed hard feasibility with three explicit profile/boundary unknowns. Stage 5A separates two objects that must not be conflated:

1. an **operating profile**, which states how one verified candidate stack is configured in one benchmark scenario; and
2. a **bridge contract**, which states what evidence/model and boundary transformation would be required to populate a decision-target metric.

## Provenance of profile fields

Every field is `known`, `unresolved` or `not_applicable` and carries provenance. A scenario-derived value is a benchmark assumption, not empirical evidence. Protocol defaults, best-case modes and convenient source configurations may not silently fill missing fields.

Stage 5A materialises three partial profiles. Across 26 field records, six context fields are known from benchmark scenarios and 20 remain unresolved. Of the 22 fields explicitly required by Stage 4F, only the two 16-byte LoRaWAN payload fields are already satisfied by the scenario definition; the other 20 remain unresolved.

## Bridge contracts

Three bridge contracts are materialised but blocked:

- `bridge_thread_stack_latency`: no matched end-to-end latency source/model exists for the frozen Thread + DTLS + CoAP + LwM2M profile.
- `bridge_lorawan_lora_whole_device_energy`: LoED is reception-side link evidence and contains no device-energy metric.
- `bridge_lrfhss_radio_to_whole_device_energy`: LR-FHSS radio transaction energy exists, but the source is radio-interface-only at 4-byte payload while the benchmark target is 16-byte whole-device energy/report.

A numerical bridge is allowed only after all required profile fields are known (or a separately validated model explicitly treats them) and the source-to-target boundary transformation is validated.

## Uncertainty

Bridge construction must inherit parent evidence semantics. In particular, LR-FHSS retains the Stage-3 `explicit_epistemic_gap`: one trace per configuration does not become a population distribution simply because a deterministic accounting model is later added.

## Frozen result

Stage 5A does not change Stage 4. The hard-feasibility result remains 21 feasible, 39 infeasible and 3 unresolved. No preference score, ranking or publication MCDA is authorised.

## Versioned profile variants and monotone decision sufficiency

Stage 5C permits a parent benchmark profile to be expanded into explicit, versioned variants when the varying parameters are enumerated rather than inferred or optimised post hoc. Variant fields must retain provenance (`scenario_derived`, `primary_source_verified`, or `explicit_model_assumption`). Enumeration does not create probabilities.

A profile may remain partial for a numeric whole-device bridge yet be decision-sufficient for a monotone one-sided bound. This special case is allowed only when the validated component quantity is a lower bound on the target and already violates a hard upper budget.

