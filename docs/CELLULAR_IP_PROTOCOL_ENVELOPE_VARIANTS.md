# Stage 5K — Cellular IP protocol-envelope sensitivity variants

## Purpose

Stage 5J exposed 130 unresolved session/transport fields across ten feasible cellular-IP profiles. Those fields are implementation and deployment choices; current evidence does not identify a probability distribution over them. Stage 5K therefore does **not** select a typical profile and does **not** enumerate a Cartesian product. It creates a compact, versioned family of deterministic sensitivity anchors that can be reused consistently by tariff-volume and report-energy analyses.

## Scientific status

The variants are **synthetic benchmark sensitivity anchors**, not empirical observations and not claims about deployment prevalence. They carry no probabilities, frequency weights or stakeholder weights. A variant may be used to ask how a result changes under an explicit protocol/session choice, but not how likely that choice is in the field.

The Stage-4 feasibility matrix remains frozen at 21 feasible / 39 infeasible / 3 unresolved. Stage 5K changes no feasibility outcome and authorises no publication MCDA.

## Compact anchor family

Each of the ten Stage-5J IP-cellular profiles is evaluated under nine designs:

1. `A0_compact_persistent` — compact persistent-session reference anchor;
2. `A1_ipv6` — isolates IPv6 versus IPv4;
3. `A2_acknowledged_delivery` — CoAP CON/piggybacked ACK or MQTT QoS 1;
4. `A3_lwm2m_cbor` — LwM2M CBOR payload representation;
5. `A4_senml_json` — SenML JSON payload representation;
6. `A5_resume_each_report` — security-context resumption once per report;
7. `A6_full_reestablishment_each_report` — full security re-establishment once per report;
8. `A7_single_retry` — one complete transaction retry per report;
9. `A8_binding_expanded` — joint binding-specific expanded-header/reliability stress anchor.

The baseline representation is SenML CBOR over IPv4 with a persistent security context and no application retry. These are benchmark anchors only. The binding-expanded CoAP side uses CON, an 8-byte token, a separate confirmable response, a 1-byte CID, 2-byte DTLS sequence field and explicit length field. The MQTT side uses a 36-byte endpoint-name anchor, an 8-byte prefix anchor, QoS 2, a keep-alive equal to half the scenario reporting interval and 40 bytes of TCP options.

## Why these values are admissible as sensitivity anchors

The standards ledger in `datasets/stage5k_protocol_envelope_variants.yml` records the normative basis. LwM2M 1.2.2 permits LwM2M CBOR, SenML CBOR and SenML JSON for Send. CoAP defines bounded token length and confirmable/non-confirmable message types. DTLS 1.3 has variable unified-header choices including sequence-field length, optional length field and optional CID. MQTT 5 defines QoS 0/1/2 packet flows. LwM2M MQTT topics contain deployment-specific endpoint/prefix components. TCP Data Offset bounds the base TCP header plus option space.

None of those standards establishes how frequently deployments choose the endpoints used here. That is why the family is unweighted.

## Output size and coverage

The audit produces:

- 10 source profiles;
- 9 anchor designs;
- 90 variants;
- 45 CoAP/DTLS/UDP variants;
- 45 MQTT/TLS/TCP variants;
- complete explicit assignments for every Stage-5J unresolved field in every variant.

The design intentionally avoids the much larger joint Cartesian product because the current evidence does not identify a joint distribution over protocol/session choices.

## Raw tariff headroom diagnostic

The Stage-5I reference tariff includes 500 MB. Stage 5K converts that allowance into a **raw aggregate byte ceiling** per application report using the frozen five-year report counts, with `1 MB = 1,000,000 bytes`. No assumption is made about the provider's unknown accounting-rounding interval.

For the current profiles:

- 900-s reporting, 200-B application payload: total allowance ≈ 2851.927903 B/report, leaving ≈ **2651.927903 B/report** for all non-application traffic;
- 60-s reporting, 64-B application payload: total allowance ≈ 190.128527 B/report, leaving ≈ **126.128527 B/report** for all non-application traffic.

These values are not predicted protocol overhead and do not prove tariff sufficiency. The 60-s profile merely has a substantially tighter aggregate margin, so protocol/session accounting is decision-critical there.

## What remains blocked

Stage 5K intentionally leaves:

- exact serialized LwM2M Send payload lengths unresolved;
- exact CoAP/MQTT transaction bytes unresolved;
- DTLS/TLS handshake/resumption traffic unresolved;
- keep-alive/session-maintenance traffic unresolved;
- retry traffic unquantified beyond its deterministic scenario label;
- tariff TopUp count unresolved;
- canonical `expected_device_energy_per_application_report_j` unresolved.

Byte accounting alone cannot calibrate the Vomhoff whole-device energy boundary. A later energy bridge must remain state/device/boundary compatible.

## Stage 5L handoff

Stage 5L should implement one auditable standards-accounting engine with two layers:

1. **steady-state application transaction:** LwM2M serialization + application binding + transport + security record + IP bytes, direction separated;
2. **session increments:** full establishment, resumption, keep-alive/maintenance and retry traffic, kept as separate components before any amortisation.

Only after those components are materialised should STACKWISE classify the finite-data tariff under each sensitivity anchor. The same anchor IDs must then be reused when evaluating whether a compatible energy-state model can close part of the Stage-5F/5G energy gap.
