from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.decision_readiness import (
    READY_STATUSES,
    audit_summary,
    build_candidate_target_readiness,
    build_gap_priority_rows,
    expand_evidence_rules,
    scenario_readiness_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: str):
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage5e_decision_readiness_policy.yml").read_text(encoding="utf-8"))


def _build():
    policy = _policy()
    rows = build_candidate_target_readiness(
        feasibility_rows=_csv("results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv"),
        candidate_rows=_csv("results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv"),
        profile_rows=_csv("results/validation/stage5_operating_profiles/operating_profiles.csv"),
        bridge_rows=_csv("results/validation/stage5_operating_profiles/bridge_contracts.csv"),
        policy=policy,
    )
    return policy, rows


def test_policy_covers_complete_stack_target_grid():
    policy = _policy()
    candidates = _csv("results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv")
    stack_ids = {r["stack_id"] for r in candidates}
    rules = expand_evidence_rules(policy, stack_ids)
    assert len(rules) == 9 * 5


def test_stage5e_preserves_non_infeasible_scope_and_has_no_ready_targets():
    policy, rows = _build()
    assert len(rows) == 120
    assert {(r["scenario_id"], r["stack_id"]) for r in rows}.__len__() == 24
    assert not any(r["readiness_status"] in READY_STATUSES for r in rows)
    assert sum(r["feasibility_status"] == "feasible" for r in { (x['scenario_id'], x['stack_id']): x for x in rows }.values()) == 21


def test_bridgeable_does_not_mean_ready_and_loed_is_not_pdr():
    _, rows = _build()
    vomhoff_energy = [r for r in rows if r["rule_id"] == "cellular_ip_report_energy"]
    assert vomhoff_energy
    assert all(r["evidence_relation"] == "BRIDGEABLE" for r in vomhoff_energy)
    assert all(r["readiness_status"] not in READY_STATUSES for r in vomhoff_energy)

    loed_delivery = [r for r in rows if r["rule_id"] == "classical_lora_delivery"]
    assert loed_delivery
    assert all(r["readiness_status"] == "ROBUSTNESS_ONLY" for r in loed_delivery)
    assert all("crc" in r["blocking_reasons"] for r in loed_delivery)


def test_first_slice_has_no_ready_candidates_and_cellular_energy_is_high_leverage():
    policy, rows = _build()
    scenarios = scenario_readiness_rows(rows)
    summary = audit_summary(rows, scenarios, policy)
    assert summary.feasible_first_slice_fully_ready_rows == 0
    assert summary.feasible_cellular_ip_rows == 10
    assert summary.cellular_ip_energy_unlock_scenarios == 3

    by_id = {r["scenario_id"]: r for r in scenarios}
    assert by_id["smart_meter_public_cellular"]["energy_bridgeable_candidate_count"] == 4
    assert by_id["asset_tracking_periodic_cross_cell"]["energy_bridgeable_candidate_count"] == 4
    assert by_id["asset_tracking_connected_handover"]["energy_bridgeable_candidate_count"] == 2


def test_gap_priority_prefers_cellular_ip_existing_evidence_bridge():
    policy, rows = _build()
    gaps = build_gap_priority_rows(rows, policy)
    assert gaps[0]["gap_id"] == "cellular_ip_report_energy_bridge"
    assert gaps[0]["preferred_next_existing_evidence_bridge"] is True
    assert gaps[0]["affected_feasible_candidate_rows"] == 10
    assert gaps[0]["affected_feasible_scenarios"] == 3
