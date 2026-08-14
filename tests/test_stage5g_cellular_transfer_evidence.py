from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.cellular_transfer_evidence import audit_summary, build_transfer_admissibility_rows, source_review_rows


ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_stage5g_contract_keeps_canonical_target_blocked():
    policy = yaml.safe_load((ROOT / "datasets/stage5g_cellular_transfer_evidence.yml").read_text(encoding="utf-8"))
    stage5f = _rows(ROOT / "results/validation/stage5_cellular_ip_energy_bridge/candidate_bridge_audit.csv")
    rows = build_transfer_admissibility_rows(stage5f, policy)
    summary = audit_summary(rows, policy)
    assert summary.feasible_candidate_incidences == 10
    assert summary.canonical_target_ready_rows == 0
    assert summary.absolute_external_calibration_authorised_rows == 0


def test_stage5g_external_model_is_structural_not_absolute():
    policy = yaml.safe_load((ROOT / "datasets/stage5g_cellular_transfer_evidence.yml").read_text(encoding="utf-8"))
    sources = source_review_rows(policy)
    assert len(sources) == 1
    assert sources[0]["measurement_boundary"] == "modem_only"
    assert sources[0]["payload_dependence"] == "supported_structurally"
    assert sources[0]["direct_absolute_transfer_to_vomhoff"] is False


def test_stage5g_all_rows_have_payload_and_cycle_structural_support():
    policy = yaml.safe_load((ROOT / "datasets/stage5g_cellular_transfer_evidence.yml").read_text(encoding="utf-8"))
    stage5f = _rows(ROOT / "results/validation/stage5_cellular_ip_energy_bridge/candidate_bridge_audit.csv")
    rows = build_transfer_admissibility_rows(stage5f, policy)
    assert all(r["payload_transfer_external_support"] == "structural_support" for r in rows)
    assert all(r["report_cycle_external_support"] == "structural_support" for r in rows)
    assert all(r["numeric_target_materialised"] is False for r in rows)
