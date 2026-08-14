from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SessionControlEnvelopeSummary:
    source_serialization_rows: int
    envelope_designs: int
    envelope_rows: int
    coap_envelope_rows: int
    mqtt_envelope_rows: int
    rows_with_security_session_surrogate_increment: int
    rows_with_mqtt_tcp_ack_surrogate_increment: int
    rows_with_exact_canonical_security_session_increment: int
    rows_with_exact_canonical_tcp_ack_overhead: int
    rows_where_augmented_raw_volume_exceeds_nominal_allowance: int
    rows_where_augmented_raw_volume_is_within_nominal_allowance: int
    source_rows_exceeding_across_all_session_control_surrogates: int
    source_rows_within_across_all_session_control_surrogates: int
    source_rows_crossing_nominal_allowance_across_session_control_surrogates: int
    mqtt_tracking_source_rows_exceeding_across_all_session_control_surrogates: int
    coap_tracking_source_rows_crossing_across_session_control_surrogates: int


def _int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# TLS 1.3 / RFC 9846 PSK handshake surrogate sizing
# ---------------------------------------------------------------------------
# These helpers size deterministic benchmark handshake surrogates from the
# current TLS 1.3 message grammar. They are not packet captures, deployment
# prevalence estimates, or upper bounds. The compact design uses psk_ke with a
# short PSK identity; the expanded design uses psk_dhe_ke + X25519 and a longer
# identity. Both use TLS_AES_128_GCM_SHA256 / SHA-256-sized binders/Finished.


def tls13_psk_handshake_record_bytes(
    *,
    psk_identity_bytes: int,
    psk_dhe: bool,
    key_share_bytes: int = 32,
    hash_bytes: int = 32,
    aead_expansion_bytes: int = 16,
) -> dict[str, int]:
    if psk_identity_bytes <= 0:
        raise ValueError("PSK identity length must be positive.")
    if key_share_bytes <= 0 or hash_bytes <= 0 or aead_expansion_bytes < 0:
        raise ValueError("Invalid TLS surrogate lengths.")

    # ClientHello fixed body before extensions:
    # legacy_version(2), random(32), session_id vector length(1, empty),
    # cipher_suites vector length(2)+one suite(2), compression vector(1)+null(1),
    # extensions vector length(2) = 43 bytes.
    fixed_client_hello_body = 43
    supported_versions_client_ext = 7  # ext hdr4 + vector len1 + version2
    psk_modes_ext = 6  # ext hdr4 + vector len1 + one mode1

    identity_entry = 2 + psk_identity_bytes + 4  # opaque identity<1..2^16-1> + age
    identities_vector = 2 + identity_entry
    binder_entry = 1 + hash_bytes
    binders_vector = 2 + binder_entry
    pre_shared_key_ext = 4 + identities_vector + binders_vector

    dhe_client_extensions = 0
    if psk_dhe:
        supported_groups_ext = 8  # ext hdr4 + vector len2 + one NamedGroup2
        key_share_ext = 4 + 2 + 2 + 2 + key_share_bytes  # ext + vector + group + key len + key
        dhe_client_extensions = supported_groups_ext + key_share_ext

    client_extensions = supported_versions_client_ext + psk_modes_ext + pre_shared_key_ext + dhe_client_extensions
    client_hello_body = fixed_client_hello_body + client_extensions
    client_hello_record = 5 + 4 + client_hello_body  # TLSPlaintext hdr + Handshake hdr + body

    # ServerHello fixed body before extensions: 40 bytes.
    fixed_server_hello_body = 40
    supported_versions_server_ext = 6  # ext hdr4 + selected version2
    selected_psk_ext = 6  # ext hdr4 + selected_identity uint16
    dhe_server_extensions = 0
    if psk_dhe:
        key_share_server_ext = 4 + 2 + 2 + key_share_bytes  # ext + group + key len + key
        dhe_server_extensions = key_share_server_ext
    server_extensions = supported_versions_server_ext + selected_psk_ext + dhe_server_extensions
    server_hello_body = fixed_server_hello_body + server_extensions
    server_hello_record = 5 + 4 + server_hello_body

    # EncryptedExtensions body is an empty extensions vector (2 bytes). Finished
    # body equals Hash.length. The two handshake messages are coalesced in one
    # encrypted record for this surrogate.
    encrypted_extensions_hs = 4 + 2
    server_finished_hs = 4 + hash_bytes
    server_encrypted_flight_record = (
        5 + encrypted_extensions_hs + server_finished_hs + 1 + aead_expansion_bytes
    )
    client_finished_record = 5 + 4 + hash_bytes + 1 + aead_expansion_bytes

    total = client_hello_record + server_hello_record + server_encrypted_flight_record + client_finished_record
    return {
        "client_hello_record_bytes": client_hello_record,
        "server_hello_record_bytes": server_hello_record,
        "server_encrypted_flight_record_bytes": server_encrypted_flight_record,
        "client_finished_record_bytes": client_finished_record,
        "tls_handshake_record_bytes": total,
        "tls_data_carrying_segments": 4,
    }


