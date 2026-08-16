# STACKWISE Paper B — External Validation Campaign Status

Current state: **DESIGN_FREEZE_1_SOURCE_FEASIBILITY_REVIEW**

Outcome-producing external analyses are **not permitted yet**. The guard runner refuses execution until a `PRE_DATA_FROZEN` protocol manifest exists.

## Completed

- External-validation protocol written and hashed.
- Frozen STACKWISE boundary taxonomy, metric catalogue, candidate-stack catalogue, component catalogue and v1.0.0 hard-feasibility matrix are SHA-256 pinned in the protocol manifest.
- Five external use cases preselected before outcome inspection.
- Three held-out empirical sources preselected, version/file/MD5 pinned.
- C0/C1/C2/E0 admissibility policy frozen.
- Negative control pre-registered: Povalac LoRaWAN sniffer evidence cannot become direct delivery probability without an attempted-transmission denominator.
- Validation tiers defined: ontology portability (all cases), decision-readiness (qualifying cases), portfolio analysis (only if at least 3 qualifying cases from at least 2 publication families).
- Vannieuwenborg smart-container and smart-parking requirements extracted before outcome analysis and retained even where the frozen STACKWISE ontology has no matching field.
- Outcome-run guard, input validator and protocol tests implemented.
- Existing Paper-B regression tests remain green.

## Still required before PRE-DATA freeze

### HINTS exact requirement extraction

Obtain and archive the exact companion artefacts from `SamirSim/Selection-Methodology-IoT` and populate:
- `HINTS_A_SMART_BUILDING`
- `HINTS_B_EVENT_VIDEO_SURVEILLANCE`
- `HINTS_C_PRECISION_AGRICULTURE`

Do not infer missing values from general IoT knowledge. Preserve exact source values and mark unrecoverable fields `unavailable`.

### Held-out files

Materialise locally and verify MD5:

1. Kousias et al. — `NB-IoT - Passive Measurements.csv`
   - DOI: 10.5281/zenodo.8224890
   - expected MD5: `c9da425b57b325a56f7ca0944c9d05b4`
   - local name: `external_validation/sources/kousias_nb_iot_passive.csv`

2. Povalac & Kral — `csv.zip`
   - DOI: 10.5281/zenodo.8090619
   - expected MD5: `075503abc397454901ed0e4457e5b998`
   - local name: `external_validation/sources/povalac_lorawan_csv.zip`

3. Leenders & Callebaut — `guusleenders/NB-IoT-Power-Measurements-v1.0.zip`
   - DOI: 10.5281/zenodo.3557239
   - expected MD5: `a146818e92f2b6c775a9a80cb200e814`
   - local name: `external_validation/sources/leenders_nbiot_power_v1.0.zip`

## Commands

Check readiness without producing outcomes:

```bash
python scripts/validate_external_validation_inputs.py
```

Attempt the final pre-data freeze only when exact HINTS requirements and all three held-out files are present:

```bash
python scripts/freeze_external_validation_protocol.py --freeze
```

A successful freeze changes `external_validation/protocol_manifest.json` to `PRE_DATA_FROZEN` and sets `outcome_analysis_permitted=true`.

Only then implement/run external source adapters and outcome analyses.
