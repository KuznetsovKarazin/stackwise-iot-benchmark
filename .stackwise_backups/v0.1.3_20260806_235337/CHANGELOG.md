# Changelog

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
