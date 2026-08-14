# Paper A — STACKWISE Empirical Evidence Benchmark

Working title: **STACKWISE Empirical Evidence Benchmark: A Harmonised Multi-Source Dataset for Layer-Aware IoT Communication Stack Analysis**

Central research/data question: **How can heterogeneous public IoT measurements be transformed into a traceable, layer-aware and uncertainty-aware empirical benchmark without erasing statistical units, accounting boundaries or provenance?**

## Scope boundary

This manuscript describes and technically validates Benchmark v1.0.0. It does **not** report Experiments 1–5, preference scoring, fleet set-cover conclusions or candidate rankings. Those belong to Paper B.

## Proposed structure

1. **Introduction** — fragmentation of empirical IoT evidence; need for a reusable harmonised evidence resource; contributions of the benchmark itself.
2. **Source datasets and provenance** — four upstream datasets, licences, DOIs, measurement purposes and why they are complementary rather than directly interchangeable.
3. **Harmonisation and canonical model** — raw→diagnostic→analysis-ready→canonical evidence workflow; schemas; typed metrics; derivation lineage; statistical and independence units.
4. **Measurement and accounting boundaries** — whole-device versus radio/receiver observations; denominators; why LoED logical-frame diversity is not PDR; boundary-preserving design.
5. **Uncertainty/dependence metadata** — bootstrap/block/robustness semantics; dependence groups; why the benchmark stores heterogeneous uncertainty rather than forcing one common probability model.
6. **Benchmark definitions and packaged layers** — 398 records, 14 metrics, seven scenarios, nine stacks, feasibility/support artefacts; empirical-derived versus synthetic/model-derived separation.
7. **Technical validation** — schema checks, format equivalence, row counts, frozen 7×9 product, licences, checksums, release QA and reproducibility.
8. **Data records and reuse notes** — file layout, CSV/JSONL/Parquet choices, recommended admissibility checks, limitations and prohibited interpretations.
9. **Data/code availability and citation** — Zenodo DOI, repository, CC BY 4.0 dataset licence and Apache-2.0 software licence.

## Main data-paper claims

- the resource is a new harmonised **derived benchmark**, not newly collected primary measurements;
- provenance, boundaries, statistical units and uncertainty semantics are retained rather than flattened;
- the four source datasets are complementary and not treated as exchangeable observations;
- technical QA and machine-readable schemas make the release reusable and auditable.

## Material explicitly excluded

Do not include the 142/175 infeasible-top-set result, the 0/10/21 admissibility inflation, the €100 cost-simplification result or the 4/5 fleet coverage result. At most mention that a separate methodology study uses the benchmark.
