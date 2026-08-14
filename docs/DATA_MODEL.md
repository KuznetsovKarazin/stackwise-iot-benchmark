# Canonical data model

STACKWISE uses a long-form canonical observation table. It does not require every dataset to supply every field.

## Identity and provenance

`dataset_id`, `study_id`, `source_file`, `observation_id`, `source_doi`, `source_license`, `evidence_grade`.

## Stack description

`technology`, `access_network`, `transport_protocol`, `application_protocol`, `security_mode`.

## Workload and session state

`payload_bytes`, `direction`, `reporting_interval_s`, `session_policy`, `confirmation_mode`, `upper_layer_bytes`.

## Radio and environment

`tx_power_dbm`, `rssi_dbm`, `snr_db`, `rsrp_dbm`, `rsrq_db`, `sinr_db`, `operator`, `environment`, `latitude`, `longitude`.

## Energy and timing

`duration_s`, `voltage_v`, `current_a`, `peak_current_a`, `power_w`, `mean_power_w`, `energy_j`, `latency_ms`, `delivery_success`, `retries`.

## Measurement boundary

This field is mandatory and must never be inferred from the technology name alone. Recommended values:

- `end_device_radio_cycle`;
- `full_device_cycle`;
- `device_to_gateway`;
- `gateway_observation`;
- `ip_to_modem`;
- `network_coverage`;
- `end_to_end_network`;
- `end_to_end_application`.

## Missing data

Unknown values remain null. A model must state which fields it requires and report how many observations were excluded for missingness.

## Stage-2 evidence records

The canonical observation table is a harmonisation contract, not the final cross-dataset comparison contract. Cross-dataset evidence is represented separately by `datasets/schema/evidence_record.schema.json` and the taxonomy described in `docs/EMPIRICAL_EVIDENCE_MODEL.md`.

In particular, the single canonical `measurement_boundary` string is decomposed at Stage 2 into system scope, temporal scope, accounting basis, conditioning/denominator, payload basis, baseline/ACK/retry accounting and path endpoints. Existing harmonised observations are not rewritten merely to adopt the Stage-2 taxonomy.
