from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from stackwise.wire_accounting import (
    _cbor_bstr_header_size,
    _mqtt_vbi_size,
    anchor_known_component_bytes,
    audit_summary,
    build_wire_accounting_rows,
    strict_transport_floor_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage5l_wire_volume_accounting.yml").read_text(encoding="utf-8"))
    variants = _csv(ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv")
    stage5i = _csv(ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv")
    rows = build_wire_accounting_rows(variants, stage5i, policy)
    return policy, variants, stage5i, rows


def _row(rows, scenario, stack, anchor):
    return next(r for r in rows if r["scenario_id"] == scenario and r["stack_id"] == stack and r["anchor_id"] == anchor)


def test_stage5l_materialises_known_component_accounting_for_all_variants_but_no_exact_wire_volume():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.variant_rows == 90
    assert summary.rows_with_strict_transport_floor == 90
    assert summary.rows_with_anchor_known_component_accounting == 90
    assert summary.rows_with_exact_wire_volume == 0
    assert summary.rows_with_unresolved_lwm2m_serialization == 90


def test_stage5l_baseline_coap_transport_floor_matches_standards_components():
    _, _, _, rows = _inputs()
    row = _row(rows, "asset_tracking_connected_handover", "ltem_ip_coap_dtls_lwm2m", "A0_compact_persistent")
    # Request known component: CoAP 10 + DTLS 19 + UDP 8 = 37.
    # Response: CoAP 4 + DTLS 19 + UDP 8 = 31. Total 68, excluding IP.
    assert int(row["strict_transport_known_component_floor_bytes_per_report"]) == 68
    assert int(row["strict_ip_wire_known_component_floor_bytes_per_report"]) == 108  # + two IPv4 headers


def test_stage5l_baseline_mqtt_transport_floor_exceeds_tracking_raw_nominal_allowance_even_with_zero_serialized_payload():
    _, _, _, rows = _inputs()
    row = _row(rows, "asset_tracking_connected_handover", "ltem_ip_mqtt_tls_lwm2m", "A0_compact_persistent")
    assert int(row["strict_transport_known_component_floor_bytes_per_report"]) == 205
    assert float(row["five_year_strict_transport_floor_mb"]) == pytest.approx(539.109)
    assert row["raw_nominal_allowance_status_from_strict_floor"].startswith("strict_raw_transport_floor_exceeds")
    assert int(row["optimistic_max_encoded_lwm2m_payload_bytes_per_report_under_strict_floor"]) == -1


def test_stage5l_raw_floor_exceedance_is_confined_to_mqtt_tracking_variants():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.rows_where_strict_raw_transport_floor_exceeds_nominal_allowance == 27
    exceeding = [r for r in rows if "exceeds_nominal" in r["raw_nominal_allowance_status_from_strict_floor"]]
    assert {r["binding_family"] for r in exceeding} == {"mqtt_tls_tcp"}
    assert {r["scenario_id"] for r in exceeding} == {
        "asset_tracking_connected_handover",
        "asset_tracking_periodic_cross_cell",
    }


def test_stage5l_keeps_billing_rounding_unresolved_and_does_not_claim_exact_topups():
    policy, _, _, rows = _inputs()
    assert policy["scientific_policy"]["billing_rounding_interval_is_unresolved"] is True
    assert all(r["billing_rounding_interval_unresolved"] is True for r in rows)
    assert all(r["tariff_topup_count_exact_ready"] is False for r in rows)
    assert policy["scientific_policy"]["exact_tariff_topup_count_authorised"] is False


def test_stage5l_session_and_tcp_unknowns_remain_explicit():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.rows_with_unresolved_session_increment == 20  # A5 + A6 across 10 profiles
    assert summary.mqtt_rows_with_unresolved_tcp_ack_segmentation == 45


def test_stage5l_anchor_accounting_changes_retry_and_binding_expanded_cases_without_changing_strict_floor_semantics():
    _, variants, _, rows = _inputs()
    base = _row(rows, "asset_tracking_connected_handover", "ltem_ip_coap_dtls_lwm2m", "A0_compact_persistent")
    retry = _row(rows, "asset_tracking_connected_handover", "ltem_ip_coap_dtls_lwm2m", "A7_single_retry")
    expanded = _row(rows, "asset_tracking_connected_handover", "ltem_ip_coap_dtls_lwm2m", "A8_binding_expanded")
    assert int(base["anchor_transport_known_component_bytes_per_report"]) == 68
    assert int(retry["strict_transport_known_component_floor_bytes_per_report"]) == 68
    assert int(retry["anchor_transport_known_component_bytes_per_report"]) == 136
    assert int(expanded["anchor_transport_known_component_bytes_per_report"]) == 162


def test_stage5l_payload_length_helpers_cover_relevant_cbor_and_mqtt_boundaries():
    assert _cbor_bstr_header_size(0) == 1
    assert _cbor_bstr_header_size(23) == 1
    assert _cbor_bstr_header_size(24) == 2
    assert _cbor_bstr_header_size(255) == 2
    assert _cbor_bstr_header_size(256) == 3
    assert _mqtt_vbi_size(127) == 1
    assert _mqtt_vbi_size(128) == 2
    assert _mqtt_vbi_size(16383) == 2
    assert _mqtt_vbi_size(16384) == 3


def test_stage5l_does_not_equate_pre_lwm2m_application_payload_with_serialized_payload():
    policy, _, _, rows = _inputs()
    assert policy["scientific_policy"]["infer_lwm2m_serialized_payload_length_from_application_payload_bytes"] is False
    assert all(r["encoded_lwm2m_payload_bytes"] == "" for r in rows)
    assert {int(r["pre_lwm2m_application_payload_bytes"]) for r in rows} == {64, 200}
