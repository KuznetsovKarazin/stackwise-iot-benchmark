# Stage 6B — Matched cellular-IP report-energy evidence audit

## Decision question

Stage 6A selected the `asset_tracking_periodic_cross_cell` IP-cellular 2×2 subset as the first development benchmark: NB-IoT/LTE-M × CoAP/DTLS/LwM2M/MQTT/TLS/LwM2M at 64 pre-LwM2M bytes every 60 s. The required soft energy target is `expected_device_energy_per_application_report_j` at a whole-device report-cycle boundary.

Stage 6B asks a narrow question: **does a public empirical source already identify that target well enough to score the four candidates?**

## External-source audit

Four primary empirical/model sources were reviewed and encoded in `datasets/stage6b_matched_cellular_energy.yml`.

1. **Vomhoff et al. (ICC Workshops 2023; Zenodo 10.5281/zenodo.7603641).** Strongest retained whole-device dual-RAT source, but the data-transfer evidence is bound to 1 KB and source HTTP/MQTT contexts. It remains Grade-A source-aligned evidence, not a 64-B/60-s candidate bridge.
2. **Sørensen et al. (IEEE IoT Journal 2022; DOI 10.1109/JIOT.2022.3152173).** Strong dual-RAT modem-state/procedure model validated experimentally. The validation campaign uses 100-B payloads and 1-h/24-h cycles; sensor/device remainder is explicitly outside the modem boundary. It supports structural dependence on payload, coverage and reporting cycle, not whole-device absolute transfer.
3. **Michelinakis et al. (IEEE IoT Journal 2021; DOI 10.1109/JIOT.2020.3013949).** Strong commercial-network NB-IoT measurements over multiple payload sizes and RAI/operator/module settings. LTE-M is absent, so it cannot identify the four-candidate comparison.
4. **Lukic et al. (IEEE SmartIoT 2020; DOI 10.1109/SmartIoT49966.2020.00046).** Includes a 64-B UDP NB-IoT transaction on a custom energy-measurement platform. The exact payload is useful as a cross-check, but LTE-M and the candidate whole-report boundary are absent.

**Result:** 0 reviewed sources match all mandatory dimensions simultaneously. No publication score is authorised.

## Minimal matched experiment

The minimum honest closure is a small repeated-measures experiment on one dual-mode LTE-M/NB-IoT application platform and one operator/SIM supporting both RATs at the same site.

### Primary cells

Four mandatory cells:

- NB-IoT + CoAP/DTLS/LwM2M;
- LTE-M + CoAP/DTLS/LwM2M;
- NB-IoT + MQTT/TLS/LwM2M;
- LTE-M + MQTT/TLS/LwM2M.

All use 64 pre-LwM2M bytes, a 60-s scheduled report cycle, the single-Opaque-Resource Stage-5M surrogate, and a fresh application transport/security session per report. The fresh-session profile is a deterministic conservative benchmark, not a claim about typical deployment.

A second unweighted sensitivity member uses resumption/context reuse where it is genuinely supported and observable. Unsupported reuse must remain unavailable, not silently replaced.

### Measurement boundary

Measure only the DUT application rail: application MCU, memory, cellular modem and protocol/security processing, from the scheduled report trigger to return to the frozen post-report sleep state. Exclude debugger, USB/interface MCU and measurement equipment. Sensor acquisition is excluded because the benchmark payload is synthetically generated and common to all candidates.

Record both full-cycle energy and active-transaction energy. A complete 60-s scheduled cycle is the replication unit. Raw current samples are never independent replicates.

### Experimental blocking

A time block contains all four primary RAT×binding conditions in randomized order under the same site/operator setup. Start with five pilot blocks. The final number of blocks is deliberately not fixed before the pilot; freeze it from observed between-block variability using a predeclared precision/power criterion before the main campaign.

Mandatory radio/network covariates include RSRP/RSRQ/SINR or available equivalents, cell/band, PSM/eDRX grants, T3324/T3412, RAI/release behaviour, retries, UL/DL bytes, session outcome and report success.

Failed reports must not be discarded. If delivery failures are non-negligible, `delivery_probability` must re-enter the decision slice rather than reporting energy conditional only on successful cycles.

## Stage decision

Stage 6B closes the literature-search question, not the energy target itself:

- matched public source found: **no**;
- targeted whole-device experiment required: **yes**;
- energy target materialised: **no**;
- publication MCDA authorised: **no**.

The cost branch can progress independently while the measurement campaign is prepared.
