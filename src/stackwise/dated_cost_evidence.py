from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from typing import Any, Iterable


@dataclass(frozen=True)
class DatedCostEvidenceSummary:
    feasible_candidate_rows: int
    operator_managed_rows: int
    ip_cellular_feasible_rows: int
    nonip_cellular_feasible_rows: int
    private_or_unresolved_lorawan_rows: int
    rows_with_dated_module_and_sim_price: int
    rows_with_ip_connectivity_tariff_evidence: int
    rows_with_canonical_lifecycle_cost_ready: int
    smart_meter_ip_rows_with_base_allowance_not_disproven: int
    tracking_ip_rows_with_base_allowance_not_disproven: int
    rows_where_base_allowance_definitely_insufficient: int


def _money(policy: dict[str, Any], evidence_role: str) -> dict[str, Any]:
    matches = [r for r in policy["monetary_evidence"] if str(r["evidence_role"]) == evidence_role]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one monetary evidence row for role {evidence_role!r}, got {len(matches)}.")
    return dict(matches[0])


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _report_count(horizon_years: int, reporting_interval_s: int | float, days_per_year: float) -> int:
    seconds = _d(horizon_years) * _d(days_per_year) * Decimal("86400")
    count = (seconds / _d(reporting_interval_s)).to_integral_value(rounding=ROUND_CEILING)
    return int(count)


def monetary_evidence_ledger_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in policy["monetary_evidence"]:
        copy = dict(row)
        sensitivity = copy.pop("quantity_sensitivity", [])
        copy["quantity_sensitivity"] = "|".join(
            f"q={x['quantity']}:EUR={x['unit_price_eur']}:{x['role']}" for x in sensitivity
        )
        if isinstance(copy.get("supported_radio_access"), list):
            copy["supported_radio_access"] = "|".join(map(str, copy["supported_radio_access"]))
        if isinstance(copy.get("ip_transport_evidence"), list):
            copy["ip_transport_evidence"] = "|".join(map(str, copy["ip_transport_evidence"]))
        out.append(copy)
    return out


def build_dated_cost_readiness(
    stage5h_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = list(stage5h_rows)
    ip_stacks = {str(x) for x in policy["ip_cellular_stack_ids"]}
    profiles = policy["scenario_reporting_profiles"]
    horizon = 5
    days_per_year = float(policy["scientific_policy"]["report_count_basis_days_per_year"])

    module = _money(policy, "device_module_reference_price")
    sim = _money(policy, "physical_sim_reference_price")
    base = _money(policy, "connectivity_base_plan")
    module_cost = _d(module["reference_value"])
    sim_cost = _d(sim["reference_value"])
    base_cost = _d(base["reference_value"])
    included_data_mb = int(base["included_data_mb"])

    out: list[dict[str, Any]] = []
    for row in rows:
        scenario_id = str(row["scenario_id"])
        stack_id = str(row["stack_id"])
        access_family = str(row["access_family"])
        mode = str(row["cost_mode"])
        is_operator = mode == "operator_managed_access"
        is_ip = is_operator and stack_id in ip_stacks
        is_nonip_cellular = is_operator and access_family == "cellular" and not is_ip

        hardware_price_evidence = is_ip
        sim_price_evidence = is_ip
        ip_tariff_evidence = is_ip
        service_mode_evidenced = is_ip

        report_count: int | str = ""
        app_payload_volume_mb: float | str = ""
        allowance_headroom_over_app_payload: float | str = ""
        tariff_status = "not_applicable"
        cost_floor: Decimal | None = None
        blockers: list[str] = []

        if is_ip:
            profile = profiles.get(scenario_id)
            if not profile:
                raise ValueError(f"Missing Stage-5I reporting profile for IP cellular scenario {scenario_id!r}.")
            report_count = _report_count(horizon, profile["reporting_interval_s"], days_per_year)
            app_bytes = int(report_count) * int(profile["application_payload_bytes"])
            app_payload_volume_mb = app_bytes / 1_000_000.0
            allowance_headroom_over_app_payload = included_data_mb / app_payload_volume_mb if app_payload_volume_mb else ""
            # The source states 1-kByte measurement/billing granularity but does not state whether
            # rounding is per packet, PDP context, interval or aggregate usage. Therefore no rounding
            # multiplication is allowed here. Application payload volume alone is below 500 MB in all
            # three Stage-5I scenarios, so the base plan is neither proven insufficient nor sufficient.
            tariff_status = "base_allowance_not_disproven_exact_transport_usage_unresolved"
            cost_floor = module_cost + sim_cost + base_cost
            blockers.append("tariff_volume_fit_not_identified")
            blockers.append("reference_retail_price_not_market_distribution")
        elif is_nonip_cellular:
            tariff_status = "nonip_operator_service_not_evidenced"
            blockers.append("operator_nonip_service_price_not_evidenced")
            blockers.append("exact_nonip_reference_hardware_applicability_not_evidenced")
        else:
            inherited = [x for x in str(row.get("blocking_reasons", "")).split("|") if x]
            blockers.extend(inherited)
            blockers.append("not_in_stage5i_cellular_price_tranche")

        canonical_ready = False
        out.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "access_family": access_family,
            "cost_mode": mode,
            "dated_module_price_evidence": hardware_price_evidence,
            "dated_sim_price_evidence": sim_price_evidence,
            "dated_ip_connectivity_tariff_evidence": ip_tariff_evidence,
            "operator_service_mode_evidenced": service_mode_evidenced,
            "reporting_interval_s": profiles.get(scenario_id, {}).get("reporting_interval_s", ""),
            "application_payload_bytes": profiles.get(scenario_id, {}).get("application_payload_bytes", ""),
            "five_year_report_count": report_count,
            "application_payload_volume_mb_5y": app_payload_volume_mb,
            "included_data_mb": included_data_mb if is_ip else "",
            "included_data_to_application_payload_ratio": allowance_headroom_over_app_payload,
            "tariff_volume_fit_status": tariff_status,
            "reference_module_eur_qty1_ex_vat": float(module_cost) if is_ip else "",
            "reference_standard_sim_eur": float(sim_cost) if is_ip else "",
            "reference_base_connectivity_cash_eur": float(base_cost) if is_ip else "",
            "reference_cost_floor_eur": float(cost_floor) if cost_floor is not None else "",
            "cost_floor_is_canonical_target": False,
            "canonical_lifecycle_cost_ready": canonical_ready,
            "readiness_status": "READY" if canonical_ready else "BLOCKED",
            "blocking_reasons": "|".join(dict.fromkeys(blockers)),
        })
    return out


