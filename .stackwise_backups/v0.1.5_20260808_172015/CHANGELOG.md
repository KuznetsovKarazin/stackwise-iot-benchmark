# Changelog

## 0.1.4

- Replaced the placeholder InSecTT generic adapter with a dataset-specific streaming nested-ZIP adapter.
- Added correct 10 us timestamp interpretation and microampere current handling.
- Added communication-period to payload mapping: 100/200/400/800/1600 ms -> 2/4/8/16/32 bytes.
- Added exact trace-level current statistics and integrated charge while intentionally leaving power/energy unset because source voltage is not present in the dataset README.
- Verified the InSecTT dataset licence as CC BY 4.0 from the source README.
- Added the related publication Table 1 reference values and an independent scale-validation script that infers the implied source voltage rather than guessing it.
- Added InSecTT adapter methodology notes and regression tests.

## 0.1.3 — 2026-08-06

- Canonicalise missing values in Vomhoff aggregation keys before cross-chunk accumulation.
- Fix one duplicate observation identifier caused by `NaN != NaN` when a logical Figure 3 group crossed a CSV chunk boundary.
- Add a regression test that forces the affected group across chunks.
- Expected regenerated dataset: 1,671 unique run-phase observations and no duplicate-ID warning.

## 0.1.2 — 2026-08-06

- Corrected the Vomhoff adapter to preserve separate run-phase segments when the authors' R scripts distinguish them by `diff_time`.
- Added `source_diff_time_s` provenance and stable collision-resistant observation identifiers.
- Removed misleading multiple-duration warnings caused by the previous segment collapse.
- Added regression tests for repeated event labels with distinct source durations and normalised-label collisions.

## 0.1.1 — 2026-08-06

- Added the missing runtime dependency `tabulate`.
- Replaced the placeholder Vomhoff NB-IoT/LTE-M adapter with a chunked run-by-phase importer for the real public CSV structure.
- Preserved the source Figure 3-5 normalisation rules and raw provenance values.
- Marked the downloaded dataset licence as verified CC BY 4.0.
- Added adapter-specific tests and documentation.
