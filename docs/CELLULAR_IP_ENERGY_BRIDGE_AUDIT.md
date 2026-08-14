# Stage 5F — Cellular-IP energy bridge audit

Stage 5F tests whether the validated Vomhoff whole-device phase-energy evidence can be converted into the canonical decision target `expected_device_energy_per_application_report_j` for the feasible IP-cellular STACKWISE candidates.

## Frozen candidate incidences

The Stage-4 hard-feasibility matrix is not changed. Ten feasible IP-cellular scenario×stack incidences are audited:

- four in `smart_meter_public_cellular`;
- four in `asset_tracking_periodic_cross_cell`;
- two LTE-M incidences in `asset_tracking_connected_handover`.

The benchmark payloads are 200 B and 64 B. The retained Vomhoff data-transfer evidence is 1024 B.

## What is authorised from Vomhoff

A source-aligned whole-device **active transaction component** is materialised for three source contexts:

- NB-IoT / HTTP / 1 KB;
- LTE-M / HTTP / 1 KB;
- NB-IoT / MQTT / 1 KB.

The component sums only the source-defined active phases:

`Connection Establishment + Data Request + Data Download + Postprocessing`.

`Standby` and `Idle` are deliberately excluded. Their source durations/normalisations do not define the benchmark reporting-cycle tail, PSM/eDRX policy, connected-idle policy or sleep energy.

When local Stage-3B bootstrap draws are available, the four phase means are summed **within the same experimental block and bootstrap replicate**. Phase dependence is therefore preserved; phase distributions are not sampled independently.

This source component is a diagnostic/model-validation quantity. It is not the canonical report-energy target.

## Why the canonical target remains blocked

All ten candidate incidences fail at least one structural transfer gate.

1. **Payload mismatch.** The benchmark payload is 64 B or 200 B; retained Vomhoff data-transfer evidence is 1024 B. The retained source does not identify a payload-scaling law for the target conditions.
2. **Application-stack mismatch.** HTTP does not identify CoAP + DTLS + LwM2M energy. The retained NB-IoT MQTT context does not identify the exact MQTT 5 + TLS 1.3 + LwM2M candidate binding. The retained dataset has no LTE-M MQTT context.
3. **Reporting-cycle boundary mismatch.** A source transaction window does not determine energy over a 60 s or 900 s application reporting cycle. Standby/Idle cannot be stretched to the reporting interval without an explicit connected/idle/PSM/eDRX state model.

Therefore Stage 5F materialises **zero** canonical `expected_device_energy_per_application_report_j` values and does not update decision-readiness to `READY_BRIDGED`.

## Prohibited shortcuts

Stage 5F explicitly forbids:

- linear or proportional 1024 B → 64/200 B scaling without a validated model;
- applying the NB-IoT HTTP↔MQTT difference as an LTE-M correction;
- treating HTTP energy as CoAP/DTLS/LwM2M energy;
- treating the source MQTT label as evidence of the exact candidate MQTT/TLS/LwM2M stack;
- scaling source Idle/Standby energy to the benchmark reporting interval without a state model;
- publishing the source active component as application-report energy.

## Next evidence requirement

Stage 5G should target the explicit transfer gaps rather than broaden dataset collection:

1. payload dependence under NB-IoT/LTE-M;
2. candidate upper-layer context, preferably matched CoAP/DTLS/LwM2M and MQTT/TLS/LwM2M measurements or a validated component model;
3. reporting-cycle state accounting (connected tail, idle, PSM/eDRX/sleep);
4. lifecycle-cost evidence remains a mandatory parallel contract.

Publication MCDA remains blocked.
