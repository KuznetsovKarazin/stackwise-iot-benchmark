from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.session_control_envelope import (
    audit_summary,
    build_session_control_envelope_rows,
    handshake_reference_rows,
    source_row_robustness_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5n_security_session_control_envelope"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy_path = ROOT / "datasets/stage5n_security_session_control_envelope.yml"
    variants_path = ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv"
    serialization_path = ROOT / "results/validation/stage5m_lwm2m_serialization_envelope/serialization_surrogate_envelope.csv"

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    variants = _read_csv(variants_path)
    serialization_rows = _read_csv(serialization_path)

    envelope_rows = build_session_control_envelope_rows(serialization_rows, variants, policy)
    robustness_rows = source_row_robustness_rows(envelope_rows)
    handshake_rows = handshake_reference_rows(policy)
    summary = audit_summary(envelope_rows, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    envelope_path = OUT / "session_control_envelope.csv"
    robustness_path = OUT / "session_control_allowance_robustness.csv"
    handshake_path = OUT / "psk_handshake_reference_sizes.csv"
    standards_path = OUT / "standards_session_control_ledger.csv"
    _write_csv(envelope_path, envelope_rows)
    _write_csv(robustness_path, robustness_rows)
    _write_csv(handshake_path, handshake_rows)
    _write_csv(standards_path, [dict(x) for x in policy.get("standards_evidence", [])])

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "canonical_security_session_increment_materialised": False,
        "canonical_mqtt_tcp_ack_segmentation_materialised": False,
        "exact_billed_volume_materialised": False,
        "exact_tariff_topup_count_materialised": False,
        "canonical_report_energy_materialised": False,
        "publication_mcda_authorised": False,
        "transport_accounting_detail_freeze_after_stage5n": bool(
            policy["scientific_policy"]["post_stage5n_transport_detail_freeze"]
        ),
        "interpretation": (
            "Stage 5N closes the planned transport/accounting refinement sequence with two deterministic, "
            "standards-bounded session/control surrogates. PSK session handshakes are sized from current TLS 1.3 "
            "and DTLS 1.3 grammar; MQTT new-connection CONNECT/CONNACK and a zero-versus-one standalone TCP ACK "
            "sensitivity are materialised. These are not empirical packet traces, probability bounds, or canonical "
            "billing volumes. Certificate/RPK credential modes, implementation packetisation, retransmission beyond "
            "the Stage-5K anchors and tariff rounding remain outside the compact envelope. No byte count is converted "
            "to report energy, and publication MCDA remains blocked until the first decision-ready slice is consolidated."
        ),
        "preferred_next_step": "stage6a_first_decision_ready_slice_consolidation_no_new_transport_detail_without_material_error",
        "envelope_artifact": "results/validation/stage5n_security_session_control_envelope/session_control_envelope.csv",
        "robustness_artifact": "results/validation/stage5n_security_session_control_envelope/session_control_allowance_robustness.csv",
        "handshake_reference_artifact": "results/validation/stage5n_security_session_control_envelope/psk_handshake_reference_sizes.csv",
        "standards_artifact": "results/validation/stage5n_security_session_control_envelope/standards_session_control_ledger.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_security_session_control_envelope.py",
        inputs=[policy_path, variants_path, serialization_path],
        outputs=[envelope_path, robustness_path, handshake_path, standards_path, summary_path],
        parameters={
            "envelope_designs": len(policy["session_control_envelope_designs"]),
            "canonical_security_session_increment_materialised": False,
            "canonical_mqtt_tcp_ack_segmentation_materialised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5N security-session/control envelope audit: OK")
    print(
        "Source serialization rows / envelope designs / envelope rows: "
        f"{summary.source_serialization_rows} / {summary.envelope_designs} / {summary.envelope_rows}"
    )
    print(
        "CoAP/DTLS / MQTT/TLS envelope rows: "
        f"{summary.coap_envelope_rows} / {summary.mqtt_envelope_rows}"
    )
    print(
        "Rows with security-session / MQTT TCP-ACK surrogate increments: "
        f"{summary.rows_with_security_session_surrogate_increment} / "
        f"{summary.rows_with_mqtt_tcp_ack_surrogate_increment}"
    )
    print(
        "Canonical security-session / TCP-ACK rows: "
        f"{summary.rows_with_exact_canonical_security_session_increment} / "
        f"{summary.rows_with_exact_canonical_tcp_ack_overhead}"
    )
    print(
        "Augmented raw-volume rows exceeding / within nominal 500-MB allowance: "
        f"{summary.rows_where_augmented_raw_volume_exceeds_nominal_allowance} / "
        f"{summary.rows_where_augmented_raw_volume_is_within_nominal_allowance}"
    )
    print(
        "Source rows robust-exceed / robust-within / session-control-sensitive: "
        f"{summary.source_rows_exceeding_across_all_session_control_surrogates} / "
        f"{summary.source_rows_within_across_all_session_control_surrogates} / "
        f"{summary.source_rows_crossing_nominal_allowance_across_session_control_surrogates}"
    )
    print(
        "MQTT tracking robust-exceed source rows / CoAP tracking session-control-sensitive source rows: "
        f"{summary.mqtt_tracking_source_rows_exceeding_across_all_session_control_surrogates} / "
        f"{summary.coap_tracking_source_rows_crossing_across_session_control_surrogates}"
    )


if __name__ == "__main__":
    main()
