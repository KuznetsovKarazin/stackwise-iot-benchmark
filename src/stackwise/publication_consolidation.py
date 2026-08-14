from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class ConsolidationSummary:
    experiments_closed: int
    headline_result_rows: int
    strong_claims: int
    partial_claims: int
    open_claims: int
    main_figures_recommended: int
    main_tables_recommended: int
    fleet_experiment_recommended: bool
    full_global_mcda_authorised: bool


def _require(summary: Mapping[str, object], key: str, expected: object) -> None:
    got = summary.get(key)
    if got != expected:
        raise ValueError(f"Unexpected checkpoint for {key}: {got!r} != {expected!r}")


def consolidate_publication_results(
    exp1: Mapping[str, object],
    exp2: Mapping[str, object],
    exp3: Mapping[str, object],
    exp4: Mapping[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, ConsolidationSummary]:
    # Frozen publication checkpoints. Fail loudly if upstream results drift.
    _require(exp1, "benchmark_version", "1.0.0")
    _require(exp1, "scenario_anchor_evaluations", 245)
    _require(exp1, "evaluable_rows_with_any_infeasible_top", 142)
    _require(exp1, "no_feasible_rows_where_score_first_still_returns_top", 70)
    _require(exp2, "canonical_evidence_records", 398)
    _require(exp2, "direct_relation_rows", 0)
    _require(exp2, "bridgeable_relation_rows", 5)
    _require(exp2, "conditional_relation_rows", 1)
    _require(exp2, "missing_relation_rows", 14)
    _require(exp2, "canonical_complete_candidates", 0)
    _require(exp2, "counterfactual_bridge_complete_candidates", 10)
    _require(exp2, "assumption_complete_candidates", 21)
    _require(exp3, "cost_aligned_state_reversals", 0)
    _require(exp3, "cost_strict_coap_cheaper_rows_total", 172)
    _require(exp3, "cost_tie_rows_total", 116)
    _require(exp3, "cost_aligned_gap_min_eur", 0.0)
    _require(exp3, "cost_aligned_gap_max_eur", 70.0)
    _require(exp4, "aligned_traffic_states", 288)
    _require(exp4, "level0_false_within_vs_final", 252)
    _require(exp4, "level3_false_within_vs_final", 36)

    headlines = pd.DataFrame([
        {
            "result_id": "R1_FEASIBILITY_FIRST",
            "experiment": 1,
            "headline": "Score-first top sets are frequently contaminated by hard-infeasible stacks.",
            "primary_value": "142/175 evaluable scenario-anchor rows",
            "secondary_value": "70/70 no-feasible rows still receive a score-first top set",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R2_GRID_ROBUSTNESS",
            "experiment": 1,
            "headline": "The feasibility-first result is not an artefact of one preference-grid resolution.",
            "primary_value": "81.1% contamination at step 0.25",
            "secondary_value": "83.5% at step 0.10 among evaluable scenarios",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R3_GRADE_NOT_ADMISSIBILITY",
            "experiment": 2,
            "headline": "Grade-A provenance does not imply decision-target admissibility.",
            "primary_value": "398/398 records retained at Grade A only",
            "secondary_value": "0 direct; 5 bridgeable; 1 conditional; 14 missing source-target relations",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R4_DECISION_SPACE_INFLATION",
            "experiment": 2,
            "headline": "Relaxing admissibility creates an artificial decision space.",
            "primary_value": "0 canonical complete candidates",
            "secondary_value": "10 with structural-transfer counterfactual; 21 with assumption priors",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R5_UNCERTAINTY_SEMANTICS",
            "experiment": 3,
            "headline": "Uncertainty treatment changes precision and interpretation even when ordering is unchanged.",
            "primary_value": "Vomhoff 3/3 marginal interval-separated source comparisons",
            "secondary_value": "relative interval widths 2.30–8.16%",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R6_MODEL_FORM_UNCERTAINTY",
            "experiment": 3,
            "headline": "LoED point estimates hide material temporal model-form sensitivity.",
            "primary_value": "4/4 campaign×metric rows have SD ratio >1.25",
            "secondary_value": "max/min SD ratio range 1.39–1.70",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R7_PAIRED_COST_ROBUSTNESS",
            "experiment": 3,
            "headline": "Paired epistemic states prevent false reversals suggested by overlapping marginal ranges.",
            "primary_value": "172 CoAP-cheaper / 116 ties / 0 MQTT-cheaper aligned rows",
            "secondary_value": "paired cost gap €0–€70 vs deterministic €10",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R8_ACCOUNTING_MISCLASSIFICATION",
            "experiment": 4,
            "headline": "Payload-only accounting severely misclassifies connectivity allowance.",
            "primary_value": "252/288 false-within states",
            "secondary_value": "misclassification falls 87.5% → 37.5% → 34.7% → 12.5% → 0%",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
        {
            "result_id": "R9_COST_UNDERESTIMATION",
            "experiment": 4,
            "headline": "Simplified accounting materially understates five-year connectivity cost.",
            "primary_value": "payload-only median €50, max €100 underestimate",
            "secondary_value": "session/control-aware still median €5, max €50 before billing",
            "probability_interpretation": False,
            "publication_strength": "STRONG",
        },
    ])

    claims = pd.DataFrame([
        {
            "claim_id": "C1_BENCHMARK_RESOURCE",
            "proposed_claim": "A harmonised multi-source empirical evidence benchmark is released with provenance, boundaries, uncertainty semantics and frozen scenarios/stacks.",
            "status": "STRONG",
            "support": "Benchmark v1.0.0: 398 records, 4 real sources, 14 metrics, 7 scenarios, 9 stacks, 25/25 final QA.",
            "publication_claim_authorised": True,
            "action": "KEEP",
        },
        {
            "claim_id": "C2_LAYER_AWARE_FEASIBILITY",
            "proposed_claim": "Layer-aware end-to-end stack modelling with hard feasibility screening prevents invalid preference comparisons.",
            "status": "STRONG",
            "support": "Frozen 7×9 feasibility matrix plus Experiment 1.",
            "publication_claim_authorised": True,
            "action": "KEEP",
        },
        {
            "claim_id": "C3_EVIDENCE_ADMISSIBILITY",
            "proposed_claim": "Source quality and decision admissibility are distinct; bridgeability and boundary compatibility must be modelled explicitly.",
            "status": "STRONG",
            "support": "Experiment 2 source-target and candidate-level ablations.",
            "publication_claim_authorised": True,
            "action": "KEEP",
        },
        {
            "claim_id": "C4_UNCERTAINTY_AWARE_TREATMENT",
            "proposed_claim": "STACKWISE preserves heterogeneous uncertainty semantics and dependence rather than forcing all evidence into one pooled probability model.",
            "status": "STRONG",
            "support": "Experiment 3: bootstrap precision, LoED block-model robustness, aligned finite cost states.",
            "publication_claim_authorised": True,
            "action": "KEEP",
        },
        {
            "claim_id": "C5_ACCOUNTING_COST_SIMPLIFICATION",
            "proposed_claim": "Ignoring protocol, serialization, session and billing boundaries can materially change tariff classification and lifecycle cost.",
            "status": "STRONG",
            "support": "Experiment 4: 252/288 false-within at payload-only; up to €100/device/5y underestimate.",
            "publication_claim_authorised": True,
            "action": "KEEP",
        },
        {
            "claim_id": "C6_GLOBAL_STOCHASTIC_MCDA",
            "proposed_claim": "The framework provides a publication-grade global stochastic ranking of all candidate stacks.",
            "status": "OPEN",
            "support": "No feasible candidate is complete for the canonical energy+cost first slice; synthetic dry run only.",
            "publication_claim_authorised": False,
            "action": "DROP_OR_REFRAME",
        },
        {
            "claim_id": "C7_FLEET_LEVEL_OPTIMISATION",
            "proposed_claim": "The framework quantifies the fleet-level penalty of single-technology or restricted portfolios.",
            "status": "OPEN",
            "support": "No fleet-level result yet in Experiments 1–4.",
            "publication_claim_authorised": False,
            "action": "ADD_ONE_FINAL_FLEET_FEASIBILITY_EXPERIMENT_OR_DROP",
        },
        {
            "claim_id": "C8_MATCHED_CELLULAR_REPORT_ENERGY",
            "proposed_claim": "Absolute whole-device energy/report is compared across the four cellular IP candidate stacks.",
            "status": "OPEN_OPTIONAL",
            "support": "Matched public evidence absent; Stage 6B experimental contract exists but no hardware/testbed data.",
            "publication_claim_authorised": False,
            "action": "LIMITATION_FUTURE_VALIDATION",
        },
    ])

    figures = pd.DataFrame([
        {"order": 1, "role": "MAIN", "source": "NEW_METHOD_FIGURE", "artifact": "STACKWISE evidence→feasibility→uncertainty→decision workflow", "reason": "Needed to explain the framework before results."},
        {"order": 2, "role": "MAIN", "source": "Experiment 1", "artifact": "figure1_score_first_topset_feasibility.png", "reason": "Directly supports feasibility-first claim."},
        {"order": 3, "role": "MAIN", "source": "Experiment 2", "artifact": "figure2_candidate_decision_space_inflation.png", "reason": "Best visual for evidence-admissibility claim."},
        {"order": 4, "role": "MAIN_COMPOSITE", "source": "Experiment 3", "artifact": "combine figure1/figure2/figure3 into one 3-panel uncertainty figure", "reason": "Three uncertainty semantics are a single conceptual result; separate figures would be redundant."},
        {"order": 5, "role": "MAIN", "source": "Experiment 4", "artifact": "figure2_misclassification_vs_billing_aware.png", "reason": "Most concise cost-of-simplification result."},
        {"order": 6, "role": "MAIN", "source": "Experiment 4", "artifact": "figure3_cost_underestimation_by_accounting_level.png", "reason": "Converts accounting simplification into EUR impact."},
        {"order": 7, "role": "SUPPLEMENT", "source": "Experiment 1", "artifact": "figure2_soft_score_concession.png", "reason": "Useful detail but secondary to infeasible-top contamination."},
        {"order": 8, "role": "SUPPLEMENT", "source": "Experiment 2", "artifact": "figure1_source_target_admissibility_ladder.png", "reason": "Technical admissibility decomposition; main text can cite a table."},
        {"order": 9, "role": "SUPPLEMENT", "source": "Experiment 4", "artifact": "figure1_exceedance_by_accounting_level.png", "reason": "Partly redundant with misclassification figure."},
    ])

    tables = pd.DataFrame([
        {"order": 1, "role": "MAIN", "table": "Benchmark overview", "source": "Benchmark v1.0.0", "content": "4 sources, 398 records, 14 metrics, boundaries/uncertainty, 7 scenarios, 9 stacks."},
        {"order": 2, "role": "MAIN", "table": "Scenario and hard-feasibility summary", "source": "Frozen Stage 4 + Experiment 1", "content": "Feasible/infeasible/unresolved counts and no-feasible scenarios."},
        {"order": 3, "role": "MAIN", "table": "Publication claims and quantitative evidence", "source": "Consolidation", "content": "One row per retained claim with headline numbers from Experiments 1–4."},
        {"order": 4, "role": "SUPPLEMENT", "table": "Evidence admissibility ladder", "source": "Experiment 2", "content": "A0–A3 and D0–D3 regimes."},
        {"order": 5, "role": "SUPPLEMENT", "table": "Uncertainty case-study diagnostics", "source": "Experiment 3", "content": "Vomhoff precision, LoED SD ratios, paired cost robustness."},
        {"order": 6, "role": "SUPPLEMENT", "table": "Accounting level ablation", "source": "Experiment 4", "content": "L0–L4 exceedance, misclassification and cost underestimation."},
    ])

    counts = claims["status"].value_counts().to_dict()
    summary = ConsolidationSummary(
        experiments_closed=4,
        headline_result_rows=len(headlines),
        strong_claims=int(counts.get("STRONG", 0)),
        partial_claims=int(counts.get("PARTIAL", 0)),
        open_claims=int(sum(v for k, v in counts.items() if k.startswith("OPEN"))),
        main_figures_recommended=int(figures["role"].str.startswith("MAIN").sum()),
        main_tables_recommended=int((tables["role"] == "MAIN").sum()),
        fleet_experiment_recommended=True,
        full_global_mcda_authorised=False,
    )
    return headlines, claims, figures, tables, summary
