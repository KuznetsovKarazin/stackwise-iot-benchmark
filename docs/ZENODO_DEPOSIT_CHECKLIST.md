# Zenodo deposit checklist — STACKWISE Empirical Evidence Benchmark v1.0.0

Status: packaging-only finalisation. The benchmark data content is frozen.

## Before creating the Zenodo record

1. Run the final benchmark QA and require `25 / 0` failures and `zenodo_finalisation_ready: true`.
2. Run `python scripts/package_benchmark_for_deposit.py`.
3. Verify the generated SHA-256 sidecar with a second hash calculation.
4. Confirm the creator list. The current benchmark metadata names Oleksandr Kuznetsov as creator. Add any other human creator only if their contribution to the benchmark itself warrants dataset authorship; do not infer the data-paper author list automatically from the dataset creator list.
5. Keep the benchmark licence as CC BY 4.0. The software repository remains Apache-2.0.
6. Confirm the four `isDerivedFrom` dataset DOIs in `ZENODO_METADATA.json` and the full attribution matrix in `SOURCE_ATTRIBUTION.csv`.

## Zenodo record

Use resource type **Dataset** and title **STACKWISE Empirical Evidence Benchmark v1.0.0**. Upload the deterministic ZIP from `dist/stackwise_benchmark_v1.0.0/`, not the repository, raw upstream archives, or the experiment outputs.

The publication date should be the actual first public release date. Zenodo can reserve a DOI before publication; reserve it if the DOI should be inserted into the two manuscripts before the record is published.

Recommended record description: use the abstract/description in packaged `ZENODO_METADATA.json` and `DATASET_CARD.md`, preserving the distinction among source-specific empirical derivatives, canonical evidence records, benchmark definitions, feasibility/support results and synthetic/model-derived sensitivity layers.

## Final manual checks before Publish

- creator names and ORCIDs are correct;
- affiliations, if entered, are current and correct;
- CC BY 4.0 is selected for the dataset;
- four upstream dataset DOIs are linked as derived-from relations;
- archive SHA-256 matches `deposit_package_summary.json`;
- no raw upstream archive is present;
- no Experiment 1–5 result is presented as part of the benchmark dataset claim;
- the record is public only when the file set is final.

After publication, record the assigned DOI in the repository, the data paper and the STACKWISE methodology paper. Do not change Benchmark v1.0.0 files; create a new benchmark version for any substantive file changes.
