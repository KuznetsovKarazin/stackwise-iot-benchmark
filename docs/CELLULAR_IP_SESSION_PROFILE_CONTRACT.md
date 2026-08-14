# Stage 5J — cellular IP session/transport profile contract

Version: **v0.1.41**  
Standards review date: **2026-08-12**

## Purpose

Stage 5I showed that dated IP-cellular hardware and tariff evidence is available, but exact five-year data usage cannot be inferred from application payload alone. Stage 5F/5G independently showed that the Vomhoff whole-device source component cannot be transferred to the benchmark report-energy target without an explicit upper-layer/report-cycle profile.

Stage 5J therefore defines one common session/profile contract for both cost and energy. It does **not** calculate a tariff TopUp count and does **not** produce a canonical report-energy value.

## Frozen telemetry transaction semantics

For the ten feasible IP-cellular candidate incidences, STACKWISE now defines the benchmark telemetry transaction as **LwM2M Send**.

This choice is a reproducible benchmark definition, not a claim that every deployment uses Send. OMA LwM2M 1.2.2 defines Send in the Information Reporting interface for both CoAP and MQTT transport bindings. For the CoAP binding, Send is one of the operations that may be Non-Confirmable; STACKWISE therefore does not silently select either CON or NON.

The benchmark payload boundary is also frozen:

> `payload_bytes` is application data **before** LwM2M representation, CoAP/MQTT framing, TLS/DTLS, TCP/UDP and IP overhead.

This prevents the Stage-4 synthetic payload values from being silently reinterpreted as already-serialized network bytes.

Because the dated operator tariff accounts both uplink and downlink transport traffic, Stage 5J requires both directions to be included in any future tariff-volume calculation.

## Why no universal protocol-overhead constant is used

Primary standards review confirms that exact byte overhead is implementation/profile dependent:

- CoAP has a four-byte base header followed by variable token/options/payload fields;
- DTLS 1.3 uses a variable-length unified record header and its encrypted expansion depends on negotiated record parameters;
- MQTT PUBLISH size depends on topic, QoS and other variable fields;
- the LwM2M MQTT topic contains a deployment-specific endpoint identifier and optional prefix;
- TLS 1.3 encrypted-record expansion depends on the selected AEAD and optional padding;
- TCP may carry options and connection/session behaviour creates additional traffic;
- IP header size depends on IPv4/IPv6 and extension/option usage.

Consequently, `payload + one fixed overhead` is prohibited as a canonical traffic model.

## Materialised profiles

Stage 5J materialises **10** profile rows:

- 5 CoAP / DTLS / UDP profiles;
- 5 MQTT / TLS / TCP profiles.

Across these profiles the contract contains **200 profile-field records**:

- 70 known or frozen from scenario, candidate-stack, benchmark or tariff-accounting semantics;
- 130 explicitly unresolved.

Shared unresolved fields include payload encoding, IP version, security-context lifetime, session re-establishment/resumption cadence and retry/failure behaviour.

Binding-specific unresolved fields include:

**CoAP/DTLS:** CON/NON selection, token length, response exchange mode, DTLS CID/sequence/length-header choices, AEAD expansion and padding.

**MQTT/TLS:** endpoint/prefix lengths, QoS, keep-alive, LwM2M MQTT token encoding, TCP options, TLS AEAD expansion and padding.

## Decision status

- profiles complete for exact tariff volume: **0 / 10**;
- profiles complete for canonical report energy: **0 / 10**;
- canonical tariff-volume rows: **0**;
- canonical report-energy rows: **0**;
- publication MCDA authorised: **no**.

This is an intentional closure result. Stage 5J converts an informal statement — "transport/session overhead is unknown" — into a typed, candidate-specific list of missing dimensions shared by both cost and energy.

## Standards freshness correction

During the Stage-5J review, the component catalogue was refreshed without changing the candidate graph:

- TLS 1.3 primary reference is updated from obsolete RFC 8446 to current RFC 9846;
- LwM2M Transport Bindings reference is updated from 1.2.1 to 1.2.2.

The Stage-4B structural catalogue was revalidated after this source refresh; component/edge counts and structural compatibility results are unchanged.

## Next step

Stage 5K should define **parameterised protocol-envelope variants**, not a single guessed profile. The first variant grid should cover only dimensions that materially change cost/energy conclusions, for example:

- LwM2M CBOR vs SenML CBOR representation;
- IPv4 vs IPv6;
- CoAP CON vs NON;
- representative token/CID choices;
- MQTT QoS 0 vs 1, endpoint/prefix-length classes and keep-alive/session persistence;
- persistent security context vs controlled re-establishment/resumption sensitivity.

These are benchmark/sensitivity variants, not empirical frequencies. They may be used to calculate standards-consistent traffic envelopes. Population probabilities or "typical deployment" weights remain prohibited without evidence.

Machine-readable contract: `datasets/stage5j_cellular_ip_session_profile.yml`.
