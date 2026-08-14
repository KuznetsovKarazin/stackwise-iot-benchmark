# Stage 5L — cellular IP wire-volume accounting

Version: **v0.1.43**  
Status: **standards-known component floors materialised; exact wire volume remains unresolved**

## Purpose

Stage 5K fixed a compact family of cellular-IP protocol/session sensitivity anchors, but it did not compute protocol bytes. Stage 5L adds byte-level accounting without making the invalid substitution

`pre-LwM2M application payload bytes = serialized LwM2M payload bytes`.

The benchmark payloads (64 B and 200 B) are defined before LwM2M serialization. OMA LwM2M permits LwM2M CBOR, SenML CBOR and SenML JSON for Send, and the exact serialized size depends on the resource/value representation. The current benchmark does not identify that representation. Therefore exact serialized payload length remains unresolved for every variant.

## Two accounting layers

### Strict primary-exchange transport floor

The strict floor contains only the primary LwM2M Send request and its required response. The unresolved serialized LwM2M data payload is set to zero **only for the floor calculation**. The floor retains the standards-defined message structure and the Stage-5K header selections.

It deliberately omits positive but unresolved/additional traffic:

- DTLS/TLS establishment or resumption;
- MQTT pure TCP ACK and segmentation effects;
- MQTT QoS acknowledgement exchanges beyond the two primary PUBLISH messages;
- MQTT keep-alives;
- Stage-5K retry increments;
- billing-rounding effects.

This is not an estimate of actual traffic. It is a one-sided known-component diagnostic.

### Stage-5K anchor known-component accounting

A second quantity follows the Stage-5K deterministic sensitivity anchor more fully. It adds the selected CoAP response exchange, MQTT QoS acknowledgement flow, MQTT keep-alive pair and the one-retry stress case. For MQTT it uses one control packet per protected data-carrying transport episode as an explicit accounting convention.

This quantity is useful for sensitivity analysis but is **not** interpreted as an empirical packetisation distribution or as the strict tariff floor.

## Standards-based components

### CoAP / DTLS / UDP

For the CoAP binding, Send is mapped to POST `/dp`. The request accounting includes:

- 4-B CoAP base header;
- Stage-5K token length;
- Uri-Path option for `dp`;
- Content-Format option for the selected Send representation;
- payload marker;
- unresolved serialized LwM2M payload;
- DTLS 1.3 record overhead from the Stage-5K CID/sequence/length/AEAD/padding anchor;
- 8-B UDP header.

The successful response is represented by the 2.04 Changed exchange. Non-Confirmable, piggybacked ACK and separate-response anchor cases remain distinct in the anchor accounting.

### MQTT / TLS / TCP

For MQTT, the LwM2M Send request uses the OMA Information Reporting CBOR map containing operation 24, token, content type and a byte-string payload. The successful response uses the Generic Response structure with result 204 and token.

The MQTT topic uses the non-bootstrap structure:

`[PREFIX "/"] "lwm2m/rd/" ENDPOINT`

The MQTT 5 PUBLISH accounting includes topic, QoS packet identifier where required, zero Property Length and the CBOR LwM2M wrapper. TLS record and TCP header components are then added. Pure TCP ACK/segmentation traffic remains unresolved and is therefore not silently added.

## Tariff boundary

The reviewed 1NCE documentation states that the 500-MB allowance counts both uplink and downlink transport data, including TCP/UDP overhead and user payload, and that usage is measured/billed to the nearest 1 kByte. It does not identify the aggregation interval for that rounding.

For this reason:

1. Stage 5L compares **raw transport bytes** with the nominal 500-MB allowance;
2. it does not claim exact billed volume;
3. it does not materialise exact TopUp count;
4. IP-header bytes are excluded from the tariff-side floor because the reviewed tariff description explicitly mentions TCP/UDP overhead but not the IP header;
5. a separate IP-wire floor includes the minimum 20-B IPv4 or fixed 40-B IPv6 header.

## Stage-5L checkpoint

The 90 Stage-5K variants produce:

- 90 strict transport known-component floors;
- 90 deterministic anchor known-component accounting rows;
- 0 exact wire-volume rows;
- 90 unresolved LwM2M serialization rows;
- 45 MQTT rows with unresolved pure-TCP ACK/segmentation overhead;
- 20 rows with unresolved per-report security resumption/full-establishment increments.

A notable one-sided raw-volume result appears for the two 60-s asset-tracking scenarios. All 27 MQTT/TLS variants in those scenarios have a strict raw transport-component floor above the nominal 500-MB allowance over five years. For the compact persistent MQTT anchor the floor is 205 B/report, or 539.109 MB over five years, **before** any serialized LwM2M data payload, pure TCP ACKs or security-session increments.

This is recorded as a raw-volume exceedance warning, not as an exact billing or TopUp conclusion, because billing-rounding aggregation remains unresolved.

For the compact CoAP tracking anchor the strict floor is 68 B/report. Under the nominal raw allowance, the optimistic maximum serialized LwM2M payload compatible with that primary-exchange floor is 122 B/report. This threshold is not a prediction of the encoded 64-B application payload; it is a diagnostic showing how much unresolved serialized payload could be accommodated before omitted positive traffic is considered.

## Remaining gaps

Stage 5L does not close the following quantities:

1. exact LwM2M serialized payload length for the 64-B and 200-B pre-LwM2M benchmark payloads;
2. DTLS/TLS establishment and resumption byte increments;
3. MQTT pure TCP ACK, segmentation/coalescing and connection-maintenance effects;
4. exact tariff rounding aggregation and billed volume;
5. any mapping from wire bytes to whole-device report energy.

Stage 5M should therefore define a reproducible LwM2M payload-serialization contract (or retain a bounded payload-size family where exact semantic records are unavailable) and separately materialise security-session increment envelopes. Exact tariff or energy targets must remain blocked until those gaps are resolved.
