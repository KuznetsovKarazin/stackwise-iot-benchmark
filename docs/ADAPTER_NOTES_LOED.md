# LoED adapter notes

## Canonical unit

One source CSV row equals one gateway reception observation. The adapter does not collapse multi-gateway receptions in the canonical layer.

## Packet identity

The raw `physical_payload` string is transformed into a SHA-256 fingerprint. The payload itself is not copied into processed artefacts. Downstream analysis-ready identity is a CRC-valid exact-PHY logical frame within the same source day. Wall-clock gap is not used because the full-corpus audit showed gateway-clock offsets, retransmissions and transitive clustering failure modes. CRC-invalid receptions are excluded from logical-frame identity because decoded payload bytes cannot be trusted as an exact identity key.

## CRC semantics

The source uses `crc_status` values 1 and -1. STACKWISE preserves the raw numeric value and exposes a convenience Boolean mapping (`1 -> True`, `-1 -> False`) for reception-side summaries. This does not create a transmission denominator.

## MType representation

The source stores MType-like values as decimal renderings of three-bit strings (for example `10` corresponds to `010`). STACKWISE stores the raw value, the zero-padded three-bit representation, a human-readable LoRaWAN MType name where defined, and a derived direction where the MType is directional.

## Sample versus full archive

The official six-day sample is the development target. A CLI file-glob override can request the complete archive. When both are extracted, the adapter selects the complete archive to avoid double counting sample days.

## Scientific limitation

LoED contains recorded gateway receptions, not all attempted transmissions. Gateway multiplicity, RSSI/SNR distributions and CRC-valid fractions are valid reception-side evidence. Absolute packet-delivery probability is not.

## Archive hygiene

The official sample archive may contain macOS AppleDouble resource-fork entries named ``._<date>.csv``. These binary metadata files are explicitly excluded before CSV discovery, as are files under ``__MACOSX``. They are not source observations and must not generate scientific warnings.

The six-day development sample need not contain receptions from all nine gateways documented for the complete campaign. Gateway counts are therefore reported as **observed gateways in the selected source profile**, not as the deployment size.



## Stage-2 evidence semantics (v0.1.14)

LoED Stage-2 evidence is not a row-level inference table. RSSI, cleaned canonical SNR and CRC-valid fraction are summarised by exact PHY stratum (`spreading factor x frequency x bandwidth`) and accompanied by gateway x PHY and gateway/day summaries. Logical-frame diversity is summarised separately from CRC-valid exact-PHY logical frames.

No LoED evidence record receives a numeric independent-unit count. High row/frame counts must not generate sqrt(n) confidence intervals. CRC-valid fraction is conditional on recorded gateway receptions and remains hard-incompatible with absolute delivery probability. Distinct-gateway logical-frame statistics are observation diversity, not simultaneous RF reception probability.
