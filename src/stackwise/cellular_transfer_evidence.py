from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


READY = "ready_bridged"
BLOCKED = "blocked_external_transfer_not_absolute"


@dataclass(frozen=True)
class TransferEvidenceSummary:
    feasible_candidate_incidences: int
    canonical_target_ready_rows: int
    payload_structural_support_rows: int
    reporting_cycle_structural_support_rows: int
    exact_upper_layer_support_rows: int
    absolute_external_calibration_authorised_rows: int
    external_sources_reviewed: int


def build_transfer_admissibility_rows(
    stage5f_rows: Iterable[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    dims = policy["transfer_dimensions"]
    rows: list[dict[str, Any]] = []
    for r in stage5f_rows:
        if str(r.get("canonical_target_status")) == READY:
            raise ValueError("Stage-5G expects Stage-5F canonical target to remain blocked")
        exact_upper = bool(r.get("exact_application_context") is True or str(r.get("exact_application_context")).lower() == "true")
        absolute_authorised = False
        blockers = [
            "external_state_model_not_absolute_vomhoff_calibration",
            "modem_only_vs_vomhoff_whole_device_boundary",
            "device_specific_state_power_characterisation_required",
        ]
        if not exact_upper:
            blockers.append("candidate_upper_layer_context_not_exactly_supported")
        rows.append({
            "scenario_id": r["scenario_id"],
            "stack_id": r["stack_id"],
            "technology": r["technology"],
            "candidate_application_family": r["candidate_application_family"],
            "scenario_payload_bytes": int(r["scenario_payload_bytes"]),
            "scenario_reporting_interval_s": int(r["scenario_reporting_interval_s"]),
            "stage5f_source_reference_id": r["source_reference_id"],
            "payload_transfer_external_support": dims["payload_dependence"]["external_support"],
            "payload_numeric_candidate_transfer": dims["payload_dependence"]["numeric_candidate_transfer"],
            "report_cycle_external_support": dims["reporting_cycle_state_accounting"]["external_support"],
            "report_cycle_numeric_candidate_transfer": dims["reporting_cycle_state_accounting"]["numeric_candidate_transfer"],
            "upper_layer_external_support": "exact" if exact_upper else dims["upper_layer_protocol_context"]["external_support"],
            "absolute_boundary_support": dims["absolute_measurement_boundary"]["external_support"],
            "device_transfer_support": dims["device_hardware_transfer"]["external_support"],
            "external_absolute_calibration_authorised": absolute_authorised,
            "canonical_target_status": BLOCKED,
            "numeric_target_materialised": False,
            "blocking_reasons": "|".join(blockers),
        })
    return rows


def source_review_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in policy["external_evidence_sources"]:
        rows.append({
            "evidence_id": src["evidence_id"],
            "citation": src["citation"],
            "doi": src["doi"],
            "technologies": "|".join(src["technologies"]),
            "evidence_type": src["evidence_type"],
            "measurement_boundary": src["measurement_boundary"],
            "validation_scope": src["validation_scope"],
            "reported_model_error": src["reported_model_error"],
            "payload_dependence": src["payload_dependence"],
            "reporting_cycle_state_accounting": src["reporting_cycle_state_accounting"],
            "upper_layer_protocol_context": src["upper_layer_protocol_context"],
            "direct_absolute_transfer_to_vomhoff": src["direct_absolute_transfer_to_vomhoff"],
            "reason_direct_transfer_prohibited": src["reason_direct_transfer_prohibited"],
        })
    return rows


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> TransferEvidenceSummary:
    rows = list(rows)
    result = TransferEvidenceSummary(
        feasible_candidate_incidences=len(rows),
        canonical_target_ready_rows=sum(str(r["canonical_target_status"]) == READY for r in rows),
        payload_structural_support_rows=sum(str(r["payload_transfer_external_support"]) == "structural_support" for r in rows),
        reporting_cycle_structural_support_rows=sum(str(r["report_cycle_external_support"]) == "structural_support" for r in rows),
        exact_upper_layer_support_rows=sum(str(r["upper_layer_external_support"]) == "exact" for r in rows),
        absolute_external_calibration_authorised_rows=sum(bool(r["external_absolute_calibration_authorised"]) for r in rows),
        external_sources_reviewed=len(policy["external_evidence_sources"]),
    )
    expected = policy["expected"]
    checks = {
        "feasible_cellular_ip_candidate_incidences": result.feasible_candidate_incidences,
        "canonical_target_ready_rows": result.canonical_target_ready_rows,
        "payload_structural_support_rows": result.payload_structural_support_rows,
        "reporting_cycle_structural_support_rows": result.reporting_cycle_structural_support_rows,
        "exact_upper_layer_support_rows": result.exact_upper_layer_support_rows,
        "absolute_external_calibration_authorised_rows": result.absolute_external_calibration_authorised_rows,
        "external_sources_reviewed": result.external_sources_reviewed,
    }
    for key, value in checks.items():
        if int(expected[key]) != int(value):
            raise ValueError(f"Stage-5G expected {key}={expected[key]}, observed {value}")
    return result
