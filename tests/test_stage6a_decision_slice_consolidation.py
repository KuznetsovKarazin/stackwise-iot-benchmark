from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.decision_slice import (
    allowance_context_by_candidate,
    audit_summary,
    build_candidate_slice_rows,
    build_criterion_readiness_rows,
    build_scenario_summary_rows,
    hard_unresolved_exclusion_rows,
    preferred_subset_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage6a_decision_slice_consolidation.yml").read_text(encoding="utf-8"))
    feasibility = _csv(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    stage5e = _csv(ROOT / "results/validation/stage5_decision_readiness/candidate_target_readiness.csv")
    stage5g = _csv(ROOT / "results/validation/stage5g_cellular_transfer_evidence/candidate_transfer_admissibility.csv")
    costs = _csv(ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv")
    robustness = _csv(ROOT / "results/validation/stage5n_security_session_control_envelope/session_control_allowance_robustness.csv")
    criteria = build_criterion_readiness_rows(
        stage5e_rows=stage5e,
        cost_rows=costs,
        stage5n_robustness_rows=robustness,
        stage5g_energy_rows=stage5g,
    )
    candidates = build_candidate_slice_rows(criteria)
    scenarios = build_scenario_summary_rows(candidates)
    unresolved = hard_unresolved_exclusion_rows(feasibility)
    subset = preferred_subset_rows(candidates, policy)
    return policy, feasibility, stage5e, stage5g, costs, robustness, criteria, candidates, scenarios, unresolved, subset


def test_stage6a_allowance_context_collapses_stage5n_to_ten_ip_candidates():
    robustness = _csv(ROOT / "results/validation/stage5n_security_session_control_envelope/session_control_allowance_robustness.csv")
    contexts = allowance_context_by_candidate(robustness)
    assert len(contexts) == 10
    classes = [r["tariff_volume_context_class"] for r in contexts.values()]
    assert classes.count("ROBUST_WITHIN_NOMINAL_RAW_ALLOWANCE") == 4
    assert classes.count("ROBUST_EXCEED_NOMINAL_RAW_ALLOWANCE") == 3
    assert classes.count("PROTOCOL_ENVELOPE_SENSITIVE") == 3


def test_stage6a_has_105_feasible_candidate_criterion_rows_and_no_ready_required_soft_target():
    *_, criteria, candidates, scenarios, unresolved, subset = _inputs()
    assert len(criteria) == 105
    required = [r for r in criteria if r["first_slice_required"]]
    assert len(required) == 42
    assert sum(r["canonical_target_ready"] for r in required) == 0
    assert sum(r["stage6a_decision_use_status"] == "CONTEXT_ONLY" for r in required) == 10
    assert sum(r["stage6a_decision_use_status"] == "BLOCKED" for r in required) == 32
    assert len(candidates) == 21
    assert len(scenarios) == 5
    assert len(unresolved) == 3
    assert len(subset) == 4


def test_stage6a_cost_context_is_only_for_feasible_ip_cellular_rows():
    *_, criteria, candidates, _, _, _ = _inputs()
    cost = [r for r in criteria if r["target_metric_id"] == "lifecycle_cost_eur"]
    context = [r for r in cost if r["stage6a_decision_use_status"] == "CONTEXT_ONLY"]
    assert len(context) == 10
    assert all("_ip_" in r["stack_id"] for r in context)
    assert all(r["score_authorised"] is False for r in context)
    assert sum(r["cost_decision_use_status"] == "CONTEXT_ONLY" for r in candidates) == 10


def test_stage6a_energy_remains_blocked_for_all_21_feasible_candidates():
    *_, criteria, _, _, _, _ = _inputs()
    energy = [r for r in criteria if r["target_metric_id"] == "expected_device_energy_per_application_report_j"]
    assert len(energy) == 21
    assert all(r["stage6a_decision_use_status"] == "BLOCKED" for r in energy)
    cellular_structural = [r for r in energy if r["evidence_maturity"] == "STRUCTURAL_TRANSFER_SUPPORT_ONLY"]
    assert len(cellular_structural) == 10


def test_stage6a_preferred_development_subset_is_periodic_tracking_ip_2x2_and_not_ready():
    *_, subset = _inputs()
    assert {r["scenario_id"] for r in subset} == {"asset_tracking_periodic_cross_cell"}
    assert {r["stack_id"] for r in subset} == {
        "nbiot_ip_coap_dtls_lwm2m",
        "ltem_ip_coap_dtls_lwm2m",
        "nbiot_ip_mqtt_tls_lwm2m",
        "ltem_ip_mqtt_tls_lwm2m",
    }
    assert all(r["first_slice_candidate_ready"] is False for r in subset)
    assert {r["tariff_volume_context_class"] for r in subset} == {
        "ROBUST_EXCEED_NOMINAL_RAW_ALLOWANCE",
        "PROTOCOL_ENVELOPE_SENSITIVE",
    }


def test_stage6a_summary_matches_frozen_counts_and_keeps_mcda_blocked():
    policy, feasibility, _, _, _, _, criteria, candidates, scenarios, unresolved, subset = _inputs()
    summary = audit_summary(
        feasibility_rows=feasibility,
        criterion_rows=criteria,
        candidate_rows=candidates,
        scenario_rows=scenarios,
        unresolved_rows=unresolved,
        subset_rows=subset,
        policy=policy,
    )
    assert summary.stage4_feasible_rows == 21
    assert summary.stage4_infeasible_rows == 39
    assert summary.stage4_unresolved_rows == 3
    assert summary.feasible_candidates_ready_for_first_slice == 0
    assert summary.preferred_development_subset_rows == 4
    assert summary.preferred_development_subset_ready_rows == 0