def remaining_gap_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for gap in str(row["blocking_reasons"]).split("|"):
            if gap:
                grouped.setdefault(gap, []).append(row)
    priority = {
        "tariff_volume_fit_not_identified": 1,
        "operator_nonip_service_price_not_evidenced": 2,
        "exact_nonip_reference_hardware_applicability_not_evidenced": 3,
        "ownership_mode_not_frozen": 4,
        "shared_infrastructure_allocation_scale_missing": 5,
        "required_price_evidence_missing": 6,
        "reference_retail_price_not_market_distribution": 7,
        "not_in_stage5i_cellular_price_tranche": 8,
    }
    out: list[dict[str, Any]] = []
    for gap, grows in grouped.items():
        out.append({
            "gap_id": gap,
            "priority_order": priority.get(gap, 99),
            "affected_candidate_rows": len(grows),
            "scenario_ids": "|".join(sorted({str(r["scenario_id"]) for r in grows})),
            "stack_ids": "|".join(sorted({str(r["stack_id"]) for r in grows})),
        })
    return sorted(out, key=lambda r: (int(r["priority_order"]), str(r["gap_id"])))


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> DatedCostEvidenceSummary:
    data = list(rows)
    operator = [r for r in data if r["cost_mode"] == "operator_managed_access"]
    ip = [r for r in data if bool(r["dated_ip_connectivity_tariff_evidence"])]
    nonip = [r for r in operator if r["access_family"] == "cellular" and not bool(r["dated_ip_connectivity_tariff_evidence"])]
    private_or_unresolved_lora = [r for r in data if r["access_family"] == "lorawan"]
    smart = [r for r in ip if r["scenario_id"] == "smart_meter_public_cellular"]
    tracking = [r for r in ip if r["scenario_id"] in {"asset_tracking_periodic_cross_cell", "asset_tracking_connected_handover"}]
    result = DatedCostEvidenceSummary(
        feasible_candidate_rows=len(data),
        operator_managed_rows=len(operator),
        ip_cellular_feasible_rows=len(ip),
        nonip_cellular_feasible_rows=len(nonip),
        private_or_unresolved_lorawan_rows=len(private_or_unresolved_lora),
        rows_with_dated_module_and_sim_price=sum(bool(r["dated_module_price_evidence"] and r["dated_sim_price_evidence"]) for r in data),
        rows_with_ip_connectivity_tariff_evidence=sum(bool(r["dated_ip_connectivity_tariff_evidence"]) for r in data),
        rows_with_canonical_lifecycle_cost_ready=sum(bool(r["canonical_lifecycle_cost_ready"]) for r in data),
        smart_meter_ip_rows_with_base_allowance_not_disproven=sum(
            r["tariff_volume_fit_status"] == "base_allowance_not_disproven_exact_transport_usage_unresolved" for r in smart
        ),
        tracking_ip_rows_with_base_allowance_not_disproven=sum(
            r["tariff_volume_fit_status"] == "base_allowance_not_disproven_exact_transport_usage_unresolved" for r in tracking
        ),
        rows_where_base_allowance_definitely_insufficient=sum(
            r["tariff_volume_fit_status"] == "base_allowance_definitely_insufficient" for r in ip
        ),
    )
    for field, expected in policy.get("expected", {}).items():
        actual = getattr(result, field)
        if actual != int(expected):
            raise ValueError(f"Stage-5I expected {field}={expected}, observed {actual}.")
    return result
