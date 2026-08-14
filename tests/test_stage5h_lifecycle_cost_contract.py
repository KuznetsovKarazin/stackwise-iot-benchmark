from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.lifecycle_cost import audit_summary, build_candidate_cost_readiness, required_components_for_mode


ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage5h_lifecycle_cost_contract.yml").read_text(encoding="utf-8"))


def test_stage5h_freezes_cost_boundary_without_inventing_prices():
    policy = _policy()
    feasibility = _rows(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    rows = build_candidate_cost_readiness(feasibility, policy)
    summary = audit_summary(rows, policy)
    assert summary.feasible_candidate_rows == 21
    assert summary.canonical_target_ready_rows == 0
    assert summary.rows_with_complete_required_price_evidence == 0
    assert policy["scientific_policy"]["use_configs_fleet_as_publication_evidence"] is False


def test_stage5h_keeps_private_infrastructure_shared_until_scale_is_frozen():
    policy = _policy()
    feasibility = _rows(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    rows = build_candidate_cost_readiness(feasibility, policy)
    private = [r for r in rows if r["cost_mode"] == "private_owned_access"]
    assert len(private) == 2
    assert all(r["shared_cost_scale_required"] is True for r in private)
    assert all(r["shared_cost_scale_ready"] is False for r in private)
    assert all("shared_infrastructure_allocation_scale_missing" in r["blocking_reasons"] for r in private)


def test_stage5h_operator_and_private_modes_require_different_components():
    policy = _policy()
    operator = required_components_for_mode(policy, "operator_managed_access")
    private = required_components_for_mode(policy, "private_owned_access")
    assert "operator_connectivity_eur_per_device_year" in operator
    assert "private_access_infrastructure_capex_eur_per_site" not in operator
    assert "private_access_infrastructure_capex_eur_per_site" in private
    assert "operator_connectivity_eur_per_device_year" not in private
    assert "device_incremental_capex_eur_per_device" in operator
    assert "device_incremental_capex_eur_per_device" in private


def test_stage5h_urban_lorawan_ownership_is_not_inferred():
    policy = _policy()
    feasibility = _rows(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    rows = build_candidate_cost_readiness(feasibility, policy)
    target = [r for r in rows if r["scenario_id"] == "urban_nonip_dual_access" and r["access_family"] == "lorawan"]
    assert len(target) == 2
    assert all(r["cost_mode"] == "unresolved_ownership_mode" for r in target)
    assert all(r["ownership_boundary_ready"] is False for r in target)
