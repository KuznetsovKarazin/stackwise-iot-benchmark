# Reproducibility workflow

## 1. Immutable external raw layer

Path: `data/raw/<dataset_id>/`

Raw third-party files are downloaded from the original source using `stackwise download`. A `download_manifest.json` records source URLs and checksums. Raw files are not committed to Git and are never edited in place.

## 2. Diagnostic layer

Path: `results/diagnostics/<dataset_id>/`

Diagnostics contain small samples, schema reports and source documentation used while developing an adapter. Diagnostics are development aids, not publishable measurements.

## 3. Harmonised/source-derived layer

Path: `data/processed/<dataset_id>/observations.parquet`

This layer maps source observations to the canonical schema while preserving source-specific provenance fields. Unit conversions are allowed only when source units are known. Dataset-specific transformations must be documented in the dataset card.

`harmonization_report.json` and `run_manifest.json` are part of the provenance record.

## 4. Source-reproduction validation

Path: `results/validation/<dataset_id>/`

Where a source publication supplies figures/tables or documented state values, STACKWISE independently checks whether the harmonised raw evidence reproduces them. A successful source reproduction validates parsing/units/aggregation but does not automatically validate every new STACKWISE-derived metric.

## 5. Analysis-ready layer

Path: `data/analysis_ready/<dataset_id>/`

This layer contains new STACKWISE statistical units and derived variables. Examples:

- aggregation of repeated source segments into one independent experimental run;
- power/energy derived from a validated external voltage with explicit provenance;
- baseline-subtracted transaction energy after transaction-count validation;
- logical-frame summaries whose semantics have been independently audited.

Analysis-ready transformations must never overwrite the source-derived layer.

## 6. Empirical evidence matrix

Path: `data/evidence/` or another explicitly versioned generated-artifact path.

Only validated analysis-ready quantities are promoted into Stage-2 evidence records. Each record must validate against `datasets/schema/evidence_record.schema.json` and declare:

- canonical metric semantics and unit;
- structured measurement/accounting boundary;
- workload conditions;
- empirical and independence units;
- source grade, derivation class and validation status;
- parent evidence and shared uncertain parameters;
- uncertainty basis, applicability and limitations.

Compatibility is assessed before any shared calibration model. C1 bridgeable evidence remains separate until the bridge is implemented and validated. C3 incompatible evidence cannot populate the target criterion.

## 7. Cross-dataset uncertainty/model layer

Only evidence records with compatible or explicitly bridged scientific meaning enter shared models. Every model must declare:

- included evidence IDs and datasets;
- target estimand;
- measurement boundaries and bridge transformations;
- missing-data exclusions;
- source grades and derivation classes;
- statistical independence assumptions;
- shared parameters and correlated uncertainty;
- study/device effects;
- sensitivity analyses.

Artificial default precision is prohibited.

## 8. Decision layer

Hard feasibility filtering precedes stochastic MCDA. Rank acceptability is an uncertainty-conditioned ranking frequency, not an objective probability of being the true best technology.

Fleet optimisation must state cost boundaries, infrastructure ownership assumptions and complexity penalties. Prototype values in smoke configurations are not publication evidence.

## 9. Publication freeze

Before manuscript submission:

1. freeze dataset versions/DOIs and checksums;
2. freeze adapter versions and tests;
3. regenerate all harmonised and analysis-ready outputs from raw sources;
4. run all source-reference validations;
5. regenerate and validate the empirical evidence matrix;
6. rerun every uncertainty model, decision table and figure from scripts/notebooks;
7. archive Git tag plus Zenodo release;
8. cite every external dataset separately;
9. disclose the related textbook chapter and identify the article's new empirical/methodological contributions.

## Stage-2 InSecTT materialisation

After strict harmonisation and Table-1 scale validation, materialise configuration-level evidence with:

```powershell
python .\scripts\build_insectt_stage2_evidence.py
```

