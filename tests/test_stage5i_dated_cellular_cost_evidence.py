from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.dated_cost_evidence import audit_summary, build_dated_cost_readiness
from stackwise.lifecycle_cost import build_candidate_cost_readiness

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    stage5h = yaml.safe_load((ROOT / "datasets/stage5h_lifecycle_cost_contract.yml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((ROOT / "datasets/stage5i_dated_cellular_cost_evidence.yml").read_text(encoding="utf-8"))
    feasibility = _csv(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    stage5h_rows = build_candidate_cost_readiness(feasibility, stage5h)
    return stage5h, policy, build_dated_cost_readiness(stage5h_rows, policy)


def test_stage5i_materialises_dated_ip_cellular_price_evidence_without_claiming_canonical_cost():
    _, policy, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.feasible_candidate_rows == 21
    assert summary.ip_cellular_feasible_rows == 10
    assert summary.rows_with_dated_module_and_sim_price == 10
    assert summary.rows_with_ip_connectivity_tariff_evidence == 10
    assert summary.rows_with_canonical_lifecycle_cost_ready == 0


def test_stage5i_does_not_leak_ip_tariff_to_nonip_candidates():
    _, _, rows = _inputs()
    nonip = [r for r in rows if r["cost_mode"] == "operator_managed_access" and r["access_family"] == "cellular" and not r["dated_ip_connectivity_tariff_evidence"]]
    assert len(nonip) == 7
    assert all(r["tariff_volume_fit_status"] == "nonip_operator_service_not_evidenced" for r in nonip)
    assert all("operator_nonip_service_price_not_evidenced" in r["blocking_reasons"] for r in nonip)


def test_stage5i_uses_same_dual_mode_reference_hardware_for_nbiot_and_ltem_ip():
    _, _, rows = _inputs()
    ip = [r for r in rows if r["dated_ip_connectivity_tariff_evidence"]]
    assert {r["reference_module_eur_qty1_ex_vat"] for r in ip} == {33.41}
    assert any(r["stack_id"].startswith("nbiot_") for r in ip)
    assert any(r["stack_id"].startswith("ltem_") for r in ip)


def test_stage5i_does_not_prorate_ten_year_prepaid_tariff_to_five_year_horizon():
    _, _, rows = _inputs()
    ip = [r for r in rows if r["dated_ip_connectivity_tariff_evidence"]]
    # 33.41 module + 1.00 SIM + full 12.00 prepaid connectivity; no 12/10*5 proration.
    assert {r["reference_cost_floor_eur"] for r in ip} == {46.41}


def test_stage5i_does_not_invent_per_report_1kb_rounding():
    _, _, rows = _inputs()
    tracking = [r for r in rows if r["scenario_id"] in {"asset_tracking_periodic_cross_cell", "asset_tracking_connected_handover"} and r["dated_ip_connectivity_tariff_evidence"]]
    assert len(tracking) == 6
    assert {r["five_year_report_count"] for r in tracking} == {2629800}
    assert {round(float(r["application_payload_volume_mb_5y"]), 6) for r in tracking} == {168.3072}
    assert all(r["tariff_volume_fit_status"] == "base_allowance_not_disproven_exact_transport_usage_unresolved" for r in tracking)
    assert all(r["cost_floor_is_canonical_target"] is False for r in tracking)


def test_stage5i_application_payload_alone_does_not_establish_tariff_sufficiency():
    _, _, rows = _inputs()
    smart = [r for r in rows if r["scenario_id"] == "smart_meter_public_cellular" and r["dated_ip_connectivity_tariff_evidence"]]
    assert {r["five_year_report_count"] for r in smart} == {175320}
    assert {round(float(r["application_payload_volume_mb_5y"]), 6) for r in smart} == {35.064}
    assert all(r["tariff_volume_fit_status"] == "base_allowance_not_disproven_exact_transport_usage_unresolved" for r in smart)
    assert all("tariff_volume_fit_not_identified" in r["blocking_reasons"] for r in smart)


def test_stage5i_has_no_row_where_base_allowance_is_proven_insufficient_without_session_profile():
    _, policy, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.smart_meter_ip_rows_with_base_allowance_not_disproven == 4
    assert summary.tracking_ip_rows_with_base_allowance_not_disproven == 6
    assert summary.rows_where_base_allowance_definitely_insufficient == 0


def test_stage5i_keeps_stage5h_frozen_with_zero_price_evidence():
    stage5h, _, _ = _inputs()
    assert stage5h["price_evidence"] == []
    assert stage5h["expected"]["canonical_target_ready_rows"] == 0
