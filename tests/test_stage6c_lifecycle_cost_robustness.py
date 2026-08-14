from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.cost_robustness import (
    audit_summary,
    build_candidate_cost_summary_rows,
    build_cost_family_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage6c_lifecycle_cost_robustness.yml").read_text(encoding="utf-8"))


def _csv(path: str):
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _family():
    policy = _policy()
    stage5n = _csv("results/validation/stage5n_security_session_control_envelope/session_control_envelope.csv")
    subset = _csv("results/validation/stage6a_decision_slice_consolidation/preferred_development_subset.csv")
    return policy, build_cost_family_rows(stage5n, subset, policy)


def test_stage6c_builds_finite_unweighted_family_for_four_candidate_subset():
    policy, family = _family()
    assert len(family) == 576
    assert {r["scenario_id"] for r in family} == {"asset_tracking_periodic_cross_cell"}
    assert len({r["stack_id"] for r in family}) == 4
    assert {r["billing_anchor_id"] for r in family} == {"B0_persistent_pdp", "B1_pdp_per_report"}
    assert {r["procurement_anchor_id"] for r in family} == {"P0_volume_250", "P1_retail_qty1"}
    assert all(r["probability_interpretation"] is False for r in family)
    assert all(r["decision_use_status"] == "READY_ROBUSTNESS_FAMILY" for r in family)


def test_stage6c_pdp_per_report_rounding_never_reduces_billed_volume():
    _, family = _family()
    grouped = {}
    for r in family:
        key = (r["session_control_row_id"] if "session_control_row_id" in r else r["cost_family_row_id"].split("__B", 1)[0], r["procurement_anchor_id"])
        grouped.setdefault(key, {})[r["billing_anchor_id"]] = r
    for pair in grouped.values():
        assert pair["B1_pdp_per_report"]["billed_transport_bytes_5y"] >= pair["B0_persistent_pdp"]["billed_transport_bytes_5y"]


def test_stage6c_candidate_summaries_are_cost_ready_but_energy_blocked():
    policy, family = _family()
    candidates = build_candidate_cost_summary_rows(family)
    assert len(candidates) == 4
    assert all(r["cost_decision_use_status"] == "READY_ROBUSTNESS_FAMILY" for r in candidates)
    assert all(r["energy_decision_use_status"] == "BLOCKED" for r in candidates)
    assert all(r["first_slice_candidate_ready"] is False for r in candidates)
    assert all(r["lifecycle_cost_max_eur"] > r["lifecycle_cost_min_eur"] for r in candidates)
    summary = audit_summary(family, candidates, policy)
    assert summary.cost_ready_candidates == 4
    assert summary.energy_ready_candidates == 0
    assert summary.first_slice_ready_candidates == 0


def test_stage6c_shared_dual_mode_hardware_makes_rat_cost_family_identical_within_binding():
    policy, family = _family()
    candidates = build_candidate_cost_summary_rows(family)
    summary = audit_summary(family, candidates, policy)
    assert summary.candidates_with_identical_nb_iot_lte_m_cost_family_within_binding == 4


def test_stage6c_platform2_rounding_is_explicitly_pdp_session_based():
    policy = _policy()
    anchors = {x["billing_anchor_id"]: x for x in policy["billing_session_anchors"]}
    assert anchors["B0_persistent_pdp"]["session_count_rule"] == "one_session_for_horizon"
    assert anchors["B1_pdp_per_report"]["session_count_rule"] == "one_session_per_report"
    assert anchors["B0_persistent_pdp"]["rounding_unit_bytes"] == 1000
    assert policy["scientific_policy"]["probability_interpretation"] is False
