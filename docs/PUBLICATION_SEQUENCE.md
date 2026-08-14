# Publication sequence after v0.1.59

The scientific experiment programme is closed. No Experiment 6 is planned.

1. **Package Benchmark v1.0.0** with `python scripts/package_benchmark_for_deposit.py` and verify the SHA-256.
2. **Create the Zenodo draft and reserve a DOI.** Confirm creators/authorship manually before publication.
3. **Insert the reserved/final benchmark DOI** into repository metadata and both manuscript drafts; do not alter benchmark data files to do this.
4. **Draft Paper A (data/benchmark)** from `PAPER_A_DATA_BENCHMARK_OUTLINE.md`. Keep Experiments 1–5 out.
5. **Draft Paper B (STACKWISE methodology/results)** from `PAPER_B_STACKWISE_METHOD_OUTLINE.md`, using Benchmark v1.0.0 as frozen input.
6. **Cross-paper overlap audit:** no duplicated Methods/Results text beyond a short benchmark synopsis and citation in Paper B.
7. **Submission QA:** verify claims against `results/publication/final_consolidation/claim_evidence_matrix.csv` and keep C7/C8 blocked.

Substantive changes to the benchmark after public release require a new benchmark version. Substantive new research results require a new experiment stage rather than editing closed Experiments 1–5 in place.
