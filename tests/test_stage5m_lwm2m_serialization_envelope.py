from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from stackwise.lwm2m_serialization import (
    audit_summary,
    base64url_unpadded_length,
    build_serialization_envelope_rows,
    serialization_size_table,
    serialized_payload_bytes,
    split_payload_evenly,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage5m_lwm2m_serialization_envelope.yml").read_text(encoding="utf-8"))
    variants = _csv(ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv")
    wire_rows = _csv(ROOT / "results/validation/stage5l_wire_volume_accounting/wire_volume_accounting.csv")
    rows = build_serialization_envelope_rows(variants, wire_rows, policy)
    return policy, variants, wire_rows, rows


def test_stage5m_exact_serialization_lengths_for_single_opaque_surrogate():
    assert serialized_payload_bytes(64, "LwM2M_CBOR", "S0_single_opaque_test_resource") == 73
    assert serialized_payload_bytes(64, "SenML_CBOR", "S0_single_opaque_test_resource") == 81
    assert serialized_payload_bytes(64, "SenML_JSON", "S0_single_opaque_test_resource") == 114
    assert serialized_payload_bytes(200, "LwM2M_CBOR", "S0_single_opaque_test_resource") == 209
    assert serialized_payload_bytes(200, "SenML_CBOR", "S0_single_opaque_test_resource") == 217
    assert serialized_payload_bytes(200, "SenML_JSON", "S0_single_opaque_test_resource") == 295


def test_stage5m_exact_serialization_lengths_for_three_resource_surrogate():
    assert serialized_payload_bytes(64, "LwM2M_CBOR", "S1_three_opaque_test_resources") == 77
    assert serialized_payload_bytes(64, "SenML_CBOR", "S1_three_opaque_test_resources") == 94
    assert serialized_payload_bytes(64, "SenML_JSON", "S1_three_opaque_test_resources") == 158
    assert serialized_payload_bytes(200, "LwM2M_CBOR", "S1_three_opaque_test_resources") == 216
    assert serialized_payload_bytes(200, "SenML_CBOR", "S1_three_opaque_test_resources") == 233
    assert serialized_payload_bytes(200, "SenML_JSON", "S1_three_opaque_test_resources") == 340


def test_stage5m_binary_length_helpers_are_deterministic():
    assert base64url_unpadded_length(0) == 0
    assert base64url_unpadded_length(1) == 2
    assert base64url_unpadded_length(2) == 3
    assert base64url_unpadded_length(3) == 4
    assert base64url_unpadded_length(64) == 86
    assert split_payload_evenly(64, 3) == [22, 21, 21]
    assert split_payload_evenly(200, 3) == [67, 67, 66]


def test_stage5m_materialises_two_surrogates_for_every_variant_without_claiming_canonical_serialization():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.source_variant_rows == 90
    assert summary.surrogate_shape_designs == 2
    assert summary.serialization_rows == 180
    assert summary.rows_with_exact_surrogate_serialization == 180
    assert summary.rows_with_canonical_application_serialization == 0
    assert all(r["exact_billed_volume_ready"] is False for r in rows)
    assert all(r["canonical_report_energy_ready"] is False for r in rows)


def test_stage5m_format_row_counts_follow_stage5k_encoding_anchors():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.lwm2m_cbor_rows == 20
    assert summary.senml_cbor_rows == 140
    assert summary.senml_json_rows == 20


def test_stage5m_all_mqtt_tracking_surrogates_remain_over_nominal_raw_allowance_at_strict_exchange():
    policy, _, _, rows = _inputs()
    summary = audit_summary(rows, policy)
    assert summary.mqtt_tracking_rows_strictly_exceeding_nominal_allowance == 54
    selected = [
        r for r in rows
        if r["binding_family"] == "mqtt_tls_tcp"
        and r["scenario_id"] in {"asset_tracking_connected_handover", "asset_tracking_periodic_cross_cell"}
    ]
    assert len(selected) == 54
    assert all("exceeds" in r["strict_surrogate_raw_nominal_allowance_status"] for r in selected)


def test_stage5m_three_resource_senml_json_flips_coap_tracking_strict_raw_allowance_while_single_resource_stays_below():
    _, _, _, rows = _inputs()
    selected = [
        r for r in rows
        if r["binding_family"] == "coap_dtls_udp"
        and r["scenario_id"] == "asset_tracking_connected_handover"
        and r["anchor_id"] == "A4_senml_json"
    ]
    assert len(selected) == 2
    by_shape = {r["shape_id"]: r for r in selected}
    assert float(by_shape["S0_single_opaque_test_resource"]["five_year_strict_transport_mb"]) == pytest.approx(478.6236)
    assert "within" in by_shape["S0_single_opaque_test_resource"]["strict_surrogate_raw_nominal_allowance_status"]
    assert float(by_shape["S1_three_opaque_test_resources"]["five_year_strict_transport_mb"]) == pytest.approx(594.3348)
    assert "exceeds" in by_shape["S1_three_opaque_test_resources"]["strict_surrogate_raw_nominal_allowance_status"]


def test_stage5m_anchor_retry_and_expanded_cases_can_exceed_even_when_strict_surrogate_exchange_is_within():
    _, _, _, rows = _inputs()
    selected = [
        r for r in rows
        if r["binding_family"] == "coap_dtls_udp"
        and r["scenario_id"] == "asset_tracking_connected_handover"
        and r["shape_id"] == "S0_single_opaque_test_resource"
        and r["anchor_id"] in {"A7_single_retry", "A8_binding_expanded"}
    ]
    assert len(selected) == 2
    assert all("within" in r["strict_surrogate_raw_nominal_allowance_status"] for r in selected)
    assert all("exceeds" in r["anchor_surrogate_raw_nominal_allowance_status"] for r in selected)


def test_stage5m_smart_meter_surrogates_remain_within_nominal_raw_allowance_even_under_anchor_accounting():
    _, _, _, rows = _inputs()
    selected = [r for r in rows if r["scenario_id"] == "smart_meter_public_cellular"]
    assert len(selected) == 72
    assert all("within" in r["strict_surrogate_raw_nominal_allowance_status"] for r in selected)
    assert all("within" in r["anchor_surrogate_raw_nominal_allowance_status"] for r in selected)


def test_stage5m_policy_uses_oma_test_object_and_forbids_production_interpretation():
    policy, _, _, _ = _inputs()
    assert int(policy["scientific_policy"]["synthetic_test_object_id"]) == 42769
    assert policy["scientific_policy"]["synthetic_test_object_production_use_authorised"] is False
    assert policy["scientific_policy"]["infer_real_application_resource_model"] is False
    assert policy["scientific_policy"]["canonical_application_serialization_authorised"] is False


def test_stage5m_size_table_contains_all_payload_shape_encoding_combinations():
    policy, _, _, _ = _inputs()
    table = serialization_size_table(policy)
    assert len(table) == 12
    assert {r["pre_lwm2m_application_payload_bytes"] for r in table} == {64, 200}
    assert {r["resource_count"] for r in table} == {1, 3}
    assert {r["lwm2m_payload_encoding"] for r in table} == {"LwM2M_CBOR", "SenML_CBOR", "SenML_JSON"}
