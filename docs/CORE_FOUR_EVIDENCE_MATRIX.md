# STACKWISE core-four empirical evidence matrix

Version: v0.1.15  
Stage: 2 — Empirical Evidence Matrix

## Purpose

The unified core-four matrix is the canonical cross-dataset evidence inventory for the four validated empirical sources. It is **not** an MCDA score table and it does not transform heterogeneous measurements into a common utility scale.

Every row remains a typed Stage-2 evidence record with its original metric semantics, measurement/accounting boundary, workload conditions, independence unit, implementation context, provenance, derivation lineage and applicability limits.

## Frozen composition

The v0.1.15 matrix is assembled from the already materialised source artifacts:

| Dataset | Stage-2 records | Main evidence role |
|---|---:|---|
| Vomhoff NB-IoT/LTE-M | 52 | whole-device phase energy and duration |
| InSecTT | 80 | whole-device trace current/charge and validated-derived power/energy |
| LR-FHSS | 20 | radio-rail full-capture, incremental transaction and ACK/RX contrast energy |
| LoED | 246 | reception-side RSSI/SNR/CRC and logical-frame observation diversity |
| **Total** | **398** | **14 empirical metric IDs** |

The InSecTT source-voltage calibration remains one shared parameter. Parent evidence and shared-parameter references are checked globally after concatenation.

## Canonical artifacts

`data/analysis_ready/core_four_evidence/` contains:

- `core_four_evidence_matrix.jsonl` — schema-preserving canonical record stream;
- `core_four_evidence_matrix.parquet` — analysis-efficient matrix with list lineage fields retained;
- `core_four_evidence_matrix.csv` — human-readable flattened export;
- `shared_parameters.json` — shared parameter registry referenced by the matrix.

`results/validation/core_four_evidence_matrix/` contains:

- `summary.json` — frozen counts and lineage checks;
- `metric_coverage.csv` — dataset/technology/metric coverage and independent-unit summary;
- `boundary_profile.csv` — unique measurement/accounting boundary signatures;
- `decision_target_gap_matrix.csv` — explicit relation of current evidence to future decision estimands;
- `nonmetric_evidence_gaps.csv` — standards/stack/scenario gaps not representable as current empirical metric records;
- `run_manifest.json` — inputs, outputs and scientific safeguards.

## Scientific safeguards

The assembler fails if:

1. a core source has an unexpected Stage-2 record count;
2. an evidence record no longer validates against the evidence schema/catalogue;
3. evidence IDs collide across datasets;
4. parent evidence IDs are unresolved;
5. shared parameter IDs are unresolved or duplicated;
6. a target-only decision metric has been materialised as empirical evidence;
7. LoED records acquire an invented independent-unit count;
8. the target-gap policy references supporting/prohibited metrics that are not actually present.

Missing target evidence is never imputed.

## Boundary profile

The 398 records currently produce 20 distinct dataset/metric measurement-boundary signatures. This is expected and scientifically important. In particular:

- Vomhoff energy is whole-device / source phase;
- InSecTT capture energy is whole-device / approximately 60 s trace window;
- LR-FHSS energy is radio-rail / trace window or transaction;
- LoED is gateway-receiver / recorded reception or CRC-valid logical frame.

Unit equality therefore remains insufficient for direct cross-source comparison. The unified matrix preserves these differences rather than normalising them away.

## Decision-target gap interpretation

Five future decision estimands are audited explicitly:

- `expected_device_energy_per_application_report_j`;
- `delivery_probability`;
- `feasible_link_probability`;
- `end_to_end_application_latency_ms`;
- `lifecycle_cost_eur`.

Current status:

- energy has bridgeable component evidence from Vomhoff, InSecTT and LR-FHSS, but no common per-report estimand yet;
- LoED RSSI/SNR are bridgeable to a LoRaWAN-specific feasible-link model, not to a universal cross-RAT score;
- LoED can condition a future delivery model but cannot provide absolute delivery probability because attempted transmissions are unavailable;
- Vomhoff phase durations are bridgeable components for an end-to-end latency model, not direct application latency;
- lifecycle cost is absent from all four empirical sources.

The gap matrix also preserves prohibited proxies: LoED CRC-valid reception fraction and logical-frame gateway diversity cannot be substituted for delivery probability or PDR.

## LoED stratum audit note

The production LoED Stage-2 summaries contain 49 reception PHY strata but 48 CRC-valid logical-frame PHY strata. The difference is one recorded-reception stratum (`SF7`, `868.3 MHz`, `250 kHz`) with 65,498 recorded receptions and zero CRC-valid receptions. The matrix retains this as a reception-side observation and does not infer why it occurs. Because logical-frame materialisation is CRC-valid by definition, the stratum correctly contributes no logical-frame row.

The 49 PHY-stratum reception summaries omit 167 reception rows with incomplete PHY keys; the corpus-level CRC record still uses all 11,263,001 recorded receptions. Those 167 omitted-from-stratum rows are CRC-invalid in the validated corpus accounting. This is a stratification detail, not an attempted-transmission denominator.

## Stage boundary

Successful v0.1.15 materialisation completes the **core-four assembly portion of Stage 2**. It does not make the five future decision targets complete.

The next scientific stage is Stage 3: define uncertainty representations, dependence structures, shared parameters and study/device effects for evidence that will later feed explicit bridge models. Stack definitions, scenarios, feasibility filtering and stochastic MCDA remain downstream.


## Production review closure

The production v0.1.15 matrix review reconciled all 398 records across dataset, metric, uncertainty-basis and boundary summaries. The 5 x 4 decision-target gap matrix is internally complete. Stage 2 is therefore closed for the validated core-four.

The next layer is governed by `docs/UNCERTAINTY_MODEL.md` and the v0.1.16 uncertainty contract. Stage-2 records remain unchanged; uncertainty is calibrated from the correct lower-level sampling units rather than inferred from matrix row counts.
