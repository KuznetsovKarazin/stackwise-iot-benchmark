# STACKWISE independent admissibility audit — instructions

Purpose: independently assess whether each evidence source can support the specified decision target. The audit is **blinded to the STACKWISE algorithmic classification**. It is a validation audit only: expert responses will not be used to change the frozen classifier or external-validation outcomes post hoc.

## Classification labels

- **C0_DIRECT** — the source directly identifies the same target estimand with compatible unit, physical/system boundary, temporal/accounting boundary, conditioning and required statistical meaning.
- **C1_BRIDGEABLE** — the source contains relevant empirical evidence, but reaching the target requires an explicit, provenance-preserving deterministic/model bridge whose assumptions must be stated.
- **C2_CONDITIONAL** — the source can characterize or condition a model for the target but does not identify a score-ready target value at the required boundary.
- **E0_MISSING** — the source does not contain the evidence required for this target estimand.

## Procedure

For each of the 35 rows in `STACKWISE_admissibility_blind_audit_for_expert.csv`:

1. Read only `source_evidence_summary` and `target_definition`.
2. Enter one of the four labels above in `expert_class`.
3. Enter `high`, `medium`, or `low` in `expert_confidence`.
4. Give a short technical reason in `expert_rationale`, especially when the distinction is C1 vs C2.
5. Do not consult STACKWISE result tables, source-target relation files, or the algorithm key while classifying.

If the summary is insufficient to decide, write `NEEDS_SOURCE_INSPECTION` in `expert_class` rather than guessing. We can then provide the original source documentation for that row without revealing the algorithm output.

## Independence

Preferred: two domain experts who were not involved in defining the STACKWISE admissibility taxonomy. Minimum useful audit: one independent expert. Coauthors may provide a secondary audit, but this is weaker evidence of independence.

## Analysis after return

The returned sheet will be compared against the frozen algorithm key using exact agreement and Cohen's kappa (for each expert separately). Disagreements will be reported transparently and will **not** retroactively change the frozen primary outcomes; an adjudicated interpretation may be discussed separately.