# ---------------------------------------------------------------------------
# DTLS 1.3 / RFC 9147 PSK handshake surrogate sizing
# ---------------------------------------------------------------------------


def dtls13_psk_handshake_transport_bytes(
    *,
    psk_identity_bytes: int,
    psk_dhe: bool,
    unified_header_bytes: int,
    server_flight_combined_datagram: bool,
    key_share_bytes: int = 32,
    hash_bytes: int = 32,
    aead_expansion_bytes: int = 16,
) -> dict[str, int]:
    if unified_header_bytes <= 0:
        raise ValueError("DTLS unified-header length must be positive.")

    # Reuse the TLS extension/body arithmetic, then adapt the framing. DTLS
    # ClientHello adds an empty legacy_cookie vector length byte. DTLS handshake
    # headers are 12 bytes rather than TLS's 4 bytes. Epoch-0 plaintext records
    # use the fixed 13-byte DTLSPlaintext header.
    tls = tls13_psk_handshake_record_bytes(
        psk_identity_bytes=psk_identity_bytes,
        psk_dhe=psk_dhe,
        key_share_bytes=key_share_bytes,
        hash_bytes=hash_bytes,
        aead_expansion_bytes=aead_expansion_bytes,
    )
    tls_ch_body = tls["client_hello_record_bytes"] - 5 - 4
    tls_sh_body = tls["server_hello_record_bytes"] - 5 - 4
    dtls_ch_body = tls_ch_body + 1  # empty legacy_cookie vector length
    dtls_sh_body = tls_sh_body

    client_hello_record = 13 + 12 + dtls_ch_body
    server_hello_record = 13 + 12 + dtls_sh_body

    protected_overhead = unified_header_bytes + 1 + aead_expansion_bytes
    server_encrypted_flight_record = (12 + 2) + (12 + hash_bytes) + protected_overhead
    client_finished_record = (12 + hash_bytes) + protected_overhead

    # RFC 9147 ACK carries a vector of RecordNumber values. The benchmark ACK
    # acknowledges one record from the client's final flight: uint16 vector
    # length + one 128-bit RecordNumber.
    ack_content = 2 + 16
    final_ack_record = ack_content + protected_overhead

    record_bytes = (
        client_hello_record
        + server_hello_record
        + server_encrypted_flight_record
        + client_finished_record
        + final_ack_record
    )
    # Compact surrogate coalesces ServerHello + encrypted server flight into one
    # UDP datagram. Expanded surrogate keeps them separate. ClientHello, client
    # Finished and final ACK each occupy their own datagram.
    datagrams = 4 if server_flight_combined_datagram else 5
    udp_headers = datagrams * 8
    return {
        "client_hello_record_bytes": client_hello_record,
        "server_hello_record_bytes": server_hello_record,
        "server_encrypted_flight_record_bytes": server_encrypted_flight_record,
        "client_finished_record_bytes": client_finished_record,
        "final_ack_record_bytes": final_ack_record,
        "dtls_record_bytes": record_bytes,
        "udp_datagrams": datagrams,
        "dtls_handshake_transport_bytes": record_bytes + udp_headers,
    }


