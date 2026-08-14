# Dataset card: `loed_lorawan_edge_2020`

## Identity

- DOI: `10.5281/zenodo.4121430`
- Dataset: LoED: The LoRaWAN at the Edge Dataset
- Technology: LoRaWAN
- Evidence grade: A for source quality; full corpus structurally validated
- Current status: complete 11,263,001-row corpus validated; CRC-valid logical-frame artifact validated; Stage-2 evidence materialised in v0.1.14

## Scientific role

Reception-side LoRaWAN link-quality and gateway-diversity evidence: RSSI, SNR, spreading factor, frequency, CRC state and multi-gateway observations in a heterogeneous urban deployment.

## Source structure

The README describes nine gateways in different indoor/outdoor urban locations. The complete source contains one CSV per collection day. The official sample contains six days.

Observed CSV schema:

- `time`;
- `device_address`;
- `physical_payload`;
- `gateway`;
- `crc_status`;
- `frequency`;
- `spreading_factor`;
- `bandwidth`;
- `code_rate`;
- `rssi`;
- `snr`;
- `size`;
- `mtype`;
- `fcnt`;
- `fport`.

The sample includes valid and invalid CRC observations. Some payload and FPort values are missing. The source parser itself analyses message counts, frequency/SF distributions and gateway-level RSSI/SNR distributions.

## Measurement boundary

Gateway reception observation. Each row describes a packet reception at one gateway, not an end-to-end application delivery event.

## Statistical units

1. packet-gateway reception row for raw link-quality distributions;
2. CRC-valid exact-PHY logical frame within one source day for distinct-gateway observation-diversity analysis; wall-clock gap is not used;
3. gateway/day and PHY-stratum aggregates for deployment summaries.

## Harmonisation

The v0.1.7 adapter maps RSSI, SNR, UTC timestamp, SF/frequency/bandwidth/code-rate, CRC state and gateway identity into the canonical layer while preserving LoED-specific provenance fields. Gateway coordinates/model/location are joined from the public README. `delivery_success` is deliberately left null.

The public physical payload is not copied into processed evidence. A SHA-256 fingerprint and decoded physical-payload length are retained for reproducible packet-identity work.

## Key limitation

The dataset is reception-side. It does not provide a complete denominator of all attempted transmissions. Therefore absolute PDR/reliability must not be inferred from counts of received rows alone.

## Sample versus full archive

The six-day sample was used to develop the adapter and remains a reproducibility checkpoint (326,870 reception rows). The complete archive has now been processed and validated with the same bounded-memory scientific transformations. The full corpus contains 11,263,001 gateway-reception rows across 188 source files and all nine documented gateways.

## Current Stage-2 action

The full-corpus source and logical-frame semantics are frozen. Stage-2 materialisation summarises reception-side evidence by exact PHY stratum and logical-frame observation diversity without rebuilding the raw corpus or introducing a transmission denominator.

## Sample/full execution policy

The registry continues to download the official six-day sample by default. For the complete archive use:

```powershell
stackwise download loed_lorawan_edge_2020 `
  --accept-license `
  --accept-unverified-license `
  --file-glob LoED_LoRaWAN_at_edge_dataset.zip
```

If both sample and complete archives are present locally, the adapter prefers the complete archive and ignores sample CSVs so sample days are not duplicated.

## Analysis-ready outputs

`scripts/build_loed_analysis_ready.py` produces:

- `logical_frame_reception_clusters.parquet`: CRC-valid exact-PHY logical frames within source day with distinct-gateway observation counts;
- `gateway_day_summary.csv`: gateway/day reception summaries with CRC-valid fraction conditional on recorded receptions.

`scripts/build_loed_stage2_evidence.py` additionally produces compact PHY-stratum and gateway-PHY summaries plus typed evidence records for RSSI, SNR, reception-side CRC-valid fraction, distinct-gateway count and multi-gateway observation fraction. No output is an absolute PDR estimate.


## SNR quality-control rule

The official sample contains rare source SNR values outside the broad physical sanity range used by STACKWISE, including `-128 dB`. The public dataset documentation does not define a sentinel interpretation for this value. STACKWISE therefore preserves the original value in `source_snr_db_raw` and maps values outside `[-50, 50] dB` to missing in canonical `snr_db`. All analysis-ready SNR summaries use the cleaned canonical field. Validation reports the number and fraction of affected source rows.


## Full-scale execution policy (v0.1.8)

The complete archive is read directly as ZIP members and written to canonical Parquet incrementally. The adapter does not extract the archive and does not concatenate all daily receptions in memory. Strict validation is vectorised over every transformed row. Downstream validation and packet clustering load only one source day at a time.

When both `LoED_LoRaWAN_at_edge_dataset-SAMPLE.zip` and `LoED_LoRaWAN_at_edge_dataset.zip` are present, the complete archive is selected automatically.

Before replacing sample outputs, run `scripts/checkpoint_loed_state.py`; it copies small reports and records SHA-256 checksums for large reproducible sample artifacts rather than duplicating them.


## Frozen full-corpus checkpoints

- 11,263,001 recorded gateway receptions;
- 8,327,571 CRC-valid and 2,935,430 CRC-invalid receptions;
- 130 raw SNR values outside the canonical range, retained separately in provenance;
- 5,378,763 CRC-valid exact-PHY logical frames within source day;
- 506,441 logical frames observed by more than one distinct gateway (9.42%);
- maximum distinct gateways per logical frame: 4.

These counts describe reception-side evidence. They do not identify attempted transmissions.
