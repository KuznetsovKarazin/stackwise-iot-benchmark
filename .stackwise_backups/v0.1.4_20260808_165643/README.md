# STACKWISE

**Layer-aware, evidence-driven and uncertainty-aware selection of IoT communication stacks**

STACKWISE is a reproducible research codebase for collecting, auditing, harmonising and analysing public empirical measurements of IoT communication technologies. It separates five tasks that are often mixed in protocol-comparison studies:

1. evidence acquisition and provenance;
2. harmonisation of measurement boundaries and units;
3. empirical calibration of energy, latency, reliability and coverage models;
4. feasibility filtering and stochastic multicriteria acceptability analysis;
5. fleet-level communication-architecture optimisation.

This repository is an initial research scaffold. The included `data/examples/` observations are **synthetic smoke-test fixtures only** and must never be used as research evidence. Research results must be generated from the public datasets listed in `datasets/registry.yml` or from explicitly documented new measurements.

## Current public evidence base

The initial registry contains publicly downloadable empirical records for:

- BLE and Thread power traces;
- NB-IoT and LTE-M energy measurements with HTTP/MQTT phases;
- LoRaWAN gateway-side RSSI/SNR observations;
- LoRaWAN LR-FHSS current traces with ACK/no-ACK conditions;
- operational 4G, NB-IoT and 5G coverage/performance measurements;
- NB-IoT coverage campaigns in Rome and Oslo;
- additional LoRa and BLE signal-quality datasets;
- two optional Kaggle BLE RSSI datasets with declared licences.

Restricted, simulated, synthetic or application-energy datasets that are unsuitable for protocol benchmarking are recorded separately in `datasets/excluded.yml`.

## Design principles

- **No silent downloading.** Dataset downloads require explicit licence acceptance.
- **No silent redistribution.** External raw files remain outside Git and are downloaded from their original repositories.
- **No mixed accounting boundaries.** Every observation records what was measured: radio-only, device cycle, device-to-gateway, IP-to-modem, or end-to-end.
- **No forced comparability.** Missing metadata are preserved as missing rather than guessed.
- **No single “best protocol”.** Results are conditional on workload, feasibility requirements, evidence and stakeholder preferences.
- **Full provenance.** Download metadata, file checksums, transformations and software versions are recorded.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"

stackwise registry-validate
stackwise registry-list
stackwise reproduce --smoke
pytest
```

The smoke pipeline creates reports in `results/smoke/` without downloading external data.

## Downloading public datasets

Review `DATA_LICENSES.md` and the live record before downloading:

```bash
stackwise download vomhoff_nbiot_ltem_energy_2023 --accept-license
stackwise download loed_lorawan_edge_2020 --accept-license
```

For a record whose licence has not yet been verified in the registry:

```bash
stackwise download insectt_wsn_power_2023 \
  --accept-license --accept-unverified-license
```

Kaggle downloads require the official Kaggle API credentials:

```bash
pip install kaggle
stackwise download kaggle_position_annotated_ble_rssi --accept-license
```

## First research pipeline

```bash
# 1. Validate registry and produce an evidence audit
stackwise audit --registry datasets/registry.yml --output results/audit

# 2. Download selected core datasets
stackwise download insectt_wsn_power_2023 --accept-license --accept-unverified-license
stackwise download vomhoff_nbiot_ltem_energy_2023 --accept-license
stackwise download loed_lorawan_edge_2020 --accept-license --accept-unverified-license
stackwise download lorawan_lrfhss_energy_2024 --accept-license --accept-unverified-license

# 3. Harmonise one dataset at a time
stackwise harmonize insectt_wsn_power_2023
stackwise harmonize vomhoff_nbiot_ltem_energy_2023
stackwise harmonize loed_lorawan_edge_2020
stackwise harmonize lorawan_lrfhss_energy_2024

# 4. Combine canonical observations and fit a provisional model
stackwise combine --output data/processed/canonical_observations.parquet
stackwise fit-energy data/processed/canonical_observations.parquet \
  --output results/models/energy
```

## Repository structure

```text
STACKWISE/
├── configs/                 benchmark, MCDA and fleet scenarios
├── data/examples/           synthetic fixtures for tests only
├── datasets/                registry, exclusions, schemas and mappings
├── docs/                    methodology and research plan
├── notebooks/               executable entry-point notebooks
├── scripts/                 thin command-line wrappers
├── src/stackwise/           reusable Python package
├── tests/                   unit and smoke tests
├── results/                 generated outputs, ignored except placeholders
└── paper/                   manuscript workspace
```

## Reproducibility contract

A publishable STACKWISE result should include:

- immutable dataset identifiers and DOI/version information;
- original checksums where available;
- a generated download manifest;
- canonical schema validation results;
- explicit exclusions and missing-data decisions;
- leave-one-study-out validation;
- sensitivity to accounting boundary and evidence grade;
- a tagged GitHub release and a Zenodo archive.

## Citation

The project is not yet archived. Until a DOI is minted, cite the repository using `CITATION.cff`. Each external dataset must also be cited independently according to its source record.

## Licence

STACKWISE code is released under Apache-2.0. External datasets retain their original licences and are not covered by the code licence. See `DATA_LICENSES.md`.
