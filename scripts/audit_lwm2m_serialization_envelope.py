from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.lwm2m_serialization import (
    audit_summary,
    build_serialization_envelope_rows,
    serialization_size_table,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5m_lwm2m_serialization_envelope"


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
    policy_path = ROOT / "datasets/stage5m_lwm2m_serialization_envelope.yml"
    variants_path = ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv"
    wire_path = ROOT / "results/validation/stage5l_wire_volume_accounting/wire_volume_accounting.csv"

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    variants = _read_csv(variants_path)
    wire_rows = _read_csv(wire_path)

    size_rows = serialization_size_table(policy)
    envelope_rows = build_serialization_envelope_rows(variants, wire_rows, policy)
    summary = audit_summary(envelope_rows, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    sizes_path = OUT / "serialization_size_table.csv"
    envelope_path = OUT / "serialization_surrogate_envelope.csv"
    standards_path = OUT / "standards_serialization_ledger.csv"
    _write_csv(sizes_path, size_rows)
    _write_csv(envelope_path, envelope_rows)
    _write_csv(standards_path, [dict(x) for x in policy.get("standards_evidence", [])])

    by_shape_binding_scenario: dict[tuple[str, str, str], dict[str, int]] = {}
    for row in envelope_rows:
        key = (str(row["shape_id"]), str(row["scenario_id"]), str(row["binding_family"]))
        bucket = by_shape_binding_scenario.setdefault(key, {"rows": 0, "strict_exceeds": 0, "anchor_exceeds": 0})
        bucket["rows"] += 1
        bucket["strict_exceeds"] += "exceeds" in str(row["strict_surrogate_raw_nominal_allowance_status"])
        bucket["anchor_exceeds"] += "exceeds" in str(row["anchor_surrogate_raw_nominal_allowance_status"])

    classification_rows = [
        {
            "shape_id": key[0],
            "scenario_id": key[1],
            "binding_family": key[2],
            **value,
        }
        for key, value in sorted(by_shape_binding_scenario.items())
    ]
    classification_path = OUT / "surrogate_allowance_classification.csv"
    _write_csv(classification_path, classification_rows)

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "exact_surrogate_serialization_materialised": True,
        "canonical_application_serialization_materialised": False,
        "exact_billed_volume_materialised": False,
        "exact_tariff_topup_count_materialised": False,
        "security_session_increment_materialised": False,
        "canonical_report_energy_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 5M replaces the zero-payload serialization placeholder with exact byte lengths only for two "
            "explicit synthetic Opaque-Resource surrogates under OMA test Object ID 42769. The one-resource and "
            "three-resource shapes preserve the 64/200-byte pre-LwM2M application payload as binary octets but do "
            "not claim to reconstruct a real application object model. All MQTT/TLS 60-s tracking surrogate rows "
            "remain above the nominal 500-MB raw transport allowance at the strict primary-exchange layer. For "
            "CoAP/DTLS tracking, the three-resource SenML-JSON surrogate crosses the nominal raw allowance while "
            "the corresponding single-resource surrogate remains below it, demonstrating real serialization-shape "
            "sensitivity. Billing rounding, security-session increments, MQTT pure TCP ACK/segmentation and the "
            "canonical application resource model remain unresolved."
        ),
        "preferred_next_step": (
            "stage5n_security_session_increment_envelopes_and_mqtt_tcp_ack_bounds_before_cost_finalisation"
        ),
        "size_table_artifact": "results/validation/stage5m_lwm2m_serialization_envelope/serialization_size_table.csv",
        "envelope_artifact": "results/validation/stage5m_lwm2m_serialization_envelope/serialization_surrogate_envelope.csv",
        "classification_artifact": "results/validation/stage5m_lwm2m_serialization_envelope/surrogate_allowance_classification.csv",
        "standards_artifact": "results/validation/stage5m_lwm2m_serialization_envelope/standards_serialization_ledger.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_lwm2m_serialization_envelope.py",
        inputs=[policy_path, variants_path, wire_path],
        outputs=[sizes_path, envelope_path, classification_path, standards_path, summary_path],
        parameters={
            "synthetic_test_object_id": policy["scientific_policy"]["synthetic_test_object_id"],
            "surrogate_shapes": len(policy["serialization_surrogates"]),
            "canonical_application_model_inferred": False,
            "security_session_increment_materialised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5M LwM2M serialization-envelope audit: OK")
    print(
        "Source variants / surrogate shapes / serialization rows: "
        f"{summary.source_variant_rows} / {summary.surrogate_shape_designs} / {summary.serialization_rows}"
    )
    print(
        "LwM2M-CBOR / SenML-CBOR / SenML-JSON rows: "
        f"{summary.lwm2m_cbor_rows} / {summary.senml_cbor_rows} / {summary.senml_json_rows}"
    )
    print(
        "Exact surrogate / canonical application serialization rows: "
        f"{summary.rows_with_exact_surrogate_serialization} / {summary.rows_with_canonical_application_serialization}"
    )
    print(
        "Strict surrogate raw volume exceeds / is within nominal 500-MB allowance: "
        f"{summary.rows_where_strict_surrogate_raw_volume_exceeds_nominal_allowance} / "
        f"{summary.rows_where_strict_surrogate_raw_volume_is_within_nominal_allowance}"
    )
    print(
        "Anchor surrogate raw volume exceeds / is within nominal 500-MB allowance: "
        f"{summary.rows_where_anchor_surrogate_raw_volume_exceeds_nominal_allowance} / "
        f"{summary.rows_where_anchor_surrogate_raw_volume_is_within_nominal_allowance}"
    )
    print(
        "MQTT tracking strict exceedance rows / CoAP tracking three-resource SenML-JSON strict exceedance rows: "
        f"{summary.mqtt_tracking_rows_strictly_exceeding_nominal_allowance} / "
        f"{summary.coap_tracking_three_resource_senml_json_rows_strictly_exceeding_nominal_allowance}"
    )


if __name__ == "__main__":
    main()
