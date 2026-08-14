# LoED packet-identity audit

## Purpose

This audit documents why STACKWISE does **not** reconstruct a physical RF emission from LoED by a fixed gateway wall-clock threshold. It is based on the full-corpus v0.1.8 analysis-ready output and the exported set of clusters with observation span greater than 1 s.

## Audit sample

The diagnostic export contained 865 clusters with `gateway_time_span_s > 1`.

- 91 clusters were CRC-invalid.
- All 91 CRC-invalid clusters shared the same Join Request fingerprint.
- 774 clusters were CRC-valid.
- Among CRC-valid long clusters, 443 were Confirmed Data Up and 331 were Unconfirmed Data Up.

The CRC-valid long clusters were strongly structured by gateway combination rather than appearing as random timing noise. In particular:

- 327 clusters contained exactly 3 rows from gateways `0000024b0b031c97`, `00800000a0001914`, and `7276ff002e062804`; median observation span was about 1.035 s.
- 145 clusters contained exactly 3 rows from gateways `00800000a0001793`, `00800000a0001914`, and `7276ff002e062804`; median span was about 1.003 s.
- 297 clusters involved gateways `00800000a0001793` and `7276ff002e062804`; these contained 3–6 reception rows and spans up to about 4.05 s, consistent with repeated receptions/retransmissions combined with gateway-clock offsets.

The previous adjacency rule (`next timestamp - previous timestamp <= 1 s`) therefore mixed two effects: gateway clock misalignment and repeated observations of the same exact LoRaWAN frame. A shorter fixed threshold would incorrectly split genuine cross-gateway observations, while a longer threshold can chain retransmissions.

## Decision

The primary analysis-ready identity unit is now a **CRC-valid logical LoRaWAN frame**, defined as the exact physical-payload fingerprint within one source day.

CRC-invalid receptions remain available in the harmonised gateway-observation table for reception-side QC, but they are excluded from logical-frame identity because corrupted decoded bytes are not a trustworthy identity key.

For a logical-frame cluster:

- `gateway_count` = number of distinct gateways that observed the exact CRC-valid frame at least once;
- `reception_rows` = all CRC-valid gateway observations of that frame within the source day;
- `repeat_reception_rows = reception_rows - gateway_count`;
- the timestamp span can reflect gateway-clock offsets and/or retransmissions and is **not** interpreted as RF propagation/reception simultaneity.

## Consequence for the paper

LoED contributes RSSI/SNR/SF/frequency/bandwidth distributions and logical-frame gateway-observation diversity. It does not provide:

1. an attempted-transmission denominator for absolute PDR;
2. sufficiently synchronized gateway clocks to identify individual physical RF emissions purely from wall-clock time; or
3. a basis for treating repeated gateway rows as independent packet transmissions.
