from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable


@dataclass(frozen=True)
class WireAccountingSummary:
    variant_rows: int
    coap_variant_rows: int
    mqtt_variant_rows: int
    rows_with_strict_transport_floor: int
    rows_with_anchor_known_component_accounting: int
    rows_with_exact_wire_volume: int
    rows_with_unresolved_lwm2m_serialization: int
    mqtt_rows_with_unresolved_tcp_ack_segmentation: int
    rows_with_unresolved_session_increment: int
    rows_where_strict_raw_transport_floor_exceeds_nominal_allowance: int
    rows_where_strict_raw_transport_floor_is_within_nominal_allowance: int


def _int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _ip_header_bytes(ip_version: str) -> int:
    if ip_version == "IPv4":
        return 20
    if ip_version == "IPv6":
        return 40
    raise ValueError(f"Unsupported IP version: {ip_version!r}")


def _content_format_id(encoding: str) -> int:
    mapping = {"SenML_JSON": 110, "SenML_CBOR": 112, "LwM2M_CBOR": 11544}
    try:
        return mapping[encoding]
    except KeyError as exc:
        raise ValueError(f"Unsupported LwM2M Send encoding: {encoding!r}") from exc


def _uint_cbor_size(value: int) -> int:
    if value < 0:
        raise ValueError("Only unsigned CBOR integers are used in the Stage-5L wrappers.")
    if value <= 23:
        return 1
    if value <= 0xFF:
        return 2
    if value <= 0xFFFF:
        return 3
    if value <= 0xFFFFFFFF:
        return 5
    return 9


def _cbor_bstr_header_size(length: int) -> int:
    if length < 0:
        raise ValueError("CBOR byte-string length must be non-negative.")
    if length <= 23:
        return 1
    if length <= 0xFF:
        return 2
    if length <= 0xFFFF:
        return 3
    if length <= 0xFFFFFFFF:
        return 5
    return 9


def _mqtt_vbi_size(value: int) -> int:
    if value < 0 or value > 268_435_455:
        raise ValueError(f"MQTT Remaining Length outside VBI range: {value}")
    if value <= 127:
        return 1
    if value <= 16_383:
        return 2
    if value <= 2_097_151:
        return 3
    return 4


def _dtls_overhead(row: dict[str, Any]) -> int:
    # RFC 9147 unified record header: flags byte + optional CID + 1/2-byte sequence
    # + optional 2-byte length. Protected DTLSInnerPlaintext adds content type and
    # the selected padding, while the AEAD expansion is supplied by the Stage-5K anchor.
    header = 1 + _int(row["dtls_connection_id_length_bytes"]) + _int(row["dtls_sequence_number_length_bytes"])
    if _bool(row["dtls_length_field_present"]):
        header += 2
    inner = 1 + _int(row["dtls_padding_bytes"])
    return header + inner + _int(row["dtls_aead_expansion_bytes"])


def _tls_overhead(row: dict[str, Any]) -> int:
    # TLSCiphertext fixed header (5) + TLSInnerPlaintext content type (1), selected
    # padding and AEAD expansion. Handshake traffic is intentionally separate.
    return 5 + 1 + _int(row["tls_padding_bytes"]) + _int(row["tls_aead_expansion_bytes"])


def _coap_content_format_option_bytes(encoding: str) -> int:
    # Uri-Path /dp precedes Content-Format. Delta=1 fits the base option nibble.
    # Content-Format integer uses its minimal network byte representation.
    cf = _content_format_id(encoding)
    value_bytes = 1 if cf <= 0xFF else 2
    return 1 + value_bytes


def _coap_request_plaintext(row: dict[str, Any], encoded_payload_bytes: int) -> int:
    token = _int(row["coap_token_length_bytes"])
    # 4-byte CoAP base header + token + Uri-Path option for one segment "dp"
    # (one option-header byte + two value bytes) + Content-Format option +
    # payload marker. Send has a non-empty semantic payload; the encoded payload
    # length itself remains an input, not inferred from pre-LwM2M application bytes.
    return 4 + token + 3 + _coap_content_format_option_bytes(str(row["lwm2m_payload_encoding"])) + 1 + encoded_payload_bytes


def _coap_response_plaintext(row: dict[str, Any]) -> int:
    return 4 + _int(row["coap_token_length_bytes"])


