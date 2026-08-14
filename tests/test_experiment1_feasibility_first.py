from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from stackwise.feasibility_first import (
    FEATURE_IDS,
    build_preference_feature_matrix,
    deterministic_simplex_weight_grid,
    run_feasibility_first_experiment,
)

ROOT = Path(__file__).resolve().parents[1]


def _source_tables():
    candidates = pd.read_csv(ROOT / "results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv")
    components = pd.read_csv(ROOT / "results/validation/stage4_component_catalog/component_catalog.csv")
    feasibility = pd.read_csv(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    return candidates, components, feasibility


def test_experiment1_preference_feature_matrix_is_complete_and_bounded():
    candidates, components, _ = _source_tables()
    features = build_preference_feature_matrix(candidates, components)
    assert len(features) == 9
    assert features["stack_id"].is_unique
    assert np.isfinite(features[list(FEATURE_IDS)].to_numpy(dtype=float)).all()
    assert ((features[list(FEATURE_IDS)] >= 0) & (features[list(FEATURE_IDS)] <= 1)).all().all()
    assert features["probability_interpretation"].eq(False).all()


def test_experiment1_structural_features_have_expected_semantics():
    candidates, components, _ = _source_tables()
    f = build_preference_feature_matrix(candidates, components).set_index("stack_id")
    assert f.loc["nbiot_nonip_lwm2m", "stack_parsimony"] == 1.0
    assert f.loc["thread_coap_dtls_lwm2m", "stack_parsimony"] == 0.0
    assert f.loc["nbiot_ip_coap_dtls_lwm2m", "explicit_transport_security"] == 1.0
    assert f.loc["lorawan_lora_lwm2m_nonip", "explicit_transport_security"] == 0.0
    assert f.loc["lorawan_lora_lwm2m_nonip", "operator_independence"] == 1.0
    assert f.loc["nbiot_ip_coap_dtls_lwm2m", "operator_independence"] == 0.0
    assert f.loc["thread_coap_dtls_lwm2m", "ip_interoperability"] == 1.0
    assert f.loc["ltem_nonip_lwm2m", "ip_interoperability"] == 0.0


def test_experiment1_simplex_grid_has_35_unweighted_anchors():
    grid = deterministic_simplex_weight_grid(step=0.25)
    assert len(grid) == 35
    assert grid["weight_anchor_id"].is_unique
    assert np.allclose(grid[list(FEATURE_IDS)].sum(axis=1), 1.0)
    assert grid["probability_interpretation"].eq(False).all()


def test_experiment1_frozen_benchmark_counts_and_ordering_effect():
    candidates, components, feasibility = _source_tables()
    features = build_preference_feature_matrix(candidates, components)
    weights = deterministic_simplex_weight_grid(step=0.25)
    outcomes, scenario_summary, summary = run_feasibility_first_experiment(
        feature_matrix=features,
        weight_grid=weights,
        hard_feasibility=feasibility,
    )
    assert summary.scenarios == 7
    assert summary.candidates == 9
    assert summary.preference_anchors == 35
    assert summary.scenario_anchor_evaluations == 245
    assert summary.scenarios_with_feasible_candidates == 5
    assert summary.scenarios_without_feasible_candidates == 2
    assert summary.evaluable_scenario_anchor_rows == 175
    assert summary.score_first_any_infeasible_top_rows == 193
    assert summary.score_first_only_infeasible_top_rows == 159
    assert summary.evaluable_rows_with_any_infeasible_top == 142
    assert summary.evaluable_rows_with_only_infeasible_top == 115
    assert summary.no_feasible_rows_where_score_first_still_returns_top == 70
    assert summary.feasibility_first_forced_decisions_without_feasible_candidate == 0
    assert len(outcomes) == 245
    assert len(scenario_summary) == 7


def test_experiment1_no_feasible_scenarios_are_not_forced_into_a_decision():
    candidates, components, feasibility = _source_tables()
    features = build_preference_feature_matrix(candidates, components)
    weights = deterministic_simplex_weight_grid(step=0.25)
    outcomes, _, _ = run_feasibility_first_experiment(
        feature_matrix=features,
        weight_grid=weights,
        hard_feasibility=feasibility,
    )
    no_feasible = outcomes[outcomes["feasible_candidate_count"] == 0]
    assert len(no_feasible) == 70
    assert no_feasible["score_first_top_set"].str.len().gt(0).all()
    assert no_feasible["feasibility_first_decision_status"].eq("NO_FEASIBLE_DECISION").all()
    assert no_feasible["feasibility_first_top_set"].eq("").all()


def test_experiment1_does_not_use_energy_cost_or_reliability_as_soft_inputs():
    assert set(FEATURE_IDS) == {
        "stack_parsimony",
        "explicit_transport_security",
        "operator_independence",
        "ip_interoperability",
    }


def test_experiment1_ordering_effect_is_not_a_single_grid_resolution_artifact():
    candidates, components, feasibility = _source_tables()
    features = build_preference_feature_matrix(candidates, components)
    fractions = []
    evaluable_fractions = []
    for step in (0.5, 0.25, 0.2, 0.1):
        weights = deterministic_simplex_weight_grid(step=step)
        outcomes, _, _ = run_feasibility_first_experiment(
            feature_matrix=features, weight_grid=weights, hard_feasibility=feasibility
        )
        fractions.append(float(outcomes["score_first_top_contains_infeasible"].mean()))
        evaluable = outcomes[outcomes["feasible_candidate_count"] > 0]
        evaluable_fractions.append(float(evaluable["score_first_top_contains_infeasible"].mean()))
    assert min(fractions) > 0.78
    assert min(evaluable_fractions) > 0.81
    assert max(fractions) < 0.84
    assert max(evaluable_fractions) < 0.84
