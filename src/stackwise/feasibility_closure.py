from __future__ import annotations

from typing import Any


def policy_by_blocker(policy: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (str(r["scenario_id"]), str(r["stack_id"]), str(r["constraint_id"])): r
        for r in policy.get("blocker_resolution_policy") or []
    }


def freeze_decision_blockers(
    blockers: list[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    lookup = policy_by_blocker(policy)
    rows: list[dict[str, Any]] = []
    for blocker in blockers:
        key = (
            str(blocker["scenario_id"]),
            str(blocker["stack_id"]),
            str(blocker["constraint_id"]),
        )
        spec = lookup.get(key)
        if spec is None:
            raise ValueError(f"No Stage-4F policy for decision blocker {key}")
        profile_fields = list(spec.get("operating_profile_fields_required") or [])
        rows.append(
            {
                "blocker_id": spec["blocker_id"],
                "scenario_id": key[0],
                "stack_id": key[1],
                "constraint_id": key[2],
                "stage4e_status": blocker.get("overall_status"),
                "stage4f_status": spec["stage4_resolution"],
                "resolution_class": spec["resolution_class"],
                "reason": spec["reason"],
                "operating_profile_required": bool(profile_fields),
                "operating_profile_fields": "|".join(map(str, profile_fields)),
                "future_resolution_evidence": spec["future_resolution_evidence"],
                "source_authority": (spec.get("primary_support") or {}).get("authority"),
                "source_identifier": (spec.get("primary_support") or {}).get("identifier"),
                "source_url": (spec.get("primary_support") or {}).get("url"),
                "resolved_from_existing_evidence": False,
            }
        )
    return rows


def lrfhss_radio_bound_diagnostic(
    evidence_rows: list[dict[str, Any]], *, budget_j: float, scenario_payload_bytes: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in evidence_rows:
        if str(record.get("metric_id")) != "radio_incremental_transaction_energy_j":
            continue
        estimate = float(record["estimate"])
        measured_payload = int(float(record["payload_bytes"]))
        rows.append(
            {
                "data_rate_mode": record.get("data_rate_mode"),
                "confirmation_mode": record.get("confirmation_mode"),
                "measured_payload_bytes": measured_payload,
                "scenario_payload_bytes": int(scenario_payload_bytes),
                "tx_power_dbm": float(record["tx_power_dbm"]),
                "radio_incremental_transaction_energy_j": estimate,
                "whole_device_budget_j": float(budget_j),
                "measured_radio_energy_exceeds_budget": bool(estimate > budget_j),
                "payload_matches_scenario": bool(measured_payload == scenario_payload_bytes),
                "measurement_boundary": "radio_interface_only",
                "scenario_boundary": "whole_device_per_report",
                "whole_device_feasibility_resolved": False,
                "interpretation": (
                    "Profile/boundary diagnostic only. A radio-only 4-byte measurement is not a "
                    "whole-device 16-byte report-energy estimate and is not promoted to a hard fact."
                ),
            }
        )
    return sorted(rows, key=lambda r: (str(r["data_rate_mode"]), str(r["confirmation_mode"])))
