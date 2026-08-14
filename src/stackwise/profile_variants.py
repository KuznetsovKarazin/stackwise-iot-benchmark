from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from stackwise.profile_bridge import validate_operating_profile


@dataclass(frozen=True)
class VariantDecision:
    variant_id: str
    status: str
    decision_sufficient_for_monotone_lower_bound: bool
    whole_device_profile_complete: bool
    whole_device_numeric_bridge_ready: bool


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _int(value: Any) -> int:
    return int(float(value))


def _float(value: Any) -> float:
    return float(value)


def build_lrfhss_source_aligned_variants(
    *,
    stage5b_screen_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    family = policy["variant_family"]
    domain = family["source_model_domain"]
    screen = {(str(r["confirmation_mode"]), _int(r["source_dr_index"])): r for r in stage5b_screen_rows}
    expected_keys = {
        (str(mode), int(dr))
        for mode in domain["confirmation_modes"]
        for dr in domain["data_rates"]
    }
    if set(screen) != expected_keys:
        raise ValueError("Stage-5C requires the complete Stage-5B DR x confirmation-mode screen.")

    variants: list[dict[str, Any]] = []
    for mode in domain["confirmation_modes"]:
        for dr in domain["data_rates"]:
            row = screen[(str(mode), int(dr))]
            variant_id = f"lrfhss_agri_dr{int(dr)}_{str(mode)}_14dbm_v{int(family['variant_version'])}"
            fields = [
                {"field_id":"application_payload_bytes","status":"known","value":int(domain["application_payload_bytes"]),"unit":"B","provenance_status":"scenario_derived","provenance_ref":"stage4_benchmark_scenarios:remote_agriculture_energy_budget","required_for_numeric_bridge":True},
                {"field_id":"reporting_interval_s","status":"known","value":float(domain["reporting_interval_s"]),"unit":"s","provenance_status":"scenario_derived","provenance_ref":"stage4_benchmark_scenarios:remote_agriculture_energy_budget","required_for_numeric_bridge":True},
                {"field_id":"lrfhss_data_rate","status":"known","value":f"DR{int(dr)}","provenance_status":"explicit_model_assumption","provenance_ref":f"stage5c:{family['family_id']}","required_for_numeric_bridge":True},
                {"field_id":"confirmation_mode","status":"known","value":str(mode),"provenance_status":"explicit_model_assumption","provenance_ref":f"stage5c:{family['family_id']}","required_for_numeric_bridge":True},
                {"field_id":"tx_power_dbm","status":"known","value":int(domain["tx_power_dbm"]),"unit":"dBm","provenance_status":"explicit_model_assumption","provenance_ref":"stage5b:source_aligned_tx_power","required_for_numeric_bridge":True},
                {"field_id":"retry_policy","status":"unresolved","provenance_status":"unresolved","required_for_numeric_bridge":True,"notes":"Additional retry behaviour is not selected by the benchmark variant."},
                {"field_id":"receive_window_policy","status":"known","value":str(domain["receive_window_policy"]),"provenance_status":"explicit_model_assumption","provenance_ref":"stage5b:source_radio_state_model","required_for_numeric_bridge":True},
                {"field_id":"end_device_hardware","status":"unresolved","provenance_status":"unresolved","required_for_numeric_bridge":True,"notes":"Whole-device MCU/sensor/platform hardware remains unspecified."},
                {"field_id":"reporting_cycle_definition","status":"unresolved","provenance_status":"unresolved","required_for_numeric_bridge":True,"notes":"No whole-device 600 s cycle accounting model is activated."},
                {"field_id":"radio_hardware","status":"known","value":str(domain["radio_hardware"]),"provenance_status":"primary_source_verified","provenance_ref":"lorawan_lrfhss_energy_2024:source_hardware","required_for_numeric_bridge":False},
                {"field_id":"accounting_boundary","status":"known","value":str(domain["accounting_boundary"]),"provenance_status":"explicit_model_assumption","provenance_ref":"stage5b:one_sided_component_lower_bound","required_for_numeric_bridge":False},
                {"field_id":"minimum_uplink_transactions_per_report","status":"known","value":int(domain["minimum_uplink_transactions_per_report"]),"provenance_status":"explicit_model_assumption","provenance_ref":"stage5b:transaction_count_for_component_lower_bound","required_for_numeric_bridge":False},
            ]
            profile = {
                "profile_id": variant_id,
                "scenario_id": family["scenario_id"],
                "stack_id": family["stack_id"],
                "scientific_status": "benchmark_profile_variant_partial",
                "notes": "Versioned source-aligned LR-FHSS operating-profile variant. It is a conditional model variant, not an observed deployment choice.",
                "fields": fields,
            }
            errors = validate_operating_profile(profile)
            if errors:
                raise ValueError(f"Invalid generated profile variant {variant_id}: {errors}")
            profile["parent_profile_id"] = family["parent_profile_id"]
            profile["variant_family_id"] = family["family_id"]
            profile["variant_version"] = int(family["variant_version"])
            profile["source_dr_index"] = int(dr)
            profile["confirmation_mode"] = str(mode)
            profile["stage5b_screen_status"] = str(row["one_sided_budget_screen_status"])
            profile["modeled_incremental_radio_energy_j"] = _float(row["modeled_incremental_radio_energy_j"])
            profile["whole_device_budget_j"] = _float(row["whole_device_budget_j"])
            profile["source_model_valid_for_payload_extrapolation"] = _bool(row["source_model_valid_for_payload_extrapolation"])
            variants.append(profile)
    return variants


def assess_lrfhss_variant(profile: dict[str, Any], policy: dict[str, Any]) -> VariantDecision:
    field_map = {str(f["field_id"]): f for f in profile["fields"]}
    unresolved_required = [
        f["field_id"] for f in profile["fields"]
        if bool(f.get("required_for_numeric_bridge")) and f.get("status") != "known"
    ]
    whole_complete = not unresolved_required
    whole_ready = False  # Stage-5C never materialises a whole-device numeric bridge.

    screen_status = str(profile["stage5b_screen_status"])
    source_valid = bool(profile["source_model_valid_for_payload_extrapolation"])
    match_fields = list(policy["lower_bound_decision_contract"]["match_fields"])
    matched = all(field_map.get(fid, {}).get("status") == "known" for fid in match_fields)
    monotone_sufficient = bool(
        matched
        and source_valid
        and screen_status == "matched_variant_infeasible_by_radio_component_lower_bound"
    )

    if monotone_sufficient:
        status = "conditionally_infeasible_by_validated_radio_lower_bound"
    elif screen_status == "whole_device_unresolved_radio_component_below_or_equal_budget":
        status = "unresolved_residual_whole_device_energy"
    elif screen_status == "model_not_authorised_for_payload_extrapolation":
        status = "unresolved_confirmed_source_model_not_validated"
    else:
        raise ValueError(f"Unexpected Stage-5B screen status: {screen_status}")

    return VariantDecision(
        variant_id=str(profile["profile_id"]),
        status=status,
        decision_sufficient_for_monotone_lower_bound=monotone_sufficient,
        whole_device_profile_complete=whole_complete,
        whole_device_numeric_bridge_ready=whole_ready,
    )


def flatten_variant_fields(variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in variants:
        for field in profile["fields"]:
            rows.append({
                "variant_id": profile["profile_id"],
                "parent_profile_id": profile["parent_profile_id"],
                "scenario_id": profile["scenario_id"],
                "stack_id": profile["stack_id"],
                "source_dr_index": profile["source_dr_index"],
                "confirmation_mode": profile["confirmation_mode"],
                "field_id": field["field_id"],
                "status": field["status"],
                "value": field.get("value"),
                "unit": field.get("unit"),
                "provenance_status": field["provenance_status"],
                "provenance_ref": field.get("provenance_ref"),
                "required_for_numeric_bridge": bool(field.get("required_for_numeric_bridge")),
                "notes": field.get("notes"),
            })
    return rows