# ---------------------------------------------------------------------------
# MQTT/TCP deterministic connection/control surrogates
# ---------------------------------------------------------------------------


def mqtt5_minimal_connect_packet_bytes(client_id_bytes: int) -> int:
    if client_id_bytes < 0:
        raise ValueError("MQTT ClientID length must be non-negative.")
    # MQTT 5 CONNECT, no Will/User/Password/properties:
    # Variable header = Protocol Name(6) + Level(1) + Flags(1) + KeepAlive(2)
    # + Properties Length(1) = 11. Payload = UTF-8 ClientID length(2)+value.
    remaining = 11 + 2 + client_id_bytes
    # All Stage-5N ClientIDs are small enough for one-byte Remaining Length.
    if remaining > 127:
        raise ValueError("Stage-5N minimal CONNECT helper currently expects Remaining Length <=127.")
    return 1 + 1 + remaining


def mqtt5_minimal_connack_packet_bytes() -> int:
    # CONNACK remaining length 3: Connect Ack Flags, Success reason, zero property length.
    return 5


def _mqtt_anchor_data_segment_count(row: dict[str, Any]) -> int:
    # Mirrors Stage-5L's convention: one MQTT control packet per protected TLS
    # record / data-carrying TCP segment.
    qos = _int(row["mqtt_qos"])
    if qos == 0:
        app_packets = 2
    elif qos == 1:
        app_packets = 4
    elif qos == 2:
        app_packets = 8
    else:
        raise ValueError(f"Unsupported MQTT QoS: {qos}")

    keep_alive = _int(row["mqtt_keep_alive_s"])
    interval = _int(row["reporting_interval_s"])
    ping_pairs = max(0, ((interval + keep_alive - 1) // keep_alive) - 1) if keep_alive > 0 else 0
    total = app_packets + 2 * ping_pairs

    if str(row["failure_retry_retransmission_profile"]) == "one_full_transaction_retry_per_application_report":
        total += app_packets
    return total


def _tcp_header_bytes(row: dict[str, Any]) -> int:
    return 20 + _int(row["tcp_header_options_bytes"])


def _tls_app_record_overhead(row: dict[str, Any]) -> int:
    return 5 + 1 + _int(row["tls_padding_bytes"]) + _int(row["tls_aead_expansion_bytes"])


def _new_tcp_connection_increment_bytes(row: dict[str, Any]) -> int:
    # Synthetic 3-way handshake: SYN, SYN-ACK, ACK. TCP options use the current
    # Stage-5K anchor value; no IP bytes are included, matching Stage 5L tariff
    # transport accounting.
    return 3 * _tcp_header_bytes(row)


def _mqtt_connect_control_increment_bytes(row: dict[str, Any]) -> int:
    client_id = _int(row["mqtt_endpoint_name_bytes"])
    connect = mqtt5_minimal_connect_packet_bytes(client_id)
    connack = mqtt5_minimal_connack_packet_bytes()
    protected = connect + connack + 2 * _tls_app_record_overhead(row)
    tcp = 2 * _tcp_header_bytes(row)
    return protected + tcp


def _tls_security_increment_bytes(row: dict[str, Any], design: dict[str, Any]) -> tuple[int, int]:
    hs = tls13_psk_handshake_record_bytes(
        psk_identity_bytes=int(design["psk_identity_bytes"]),
        psk_dhe=bool(design["psk_dhe"]),
        key_share_bytes=int(design.get("x25519_key_share_bytes", 32)),
        hash_bytes=int(design.get("sha256_hash_bytes", 32)),
        aead_expansion_bytes=int(design.get("aead_expansion_bytes", 16)),
    )
    tcp = hs["tls_data_carrying_segments"] * _tcp_header_bytes(row)
    return hs["tls_handshake_record_bytes"] + tcp, hs["tls_data_carrying_segments"]


def _dtls_security_increment_bytes(row: dict[str, Any], design: dict[str, Any]) -> int:
    hs = dtls13_psk_handshake_transport_bytes(
        psk_identity_bytes=int(design["psk_identity_bytes"]),
        psk_dhe=bool(design["psk_dhe"]),
        unified_header_bytes=int(design["dtls_unified_header_bytes"]),
        server_flight_combined_datagram=bool(design["dtls_server_flight_combined_datagram"]),
        key_share_bytes=int(design.get("x25519_key_share_bytes", 32)),
        hash_bytes=int(design.get("sha256_hash_bytes", 32)),
        aead_expansion_bytes=int(design.get("aead_expansion_bytes", 16)),
    )
    return hs["dtls_handshake_transport_bytes"]


def build_session_control_envelope_rows(
    serialization_rows: Iterable[dict[str, Any]],
    variants: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    variants_by_id = {str(r["variant_id"]): r for r in variants}
    mb_bytes = int(policy["scientific_policy"]["tariff_megabyte_definition_bytes"])
    out: list[dict[str, Any]] = []

    for source in serialization_rows:
        variant = variants_by_id[str(source["variant_id"])]
        binding = str(source["binding_family"])
        lifecycle = str(variant["security_context_lifecycle"])
        needs_security_session = lifecycle in {"resumed_security_context", "full_security_context_reestablishment"}
        base_anchor = _int(source["anchor_transport_bytes_per_report_with_surrogate"])
        reports = _int(source["five_year_report_count"])
        included_bytes = _int(source["included_data_bytes"])

        for design in policy["session_control_envelope_designs"]:
            design_id = str(design["envelope_id"])
            security_increment = 0
            tcp_connection_increment = 0
            mqtt_connect_increment = 0
            tcp_ack_increment = 0
            mqtt_data_segments = 0
            session_data_segments = 0
            security_semantics = "persistent_no_security_handshake_increment"

            if needs_security_session:
                if lifecycle == "resumed_security_context":
                    security_semantics = "tls_dtls_psk_resumption_surrogate"
                else:
                    security_semantics = "tls_dtls_external_psk_full_reestablishment_surrogate"

                if binding == "coap_dtls_udp":
                    security_increment = _dtls_security_increment_bytes(variant, design)
                elif binding == "mqtt_tls_tcp":
                    tls_increment, session_data_segments = _tls_security_increment_bytes(variant, design)
                    security_increment = tls_increment
                    tcp_connection_increment = _new_tcp_connection_increment_bytes(variant)
                    mqtt_connect_increment = _mqtt_connect_control_increment_bytes(variant)
                else:
                    raise ValueError(f"Unsupported Stage-5N binding: {binding}")

            if binding == "mqtt_tls_tcp":
                mqtt_data_segments = _mqtt_anchor_data_segment_count(variant)
                if bool(design["one_pure_tcp_ack_per_modeled_data_segment"]):
                    # Expanded deterministic ACK-only anchor. It is not an upper bound:
                    # delayed/cumulative/piggybacked ACKs can reduce count, while real
                    # segmentation/retransmission can increase it.
                    acked_segments = mqtt_data_segments
                    if needs_security_session:
                        acked_segments += session_data_segments + 2  # TLS handshake records + CONNECT/CONNACK
                    tcp_ack_increment = acked_segments * _tcp_header_bytes(variant)

            augmented = (
                base_anchor
                + security_increment
                + tcp_connection_increment
                + mqtt_connect_increment
                + tcp_ack_increment
            )
            five_year_bytes = augmented * reports
            exceeds = five_year_bytes > included_bytes

            out.append({
                "session_control_row_id": f"{source['serialization_row_id']}__{design_id}",
                "serialization_row_id": source["serialization_row_id"],
                "variant_id": source["variant_id"],
                "profile_id": source["profile_id"],
                "scenario_id": source["scenario_id"],
                "stack_id": source["stack_id"],
                "binding_family": binding,
                "access_technology": source["access_technology"],
                "anchor_id": source["anchor_id"],
                "shape_id": source["shape_id"],
                "lwm2m_payload_encoding": source["lwm2m_payload_encoding"],
                "serialized_lwm2m_payload_bytes": _int(source["serialized_lwm2m_payload_bytes"]),
                "envelope_id": design_id,
                "envelope_semantics": design["semantics"],
                "envelope_probability": "",
                "envelope_weight": "",
                "security_context_lifecycle": lifecycle,
                "security_session_semantics": security_semantics,
                "psk_identity_bytes": int(design["psk_identity_bytes"]),
                "psk_dhe": bool(design["psk_dhe"]),
                "base_anchor_transport_bytes_per_report_with_surrogate": base_anchor,
                "security_session_surrogate_increment_bytes_per_report": security_increment,
                "tcp_connection_surrogate_increment_bytes_per_report": tcp_connection_increment,
                "mqtt_connect_connack_surrogate_increment_bytes_per_report": mqtt_connect_increment,
                "mqtt_modeled_data_carrying_segments_per_report": mqtt_data_segments,
                "mqtt_pure_tcp_ack_surrogate_increment_bytes_per_report": tcp_ack_increment,
                "session_control_augmented_transport_bytes_per_report": augmented,
                "five_year_report_count": reports,
                "included_data_bytes": included_bytes,
                "five_year_session_control_augmented_transport_bytes": five_year_bytes,
                "five_year_session_control_augmented_transport_mb": five_year_bytes / mb_bytes,
                "raw_nominal_allowance_status_from_session_control_surrogate": (
                    "session_control_surrogate_raw_volume_exceeds_nominal_500mb_allowance_billing_rounding_unresolved"
                    if exceeds
                    else "session_control_surrogate_raw_volume_within_nominal_500mb_allowance_billing_rounding_unresolved"
                ),
                "security_session_surrogate_materialised": needs_security_session,
                "canonical_security_session_increment_identified": False,
                "mqtt_tcp_ack_surrogate_materialised": binding == "mqtt_tls_tcp",
                "canonical_mqtt_tcp_ack_segmentation_identified": False,
                "canonical_application_serialization_identified": False,
                "billing_rounding_interval_unresolved": True,
                "exact_billed_volume_ready": False,
                "tariff_topup_count_exact_ready": False,
                "canonical_report_energy_ready": False,
                "publication_mcda_authorised": False,
            })

    return sorted(
        out,
        key=lambda r: (
            str(r["scenario_id"]),
            str(r["stack_id"]),
            str(r["anchor_id"]),
            str(r["shape_id"]),
            str(r["envelope_id"]),
        ),
    )


def source_row_robustness_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["serialization_row_id"]), []).append(row)

    out: list[dict[str, Any]] = []
    for source_id, grows in sorted(grouped.items()):
        statuses = ["exceeds" in str(r["raw_nominal_allowance_status_from_session_control_surrogate"]) for r in grows]
        if all(statuses):
            classification = "exceeds_across_all_session_control_surrogates"
        elif not any(statuses):
            classification = "within_across_all_session_control_surrogates"
        else:
            classification = "crosses_nominal_allowance_across_session_control_surrogates"
        first = grows[0]
        values = [float(r["five_year_session_control_augmented_transport_mb"]) for r in grows]
        out.append({
            "serialization_row_id": source_id,
            "scenario_id": first["scenario_id"],
            "stack_id": first["stack_id"],
            "binding_family": first["binding_family"],
            "anchor_id": first["anchor_id"],
            "shape_id": first["shape_id"],
            "session_control_surrogate_designs": len(grows),
            "min_five_year_augmented_transport_mb": min(values),
            "max_five_year_augmented_transport_mb": max(values),
            "session_control_allowance_robustness_class": classification,
            "probability_interpretation": False,
        })
    return out


def handshake_reference_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for design in policy["session_control_envelope_designs"]:
        tls = tls13_psk_handshake_record_bytes(
            psk_identity_bytes=int(design["psk_identity_bytes"]),
            psk_dhe=bool(design["psk_dhe"]),
            key_share_bytes=int(design.get("x25519_key_share_bytes", 32)),
            hash_bytes=int(design.get("sha256_hash_bytes", 32)),
            aead_expansion_bytes=int(design.get("aead_expansion_bytes", 16)),
        )
        dtls = dtls13_psk_handshake_transport_bytes(
            psk_identity_bytes=int(design["psk_identity_bytes"]),
            psk_dhe=bool(design["psk_dhe"]),
            unified_header_bytes=int(design["dtls_unified_header_bytes"]),
            server_flight_combined_datagram=bool(design["dtls_server_flight_combined_datagram"]),
            key_share_bytes=int(design.get("x25519_key_share_bytes", 32)),
            hash_bytes=int(design.get("sha256_hash_bytes", 32)),
            aead_expansion_bytes=int(design.get("aead_expansion_bytes", 16)),
        )
        rows.append({
            "envelope_id": design["envelope_id"],
            "psk_identity_bytes": int(design["psk_identity_bytes"]),
            "psk_dhe": bool(design["psk_dhe"]),
            **{f"tls_{key}": value for key, value in tls.items()},
            **{f"dtls_{key}": value for key, value in dtls.items()},
            "normative_exact_deployment_trace": False,
            "interpretation": (
                "Deterministic PSK handshake size surrogate derived from RFC 9846/RFC 9147 grammar; "
                "credential identity length, key-exchange mode and DTLS packing are sensitivity anchors, not observed prevalence."
            ),
        })
    return rows


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> SessionControlEnvelopeSummary:
    data = list(rows)
    robust = source_row_robustness_rows(data)
    result = SessionControlEnvelopeSummary(
        source_serialization_rows=len({str(r["serialization_row_id"]) for r in data}),
        envelope_designs=len({str(r["envelope_id"]) for r in data}),
        envelope_rows=len(data),
        coap_envelope_rows=sum(str(r["binding_family"]) == "coap_dtls_udp" for r in data),
        mqtt_envelope_rows=sum(str(r["binding_family"]) == "mqtt_tls_tcp" for r in data),
        rows_with_security_session_surrogate_increment=sum(
            _int(r["security_session_surrogate_increment_bytes_per_report"]) > 0 for r in data
        ),
        rows_with_mqtt_tcp_ack_surrogate_increment=sum(
            _int(r["mqtt_pure_tcp_ack_surrogate_increment_bytes_per_report"]) > 0 for r in data
        ),
        rows_with_exact_canonical_security_session_increment=sum(
            _bool(r["canonical_security_session_increment_identified"]) for r in data
        ),
        rows_with_exact_canonical_tcp_ack_overhead=sum(
            _bool(r["canonical_mqtt_tcp_ack_segmentation_identified"]) for r in data
        ),
        rows_where_augmented_raw_volume_exceeds_nominal_allowance=sum(
            "exceeds" in str(r["raw_nominal_allowance_status_from_session_control_surrogate"]) for r in data
        ),
        rows_where_augmented_raw_volume_is_within_nominal_allowance=sum(
            "within" in str(r["raw_nominal_allowance_status_from_session_control_surrogate"]) for r in data
        ),
        source_rows_exceeding_across_all_session_control_surrogates=sum(
            r["session_control_allowance_robustness_class"] == "exceeds_across_all_session_control_surrogates"
            for r in robust
        ),
        source_rows_within_across_all_session_control_surrogates=sum(
            r["session_control_allowance_robustness_class"] == "within_across_all_session_control_surrogates"
            for r in robust
        ),
        source_rows_crossing_nominal_allowance_across_session_control_surrogates=sum(
            r["session_control_allowance_robustness_class"] == "crosses_nominal_allowance_across_session_control_surrogates"
            for r in robust
        ),
        mqtt_tracking_source_rows_exceeding_across_all_session_control_surrogates=sum(
            str(r["binding_family"]) == "mqtt_tls_tcp"
            and "asset_tracking" in str(r["scenario_id"])
            and r["session_control_allowance_robustness_class"] == "exceeds_across_all_session_control_surrogates"
            for r in robust
        ),
        coap_tracking_source_rows_crossing_across_session_control_surrogates=sum(
            str(r["binding_family"]) == "coap_dtls_udp"
            and "asset_tracking" in str(r["scenario_id"])
            and r["session_control_allowance_robustness_class"] == "crosses_nominal_allowance_across_session_control_surrogates"
            for r in robust
        ),
    )
    for field, expected in policy.get("expected", {}).items():
        actual = getattr(result, field)
        if int(actual) != int(expected):
            raise ValueError(f"Stage-5N checkpoint mismatch for {field}: expected={expected} actual={actual}")
    return result