def _coap_transport_message_bytes(row: dict[str, Any], coap_plaintext_bytes: int, *, include_ip: bool) -> int:
    value = coap_plaintext_bytes + _dtls_overhead(row) + 8  # UDP header
    if include_ip:
        value += _ip_header_bytes(str(row["ip_version"]))
    return value


def _coap_primary_exchange(row: dict[str, Any], encoded_payload_bytes: int, *, include_ip: bool) -> int:
    request = _coap_transport_message_bytes(row, _coap_request_plaintext(row, encoded_payload_bytes), include_ip=include_ip)
    response = _coap_transport_message_bytes(row, _coap_response_plaintext(row), include_ip=include_ip)
    return request + response


def _coap_anchor_exchange(row: dict[str, Any], encoded_payload_bytes: int, *, include_ip: bool) -> int:
    request = _coap_transport_message_bytes(row, _coap_request_plaintext(row, encoded_payload_bytes), include_ip=include_ip)
    response_mode = str(row["coap_response_exchange_mode"])
    if response_mode in {"non_confirmable_response_exchange", "piggybacked_ack_response"}:
        total = request + _coap_transport_message_bytes(row, _coap_response_plaintext(row), include_ip=include_ip)
    elif response_mode == "separate_confirmable_response":
        empty_ack = _coap_transport_message_bytes(row, 4, include_ip=include_ip)
        separate_response = _coap_transport_message_bytes(row, _coap_response_plaintext(row), include_ip=include_ip)
        client_ack = _coap_transport_message_bytes(row, 4, include_ip=include_ip)
        total = request + empty_ack + separate_response + client_ack
    else:
        raise ValueError(f"Unsupported CoAP response exchange mode: {response_mode!r}")
    if str(row["failure_retry_retransmission_profile"]) == "one_full_transaction_retry_per_application_report":
        total *= 2
    return total


def _mqtt_topic_bytes(row: dict[str, Any]) -> int:
    # OMA topic: [PREFIX "/"] "lwm2m/rd/" ENDPOINT for non-bootstrap interfaces.
    base = 10  # len("lwm2m/rd/")
    endpoint = _int(row["mqtt_endpoint_name_bytes"])
    prefix = _int(row["mqtt_prefix_bytes"])
    return base + endpoint + (prefix + 1 if prefix else 0)


def _mqtt_ir_send_payload_bytes(row: dict[str, Any], encoded_lwm2m_payload_bytes: int) -> int:
    # OMA IR_Payload Send map has four pairs: operation=24, token, ct and payload.
    # CBOR keys (1,2,19,7) each occupy one byte. The Stage-5K token field is the
    # total CBOR-encoded uint length used for the token value.
    token_value = _int(row["lwm2m_mqtt_token_cbor_bytes"])
    ct_value = _uint_cbor_size(_content_format_id(str(row["lwm2m_payload_encoding"])))
    return (
        1  # map(4)
        + 1 + _uint_cbor_size(24)
        + 1 + token_value
        + 1 + ct_value
        + 1 + _cbor_bstr_header_size(encoded_lwm2m_payload_bytes) + encoded_lwm2m_payload_bytes
    )


def _mqtt_generic_send_response_payload_bytes(row: dict[str, Any]) -> int:
    # Generic_Response_Payload for successful Send: {result=>204, token=>uint}.
    token_value = _int(row["lwm2m_mqtt_token_cbor_bytes"])
    return 1 + 1 + _uint_cbor_size(204) + 1 + token_value


def _mqtt_publish_packet_bytes(row: dict[str, Any], payload_bytes: int) -> int:
    topic = _mqtt_topic_bytes(row)
    qos = _int(row["mqtt_qos"])
    remaining = 2 + topic + (2 if qos > 0 else 0) + 1 + payload_bytes  # topic prefix, packet id, zero properties
    return 1 + _mqtt_vbi_size(remaining) + remaining


def _mqtt_min_ack_packet_bytes() -> int:
    # PUBACK/PUBREC/PUBREL/PUBCOMP success with no properties may omit reason code
    # and property length, giving Remaining Length=2 => 4-byte control packet.
    return 4


def _mqtt_ping_packet_bytes() -> int:
    # PINGREQ and PINGRESP both have Remaining Length zero.
    return 2


