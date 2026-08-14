from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class FinalPublicationSummary:
    experiments_closed: int
    headline_result_rows: int
    strong_claims: int
    open_claims: int
    methodology_main_figures: int
    methodology_main_tables: int
    data_paper_core_sections: int
    two_paper_split_recommended: bool
    broad_methodology_article_ready: bool
    global_mcda_authorised: bool


def _require(summary: Mapping[str, object], key: str, expected: object) -> None:
    got = summary.get(key)
    if got != expected:
        raise ValueError(f"Unexpected checkpoint for {key}: {got!r} != {expected!r}")


def finalise_publication_results(
    exp1: Mapping[str, object],
    exp2: Mapping[str, object],
    exp3: Mapping[str, object],
    exp4: Mapping[str, object],
    exp5: Mapping[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, FinalPublicationSummary]:
    # Freeze the final publication checkpoints. Fail loudly if upstream results drift.
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

    _require(exp5, "benchmark_version", "1.0.0")
    _require(exp5, "total_scenarios", 7)
    _require(exp5, "strict_serviceable_scenarios", 5)
    _require(exp5, "unresolved_only_scenarios", 2)
    _require(exp5, "strict_best_single_stack_coverage", 4)
    _require(exp5, "strict_best_single_technology_coverage", 4)
    _require(exp5, "strict_best_single_family_coverage", 4)
    _require(exp5, "strict_min_stacks_for_complete_coverage", 2)
    _require(exp5, "strict_min_technologies_for_complete_coverage", 2)
    _require(exp5, "strict_min_families_for_complete_coverage", 2)
    _require(exp5, "optimistic_min_technologies_for_complete_coverage", 3)
    _require(exp5, "strict_minimum_complete_family_portfolios", 1)
    _require(exp5, "global_candidate_ranking_performed", False)

    headlines = pd.DataFrame([
        {"result_id":"R1_FEASIBILITY_FIRST","experiment":1,"headline":"Score-first top sets are frequently contaminated by hard-infeasible stacks.","primary_value":"142/175 evaluable scenario-anchor rows","secondary_value":"70/70 no-feasible rows still receive a score-first top set","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R2_GRID_ROBUSTNESS","experiment":1,"headline":"The feasibility-first result is not an artefact of one preference-grid resolution.","primary_value":"81.1% contamination at step 0.25","secondary_value":"83.5% at step 0.10 among evaluable scenarios","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R3_GRADE_NOT_ADMISSIBILITY","experiment":2,"headline":"Grade-A provenance does not imply decision-target admissibility.","primary_value":"398/398 records retained at Grade A only","secondary_value":"0 direct; 5 bridgeable; 1 conditional; 14 missing source-target relations","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R4_DECISION_SPACE_INFLATION","experiment":2,"headline":"Relaxing admissibility creates an artificial decision space.","primary_value":"0 canonical complete candidates","secondary_value":"10 with structural-transfer counterfactual; 21 with assumption priors","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R5_UNCERTAINTY_SEMANTICS","experiment":3,"headline":"Uncertainty treatment changes precision and interpretation even when ordering is unchanged.","primary_value":"Vomhoff 3/3 marginal interval-separated source comparisons","secondary_value":"relative interval widths 2.30–8.16%","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R6_MODEL_FORM_UNCERTAINTY","experiment":3,"headline":"LoED point estimates hide material temporal model-form sensitivity.","primary_value":"4/4 campaign×metric rows have SD ratio >1.25","secondary_value":"max/min SD ratio range 1.39–1.70","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R7_PAIRED_COST_ROBUSTNESS","experiment":3,"headline":"Paired epistemic states prevent false reversals suggested by overlapping marginal ranges.","primary_value":"172 CoAP-cheaper / 116 ties / 0 MQTT-cheaper aligned rows","secondary_value":"paired cost gap €0–€70 vs deterministic €10","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R8_ACCOUNTING_MISCLASSIFICATION","experiment":4,"headline":"Payload-only accounting severely misclassifies connectivity allowance.","primary_value":"252/288 false-within states","secondary_value":"misclassification falls 87.5% → 37.5% → 34.7% → 12.5% → 0%","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R9_COST_UNDERESTIMATION","experiment":4,"headline":"Simplified accounting materially understates five-year connectivity cost.","primary_value":"payload-only median €50, max €100 underestimate","secondary_value":"session/control-aware still median €5, max €50 before billing","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R10_FLEET_SINGLE_OPTION_LOSS","experiment":5,"headline":"A single stack, access technology or access family cannot cover all strictly serviceable scenario classes.","primary_value":"best single option covers 4/5 strict-serviceable scenarios","secondary_value":"20% structural serviceability loss","probability_interpretation":False,"publication_strength":"STRONG"},
        {"result_id":"R11_MINIMUM_HETEROGENEOUS_PORTFOLIO","experiment":5,"headline":"Complete strict fleet serviceability requires a heterogeneous two-element portfolio.","primary_value":"minimum 2 stacks / 2 technologies / 2 families","secondary_value":"unique family-level solution: cellular + LoRaWAN; optimistic 7/7 sensitivity requires 3 elements and Thread","probability_interpretation":False,"publication_strength":"STRONG"},
    ])

    claims = pd.DataFrame([
        {"claim_id":"C1_BENCHMARK_RESOURCE","proposed_claim":"A harmonised multi-source empirical evidence benchmark is released with provenance, boundaries, uncertainty semantics and frozen scenarios/stacks.","status":"STRONG","support":"Benchmark v1.0.0: 398 records, 4 real sources, 14 metrics, 7 scenarios, 9 stacks, 25/25 final QA.","publication_claim_authorised":True,"primary_paper":"DATA_PAPER","action":"KEEP"},
        {"claim_id":"C2_LAYER_AWARE_FEASIBILITY","proposed_claim":"Layer-aware end-to-end stack modelling with hard feasibility screening prevents invalid preference comparisons.","status":"STRONG","support":"Frozen 7×9 feasibility matrix plus Experiment 1.","publication_claim_authorised":True,"primary_paper":"METHOD_PAPER","action":"KEEP"},
        {"claim_id":"C3_EVIDENCE_ADMISSIBILITY","proposed_claim":"Source quality and decision admissibility are distinct; bridgeability and boundary compatibility must be modelled explicitly.","status":"STRONG","support":"Experiment 2 source-target and candidate-level ablations.","publication_claim_authorised":True,"primary_paper":"METHOD_PAPER","action":"KEEP"},
        {"claim_id":"C4_UNCERTAINTY_AWARE_TREATMENT","proposed_claim":"STACKWISE preserves heterogeneous uncertainty semantics and dependence rather than forcing all evidence into one pooled probability model.","status":"STRONG","support":"Experiment 3: bootstrap precision, LoED block-model robustness, aligned finite cost states.","publication_claim_authorised":True,"primary_paper":"METHOD_PAPER","action":"KEEP"},
        {"claim_id":"C5_ACCOUNTING_COST_SIMPLIFICATION","proposed_claim":"Ignoring protocol, serialization, session and billing boundaries can materially change tariff classification and lifecycle cost.","status":"STRONG","support":"Experiment 4: 252/288 false-within at payload-only; up to €100/device/5y underestimate.","publication_claim_authorised":True,"primary_paper":"METHOD_PAPER","action":"KEEP"},
        {"claim_id":"C6_FLEET_PORTFOLIO_SIMPLIFICATION","proposed_claim":"Hard-feasibility structure quantifies the fleet-level serviceability penalty of single-option portfolios and the minimum heterogeneous portfolio required for complete strict coverage.","status":"STRONG","support":"Experiment 5: 4/5 best single coverage; minimum two-element strict portfolio; unique family-level cellular+LoRaWAN solution.","publication_claim_authorised":True,"primary_paper":"METHOD_PAPER","action":"KEEP"},
        {"claim_id":"C7_GLOBAL_STOCHASTIC_MCDA","proposed_claim":"The framework provides a publication-grade global stochastic ranking of all candidate stacks.","status":"OPEN","support":"Canonical energy+cost completeness remains absent; Stage 6D is a synthetic decision-engine dry run only.","publication_claim_authorised":False,"primary_paper":"NEITHER","action":"DROP_OR_REFRAME_AS_FUTURE_EXTENSION"},
        {"claim_id":"C8_MATCHED_CELLULAR_REPORT_ENERGY","proposed_claim":"Absolute whole-device energy/report is compared across the four cellular IP candidate stacks.","status":"OPEN_OPTIONAL","support":"Matched public evidence absent; Stage 6B experimental contract exists but no hardware/testbed data.","publication_claim_authorised":False,"primary_paper":"NEITHER","action":"LIMITATION_FUTURE_VALIDATION"},
    ])

    split = pd.DataFrame([
        {"content_block":"Motivation and need for harmonised empirical IoT evidence","data_paper":"PRIMARY","method_paper":"SHORT_CROSS_REFERENCE","duplication_rule":"Different research question; avoid duplicated literature narrative."},
        {"content_block":"Four upstream datasets, licences, citations and acquisition provenance","data_paper":"PRIMARY","method_paper":"CITE_DATASET_ONLY","duplication_rule":"Full source-level detail only in data paper."},
        {"content_block":"Harmonisation pipeline, schemas, statistical units, measurement boundaries and lineage","data_paper":"PRIMARY","method_paper":"ONE_PARAGRAPH_SUMMARY","duplication_rule":"Method paper cites benchmark DOI and gives only decision-relevant abstraction."},
        {"content_block":"Uncertainty/dependence metadata and validation contracts","data_paper":"PRIMARY_TECHNICAL_VALIDATION","method_paper":"USE_IN_EXPERIMENT_3","duplication_rule":"Data paper validates representation; method paper tests methodological consequences."},
        {"content_block":"Seven benchmark scenarios, nine stacks and frozen hard-feasibility matrix","data_paper":"BENCHMARK_DEFINITION","method_paper":"ANALYSIS_INPUT","duplication_rule":"Definitions may be summarised in both; analysis/result interpretation only in method paper."},
        {"content_block":"Final release QA, checksums, dataset card, schemas, CC BY 4.0","data_paper":"PRIMARY","method_paper":"CITE_DATASET_ONLY","duplication_rule":"No duplicated release-engineering section."},
        {"content_block":"Experiment 1 feasibility-first","data_paper":"EXCLUDE","method_paper":"PRIMARY","duplication_rule":"Research result belongs only to method paper."},
        {"content_block":"Experiment 2 evidence admissibility","data_paper":"EXCLUDE","method_paper":"PRIMARY","duplication_rule":"Research result belongs only to method paper."},
        {"content_block":"Experiment 3 uncertainty treatment","data_paper":"EXCLUDE","method_paper":"PRIMARY","duplication_rule":"Research result belongs only to method paper."},
        {"content_block":"Experiment 4 accounting/cost simplification","data_paper":"EXCLUDE","method_paper":"PRIMARY","duplication_rule":"Research result belongs only to method paper."},
        {"content_block":"Experiment 5 fleet portfolio feasibility","data_paper":"EXCLUDE","method_paper":"PRIMARY","duplication_rule":"Research result belongs only to method paper."},
        {"content_block":"Global MCDA and matched cellular energy","data_paper":"EXCLUDE","method_paper":"LIMITATIONS_FUTURE_WORK","duplication_rule":"Do not imply completed evidence or ranking."},
    ])

    figures = pd.DataFrame([
        {"order":1,"paper":"METHOD_PAPER","role":"MAIN","source":"NEW_METHOD_FIGURE","artifact":"STACKWISE evidence→admissibility→feasibility→uncertainty→decision/fleet workflow","reason":"Single conceptual framework figure."},
        {"order":2,"paper":"METHOD_PAPER","role":"MAIN","source":"Experiment 1","artifact":"figure1_score_first_topset_feasibility.png","reason":"Direct feasibility-first evidence."},
        {"order":3,"paper":"METHOD_PAPER","role":"MAIN","source":"Experiment 2","artifact":"figure2_candidate_decision_space_inflation.png","reason":"Best visual for admissibility inflation."},
        {"order":4,"paper":"METHOD_PAPER","role":"MAIN_COMPOSITE","source":"Experiment 3","artifact":"combine the three Experiment-3 panels","reason":"One figure for three uncertainty semantics."},
        {"order":5,"paper":"METHOD_PAPER","role":"MAIN_COMPOSITE","source":"Experiment 4","artifact":"combine misclassification and cost-underestimation panels","reason":"One compact cost-of-simplification figure."},
        {"order":6,"paper":"METHOD_PAPER","role":"MAIN","source":"Experiment 5","artifact":"figure1_portfolio_serviceability_frontier.png","reason":"Closes heterogeneous-fleet claim."},
        {"order":7,"paper":"METHOD_PAPER","role":"SUPPLEMENT","source":"Experiment 5","artifact":"figure2_scenario_serviceability_status.png","reason":"Useful scenario detail but not required in main text."},
        {"order":8,"paper":"DATA_PAPER","role":"MAIN","source":"NEW_DATA_FIGURE","artifact":"source→harmonisation→canonical benchmark data-flow diagram","reason":"Data paper needs a dataset-construction figure distinct from method framework."},
        {"order":9,"paper":"DATA_PAPER","role":"MAIN","source":"NEW_DATA_FIGURE","artifact":"benchmark layer/schema and provenance diagram","reason":"Show release structure and traceability."},
    ])

    tables = pd.DataFrame([
        {"order":1,"paper":"METHOD_PAPER","role":"MAIN","table":"Scenario and hard-feasibility summary","source":"Benchmark v1.0.0","content":"7 scenarios, 9 stacks, 21 feasible / 39 infeasible / 3 unresolved."},
        {"order":2,"paper":"METHOD_PAPER","role":"MAIN","table":"Five-experiment quantitative evidence summary","source":"Final consolidation","content":"Experiments 1–5 and retained claims."},
        {"order":3,"paper":"METHOD_PAPER","role":"MAIN","table":"Scope/limitations guardrail","source":"Final consolidation","content":"Authorised claims versus blocked global MCDA/matched-energy claims."},
        {"order":4,"paper":"DATA_PAPER","role":"MAIN","table":"Upstream dataset inventory and provenance","source":"Benchmark v1.0.0","content":"Four sources, licence, statistical unit, measurement boundary, primary metrics."},
        {"order":5,"paper":"DATA_PAPER","role":"MAIN","table":"Canonical benchmark layers and artifacts","source":"Benchmark v1.0.0","content":"L0–L5, schemas, row counts, empirical/derived/synthetic separation."},
        {"order":6,"paper":"DATA_PAPER","role":"MAIN","table":"Technical validation and QA summary","source":"Benchmark v1.0.0","content":"398 records, format equivalence, 7×9 product, checksums, licences, 25/25 QA."},
    ])

    counts = claims["status"].value_counts().to_dict()
    summary = FinalPublicationSummary(
        experiments_closed=5,
        headline_result_rows=len(headlines),
        strong_claims=int(counts.get("STRONG", 0)),
        open_claims=int(sum(v for k, v in counts.items() if k.startswith("OPEN"))),
        methodology_main_figures=int(((figures.paper == "METHOD_PAPER") & figures.role.str.startswith("MAIN")).sum()),
        methodology_main_tables=int(((tables.paper == "METHOD_PAPER") & (tables.role == "MAIN")).sum()),
        data_paper_core_sections=6,
        two_paper_split_recommended=True,
        broad_methodology_article_ready=True,
        global_mcda_authorised=False,
    )
    return headlines, claims, split, figures, tables, summary
