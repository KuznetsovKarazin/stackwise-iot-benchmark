# STACKWISE v0.1.0 validation report

Validation date: 6 August 2026

## Completed checks

- Python package compilation succeeded for `src/`, `scripts/` and `tests/`.
- Dataset registry JSON Schema validation succeeded.
- Active registry contains 12 empirical public-data records.
- Exclusion register contains restricted, simulated, synthetic or irrelevant candidates.
- All 13 automated tests passed.
- Editable package installation was tested with `--no-build-isolation` in the build environment.
- Installed `stackwise` CLI successfully listed registry records.
- Self-contained smoke pipeline completed successfully and generated nine outputs.
- SMAA rank-acceptability rows sum to one in tests.
- Fleet assignments satisfy group-specific feasibility constraints.
- Trace integration refuses to invent energy when voltage is absent.
- Canonical observation fixtures pass JSON Schema validation.

## Smoke outputs

`results/smoke/` contains:

- dataset and metric coverage audit;
- provisional energy-model summary;
- rank-acceptability table and plot;
- fleet-optimisation result.

These outputs use `data/examples/smoke_observations.csv`, which is explicitly marked `TEST_ONLY`. They are software-validation artefacts, not research results.

## External-data boundary

Large third-party datasets are not included in this archive. The download layer resolves files from Zenodo or Kaggle, records metadata and checksums, and requires explicit licence acceptance. External network downloads were not executed during archive validation because the execution container has no direct Internet access.

Dataset-specific adapters are deliberately conservative and may report missing columns rather than infer units or measurement boundaries. Each adapter must be validated against the downloaded record before production analysis. This validation is the first task of Stage 1 in `docs/RESEARCH_PLAN.md`.