def _mqtt_data_episode_bytes(row: dict[str, Any], mqtt_bytes: int, *, include_ip: bool) -> int:
    value = mqtt_bytes + _tls_overhead(row) + 20 + _int(row["tcp_header_options_bytes"])
    if include_ip:
        value += _ip_header_bytes(str(row["ip_version"]))
    return value


def _mqtt_primary_exchange(row: dict[str, Any], encoded_payload_bytes: int, *, include_ip: bool) -> int:
    # Strict floor: one mandatory Send PUBLISH uplink and one mandatory Generic
    # Response PUBLISH downlink. QoS acknowledgements, keep-alives, retries,
    # session handshakes and pure TCP ACKs are omitted; this makes the result
    # suitable only as a one-sided minimum known-component test.
    request_payload = _mqtt_ir_send_payload_bytes(row, encoded_payload_bytes)
    response_payload = _mqtt_generic_send_response_payload_bytes(row)
    request = _mqtt_data_episode_bytes(row, _mqtt_publish_packet_bytes(row, request_payload), include_ip=include_ip)
    response = _mqtt_data_episode_bytes(row, _mqtt_publish_packet_bytes(row, response_payload), include_ip=include_ip)
    return request + response


def _mqtt_anchor_exchange(row: dict[str, Any], encoded_payload_bytes: int, *, include_ip: bool) -> int:
    # Deterministic Stage-5K accounting convention: one MQTT control packet per
    # TLS record / data-carrying TCP segment. This is an anchor accounting model,
    # not a claim about implementation packetisation and not the strict tariff floor.
    request_payload = _mqtt_ir_send_payload_bytes(row, encoded_payload_bytes)
    response_payload = _mqtt_generic_send_response_payload_bytes(row)
    packets = [
        _mqtt_publish_packet_bytes(row, request_payload),
        _mqtt_publish_packet_bytes(row, response_payload),
    ]
    qos = _int(row["mqtt_qos"])
    if qos == 1:
        packets.extend([_mqtt_min_ack_packet_bytes(), _mqtt_min_ack_packet_bytes()])
    elif qos == 2:
        packets.extend([_mqtt_min_ack_packet_bytes()] * 6)
    elif qos != 0:
        raise ValueError(f"Unsupported MQTT QoS: {qos}")

    keep_alive = _int(row["mqtt_keep_alive_s"])
    interval = _int(row["reporting_interval_s"])
    ping_pairs = max(0, ceil(interval / keep_alive) - 1) if keep_alive > 0 else 0
    packets.extend([_mqtt_ping_packet_bytes(), _mqtt_ping_packet_bytes()] * ping_pairs)

    total = sum(_mqtt_data_episode_bytes(row, packet, include_ip=include_ip) for packet in packets)
    if str(row["failure_retry_retransmission_profile"]) == "one_full_transaction_retry_per_application_report":
        # Retry the LwM2M application transaction and its QoS delivery flow; keep-alive
        # traffic is interval-driven and is therefore not duplicated.
        app_packet_count = 2 + (2 if qos == 1 else 6 if qos == 2 else 0)
        total += sum(_mqtt_data_episode_bytes(row, packet, include_ip=include_ip) for packet in packets[:app_packet_count])
    return total


def strict_transport_floor_bytes(row: dict[str, Any], encoded_lwm2m_payload_bytes: int = 0) -> int:
    binding = str(row["binding_family"])
    if binding == "coap_dtls_udp":
        return _coap_primary_exchange(row, encoded_lwm2m_payload_bytes, include_ip=False)
    if binding == "mqtt_tls_tcp":
        return _mqtt_primary_exchange(row, encoded_lwm2m_payload_bytes, include_ip=False)
    raise ValueError(f"Unsupported binding: {binding!r}")


def strict_ip_wire_floor_bytes(row: dict[str, Any], encoded_lwm2m_payload_bytes: int = 0) -> int:
    binding = str(row["binding_family"])
    if binding == "coap_dtls_udp":
        return _coap_primary_exchange(row, encoded_lwm2m_payload_bytes, include_ip=True)
    if binding == "mqtt_tls_tcp":
        return _mqtt_primary_exchange(row, encoded_lwm2m_payload_bytes, include_ip=True)
    raise ValueError(f"Unsupported binding: {binding!r}")


