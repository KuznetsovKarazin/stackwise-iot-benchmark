from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from stackwise.wire_accounting import anchor_known_component_bytes, strict_transport_floor_bytes


@dataclass(frozen=True)
class Lwm2mSerializationSummary:
    source_variant_rows: int
    surrogate_shape_designs: int
    serialization_rows: int
    single_resource_rows: int
    three_resource_rows: int
    lwm2m_cbor_rows: int
    senml_cbor_rows: int
    senml_json_rows: int
    rows_with_exact_surrogate_serialization: int
    rows_with_canonical_application_serialization: int
    rows_where_strict_surrogate_raw_volume_exceeds_nominal_allowance: int
    rows_where_strict_surrogate_raw_volume_is_within_nominal_allowance: int
    rows_where_anchor_surrogate_raw_volume_exceeds_nominal_allowance: int
    rows_where_anchor_surrogate_raw_volume_is_within_nominal_allowance: int
    mqtt_tracking_rows_strictly_exceeding_nominal_allowance: int
    coap_tracking_three_resource_senml_json_rows_strictly_exceeding_nominal_allowance: int


def _int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _cbor_head_size(argument: int) -> int:
    if argument < 0:
        raise ValueError("CBOR definite-length/unsigned argument must be non-negative.")
    if argument <= 23:
        return 1
    if argument <= 0xFF:
        return 2
    if argument <= 0xFFFF:
        return 3
    if argument <= 0xFFFFFFFF:
        return 5
    return 9


def base64url_unpadded_length(octets: int) -> int:
    if octets < 0:
        raise ValueError("Binary payload length must be non-negative.")
    q, r = divmod(octets, 3)
    return 4 * q + (0 if r == 0 else 2 if r == 1 else 3)


def split_payload_evenly(total_octets: int, resources: int) -> list[int]:
    if total_octets < 0 or resources <= 0:
        raise ValueError("Payload length must be non-negative and resource count positive.")
    q, r = divmod(total_octets, resources)
    return [q + (1 if idx < r else 0) for idx in range(resources)]


def _json_single_opaque_length(payload_octets: int, path: str) -> int:
    # Compact UTF-8 JSON with no optional whitespace. The binary value uses
    # RFC 8428 SenML Data Value (vd) base64url with padding omitted.
    b64 = base64url_unpadded_length(payload_octets)
    return len('[{"n":"') + len(path.encode("utf-8")) + len('","vd":"') + b64 + len('"}]')


def _json_three_opaque_length(payload_octets: int, base_name: str) -> int:
    chunks = split_payload_evenly(payload_octets, 3)
    # [{"bn":"<base>","n":"0","vd":"..."},{"n":"1","vd":"..."},{"n":"2","vd":"..."}]
    first = (
        len('{"bn":"') + len(base_name.encode("utf-8")) + len('","n":"0","vd":"')
        + base64url_unpadded_length(chunks[0]) + len('"}')
    )
    others = sum(
        len('{"n":"') + 1 + len('","vd":"') + base64url_unpadded_length(chunk) + len('"}')
        for chunk in chunks[1:]
    )
    return 1 + first + 2 + others + 1  # '[' + records + two commas + ']'


def _senml_cbor_single_opaque_length(payload_octets: int, path: str) -> int:
    # definite array(1), map(2), n=0 with full path tstr, vd=8 with bstr
    path_bytes = len(path.encode("utf-8"))
    return (
        _cbor_head_size(1)
        + _cbor_head_size(2)
        + _cbor_head_size(0) + _cbor_head_size(path_bytes) + path_bytes
        + _cbor_head_size(8) + _cbor_head_size(payload_octets) + payload_octets
    )


def _senml_cbor_three_opaque_length(payload_octets: int, base_name: str) -> int:
    chunks = split_payload_evenly(payload_octets, 3)
    base_bytes = len(base_name.encode("utf-8"))
    total = _cbor_head_size(3)  # array(3)
    # First record: {-2: base_name, 0: "0", 8: bstr}
    total += _cbor_head_size(3)
    total += _cbor_head_size(1)  # negative integer -2 is one octet
    total += _cbor_head_size(base_bytes) + base_bytes
    total += _cbor_head_size(0) + _cbor_head_size(1) + 1
    total += _cbor_head_size(8) + _cbor_head_size(chunks[0]) + chunks[0]
    # Remaining records: {0: "1|2", 8: bstr}
    for chunk in chunks[1:]:
        total += _cbor_head_size(2)
        total += _cbor_head_size(0) + _cbor_head_size(1) + 1
        total += _cbor_head_size(8) + _cbor_head_size(chunk) + chunk
    return total


def _lwm2m_cbor_single_opaque_length(payload_octets: int, object_id: int) -> int:
    # Definite map(1): {[object_id, 0, 0]: bstr}
    return (
        _cbor_head_size(1)
        + _cbor_head_size(3)
        + _cbor_head_size(object_id)
        + _cbor_head_size(0)
        + _cbor_head_size(0)
        + _cbor_head_size(payload_octets)
        + payload_octets
    )


