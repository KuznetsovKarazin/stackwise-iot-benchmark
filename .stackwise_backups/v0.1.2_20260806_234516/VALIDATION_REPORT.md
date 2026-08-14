# STACKWISE v0.1.1 validation report

Validation date: 6 August 2026

## Completed checks

- Python source compilation succeeded for `src/`, `scripts/`, and `tests/`.
- Dataset registry validation succeeded and contains 12 empirical public-data records.
- All 16 automated tests passed.
- The self-contained smoke pipeline completed and generated nine outputs.
- The Vomhoff NB-IoT/LTE-M adapter was exercised against the user-provided diagnostic samples from all three public CSV files.
- The adapter produced non-empty run-by-phase observations and preserved raw and normalised energy values.
- Synthetic unit tests reproduce the source Figure 3, Figure 4, and Figure 5 normalisation rules.
- SMAA rank-acceptability rows sum to one in tests.
- Fleet assignments satisfy group-specific feasibility constraints.
- Trace integration refuses to invent energy when voltage is absent.
- Canonical observation fixtures pass JSON Schema validation.

## v0.1.1 corrections

- Added the missing `tabulate>=0.9` runtime dependency required by `pandas.DataFrame.to_markdown()`.
- Implemented chunked parsing of the actual Vomhoff CSV schema.
- Marked `vomhoff_nbiot_ltem_energy_2023` as verified CC BY 4.0.
- Added source-specific provenance and adapter documentation.

## Smoke outputs

The smoke pipeline generates:

- dataset and metric coverage audit;
- provisional energy-model summary;
- rank-acceptability table and plot;
- fleet-optimisation result.

These outputs use `data/examples/smoke_observations.csv`, which is explicitly marked `TEST_ONLY`. They are software-validation artefacts, not research results.

## External-data boundary

The full 541 MB Vomhoff dataset was downloaded and checksum-verified in the user's local environment. The execution container used to build v0.1.1 received only diagnostic samples, metadata, README, and the authors' R scripts. Therefore, full-dataset row counts and source-figure numerical equality must be checked after the patch is applied locally.

The new adapter processes the full CSV files in chunks and does not require loading them entirely into memory.
