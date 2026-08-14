# Stage 4D — Quantitative Benchmark Scenarios and Hard Feasibility

Stage 4D freezes six **synthetic, reproducible benchmark scenarios** and screens the nine
Stage-4C verified reference candidates before any preference model.

The scenarios are modelling assumptions, not claims that a real deployment has exactly
these payloads, intervals, infrastructure conditions or limits. Quantitative context is
stored even when it is not a hard predicate. A value becomes hard only when the scenario
lists an explicit `hard_constraint`.

## Tri-state semantics

Each scenario × candidate pair is evaluated as:

- `feasible`: every declared hard predicate passes;
- `infeasible`: at least one declared hard predicate fails;
- `unresolved`: no predicate fails, but at least one mandatory candidate fact is unknown.

`unknown` never passes silently, and infeasibility cannot be compensated by a later score.
A Stage-4D `feasible` label means only that the **declared** hard predicates pass; it does
not imply complete empirical support, proven coverage, acceptable cost, or MCDA superiority.

## Candidate facts

Only graph-derived facts are currently resolved: access family/deployment dependency,
device-side IP versus Non-IP mode, explicit TLS/DTLS presence and LwM2M presence. Numeric
payload capacity, guaranteed end-to-end latency, common whole-device per-report energy and
verified mobility remain `NULL` until a source-backed Stage-4 capability bridge exists.

## Frozen scenarios

1. battery environmental sensing with private LoRaWAN service;
2. smart metering with site-available cellular service;
3. private industrial IPv6 monitoring with an explicit 500 ms hard latency ceiling;
4. urban Non-IP telemetry with both cellular and LoRaWAN service available;
5. asset tracking with a hard verified-mobility requirement;
6. remote agriculture with a hard 0.2 J whole-device per-report energy budget.

The numerical values are benchmark inputs, not empirical measurements. They are deliberately
kept separate from standards-derived candidate capabilities.

## Stage-4D guardrails

- no MCDA score, weights or ranking;
- no default payload/latency/energy capability inferred from technology names;
- no empirical-support completeness inferred from hard feasibility;
- no promotion of contextual quantitative facts to hard constraints;
- unresolved facts remain unresolved until Stage 4E or later.

## Stage 4E — targeted blocker review and mobility-semantics refinement

Stage 4D produced nine decision-blocking unknown results. Primary-source review showed that six of them came from an underspecified binary `mobility_supported_verified` fact, not from a single missing technology value.

The binary mobility requirement is therefore **superseded for forward analysis** by two explicit benchmark variants:

1. `asset_tracking_periodic_cross_cell` — standardized idle-mode cell reselection is sufficient for periodic cross-cell reporting;
2. `asset_tracking_connected_handover` — network-managed connected-mode handover is mandatory.

No probability or preference is assigned to either variant. They are alternative hard-requirement semantics.

Primary-source basis:

- ETSI TS 136 304 V18.1.0 / 3GPP TS 36.304 Release 18 specifies NB-IoT cell-reselection procedures;
- ETSI TS 136 331 V18.8.0 / 3GPP TS 36.331 Release 18 distinguishes general RRC connected-mode mobility/handover and limits the applicability of that function for NB-IoT;
- 3GPP RAN4 Cat-M1 handover requirements establish LTE-M/Cat-M1 connected-mode handover support.

The refined seven-scenario screen has 63 scenario×candidate rows: 21 feasible, 39 infeasible and 3 unresolved. The remaining decision blockers are deliberately unresolved:

- Thread candidate: no normative stack-level guarantee of `<=500 ms` end-to-end latency was identified in the reviewed Thread material;
- classical-LoRa LoRaWAN candidate: no common whole-device per-report energy estimand exists in core-four evidence;
- LR-FHSS LoRaWAN candidate: radio-interface-only transaction/capture energy cannot verify a whole-device `0.2 J/report` budget.

`feasible` continues to mean only that all declared hard predicates for that scenario variant pass. It does not mean full empirical support or superiority.

## Stage 4F closure

The Stage-4E refined screen is frozen at 21 feasible / 39 infeasible / 3 unresolved rows. The final three unknowns are not coerced to scalars because their decision facts are operating-profile and/or measurement-boundary dependent.

Thread 500-ms latency requires a frozen device role/sleep policy, topology/path and retry profile plus a matched end-to-end measurement/model. Classical LoRaWAN report energy lacks core-four device-energy evidence. LR-FHSS has useful radio-only mode-specific energy measurements, but the benchmark is 16-byte whole-device/report and cannot be resolved by direct substitution.

Stage 5A may define explicit operating profiles and bridge contracts. Hard infeasibility or unresolved hard facts remain non-compensatory; preference scoring is still blocked.