def _lwm2m_cbor_three_opaque_length(payload_octets: int, object_id: int) -> int:
    # Deterministic compact hierarchical form permitted by OMA LwM2M CBOR:
    # {object_id: {0: {0: bstr0, 1: bstr1, 2: bstr2}}}
    chunks = split_payload_evenly(payload_octets, 3)
    total = _cbor_head_size(1) + _cbor_head_size(object_id)
    total += _cbor_head_size(1) + _cbor_head_size(0)
    total += _cbor_head_size(3)
    for rid, chunk in enumerate(chunks):
        total += _cbor_head_size(rid) + _cbor_head_size(chunk) + chunk
    return total


def serialized_payload_bytes(
    payload_octets: int,
    encoding: str,
    shape_id: str,
    *,
    object_id: int = 42769,
) -> int:
    path = f"/{object_id}/0/0"
    base_name = f"/{object_id}/0/"
    if shape_id == "S0_single_opaque_test_resource":
        if encoding == "LwM2M_CBOR":
            return _lwm2m_cbor_single_opaque_length(payload_octets, object_id)
        if encoding == "SenML_CBOR":
            return _senml_cbor_single_opaque_length(payload_octets, path)
        if encoding == "SenML_JSON":
            return _json_single_opaque_length(payload_octets, path)
    elif shape_id == "S1_three_opaque_test_resources":
        if encoding == "LwM2M_CBOR":
            return _lwm2m_cbor_three_opaque_length(payload_octets, object_id)
        if encoding == "SenML_CBOR":
            return _senml_cbor_three_opaque_length(payload_octets, base_name)
        if encoding == "SenML_JSON":
            return _json_three_opaque_length(payload_octets, base_name)
    raise ValueError(f"Unsupported Stage-5M shape/encoding: {shape_id!r} / {encoding!r}")


def serialization_size_table(policy: dict[str, Any]) -> list[dict[str, Any]]:
    object_id = int(policy["scientific_policy"]["synthetic_test_object_id"])
    rows: list[dict[str, Any]] = []
    for payload in policy["benchmark_payload_octets"]:
        for shape in policy["serialization_surrogates"]:
            shape_id = str(shape["shape_id"])
            for encoding in policy["encodings"]:
                encoded = serialized_payload_bytes(int(payload), str(encoding), shape_id, object_id=object_id)
                rows.append({
                    "pre_lwm2m_application_payload_bytes": int(payload),
                    "shape_id": shape_id,
                    "resource_count": int(shape["resource_count"]),
                    "lwm2m_payload_encoding": str(encoding),
                    "serialized_lwm2m_payload_bytes": encoded,
                    "serialization_overhead_bytes": encoded - int(payload),
                    "serialization_expansion_ratio": encoded / int(payload),
                    "synthetic_test_object_id": object_id,
                    "canonical_application_model": False,
                })
    return rows


