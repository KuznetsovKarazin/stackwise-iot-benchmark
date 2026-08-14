from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.wire_accounting import (
    audit_summary,
    build_wire_accounting_rows,
    threshold_summary_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5l_wire_volume_accounting"


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
    policy_path = ROOT / "datasets/stage5l_wire_volume_accounting.yml"
    variants_path = ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv"
    stage5i_path = ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv"

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    variants = _read_csv(variants_path)
    stage5i = _read_csv(stage5i_path)

    rows = build_wire_accounting_rows(variants, stage5i, policy)
    thresholds = threshold_summary_rows(rows)
    summary = audit_summary(rows, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    accounting_path = OUT / "wire_volume_accounting.csv"
    threshold_path = OUT / "raw_nominal_allowance_payload_thresholds.csv"
    standards_path = OUT / "standards_accounting_ledger.csv"
    _write_csv(accounting_path, rows)
    _write_csv(threshold_path, thresholds)
    _write_csv(standards_path, [dict(x) for x in policy.get("standards_evidence", [])])

    by_scenario_binding: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (str(row["scenario_id"]), str(row["binding_family"]))
        bucket = by_scenario_binding.setdefault(key, {"rows": 0, "raw_floor_exceeds_nominal_allowance": 0})
        bucket["rows"] += 1
        bucket["raw_floor_exceeds_nominal_allowance"] += (
            row["raw_nominal_allowance_status_from_strict_floor"]
            == "strict_raw_transport_floor_exceeds_nominal_500mb_allowance_billing_rounding_unresolved"
        )

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "raw_floor_exceedance_by_scenario_and_binding": [
            {
                "scenario_id": key[0],
                "binding_family": key[1],
                **value,
            }
            for key, value in sorted(by_scenario_binding.items())
        ],
        "exact_wire_volume_materialised": False,
        "exact_billed_volume_materialised": False,
        "exact_tariff_topup_count_materialised": False,
        "canonical_report_energy_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 5L materialises standards-based known-component byte accounting for all 90 Stage-5K variants "
            "without equating the 64/200-byte pre-LwM2M benchmark payload to a serialized LwM2M representation. "
            "A strict primary-exchange transport floor and a deterministic anchor accounting are reported separately. "
            "For 27 MQTT/TLS tracking variants, the strict raw transport-component floor alone exceeds the nominal "
            "500-MB allowance over five years; because the source billing aggregation interval for nearest-1-kByte "
            "measurement is unresolved, this remains a raw-volume warning rather than an exact billed-volume or TopUp claim."
        ),
        "preferred_next_step": (
            "stage5m_lwm2m_payload_serialization_contract_and_session_increment_envelopes_before_exact_tariff_or_energy_transfer"
        ),
        "accounting_artifact": "results/validation/stage5l_wire_volume_accounting/wire_volume_accounting.csv",
        "payload_threshold_artifact": "results/validation/stage5l_wire_volume_accounting/raw_nominal_allowance_payload_thresholds.csv",
        "standards_artifact": "results/validation/stage5l_wire_volume_accounting/standards_accounting_ledger.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_wire_volume_accounting.py",
        inputs=[policy_path, variants_path, stage5i_path],
        outputs=[accounting_path, threshold_path, standards_path, summary_path],
        parameters={
            "pre_lwm2m_payload_silently_equated_to_serialized_payload": False,
            "exact_wire_volume_materialised": False,
            "exact_billed_volume_materialised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5L wire-volume accounting audit: OK")
    print(f"Variant rows / CoAP / MQTT: {summary.variant_rows} / {summary.coap_variant_rows} / {summary.mqtt_variant_rows}")
    print(
        "Rows with strict floor / anchor accounting / exact wire volume: "
        f"{summary.rows_with_strict_transport_floor} / {summary.rows_with_anchor_known_component_accounting} / {summary.rows_with_exact_wire_volume}"
    )
    print(
        "Unresolved LwM2M serialization / MQTT TCP ACK-segmentation / session increment rows: "
        f"{summary.rows_with_unresolved_lwm2m_serialization} / {summary.mqtt_rows_with_unresolved_tcp_ack_segmentation} / {summary.rows_with_unresolved_session_increment}"
    )
    print(
        "Strict raw transport floor exceeds / is within nominal 500-MB allowance: "
        f"{summary.rows_where_strict_raw_transport_floor_exceeds_nominal_allowance} / "
        f"{summary.rows_where_strict_raw_transport_floor_is_within_nominal_allowance}"
    )
    for key, value in sorted(by_scenario_binding.items()):
        if value["raw_floor_exceeds_nominal_allowance"]:
            print(
                f"Raw-floor exceedance: {key[0]} / {key[1]} = "
                f"{value['raw_floor_exceeds_nominal_allowance']} of {value['rows']} variants"
            )


if __name__ == "__main__":
    main()
