# Stage 5E — Decision-readiness and evidence-gap audit

## Purpose

Stage 5E determines whether the frozen Stage-4 non-infeasible candidates can be compared at the canonical decision-target boundary. It does **not** compute preference scores, ranks, stakeholder weights or fleet assignments.

The audit separates three concepts that must not be conflated:

1. source evidence exists;
2. source evidence is scientifically bridgeable to a decision target;
3. the decision target is actually materialised under a complete operating profile with valid uncertainty semantics.

A `BRIDGEABLE` relation is therefore not considered decision-ready.

## Frozen inputs

Stage 5E consumes only existing validated artifacts:

- the Stage-4 refined feasibility matrix: 21 feasible / 39 infeasible / 3 unresolved;
- the nine verified candidate stacks;
- the Stage-5A operating-profile records;
- the Stage-5A bridge contracts;
- the Stage-2/3 evidence and uncertainty decisions already encoded in the repository.

No new dataset or numerical prior is introduced.

## Canonical target set

Five decision targets remain visible in the audit:

- `expected_device_energy_per_application_report_j`;
- `lifecycle_cost_eur`;
- `end_to_end_application_latency_ms`;
- `delivery_probability`;
- `feasible_link_probability`.

For the **first feasibility-conditioned decision slice**, only energy/report and lifecycle cost are treated as mandatory soft quantities. Latency, delivery and link feasibility are not automatically re-scored after hard feasibility. They may become soft criteria later only when a separate decision role and comparable target evidence are justified.

This is an audit lens, not an MCDA authorisation.

## Readiness semantics

`READY_DIRECT` means the canonical target is directly measured at a compatible boundary.

`READY_BRIDGED` means a validated numerical bridge has materialised the target under a complete profile.

`PROFILE_UNRESOLVED` means useful source evidence exists, but the decision-relevant operating profile is incomplete or absent.

`BRIDGEABLE` means a valid bridge path exists conceptually, but the target has not yet been materialised.

`ROBUSTNESS_ONLY` means evidence can condition/stress-test a future model but does not identify the target metric itself. LoED RSSI/SNR fall in this class for delivery/coverage unless an external outcome/link model is supplied.

`MISSING` means the current core-four do not identify the target for the candidate.

`INCOMPATIBLE` means related evidence exists but cannot be transferred to the candidate mode/boundary without a separately validated transfer model or new evidence.

## Production result

The audit covers 24 non-infeasible scenario-stack combinations (21 feasible + 3 unresolved) across five targets, for **120 candidate-target rows**.

Current checkpoint:

- decision-ready target rows: **0 / 120**;
- feasible candidates fully ready for the first energy+cost slice: **0 / 21**;
- feasible cellular-IP candidate incidences with bridgeable Vomhoff energy evidence: **10**;
- frozen scenarios that would obtain at least two energy-comparable candidates after the cellular-IP energy bridge: **3**.

Those three scenarios are:

- `smart_meter_public_cellular` — four bridgeable IP cellular candidates;
- `asset_tracking_periodic_cross_cell` — four bridgeable IP cellular candidates;
- `asset_tracking_connected_handover` — two bridgeable LTE-M IP candidates.

The result should not be read as “no useful evidence exists.” It means that no source quantity has yet been promoted, without a validated bridge, to the canonical decision estimand.

## Gap priority conclusion

Two gaps dominate the first decision slice for different reasons.

### Preferred next bridge using existing empirical evidence

`cellular_ip_report_energy_bridge`

Vomhoff provides replicated whole-device phase energy and dependence-preserving physical-run bootstrap uncertainty. A successful scenario-specific phase-to-report bridge would affect 10 feasible candidate incidences and create a multi-candidate energy comparison in three scenarios without collecting another dataset.

The bridge must still account explicitly for the source application context (HTTP/MQTT) versus the frozen candidate stacks and must not silently treat phase energy as CoAP/DTLS/LwM2M or MQTT5/TLS/LwM2M whole-stack energy.

### Mandatory parallel cross-cutting contract

`lifecycle_cost_model`

Lifecycle cost is missing for all 21 feasible candidates. Existing `configs/fleet.yml` values are smoke/test inputs and are not publication evidence. A separate dated cost contract is required before first-slice decision scoring or fleet optimisation.

## Stage 5F handoff

Stage 5F is authorised to work on the cellular-IP report-energy bridge only.

Required order:

1. freeze scenario-specific reporting/session/accounting profiles for the relevant IP cellular candidates;
2. define which Vomhoff source phases may enter a report-energy composition and which source/application differences remain structural uncertainty;
3. validate the bridge against the source accounting boundary;
4. propagate the existing joint physical-run bootstrap without manufacturing cross-block dependence;
5. emit canonical `expected_device_energy_per_application_report_j` only where the bridge is scientifically defensible;
6. preserve unresolved/incompatible Non-IP candidates rather than borrowing IP evidence.

Publication MCDA, ranking and fleet optimisation remain prohibited after Stage 5E.