def build_serialization_envelope_rows(
    variants: Iterable[dict[str, Any]],
    wire_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    wire_by_variant = {str(row["variant_id"]): row for row in wire_rows}
    mb_bytes = int(policy["scientific_policy"]["tariff_megabyte_definition_bytes"])
    object_id = int(policy["scientific_policy"]["synthetic_test_object_id"])
    out: list[dict[str, Any]] = []
    for variant in variants:
        wire = wire_by_variant[str(variant["variant_id"])]
        payload = _int(variant["application_payload_bytes"])
        encoding = str(variant["lwm2m_payload_encoding"])
        reports = _int(wire["five_year_report_count"])
        included_bytes = _int(wire["included_data_bytes"])
        for shape in policy["serialization_surrogates"]:
            shape_id = str(shape["shape_id"])
            encoded = serialized_payload_bytes(payload, encoding, shape_id, object_id=object_id)
            strict = strict_transport_floor_bytes(variant, encoded)
            anchor = anchor_known_component_bytes(variant, encoded, include_ip=False)
            strict_5y = strict * reports
            anchor_5y = anchor * reports
            strict_exceeds = strict_5y > included_bytes
            anchor_exceeds = anchor_5y > included_bytes
            out.append({
                "serialization_row_id": f"{variant['variant_id']}__{shape_id}",
                "variant_id": variant["variant_id"],
                "profile_id": variant["profile_id"],
                "scenario_id": variant["scenario_id"],
                "stack_id": variant["stack_id"],
                "binding_family": variant["binding_family"],
                "access_technology": variant["access_technology"],
                "anchor_id": variant["anchor_id"],
                "shape_id": shape_id,
                "resource_count": int(shape["resource_count"]),
                "synthetic_test_object_id": object_id,
                "pre_lwm2m_application_payload_bytes": payload,
                "lwm2m_payload_encoding": encoding,
                "serialized_lwm2m_payload_bytes": encoded,
                "serialization_overhead_bytes": encoded - payload,
                "serialization_expansion_ratio": encoded / payload,
                "exact_surrogate_serialization_identified": True,
                "canonical_application_serialization_identified": False,
                "strict_transport_bytes_per_report_with_surrogate": strict,
                "anchor_transport_bytes_per_report_with_surrogate": anchor,
                "five_year_report_count": reports,
                "included_data_bytes": included_bytes,
                "five_year_strict_transport_bytes": strict_5y,
                "five_year_strict_transport_mb": strict_5y / mb_bytes,
                "five_year_anchor_transport_bytes": anchor_5y,
                "five_year_anchor_transport_mb": anchor_5y / mb_bytes,
                "strict_surrogate_raw_nominal_allowance_status": (
                    "surrogate_strict_raw_volume_exceeds_nominal_500mb_allowance"
                    if strict_exceeds else "surrogate_strict_raw_volume_within_nominal_500mb_allowance"
                ),
                "anchor_surrogate_raw_nominal_allowance_status": (
                    "surrogate_anchor_raw_volume_exceeds_nominal_500mb_allowance"
                    if anchor_exceeds else "surrogate_anchor_raw_volume_within_nominal_500mb_allowance"
                ),
                "security_session_increment_unresolved": bool(wire["security_session_increment_unresolved"] in {True, "True", "true", "1"}),
                "mqtt_pure_tcp_ack_and_segmentation_overhead_unresolved": bool(wire["mqtt_pure_tcp_ack_and_segmentation_overhead_unresolved"] in {True, "True", "true", "1"}),
                "billing_rounding_interval_unresolved": True,
                "exact_billed_volume_ready": False,
                "tariff_topup_count_exact_ready": False,
                "canonical_report_energy_ready": False,
                "surrogate_interpretation": str(shape["interpretation"]),
            })
    return sorted(out, key=lambda r: (str(r["scenario_id"]), str(r["stack_id"]), str(r["anchor_id"]), str(r["shape_id"])))


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> Lwm2mSerializationSummary:
    data = list(rows)
    tracking_scenarios = {"asset_tracking_connected_handover", "asset_tracking_periodic_cross_cell"}
    result = Lwm2mSerializationSummary(
        source_variant_rows=len({str(r["variant_id"]) for r in data}),
        surrogate_shape_designs=len({str(r["shape_id"]) for r in data}),
        serialization_rows=len(data),
        single_resource_rows=sum(r["shape_id"] == "S0_single_opaque_test_resource" for r in data),
        three_resource_rows=sum(r["shape_id"] == "S1_three_opaque_test_resources" for r in data),
        lwm2m_cbor_rows=sum(r["lwm2m_payload_encoding"] == "LwM2M_CBOR" for r in data),
        senml_cbor_rows=sum(r["lwm2m_payload_encoding"] == "SenML_CBOR" for r in data),
        senml_json_rows=sum(r["lwm2m_payload_encoding"] == "SenML_JSON" for r in data),
        rows_with_exact_surrogate_serialization=sum(bool(r["exact_surrogate_serialization_identified"]) for r in data),
        rows_with_canonical_application_serialization=sum(bool(r["canonical_application_serialization_identified"]) for r in data),
        rows_where_strict_surrogate_raw_volume_exceeds_nominal_allowance=sum("exceeds" in str(r["strict_surrogate_raw_nominal_allowance_status"]) for r in data),
        rows_where_strict_surrogate_raw_volume_is_within_nominal_allowance=sum("within" in str(r["strict_surrogate_raw_nominal_allowance_status"]) for r in data),
        rows_where_anchor_surrogate_raw_volume_exceeds_nominal_allowance=sum("exceeds" in str(r["anchor_surrogate_raw_nominal_allowance_status"]) for r in data),
        rows_where_anchor_surrogate_raw_volume_is_within_nominal_allowance=sum("within" in str(r["anchor_surrogate_raw_nominal_allowance_status"]) for r in data),
        mqtt_tracking_rows_strictly_exceeding_nominal_allowance=sum(
            str(r["scenario_id"]) in tracking_scenarios
            and r["binding_family"] == "mqtt_tls_tcp"
            and "exceeds" in str(r["strict_surrogate_raw_nominal_allowance_status"])
            for r in data
        ),
        coap_tracking_three_resource_senml_json_rows_strictly_exceeding_nominal_allowance=sum(
            str(r["scenario_id"]) in tracking_scenarios
            and r["binding_family"] == "coap_dtls_udp"
            and r["shape_id"] == "S1_three_opaque_test_resources"
            and r["lwm2m_payload_encoding"] == "SenML_JSON"
            and "exceeds" in str(r["strict_surrogate_raw_nominal_allowance_status"])
            for r in data
        ),
    )
    expected = policy.get("expected", {})
    for key, actual in result.__dict__.items():
        if key in expected and int(expected[key]) != int(actual):
            raise ValueError(f"Stage-5M checkpoint mismatch for {key}: expected={expected[key]} actual={actual}")
    return result
