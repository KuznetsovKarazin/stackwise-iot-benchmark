# STACKWISE Empirical Evidence Benchmark v1.0.0

Project version: v0.1.51  
Released: 2026-08-12  
Licence: CC BY 4.0  
Status: final benchmark dataset release

## Purpose

STACKWISE v1.0.0 is a harmonised, provenance-preserving benchmark derived from real measurements published by four independent upstream studies. It is **not** a new physical measurement campaign.

The benchmark is deliberately layered instead of flattening heterogeneous evidence into one comparison table. Measurement boundaries, statistical units, independence assumptions, uncertainty semantics, derivation lineage and applicability limits are preserved.

## Core empirical sources

The release contains derivatives/evidence from exactly four validated sources:

1. InSecTT WSN Power Consumption — BLE, Thread/OpenThread, UWB and EPhESOS;
2. Vomhoff et al. NB-IoT/LTE-M energy measurements;
3. LoED real-world LoRaWAN gateway-reception observations;
4. LoRaWAN LR-FHSS current-consumption measurements.

The canonical cross-source evidence matrix contains **398 typed Grade-A evidence records spanning 14 metric IDs**. Every upstream source is identified in `SOURCE_ATTRIBUTION.csv` and `SOURCE_LICENSES.csv` and must be cited independently when its evidence is used.

## Release layers

### L0 — analysis-ready source-specific data

Compact processed derivatives of the real upstream measurements: Vomhoff logical run/phase observations, InSecTT and LR-FHSS configuration observations, LR-FHSS ACK/RX contrasts, and LoED PHY/gateway/day/logical-frame summaries.

These tables are derived from real measurements but are not mirrored raw source archives.

### L1 — canonical evidence records

The 398-record `core_four_evidence_matrix` in CSV, JSONL and Parquet form plus the shared-parameter registry. Evidence records retain source DOI/licence, measurement boundary, statistical and independence units, derivation class, uncertainty semantics and applicability domain.

### L2 — uncertainty/dependence contracts

The frozen uncertainty plan, dependence groups and LoED robustness family. Empirical resampling, unweighted robustness families and explicit non-identifiability remain distinguishable; they are not pooled into one artificial probability model.

### L3 — benchmark definitions

Seven quantitative STACKWISE scenarios, nine end-to-end candidate stacks and the 25-component catalogue. These are STACKWISE-authored benchmark definitions, not measurements.

### L4 — feasibility and evidence support

The frozen **63-row** tri-state hard-feasibility product: **21 feasible / 39 infeasible / 3 unresolved**, plus stack evidence-support and current criterion-readiness tables.

### L5 — synthetic/model-derived sensitivity

Protocol/session/serialization and lifecycle-cost sensitivity artifacts. L5 is intentionally segregated and **must never be described as empirical measurement data**.

## Licence and attribution

STACKWISE-authored benchmark material is released under **CC BY 4.0**. This dataset licence is separate from the Apache-2.0 software licence used by the repository code.

The benchmark does not mirror upstream raw archives. All four upstream source licences are verified as redistributable in the release ledger. Attribution metadata are frozen in `SOURCE_ATTRIBUTION.csv`; upstream datasets remain independently citable works.

## Frozen scientific checkpoints

The final builder fails closed if these counts drift:

- 398 canonical evidence records;
- 4 core empirical datasets;
- 14 metric IDs;
- 398 Grade-A evidence records;
- 7 benchmark scenarios;
- 9 candidate stacks;
- 63 scenario×stack feasibility rows;
- 21 feasible / 39 infeasible / 3 unresolved.

## Important scientific non-claims

STACKWISE v1.0.0 does not claim that STACKWISE collected the upstream physical measurements. It does not make heterogeneous energy measurements directly comparable merely because they share units, infer PDR from LoED reception-side CRC statistics, interpret single traces as repeated experiments, or convert L5 sensitivity variants into empirical observations.

The benchmark does not contain a final real-candidate MCDA ranking. Decision analyses must respect evidence readiness and measurement-boundary compatibility.

## Build and QA

With the validated local analysis-ready artifacts present:

```powershell
python .\scripts\build_benchmark_release.py
python .\scripts\audit_benchmark_release.py
```

The final package is written to:

`release/stackwise_benchmark_v1.0.0/`

The release-level audit checks canonical table equivalence, Parquet row metadata, complete 7×9 feasibility coverage, unique IDs/pairs, source licence and attribution gates, checksum coverage, absence of mirrored raw archives, benchmark licence declaration and final-version metadata.
