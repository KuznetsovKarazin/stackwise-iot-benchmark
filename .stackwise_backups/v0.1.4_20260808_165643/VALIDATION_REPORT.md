# STACKWISE v0.1.3 validation report

Validation date: 6 August 2026

## Completed checks

- Python package compilation succeeded for `src/`, `scripts/` and `tests/`.
- Dataset registry JSON Schema validation succeeded.
- Active registry contains 12 empirical public-data records.
- All 18 automated tests passed.
- Self-contained smoke pipeline completed successfully.
- The Vomhoff adapter reproduces source-defined Figure 3--5 normalisation rules.
- Regression tests confirm that repeated event labels with distinct `diff_time` values remain separate observations.
- Observation identifiers remain unique when raw labels normalise to the same canonical technology or protocol name.

## External-data validation finding

The v0.1.1 production run generated 1,450 rows but reported 222 repeated-event warnings and one duplicate observation identifier. Inspection showed that the source R scripts group by `diff_time`, whereas v0.1.1 collapsed those segments before averaging duration. Version 0.1.3 corrects the grouping key and should be used to regenerate the processed Parquet file.

## External-data boundary

Large third-party datasets are not included. Raw files remain under `data/raw/`; patch application does not modify or delete them.


## v0.1.3 regression

The reported duplicate was traced to a logical group with a missing `data` value crossing a CSV chunk boundary. Python NaN values are not equal to themselves, so two persistent accumulators were created. v0.1.3 canonicalises missing group values before accumulation and includes a forced-chunk regression test. The corrected production harmonisation is expected to contain 1,671 unique observations.
