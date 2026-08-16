# STACKWISE Paper B - Independent admissibility audit

## Design

The primary audit uses four independent expert groups, anonymised here as Raters A-D. Each rater independently classified the same 35 blinded source-target relations (20 frozen-benchmark items and 15 held-out-source items) using `C0_DIRECT`, `C1_BRIDGEABLE`, `C2_CONDITIONAL`, or `E0_MISSING`. The frozen STACKWISE label was hidden during classification. No frozen classifier label was changed after the responses were received.

## Primary results

| Rater | Agreement vs frozen classifier | Cohen kappa | Internal agreement | Held-out agreement |
|---|---:|---:|---:|---:|
| A | 80.0% (28/35) | 0.558 | 80.0% | 80.0% |
| B | 80.0% (28/35) | 0.543 | 80.0% | 80.0% |
| C | 65.7% (23/35) | 0.332 | 65.0% | 66.7% |
| D | 85.7% (30/35) | 0.685 | 80.0% | 93.3% |

Across the four independent raters, Fleiss' kappa is **0.537** overall, **0.497** for the 20 internal items, and **0.587** for the 15 held-out items. The frozen key is class-imbalanced (`E0_MISSING` = 24/35), so kappa is interpreted together with raw agreement.

Unanimous 4/4 agreement occurs for **22/35 (62.9%)** items. At least 3/4 raters agree on the same class for **32/35 (91.4%)** items. Among those 32 majority-or-unanimous items, consensus matches the frozen classifier in **27/32 (84.4%)** cases.

## Consensus disagreements with the frozen classifier

| Item | Partition | Target | Frozen class | Primary expert consensus | Support |
|---|---|---|---|---|---:|
| I02 | internal | `delivery_probability` | `C2_CONDITIONAL` | `E0_MISSING` | 4/4 |
| I14 | internal | `feasible_link_probability` | `C1_BRIDGEABLE` | `C2_CONDITIONAL` | 3/4 |
| I12 | internal | `expected_device_energy_per_application_report_j` | `C1_BRIDGEABLE` | `C0_DIRECT` | 3/4 |
| E06 | held-out | `delivery_probability` | `C2_CONDITIONAL` | `E0_MISSING` | 4/4 |
| E09 | held-out | `feasible_link_probability` | `C1_BRIDGEABLE` | `C2_CONDITIONAL` | 3/4 |

The confirmatory classifier remains frozen. These disagreements are treated as construct-validity evidence about bridge severity, not as a tuning signal.

## Public reproducibility

`external_validation/results_public/audit_primary_labels_anonymized.csv` contains only anonymised primary labels/confidence and excludes names, identifying information, and free-text rationales. Aggregate agreement files are published alongside it. Original returned audit files remain private.
