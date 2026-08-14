# STACKWISE Empirical Evidence Benchmark v1.0.0-rc1

Project version: v0.1.50.post2  
Prepared: 2026-08-12  
Status: release candidate for manual scientific/licence review

## Purpose

This release candidate turns the already validated STACKWISE research artifacts into one versioned benchmark dataset. It is derived from real measurements published by four independent upstream studies; it is not a new physical measurement campaign.

The benchmark is intentionally **layered** rather than flattened into one score table. Heterogeneous measurement boundaries, statistical units, uncertainty semantics and applicability limits are preserved.

## Core empirical sources

The release uses exactly four validated core sources:

1. InSecTT WSN Power Consumption — BLE, Thread, UWB and EPhESOS;
2. Vomhoff NB-IoT/LTE-M energy measurements;
3. LoED real-world LoRaWAN gateway observations;
4. LoRaWAN LR-FHSS current-consumption measurements.

The frozen cross-source evidence matrix contains 398 typed Grade-A evidence records spanning 14 metric IDs. Source-specific Stage-2/analysis-ready tables are retained where they are compact and scientifically useful.

## Release layers

### L0 — analysis-ready source-specific data

Processed derivatives of the real upstream measurements, such as Vomhoff logical physical-run phases, InSecTT/LR-FHSS configuration observations, and compact LoED PHY/gateway/day summaries.

These are not raw mirrored source archives.

### L1 — canonical evidence records

The 398-record `core_four_evidence_matrix` in CSV, JSONL and Parquet form, plus the shared-parameter registry. Every record retains the upstream dataset ID/DOI, metric semantics, measurement boundary, statistical/independence unit, derivation lineage, uncertainty basis and applicability domain.

### L2 — uncertainty/dependence contracts

The frozen uncertainty plan, dependence groups and LoED robustness-family summary. Empirical resampling, robustness scenarios and non-identifiability remain distinguishable; they are not pooled into one artificial probability model.

### L3 — benchmark definitions

STACKWISE-authored scenarios, candidate stacks and component catalogue. These are benchmark definitions, not empirical measurements.

### L4 — feasibility and evidence support

The frozen 63-row tri-state hard-feasibility matrix (21 feasible / 39 infeasible / 3 unresolved), candidate evidence-support table and current criterion-readiness table.

### L5 — synthetic/model-derived sensitivity

Explicit protocol/session/cost sensitivity artifacts. These are included because they are needed to reproduce STACKWISE methodology/results, but they must never be described as measurements. They are physically separated from L0/L1.

## Licence and redistribution policy

The compact benchmark includes no raw external archives. The builder requires all four core-source registry entries to have a verified redistributable licence and fails closed otherwise.

At v0.1.50 all four core sources are recorded as CC BY 4.0. The release therefore permits redistribution of STACKWISE's own derived tables with attribution. Every upstream dataset must still be cited independently.

The release matrix resolves `source_license` to the currently verified release licence. Any change from the licence metadata stored when the evidence matrix was first materialised is recorded separately in `LICENSE_METADATA_CORRECTIONS.csv`. This is a metadata correction only; empirical values and scientific boundaries are unchanged.

## Frozen counts

The builder fails if the following production checkpoints drift:

- 398 core evidence records;
- 4 core empirical datasets;
- 14 metric IDs;
- 398 Grade-A records;
- 7 benchmark scenarios;
- 9 candidate stacks;
- 63 scenario×stack feasibility rows;
- 21 feasible / 39 infeasible / 3 unresolved.

## What this release does not claim

- It does not claim that STACKWISE collected the upstream physical measurements.
- It does not make heterogeneous energy values directly comparable merely because they share units.
- It does not infer PDR from LoED CRC fractions.
- It does not convert synthetic protocol sensitivity variants into empirical observations.
- It does not include a real candidate ranking.
- It does not authorise publication MCDA.

## Build

With the validated local `data/analysis_ready/` artifacts present:

```powershell
python .\scripts\build_benchmark_release_candidate.py
```

The default output is:

`release/stackwise_benchmark_v1.0.0-rc1/`

The release contains:

- layered tables;
- `SOURCE_LICENSES.csv`;
- `RELEASE_TABLE_MANIFEST.csv`;
- `release_summary.json`;
- `CHECKSUMS.sha256`;
- release `README.md`.

The builder performs licence gates, required-artifact checks, frozen-count validation, evidence-ID uniqueness checks and checksum materialisation.

## Release gate

A successful build means **ready for manual review**, not automatically ready for Zenodo upload. `zenodo_upload_authorised` remains false in RC1. Before v1.0.0 final, manually inspect the generated release directory, attribution, file sizes, licence ledger and whether every L5 artifact is correctly labelled synthetic/model-derived.


## Stage-4 scenario materialisation note

The release candidate contains the canonical **seven-scenario Stage-4E benchmark**. The original Stage-4D definition had six rows because `asset_tracking_mobility` was still underspecified; Stage-4E replaced that row with `asset_tracking_periodic_cross_cell` and `asset_tracking_connected_handover`. The release builder materialises those refined scenarios directly from `datasets/stage4_benchmark_scenarios.yml` and therefore remains consistent with the frozen 63-row feasibility matrix (21 feasible / 39 infeasible / 3 unresolved).

## RC QA (v0.1.50.post2)

After the first full local build, the RC is approximately 2.95 MB and is retained as one compact package. Parquet row counts in the manifest are now read from Parquet metadata rather than an empty-column Pandas read. The package additionally includes `DATASET_CARD.md`, eight canonical JSON schemas and the four upstream dataset cards.

Run the release-level QA after rebuilding:

```powershell
python .\scripts\audit_benchmark_release_candidate.py
```

A successful integrity audit checks CSV/JSONL/Parquet equivalence of the canonical evidence table, complete 7×9 feasibility coverage, row counts, checksums, source licences and absence of mirrored raw archives. It does **not** choose the licence for STACKWISE-authored benchmark material and does not authorise Zenodo publication by itself.
