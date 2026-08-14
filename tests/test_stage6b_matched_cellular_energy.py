from __future__ import annotations

from pathlib import Path

import yaml

from stackwise.matched_energy import audit_summary, experiment_cell_rows, source_review_rows

ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage6b_matched_cellular_energy.yml").read_text(encoding="utf-8"))


def test_stage6b_reviews_four_sources_but_finds_no_candidate_boundary_match():
    policy = _policy()
    rows = source_review_rows(policy)
    assert len(rows) == 4
    assert sum(r["both_rats"] for r in rows) == 2
    assert sum(r["exact_64b_payload"] for r in rows) == 1
    assert sum(r["exact_60s_cycle"] for r in rows) == 0
    assert sum(r["candidate_boundary_ready"] for r in rows) == 0
    assert all(r["canonical_energy_target_authorised"] is False for r in rows)


def test_stage6b_minimum_experiment_is_four_primary_plus_four_robustness_cells():
    policy = _policy()
    rows = experiment_cell_rows(policy)
    assert len(rows) == 8
    primary = [r for r in rows if r["required_for_first_slice"]]
    sensitivity = [r for r in rows if not r["required_for_first_slice"]]
    assert len(primary) == 4
    assert len(sensitivity) == 4
    assert {r["rat"] for r in primary} == {"NB-IoT", "LTE-M"}
    assert {r["binding_family"] for r in primary} == {"coap_dtls_udp", "mqtt_tls_tcp"}
    assert {r["pre_lwm2m_application_payload_bytes"] for r in rows} == {64}
    assert {r["reporting_interval_s"] for r in rows} == {60}
    assert all(r["canonical_target_ready"] is False for r in rows)
    assert all(r["score_authorised"] is False for r in rows)


def test_stage6b_contract_uses_complete_cycle_as_replication_unit_and_preserves_failures():
    contract = _policy()["minimum_experiment_contract"]
    assert contract["replication_unit"] == "one complete scheduled 60-s report cycle"
    assert contract["pilot_blocks"] == 5
    assert "Do not discard failed cycles" in contract["failed_reports_policy"]
    assert "not frozen before pilot" in contract["final_replication_count"]


def test_stage6b_summary_matches_expected_and_keeps_mcda_blocked():
    policy = _policy()
    sources = source_review_rows(policy)
    experiments = experiment_cell_rows(policy)
    summary = audit_summary(policy, sources, experiments)
    assert summary.external_sources_reviewed == 4
    assert summary.sources_covering_both_rats == 2
    assert summary.sources_candidate_boundary_ready == 0
    assert summary.primary_experiment_cells == 4
    assert summary.robustness_experiment_cells == 4
    assert policy["expected"]["publication_mcda_authorised"] is False