def anchor_known_component_bytes(row: dict[str, Any], encoded_lwm2m_payload_bytes: int = 0, *, include_ip: bool = False) -> int:
    binding = str(row["binding_family"])
    if binding == "coap_dtls_udp":
        return _coap_anchor_exchange(row, encoded_lwm2m_payload_bytes, include_ip=include_ip)
    if binding == "mqtt_tls_tcp":
        return _mqtt_anchor_exchange(row, encoded_lwm2m_payload_bytes, include_ip=include_ip)
    raise ValueError(f"Unsupported binding: {binding!r}")


def _max_payload_under_tariff(row: dict[str, Any], reports: int, included_bytes: int, *, limit: int = 1_000_000) -> int:
    # Optimistic maximum serialized LwM2M payload consistent with the strict primary-
    # exchange floor. It deliberately omits session increments and other positive traffic.
    if strict_transport_floor_bytes(row, 0) * reports > included_bytes:
        return -1
    lo, hi = 0, 1
    while hi < limit and strict_transport_floor_bytes(row, hi) * reports <= included_bytes:
        hi *= 2
    hi = min(hi, limit)
    if strict_transport_floor_bytes(row, hi) * reports <= included_bytes:
        return hi
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if strict_transport_floor_bytes(row, mid) * reports <= included_bytes:
            lo = mid
        else:
            hi = mid
    return lo


