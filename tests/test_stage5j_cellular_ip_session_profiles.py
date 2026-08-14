from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.session_profile import (
    audit_summary,
    build_session_profiles,
    gap_priority_rows,
    profile_field_rows,
    readiness_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage5j_cellular_ip_session_profile.yml").read_text(encoding="utf-8"))
    stage5i = _csv(ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv")
    profiles = build_session_profiles(stage5i, policy)
    fields = profile_field_rows(profiles, policy)
    readiness = readiness_rows(profiles, fields)
    return policy, profiles, fields, readiness


def test_stage5j_materialises_ten_ip_profiles_split_evenly_by_binding():
    policy, profiles, fields, readiness = _inputs()
    summary = audit_summary(profiles, fields, readiness, policy)
    assert summary.feasible_ip_cellular_profile_rows == 10
    assert summary.coap_dtls_profile_rows == 5
    assert summary.mqtt_tls_profile_rows == 5


def test_stage5j_freezes_common_lwm2m_send_semantics_without_claiming_measurement():
    policy, profiles, _, _ = _inputs()
    assert policy["scientific_policy"]["benchmark_operation_is_empirical_measurement"] is False
    assert {p["lwm2m_operation"] for p in profiles} == {"Send"}
    assert {p["application_payload_boundary"] for p in profiles} == {"pre_lwm2m_application_data"}
    assert all(p["account_uplink_and_downlink"] is True for p in profiles)


def test_stage5j_keeps_exact_wire_volume_and_report_energy_blocked():
    policy, profiles, fields, readiness = _inputs()
    summary = audit_summary(profiles, fields, readiness, policy)
    assert summary.profiles_complete_for_exact_tariff_volume == 0
    assert summary.profiles_complete_for_canonical_report_energy == 0
    assert summary.canonical_tariff_volume_rows == 0
    assert summary.canonical_report_energy_rows == 0
    assert all(r["exact_tariff_volume_ready"] is False for r in readiness)
    assert all(r["canonical_report_energy_ready"] is False for r in readiness)


def test_stage5j_does_not_infer_ip_version_or_security_session_lifetime():
    _, _, fields, _ = _inputs()
    common = [r for r in fields if r["field_id"] in {"ip_version", "security_context_lifecycle", "session_reestablishment_or_resumption_cadence"}]
    assert len(common) == 30
    assert all(r["field_status"] == "UNRESOLVED" for r in common)


def test_stage5j_coap_send_confirmability_is_not_best_case_selected():
    _, profiles, fields, _ = _inputs()
    coap_profiles = {p["profile_id"] for p in profiles if p["binding_family"] == "coap_dtls_udp"}
    rows = [r for r in fields if r["profile_id"] in coap_profiles and r["field_id"] == "coap_message_type"]
    assert len(rows) == 5
    assert {r["allowed_values"] for r in rows} == {"CON|NON"}
    assert all(r["field_status"] == "UNRESOLVED" for r in rows)


def test_stage5j_mqtt_topic_and_qos_dimensions_remain_explicit():
    _, profiles, fields, _ = _inputs()
    mqtt_profiles = {p["profile_id"] for p in profiles if p["binding_family"] == "mqtt_tls_tcp"}
    required = {"mqtt_endpoint_name_bytes", "mqtt_prefix_bytes", "mqtt_qos", "mqtt_keep_alive_s"}
    rows = [r for r in fields if r["profile_id"] in mqtt_profiles and r["field_id"] in required]
    assert len(rows) == 20
    assert all(r["field_status"] == "UNRESOLVED" for r in rows)


def test_stage5j_field_count_and_unresolved_count_are_versioned_checkpoints():
    policy, profiles, fields, readiness = _inputs()
    summary = audit_summary(profiles, fields, readiness, policy)
    assert summary.field_rows == 200
    assert summary.known_or_frozen_field_rows == 70
    assert summary.unresolved_field_rows == 130


def test_stage5j_gap_priorities_expose_shared_cross_binding_blockers():
    _, _, _, readiness = _inputs()
    gaps = gap_priority_rows(readiness)
    by_key = {(r["target"], r["field_id"]): r for r in gaps}
    assert by_key[("tariff_volume", "ip_version")]["affected_profile_rows"] == 10
    assert by_key[("report_energy", "security_context_lifecycle")]["affected_profile_rows"] == 10
    assert by_key[("tariff_volume", "lwm2m_payload_encoding")]["affected_profile_rows"] == 10
