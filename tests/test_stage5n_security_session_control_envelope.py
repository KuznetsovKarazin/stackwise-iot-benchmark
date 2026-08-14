from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from stackwise.session_control_envelope import (
    audit_summary,
    build_session_control_envelope_rows,
    dtls13_psk_handshake_transport_bytes,
    handshake_reference_rows,
    mqtt5_minimal_connack_packet_bytes,
    mqtt5_minimal_connect_packet_bytes,
    source_row_robustness_rows,
    tls13_psk_handshake_record_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage5n_security_session_control_envelope.yml").read_text(encoding="utf-8"))
    variants = _csv(ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv")
    serial = _csv(ROOT / "results/validation/stage5m_lwm2m_serialization_envelope/serialization_surrogate_envelope.csv")
    rows = build_session_control_envelope_rows(serial, variants, policy)
    return policy, variants, serial, rows


def test_stage5n_tls_psk_reference_sizes_are_deterministic():
    compact = tls13_psk_handshake_record_bytes(psk_identity_bytes=16, psk_dhe=False)
    expanded = tls13_psk_handshake_record_bytes(psk_identity_bytes=64, psk_dhe=True)
    assert compact["tls_handshake_record_bytes"] == 311
    assert expanded["tls_handshake_record_bytes"] == 449
    assert compact["tls_data_carrying_segments"] == expanded["tls_data_carrying_segments"] == 4


def test_stage5n_dtls_psk_reference_sizes_include_final_ack_and_udp_packing():
    compact = dtls13_psk_handshake_transport_bytes(
        psk_identity_bytes=16,
        psk_dhe=False,
        unified_header_bytes=2,
        server_flight_combined_datagram=True,
    )
    expanded = dtls13_psk_handshake_transport_bytes(
        psk_identity_bytes=64,
        psk_dhe=True,
        unified_header_bytes=6,
        server_flight_combined_datagram=False,
    )
    assert compact["final_ack_record_bytes"] == 37
    assert compact["dtls_handshake_transport_bytes"] == 431
    assert expanded["dtls_handshake_transport_bytes"] == 589
    assert compact["udp_datagrams"] == 4
    assert expanded["udp_datagrams"] == 5


def test_stage5n_minimal_mqtt_connect_connack_sizes():
    assert mqtt5_minimal_connect_packet_bytes(36) == 51
    assert mqtt5_minimal_connack_packet_bytes() == 5


def test_stage5n_materialises_two_envelopes_per_stage5m_row_without_canonical_claims():
    policy, _, serial, rows = _inputs()
    assert len(serial) == 180
    assert len(rows) == 360
    assert {r["envelope_id"] for r in rows} == {"E0_compact_psk_control", "E1_expanded_psk_dhe_control"}
    assert all(r["envelope_probability"] == "" and r["envelope_weight"] == "" for r in rows)
    assert all(r["canonical_security_session_increment_identified"] is False for r in rows)
    assert all(r["canonical_mqtt_tcp_ack_segmentation_identified"] is False for r in rows)
    assert all(r["publication_mcda_authorised"] is False for r in rows)
    audit_summary(rows, policy)


def test_stage5n_security_increment_only_applies_to_resume_and_full_reestablishment_anchors():
    _, _, _, rows = _inputs()
    positive = [r for r in rows if int(r["security_session_surrogate_increment_bytes_per_report"]) > 0]
    assert positive
    assert {r["anchor_id"] for r in positive} == {"A5_resume_each_report", "A6_full_reestablishment_each_report"}
    assert len(positive) == 80  # 20 source rows (10 variants x 2 shapes) x 2 envelope designs


def test_stage5n_expanded_mqtt_ack_anchor_is_positive_compact_is_zero():
    _, _, _, rows = _inputs()
    mqtt = [r for r in rows if r["binding_family"] == "mqtt_tls_tcp"]
    compact = [r for r in mqtt if r["envelope_id"] == "E0_compact_psk_control"]
    expanded = [r for r in mqtt if r["envelope_id"] == "E1_expanded_psk_dhe_control"]
    assert len(compact) == len(expanded) == 90
    assert all(int(r["mqtt_pure_tcp_ack_surrogate_increment_bytes_per_report"]) == 0 for r in compact)
    assert all(int(r["mqtt_pure_tcp_ack_surrogate_increment_bytes_per_report"]) > 0 for r in expanded)


def test_stage5n_robustness_classifies_each_stage5m_source_row_once():
    _, _, serial, rows = _inputs()
    robust = source_row_robustness_rows(rows)
    assert len(robust) == len(serial) == 180
    assert {r["session_control_surrogate_designs"] for r in robust} == {2}
    assert all(r["probability_interpretation"] is False for r in robust)


def test_stage5n_handshake_reference_ledger_has_current_two_anchor_designs():
    policy, _, _, _ = _inputs()
    rows = handshake_reference_rows(policy)
    assert len(rows) == 2
    by_id = {r["envelope_id"]: r for r in rows}
    assert by_id["E0_compact_psk_control"]["tls_tls_handshake_record_bytes"] == 311
    assert by_id["E1_expanded_psk_dhe_control"]["tls_tls_handshake_record_bytes"] == 449
    assert all(r["normative_exact_deployment_trace"] is False for r in rows)