The command requires the validated 20-row processed table and fails if the 4 x 5 design, payload mapping, evidence schema, shared-parameter schema, or validated voltage-scale checkpoint changes unexpectedly. It does not modify raw or harmonised observations. Derived power/energy are written only to `data/analysis_ready/insectt_wsn_power_2023/` and share one explicit voltage parameter. Publication MCDA is not part of this command.


### LR-FHSS Stage-2 materialisation

```powershell
python .\scripts\build_lrfhss_stage2_evidence.py
```

This command requires the validated eight-row harmonised LR-FHSS observations table. It fails if the complete ACK/noACK x DR8--DR11 design is not present, if any capture has a TX-burst count other than one, or if validated baseline/measurement checkpoints are violated. It writes full-capture energy, incremental transaction energy and matched-DR ACK/RX contrast artifacts without generating confidence intervals or MCDA rankings.


## LoED Stage-2 materialisation

After fast full-corpus validation and with the validated logical-frame artifact present:

```powershell
python .\scripts\validate_loed_reference.py
python .\scripts\build_loed_stage2_evidence.py
```

The Stage-2 builder scans the processed reception Parquet and logical-frame Parquet by row group, writes compact summary/evidence artifacts, and checks frozen full-corpus counts. It does not rebuild clustering. Use `--rebuild-clusters` only when the logical-frame methodology itself changes.


## Unified core-four Stage-2 matrix

After the four dataset-specific Stage-2 materialisers pass, run:

```powershell
python .\scripts\build_core_four_evidence_matrix.py
```

The assembler validates all 398 records and the shared-parameter registry before writing `data/analysis_ready/core_four_evidence/`. The generated decision-target gap matrix is an audit of evidence availability/bridge requirements, not an MCDA input-score table. Missing target evidence must remain missing until an explicit source-backed bridge or new evidence source is validated.


## Stage 3 — Uncertainty specification and calibration

Stage 3 operates only on validated Stage-2 evidence plus the lower-level analysis-ready artifacts required by a declared uncertainty model.

Required sequence:

1. identify the population estimand and physical sampling unit;
2. record parent/shared-parameter dependence;
3. determine whether between-unit variability is empirically identifiable;
4. if replicated units exist, calibrate uncertainty without breaking within-unit dependence;
5. if only one unit exists, preserve the point evidence and require external repeatability evidence/prior rather than manufacturing a CI;
6. for hierarchical observational data, construct grouped/block calibration artifacts before stochastic sampling;
7. keep study/implementation and bridge-structural uncertainty separate;
8. validate the uncertainty specification before generating any publication stochastic samples.

Forbidden:

- IID bootstrap of source segments, high-frequency electrical samples or LoED receptions when those are not independent units;
- default SD/CV fallbacks;
- generic study random effects when study is confounded with technology/boundary;
- independent sampling of records sharing a parent trace/run or shared calibration parameter;
- publication MCDA before bridge-target uncertainty is validated.

## Stage 5B — LR-FHSS source-model bridge audit

After Stage 5A and the LR-FHSS Stage-2/validation artifacts are present:

```powershell
python .\scripts\audit_lrfhss_source_model_bridge.py
```

The audit requires the Stage-5A profile artifacts, the eight-row LR-FHSS `transaction_derivation.csv`, the eight-row trace-validation table, and the Stage-3 uncertainty state. It reproduces the source publication's Table-6 timing rows, compares modeled and measured 4-byte incremental radio energy, audits the TX plateau against the published state current, and materialises 16-byte radio-component diagnostics only where source-trace reproduction passes.

The script must not update the frozen Stage-4 matrix, choose a best DR/confirmation mode, treat a radio-component quantity as whole-device energy, infer population uncertainty from one trace, or generate preference/MCDA output.

### Stage 5C — LR-FHSS profile-variant materialisation

```powershell
python .\scripts\materialise_lrfhss_profile_variants.py
```

The command consumes frozen Stage-5A profiles and Stage-5B source-model outputs. It enumerates all eight source-aligned DR/confirmation variants, verifies that no variant weights or deployment selection are introduced, materialises conditional feasibility implications, and preserves the frozen Stage-4 matrix.

