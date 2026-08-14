# Stage 5N — Security-session and MQTT/TCP control envelope

## Purpose

Stage 5N is the final planned transport/accounting refinement before STACKWISE returns to decision-layer consolidation. It closes two explicit Stage-5M gaps without inventing a canonical deployment trace:

1. DTLS/TLS session establishment or resumption traffic for the `A5_resume_each_report` and `A6_full_reestablishment_each_report` anchors;
2. pure TCP ACK/control uncertainty for MQTT/TLS variants.

The result is a **deterministic standards-bounded sensitivity envelope**, not an empirical packet trace, probability distribution, billed-volume model, or report-energy model.

## Frozen scientific rules

- The Stage-5K protocol variants and Stage-5M synthetic LwM2M serialization surrogates are inherited unchanged.
- LwM2M Pre-Shared Key mode is used as a valid security **surrogate**, not as a claim that all candidate deployments use PSK.
- Two session/control anchors are evaluated with no probabilities or frequencies:
  - `E0_compact_psk_control` — TLS/DTLS `psk_ke`, 16-byte PSK identity, compact DTLS encrypted header/packing, and zero standalone TCP ACK-only segments;
  - `E1_expanded_psk_dhe_control` — `psk_dhe_ke` with X25519, 64-byte PSK identity, expanded DTLS encrypted-header/packing sensitivity, and one TCP ACK-only segment per modeled data-carrying segment.
- Neither envelope is a universal lower or upper bound. Real certificate/RPK modes, TCP segmentation, retransmissions and implementation-specific ACK behaviour can fall outside this compact family.
- Billing rounding remains unresolved, so raw-byte threshold results are not exact tariff TopUp counts.
- No network-byte result is converted to device energy.

## TLS 1.3 PSK reference surrogates

The deterministic TLS handshake grammar produces the following protected/plaintext record totals before TCP/IP:

| Envelope | PSK identity | Key exchange | ClientHello | ServerHello | Server encrypted flight | Client Finished | TLS records total |
|---|---:|---|---:|---:|---:|---:|---:|
| E0 | 16 B | `psk_ke` | 128 B | 61 B | 64 B | 58 B | **311 B** |
| E1 | 64 B | `psk_dhe_ke` + X25519 | 226 B | 101 B | 64 B | 58 B | **449 B** |

For MQTT/TLS, Stage 5N additionally applies the Stage-5L convention of one TLS record per data-carrying TCP segment, adds a synthetic TCP three-way handshake for a rebuilt connection, and adds a minimal MQTT 5 `CONNECT`/successful `CONNACK` pair.

## DTLS 1.3 PSK reference surrogates

DTLS uses 12-byte handshake framing, DTLS plaintext/encrypted record framing and a mandatory ACK for the client final flight when no subsequent flight implicitly acknowledges it.

| Envelope | DTLS record bytes | UDP datagrams | DTLS+UDP session surrogate |
|---|---:|---:|---:|
| E0 | 399 B | 4 | **431 B** |
| E1 | 549 B | 5 | **589 B** |

The compact design coalesces the ServerHello and encrypted server flight into one UDP datagram. The expanded design keeps them separate and uses the larger encrypted-record-header sensitivity.

## MQTT/TCP ACK envelope

TCP acknowledgement count is not uniquely recoverable from an MQTT message list because delayed, cumulative and piggybacked ACK behaviour is implementation/timing dependent. Stage 5N therefore uses two deterministic endpoints:

- E0: no standalone ACK-only TCP segment is added;
- E1: one ACK-only segment is added per modeled data-carrying TCP segment.

The E1 rule is **not an upper bound**: segmentation/retransmission can add more traffic, while delayed/cumulative/piggybacked ACKs can add less.

## Audit result

Stage 5N expands the 180 Stage-5M serialization rows by two session/control envelopes:

- source serialization rows: **180**;
- envelope designs: **2**;
- envelope rows: **360**;
- CoAP/DTLS rows: **180**;
- MQTT/TLS rows: **180**;
- rows with non-zero security-session surrogate increment: **80**;
- rows with non-zero MQTT ACK-only surrogate increment: **90**;
- canonical security-session rows: **0**;
- canonical MQTT/TCP ACK rows: **0**.

Across the 360 augmented rows:

- **162** exceed the nominal raw 500-MB allowance;
- **198** remain within it.

More importantly, when the two session/control envelopes are collapsed back to the 180 Stage-5M source rows:

- **81/180** exceed under **both** E0 and E1;
- **99/180** remain within under **both** E0 and E1;
- **0/180** cross the 500-MB threshold solely because E0 versus E1 was selected.

Thus, within this deliberately compact PSK/TCP-control sensitivity family, session/control detail does not determine which side of the nominal threshold a Stage-5M row occupies. The dominant threshold drivers are already higher-level choices: binding, report interval, LwM2M serialization/resource shape, retry policy and whether a security session is rebuilt per report.

All **54 MQTT/TLS tracking source rows** remain above the nominal raw allowance across both session/control envelopes. CoAP tracking contains both below- and above-threshold rows, but no row flips solely because of E0/E1.

Examples for the 60-s tracking single-resource surrogate:

- CoAP compact persistent: **149 B/report**, about **391.84 MB/5y**;
- CoAP resumption/re-establishment each report: **580–738 B/report**, about **1.53–1.94 GB/5y**;
- MQTT compact persistent: **288–328 B/report**, about **757.38–862.57 MB/5y**;
- MQTT resumption/re-establishment each report: **879–1177 B/report**, about **2.31–3.10 GB/5y**.

These values are deterministic surrogate results, not canonical deployment traffic.

## What Stage 5N does not identify

Stage 5N does **not** identify:

- certificate or Raw Public Key handshake traffic;
- an empirical distribution over security modes or PSK identity lengths;
- actual TCP segmentation or ACK count;
- network retransmissions beyond the Stage-5K application-retry anchor;
- exact tariff billing/rounding behaviour;
- canonical real-application LwM2M object structure;
- device energy from network bytes.

These limitations are now frozen rather than recursively expanded into additional transport stages unless a material methodological error is discovered.

## Next step

The next work item is **Stage 6A — first decision-ready slice consolidation**. It should consume the frozen Stage-4 feasibility matrix and the Stage-5 evidence/cost/transport contracts, identify which scenario/candidate/criterion combinations can now be used quantitatively, and define the minimum remaining evidence treatment needed to run the first stochastic decision experiment. No new transport-detail stage should be opened by default.