def build_wire_accounting_rows(
    variants: Iterable[dict[str, Any]],
    stage5i_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    stage5i = {(str(r["scenario_id"]), str(r["stack_id"])): r for r in stage5i_rows}
    mb_bytes = int(policy["scientific_policy"]["tariff_megabyte_definition_bytes"])
    out: list[dict[str, Any]] = []
    for row in variants:
        key = (str(row["scenario_id"]), str(row["stack_id"]))
        tariff = stage5i[key]
        reports = _int(tariff.get("five_year_report_count"))
        included_mb = _int(tariff.get("included_data_mb"))
        included_bytes = included_mb * mb_bytes

        strict_transport = strict_transport_floor_bytes(row, 0)
        strict_ip_wire = strict_ip_wire_floor_bytes(row, 0)
        anchor_transport = anchor_known_component_bytes(row, 0, include_ip=False)
        anchor_ip_wire = anchor_known_component_bytes(row, 0, include_ip=True)
        five_year_strict = strict_transport * reports
        raw_exceeds_nominal = five_year_strict > included_bytes
        max_payload = _max_payload_under_tariff(row, reports, included_bytes)

        session_unresolved = str(row["security_context_lifecycle"]) in {
            "resumed_security_context",
            "full_security_context_reestablishment",
        }
        mqtt_tcp_unresolved = str(row["binding_family"]) == "mqtt_tls_tcp"

        out.append({
            "variant_id": row["variant_id"],
            "profile_id": row["profile_id"],
            "scenario_id": row["scenario_id"],
            "stack_id": row["stack_id"],
            "binding_family": row["binding_family"],
            "access_technology": row["access_technology"],
            "anchor_id": row["anchor_id"],
            "reporting_interval_s": _int(row["reporting_interval_s"]),
            "pre_lwm2m_application_payload_bytes": _int(row["application_payload_bytes"]),
            "lwm2m_payload_encoding": row["lwm2m_payload_encoding"],
            "encoded_lwm2m_payload_bytes": "",
            "encoded_lwm2m_payload_bytes_identified": False,
            "strict_transport_known_component_floor_bytes_per_report": strict_transport,
            "strict_ip_wire_known_component_floor_bytes_per_report": strict_ip_wire,
            "anchor_transport_known_component_bytes_per_report": anchor_transport,
            "anchor_ip_wire_known_component_bytes_per_report": anchor_ip_wire,
            "five_year_report_count": reports,
            "included_data_mb": included_mb,
            "included_data_bytes": included_bytes,
            "five_year_strict_transport_floor_bytes": five_year_strict,
            "five_year_strict_transport_floor_mb": five_year_strict / mb_bytes,
            "raw_nominal_allowance_status_from_strict_floor": (
                "strict_raw_transport_floor_exceeds_nominal_500mb_allowance_billing_rounding_unresolved"
                if raw_exceeds_nominal
                else "strict_raw_transport_floor_within_nominal_500mb_allowance_billing_rounding_unresolved"
            ),
            "optimistic_max_encoded_lwm2m_payload_bytes_per_report_under_strict_floor": max_payload,
            "lwm2m_serialization_delta_unresolved": True,
            "security_session_increment_unresolved": session_unresolved,
            "mqtt_pure_tcp_ack_and_segmentation_overhead_unresolved": mqtt_tcp_unresolved,
            "billing_rounding_interval_unresolved": True,
            "exact_wire_volume_ready": False,
            "tariff_topup_count_exact_ready": False,
            "canonical_report_energy_ready": False,
            "strict_floor_interpretation": (
                "One-sided minimum using only the primary LwM2M Send request/response transport components. "
                "Encoded LwM2M payload bytes are set to zero for the floor; session handshakes, MQTT pure TCP ACKs, "
                "extra QoS/control traffic, retries and billing-rounding effects are omitted."
            ),
            "anchor_accounting_interpretation": (
                "Deterministic Stage-5K sensitivity accounting with one protected application/control message per "
                "data-carrying transport episode. It is not an empirical packetisation claim and is not used for "
                "the one-sided tariff insufficiency classification."
            ),
        })
    return sorted(out, key=lambda r: (str(r["scenario_id"]), str(r["stack_id"]), str(r["anchor_id"])))


def threshold_summary_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    data = list(rows)
    grouped: dict[tuple[int, int, str, str], list[dict[str, Any]]] = {}
    for row in data:
        key = (
            int(row["reporting_interval_s"]),
            int(row["pre_lwm2m_application_payload_bytes"]),
            str(row["binding_family"]),
            str(row["anchor_id"]),
        )
        grouped.setdefault(key, []).append(row)
    out = []
    for key, grows in sorted(grouped.items()):
        values = {int(r["optimistic_max_encoded_lwm2m_payload_bytes_per_report_under_strict_floor"]) for r in grows}
        floors = {int(r["strict_transport_known_component_floor_bytes_per_report"]) for r in grows}
        if len(values) != 1 or len(floors) != 1:
            raise ValueError(f"Unexpected technology-specific Stage-5L transport floor within group {key}.")
        out.append({
            "reporting_interval_s": key[0],
            "pre_lwm2m_application_payload_bytes": key[1],
            "binding_family": key[2],
            "anchor_id": key[3],
            "strict_transport_known_component_floor_bytes_per_report": next(iter(floors)),
            "optimistic_max_encoded_lwm2m_payload_bytes_per_report_under_strict_floor": next(iter(values)),
            "candidate_rows": len(grows),
        })
    return out


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> WireAccountingSummary:
    data = list(rows)
    result = WireAccountingSummary(
        variant_rows=len(data),
        coap_variant_rows=sum(str(r["binding_family"]) == "coap_dtls_udp" for r in data),
        mqtt_variant_rows=sum(str(r["binding_family"]) == "mqtt_tls_tcp" for r in data),
        rows_with_strict_transport_floor=sum(r["strict_transport_known_component_floor_bytes_per_report"] != "" for r in data),
        rows_with_anchor_known_component_accounting=sum(r["anchor_transport_known_component_bytes_per_report"] != "" for r in data),
        rows_with_exact_wire_volume=sum(bool(r["exact_wire_volume_ready"]) for r in data),
        rows_with_unresolved_lwm2m_serialization=sum(bool(r["lwm2m_serialization_delta_unresolved"]) for r in data),
        mqtt_rows_with_unresolved_tcp_ack_segmentation=sum(bool(r["mqtt_pure_tcp_ack_and_segmentation_overhead_unresolved"]) for r in data),
        rows_with_unresolved_session_increment=sum(bool(r["security_session_increment_unresolved"]) for r in data),
        rows_where_strict_raw_transport_floor_exceeds_nominal_allowance=sum(
            r["raw_nominal_allowance_status_from_strict_floor"]
            == "strict_raw_transport_floor_exceeds_nominal_500mb_allowance_billing_rounding_unresolved"
            for r in data
        ),
        rows_where_strict_raw_transport_floor_is_within_nominal_allowance=sum(
            r["raw_nominal_allowance_status_from_strict_floor"]
            == "strict_raw_transport_floor_within_nominal_500mb_allowance_billing_rounding_unresolved"
            for r in data
        ),
    )
    for field, expected in policy.get("expected", {}).items():
        actual = getattr(result, field)
        if int(actual) != int(expected):
            raise ValueError(f"Stage-5L checkpoint mismatch for {field}: expected={expected} actual={actual}")
    return result
