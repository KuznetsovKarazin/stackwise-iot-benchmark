# STACKWISE

**Layer-aware, feasibility-first and uncertainty-aware analysis of IoT communication stacks**

[![Dataset DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21937093.svg)](https://doi.org/10.5281/zenodo.21937093)
[![License](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](pyproject.toml)
[![CI](https://github.com/KuznetsovKarazin/stackwise-iot-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/KuznetsovKarazin/stackwise-iot-benchmark/actions/workflows/ci.yml)

STACKWISE is a reproducible Python research codebase for constructing, validating and analysing a harmonised empirical evidence benchmark for IoT communication-stack selection. It keeps hard feasibility, measurement boundaries, provenance, statistical independence and heterogeneous uncertainty semantics explicit instead of forcing heterogeneous source measurements into a single undifferentiated score table.

## Frozen benchmark

The code accompanies the published **STACKWISE Empirical Evidence Benchmark v1.0.0**:

- DOI: **https://doi.org/10.5281/zenodo.21937093**
- 398 canonical evidence records
- 4 independently published empirical source datasets
- 14 metric families
- 7 benchmark scenarios
- 9 end-to-end candidate stacks
- complete 7 × 9 hard-feasibility matrix
- 21 feasible / 39 infeasible / 3 unresolved scenario–stack relations
- final benchmark QA: 25/25 checks passed
- deterministic deposit archive SHA-256: `22c17bf6f6bc53e893764a8e94668926e7b94365262ba34c052479d432957dac`

The benchmark is a **derived harmonised research resource**, not a claim of newly collected primary measurements. Raw upstream archives are not redistributed here. STACKWISE-authored benchmark material is CC BY 4.0; upstream datasets retain their original licences and attribution requirements.

## What this repository contains

The repository contains the code and machine-readable definitions used to:

1. register and audit public IoT measurement datasets;
2. reproduce source-specific quantities and validate measurement semantics;
3. materialise analysis-ready derivatives and canonical evidence records;
4. preserve measurement boundary, statistical unit, independence unit and provenance;
5. model heterogeneous uncertainty and dependence without unsupported pooling;
6. define layer-aware end-to-end candidate communication stacks;
7. perform tri-state hard-feasibility screening (`feasible`, `infeasible`, `unresolved`);
8. build and audit the frozen benchmark release;
9. reproduce the five publication experiments used in the STACKWISE methodology study.

No publication-grade global stochastic ranking across all candidate stacks is claimed. Matched whole-device energy-per-report evidence for the four cellular IP candidates remains a documented future-validation limitation.

## Repository layout

```text
.
├── configs/              benchmark and analysis configuration
├── datasets/             registries, benchmark definitions, schemas and evidence contracts
├── docs/                 methodology, dataset cards and validation documentation
├── notebooks/            compact entry-point notebooks
├── scripts/              reproducible command-line research workflows
├── src/stackwise/        reusable Python package
├── tests/                unit, regression and release-integrity tests
├── CITATION.cff          software citation metadata
├── DATA_LICENSES.md      upstream data licensing and redistribution policy
├── LICENSE               Apache-2.0 software licence
└── pyproject.toml        Python package definition
```

Local raw/derived data, generated results, release packages, backups and manuscript files are deliberately excluded from Git. The frozen benchmark itself is distributed through Zenodo.

## Installation

Python 3.10 or newer is required.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the source-only regression suite:

```bash
pytest -q
```

Tests that require locally downloaded upstream data are designed to skip when those data are absent; the repository never silently substitutes synthetic evidence for missing empirical measurements.

## Use the frozen benchmark

For most reuse, download the published benchmark directly from Zenodo rather than reconstructing it from the large upstream archives:

**https://doi.org/10.5281/zenodo.21937093**

The release contains analysis-ready derivatives, canonical evidence records, uncertainty/dependence contracts, scenario/stack definitions, feasibility/support tables, schemas, source dataset cards, licence metadata, attribution records and checksums.

## Reconstruct from upstream public data

The authoritative source registry is `datasets/registry.yml`. Review `DATA_LICENSES.md` before downloading any upstream data.

Typical workflow:

```bash
stackwise registry-validate
stackwise registry-list
```

Then download only the source datasets required for the intended reconstruction using the explicit licence-acceptance commands documented in the registry and dataset cards. Source-specific processing is documented in:

- `docs/DATASET_CARDS/`
- `docs/ADAPTER_NOTES_VOMHOFF.md`
- `docs/ADAPTER_NOTES_INSECTT.md`
- `docs/ADAPTER_NOTES_LRFHSS.md`
- `docs/ADAPTER_NOTES_LOED.md`
- `docs/REPRODUCIBILITY_WORKFLOW.md`

The core integration steps are implemented by the scripts under `scripts/`. They are intentionally fail-closed when required inputs, provenance fields, licences or validation conditions are missing.

## Reproduce the publication experiments

After the required frozen/materialised inputs are available, the five closed experiments are run with:

```bash
python scripts/run_experiment1_feasibility_first.py
python scripts/run_experiment2_evidence_admissibility.py
python scripts/run_experiment3_uncertainty_treatment.py
python scripts/run_experiment4_accounting_simplification.py
python scripts/run_experiment5_fleet_portfolio.py
```

The experiments support five distinct methodological analyses:

- feasibility-first versus score-first ordering;
- source quality versus target-level evidence admissibility;
- deterministic versus uncertainty-/robustness-aware treatment;
- protocol/session/billing accounting simplification;
- fleet portfolio feasibility and structural serviceability loss.

Generated results are intentionally not committed to the repository.

## Benchmark release integrity

The final benchmark can be rebuilt and audited locally after the validated data products are available:

```bash
python scripts/build_benchmark_release.py
python scripts/audit_benchmark_release.py
python scripts/package_benchmark_for_deposit.py
```

The public Zenodo record is the authoritative frozen data release. Rebuilding should reproduce the same scientific content; local packaging metadata may differ only when explicitly versioned.

## Public-repository safety check

Before contributing or creating a public release, run:

```bash
python scripts/audit_public_repository.py --working-tree
```

After staging changes with Git:

```bash
python scripts/audit_public_repository.py --staged
```

The audit rejects local backup/result/data paths, binary archives, oversized public files and common credential patterns. GitHub should still be treated as the final secret-scanning backstop, not as a substitute for local review.

## Citation

For the benchmark dataset, cite:

> Kuznetsov, O. (2026). *STACKWISE Empirical Evidence Benchmark: A Harmonised Multi-Source Dataset for Layer-Aware IoT Communication Stack Analysis* (Version 1.0.0) [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.21937093

For the software, use the repository's `CITATION.cff` and the immutable GitHub release/tag corresponding to the analysis. Each upstream empirical dataset must also be cited independently according to its source record.

## Code availability

A manuscript-ready code-availability statement is provided in `docs/CODE_AVAILABILITY.md`.

## Licensing

- **Software:** Apache License 2.0 (`LICENSE`).
- **STACKWISE Benchmark v1.0.0:** CC BY 4.0.
- **Upstream datasets:** retain their original licences; see `DATA_LICENSES.md` and `datasets/registry.yml`.

## Project status

- Benchmark v1.0.0: frozen and published.
- Benchmark QA: passed.
- Experiments 1–5: closed.
- Global publication-grade stochastic MCDA: not claimed.
- Matched whole-device cellular report-energy comparison: not claimed; future validation.
