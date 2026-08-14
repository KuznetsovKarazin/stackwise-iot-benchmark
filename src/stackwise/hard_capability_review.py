from __future__ import annotations

import copy
from typing import Any

from .scenario_screening import derive_candidate_hard_capabilities


def claim_by_access(policy: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(c["access_family"]), str(c["capability_key"])): c
        for c in policy.get("capability_claims") or []
    }


def access_variant(stack_id: str) -> str:
    if stack_id.startswith("nbiot_"):
        return "NB-IoT"
    if stack_id.startswith("ltem_"):
        return "LTE-M"
    if stack_id.startswith("lorawan_lora_"):
        return "LoRaWAN-LoRa"
    if stack_id.startswith("lorawan_lrfhss_"):
        return "LoRaWAN-LR-FHSS"
    if stack_id.startswith("thread_"):
        return "Thread"
    return "other"


def overlay_reviewed_capabilities(
    stack: dict[str, Any], catalog: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    out = derive_candidate_hard_capabilities(stack, catalog)
    out["idle_cell_reselection_supported_verified"] = None
    out["connected_mode_handover_supported_verified"] = None
    claims = claim_by_access(policy)
    family = access_variant(str(out["stack_id"]))
    for key in (
        "idle_cell_reselection_supported_verified",
        "connected_mode_handover_supported_verified",
        "guaranteed_max_end_to_end_latency_ms",
        "expected_device_energy_per_report_j",
    ):
        claim = claims.get((family, key))
        if claim is not None:
            out[key] = claim.get("value")
    return out


def build_refined_scenarios(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Replace the underspecified binary mobility benchmark with two explicit variants.

    This does not choose a preferred mobility definition. It preserves both a periodic
    cross-cell reporting case (idle reselection sufficient) and a connected-mode
    service-continuity case (network-managed handover required).
    """
    scenarios = payload.get("scenarios") or []
    refined: list[dict[str, Any]] = []
    change_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        if scenario["scenario_id"] != "asset_tracking_mobility":
            refined.append(copy.deepcopy(scenario))
            continue

        periodic = copy.deepcopy(scenario)
        periodic["scenario_id"] = "asset_tracking_periodic_cross_cell"
        periodic["name"] = "Operator-served asset tracking: periodic reports with idle cell reselection sufficient"
        periodic["quantitative_context"]["notes"] = (
            "Stage-4E mobility variant. Cross-cell operation may be satisfied by standardized idle-mode cell reselection; "
            "no seamless connected-mode handover is required."
        )
        for constraint in periodic["hard_constraints"]:
            if constraint["constraint_id"] == "mobility":
                constraint["constraint_id"] = "idle_cell_reselection"
                constraint["fact_key"] = "idle_cell_reselection_supported_verified"
                constraint["rationale"] = "A standardized idle-mode cell-reselection mechanism is required."
        refined.append(periodic)

        connected = copy.deepcopy(scenario)
        connected["scenario_id"] = "asset_tracking_connected_handover"
        connected["name"] = "Operator-served asset tracking: connected-mode handover required"
        connected["quantitative_context"]["notes"] = (
            "Stage-4E mobility variant. Network-managed connected-mode handover is explicitly required; "
            "idle-only reselection does not satisfy this variant."
        )
        for constraint in connected["hard_constraints"]:
            if constraint["constraint_id"] == "mobility":
                constraint["constraint_id"] = "connected_mode_handover"
                constraint["fact_key"] = "connected_mode_handover_supported_verified"
                constraint["rationale"] = "Network-managed connected-mode handover is mandatory."
        refined.append(connected)

        change_rows.extend([
            {"original_scenario_id":"asset_tracking_mobility","refined_scenario_id":periodic["scenario_id"],"mobility_semantics":"idle_cell_reselection_sufficient","post_hoc_preference_choice":False},
            {"original_scenario_id":"asset_tracking_mobility","refined_scenario_id":connected["scenario_id"],"mobility_semantics":"connected_mode_handover_required","post_hoc_preference_choice":False},
        ])
    return refined, change_rows
