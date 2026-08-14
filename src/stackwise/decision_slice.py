from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


REQUIRED_SOFT_TARGETS = {
    "expected_device_energy_per_application_report_j",
    "lifecycle_cost_eur",
}


@dataclass(frozen=True)
class DecisionSliceSummary:
    stage4_feasible_rows: int
    stage4_infeasible_rows: int
    stage4_unresolved_rows: int
    feasible_candidate_rows: int
    hard_unresolved_exclusion_rows: int
    criterion_rows: int
    required_soft_criterion_rows: int
    ready_required_soft_criterion_rows: int
    context_only_required_soft_criterion_rows: int
    blocked_required_soft_criterion_rows: int
    feasible_candidates_ready_for_first_slice: int
    feasible_candidates_with_cost_context: int
    cost_context_robust_within_candidates: int
    cost_context_robust_exceed_candidates: int
    cost_context_protocol_envelope_sensitive_candidates: int
    preferred_development_subset_rows: int
    preferred_development_subset_ready_rows: int
    scenarios_with_feasible_candidates: int


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _by_pair(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["scenario_id"]), str(row["stack_id"]))
        if key in out:
            raise ValueError(f"Duplicate scenario/stack row: {key}")
        out[key] = row
    return out


def _by_pair_target(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["scenario_id"]), str(row["stack_id"]), str(row["target_metric_id"]))
        if key in out:
            raise ValueError(f"Duplicate scenario/stack/target row: {key}")
        out[key] = row
    return out


def allowance_context_by_candidate(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["scenario_id"]), str(row["stack_id"]))].append(row)

    out: dict[tuple[str, str], dict[str, Any]] = {}
    within_label = "within_across_all_session_control_surrogates"
    exceed_label = "exceeds_across_all_session_control_surrogates"
    crossing_label = "crosses_nominal_allowance_across_session_control_surrogates"
    for key, grows in grouped.items():
        classes = {str(r["session_control_allowance_robustness_class"]) for r in grows}
        if crossing_label in classes:
            context_class = "SESSION_CONTROL_SENSITIVE"
        elif classes == {within_label}:
            context_class = "ROBUST_WITHIN_NOMINAL_RAW_ALLOWANCE"
        elif classes == {exceed_label}:
            context_class = "ROBUST_EXCEED_NOMINAL_RAW_ALLOWANCE"
        elif classes.issubset({within_label, exceed_label}) and len(classes) == 2:
            context_class = "PROTOCOL_ENVELOPE_SENSITIVE"
        else:
            raise ValueError(f"Unexpected Stage-5N robustness classes for {key}: {sorted(classes)}")

        mins = [_float(r["min_five_year_augmented_transport_mb"]) for r in grows]
        maxs = [_float(r["max_five_year_augmented_transport_mb"]) for r in grows]
        out[key] = {
            "tariff_volume_context_class": context_class,
            "tariff_volume_source_rows": len(grows),
            "tariff_volume_min_mb_5y": min(x for x in mins if x is not None),
            "tariff_volume_max_mb_5y": max(x for x in maxs if x is not None),
            "tariff_volume_probability_interpretation": False,
        }
    return out


def build_criterion_readiness_rows(
    *,
    stage5e_rows: Iterable[dict[str, Any]],
    cost_rows: Iterable[dict[str, Any]],
    stage5n_robustness_rows: Iterable[dict[str, Any]],
    stage5g_energy_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    stage5e = [r for r in stage5e_rows if str(r["feasibility_status"]) == "feasible"]
    costs = _by_pair(cost_rows)
    energy_transfer = _by_pair(stage5g_energy_rows)
    allowance = allowance_context_by_candidate(stage5n_robustness_rows)

    out: list[dict[str, Any]] = []
    for row in stage5e:
        scenario_id = str(row["scenario_id"])
        stack_id = str(row["stack_id"])
        target = str(row["target_metric_id"])
        key = (scenario_id, stack_id)
        first_slice_required = _bool(row["first_slice_required"])
        decision_use_status = "BLOCKED"
        evidence_maturity = str(row["readiness_status"])
        current_blocking_reasons = str(row.get("blocking_reasons") or "")
        context_class = ""
        context_min_mb = ""
        context_max_mb = ""

        if target == "expected_device_energy_per_application_report_j":
            if key in energy_transfer:
                erow = energy_transfer[key]
                evidence_maturity = "STRUCTURAL_TRANSFER_SUPPORT_ONLY"
                current_blocking_reasons = str(erow.get("blocking_reasons") or current_blocking_reasons)
            elif str(row["evidence_relation"]) == "CONDITIONAL_INPUT_ONLY":
                evidence_maturity = "COMPONENT_OR_LINK_CONTEXT_ONLY"
            # No Stage-5 result materialises candidate-boundary report energy.
            decision_use_status = "BLOCKED"

        elif target == "lifecycle_cost_eur":
            crow = costs.get(key)
            if crow is None:
                raise ValueError(f"Missing Stage-5I cost-readiness row for feasible candidate {key}")
            if key in allowance and _bool(crow.get("dated_ip_connectivity_tariff_evidence", False)):
                decision_use_status = "CONTEXT_ONLY"
                evidence_maturity = "DATED_COST_FLOOR_PLUS_RAW_TARIFF_ROBUSTNESS_CONTEXT"
                ctx = allowance[key]
                context_class = str(ctx["tariff_volume_context_class"])
                context_min_mb = ctx["tariff_volume_min_mb_5y"]
                context_max_mb = ctx["tariff_volume_max_mb_5y"]
                current_blocking_reasons = str(crow.get("blocking_reasons") or "")
            else:
                decision_use_status = "BLOCKED"
                evidence_maturity = "COST_TARGET_NOT_IDENTIFIED"
                current_blocking_reasons = str(crow.get("blocking_reasons") or current_blocking_reasons)

        elif target in {"end_to_end_application_latency_ms", "feasible_link_probability"}:
            decision_use_status = "HARD_SCREEN_ONLY"
            evidence_maturity = "UPSTREAM_FEASIBILITY_CONTEXT_NOT_SOFT_SCORE"

        elif target == "delivery_probability":
            decision_use_status = "DEFERRED"
            evidence_maturity = "OPTIONAL_TARGET_NOT_RETAINED_IN_FIRST_SLICE"

        else:
            raise ValueError(f"Unexpected Stage-6A target {target!r}")

        out.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "feasibility_status": "feasible",
            "target_metric_id": target,
            "first_slice_required": first_slice_required,
            "stage5e_readiness_status": str(row["readiness_status"]),
            "stage6a_decision_use_status": decision_use_status,
            "evidence_maturity": evidence_maturity,
            "canonical_target_ready": decision_use_status in {"READY_PROBABILISTIC", "READY_ROBUSTNESS_FAMILY"},
            "score_authorised": decision_use_status in {"READY_PROBABILISTIC", "READY_ROBUSTNESS_FAMILY"},
            "tariff_volume_context_class": context_class,
            "tariff_volume_min_mb_5y": context_min_mb,
            "tariff_volume_max_mb_5y": context_max_mb,
            "probability_interpretation": False if decision_use_status in {"CONTEXT_ONLY", "HARD_SCREEN_ONLY", "DEFERRED"} else "",
            "blocking_reasons": current_blocking_reasons,
        })
    return out


def build_candidate_slice_rows(criterion_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in criterion_rows:
        grouped[(str(row["scenario_id"]), str(row["stack_id"]))].append(row)

    out: list[dict[str, Any]] = []
    for (scenario_id, stack_id), rows in sorted(grouped.items()):
        required = [r for r in rows if _bool(r["first_slice_required"])]
        if len(required) != 2:
            raise ValueError(f"Expected exactly two required soft targets for {(scenario_id, stack_id)}")
        by_target = {str(r["target_metric_id"]): r for r in rows}
        energy = by_target["expected_device_energy_per_application_report_j"]
        cost = by_target["lifecycle_cost_eur"]
        ready_count = sum(_bool(r["canonical_target_ready"]) for r in required)
        context_count = sum(str(r["stage6a_decision_use_status"]) == "CONTEXT_ONLY" for r in required)
        blocked_count = sum(str(r["stage6a_decision_use_status"]) == "BLOCKED" for r in required)
        out.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "energy_decision_use_status": energy["stage6a_decision_use_status"],
            "energy_evidence_maturity": energy["evidence_maturity"],
            "cost_decision_use_status": cost["stage6a_decision_use_status"],
            "cost_evidence_maturity": cost["evidence_maturity"],
            "tariff_volume_context_class": cost["tariff_volume_context_class"],
            "tariff_volume_min_mb_5y": cost["tariff_volume_min_mb_5y"],
            "tariff_volume_max_mb_5y": cost["tariff_volume_max_mb_5y"],
            "required_soft_ready_count": ready_count,
            "required_soft_context_only_count": context_count,
            "required_soft_blocked_count": blocked_count,
            "first_slice_candidate_ready": ready_count == len(required),
            "publication_score_authorised": False,
        })
    return out


def build_scenario_summary_rows(candidate_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        grouped[str(row["scenario_id"])].append(row)

    out: list[dict[str, Any]] = []
    for scenario_id, rows in sorted(grouped.items()):
        contexts = Counter(str(r["tariff_volume_context_class"]) for r in rows if r["tariff_volume_context_class"])
        out.append({
            "scenario_id": scenario_id,
            "feasible_candidate_count": len(rows),
            "first_slice_ready_candidate_count": sum(_bool(r["first_slice_candidate_ready"]) for r in rows),
            "cost_context_candidate_count": sum(str(r["cost_decision_use_status"]) == "CONTEXT_ONLY" for r in rows),
            "cost_robust_within_candidate_count": contexts["ROBUST_WITHIN_NOMINAL_RAW_ALLOWANCE"],
            "cost_robust_exceed_candidate_count": contexts["ROBUST_EXCEED_NOMINAL_RAW_ALLOWANCE"],
            "cost_protocol_envelope_sensitive_candidate_count": contexts["PROTOCOL_ENVELOPE_SENSITIVE"],
            "first_slice_comparison_ready": sum(_bool(r["first_slice_candidate_ready"]) for r in rows) >= 2,
            "publication_mcda_authorised": False,
        })
    return out


def hard_unresolved_exclusion_rows(feasibility_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": str(r["scenario_id"]),
            "stack_id": str(r["stack_id"]),
            "feasibility_status": str(r["status"]),
            "decision_slice_status": "EXCLUDED_PENDING_HARD_FEASIBILITY",
        }
        for r in feasibility_rows
        if str(r["status"]) == "unresolved"
    ]


def preferred_subset_rows(candidate_rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    spec = policy["preferred_development_subset"]
    scenario = str(spec["scenario_id"])
    stacks = {str(x) for x in spec["stack_ids"]}
    rows = [dict(r) for r in candidate_rows if str(r["scenario_id"]) == scenario and str(r["stack_id"]) in stacks]
    if {str(r["stack_id"]) for r in rows} != stacks:
        raise ValueError("Preferred Stage-6A development subset is not fully present in the feasible candidate rows.")
    for row in rows:
        row["subset_id"] = str(spec["subset_id"])
        row["publication_scope"] = str(spec["publication_scope"])
        row["subset_selection_rationale"] = str(spec["selection_rationale"])
    return sorted(rows, key=lambda r: str(r["stack_id"]))


def gap_priority_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(x) for x in policy["stage6b_gap_priorities"]]
    rows.sort(key=lambda r: int(r["priority_order"]))
    return rows


def audit_summary(
    *,
    feasibility_rows: Iterable[dict[str, Any]],
    criterion_rows: Iterable[dict[str, Any]],
    candidate_rows: Iterable[dict[str, Any]],
    scenario_rows: Iterable[dict[str, Any]],
    unresolved_rows: Iterable[dict[str, Any]],
    subset_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> DecisionSliceSummary:
    feasibility = list(feasibility_rows)
    criteria = list(criterion_rows)
    candidates = list(candidate_rows)
    scenarios = list(scenario_rows)
    unresolved = list(unresolved_rows)
    subset = list(subset_rows)
    counts = Counter(str(r["status"]) for r in feasibility)
    required = [r for r in criteria if _bool(r["first_slice_required"])]

    cost_contexts = Counter(str(r["tariff_volume_context_class"]) for r in candidates if r["tariff_volume_context_class"])
    result = DecisionSliceSummary(
        stage4_feasible_rows=counts["feasible"],
        stage4_infeasible_rows=counts["infeasible"],
        stage4_unresolved_rows=counts["unresolved"],
        feasible_candidate_rows=len(candidates),
        hard_unresolved_exclusion_rows=len(unresolved),
        criterion_rows=len(criteria),
        required_soft_criterion_rows=len(required),
        ready_required_soft_criterion_rows=sum(_bool(r["canonical_target_ready"]) for r in required),
        context_only_required_soft_criterion_rows=sum(str(r["stage6a_decision_use_status"]) == "CONTEXT_ONLY" for r in required),
        blocked_required_soft_criterion_rows=sum(str(r["stage6a_decision_use_status"]) == "BLOCKED" for r in required),
        feasible_candidates_ready_for_first_slice=sum(_bool(r["first_slice_candidate_ready"]) for r in candidates),
        feasible_candidates_with_cost_context=sum(str(r["cost_decision_use_status"]) == "CONTEXT_ONLY" for r in candidates),
        cost_context_robust_within_candidates=cost_contexts["ROBUST_WITHIN_NOMINAL_RAW_ALLOWANCE"],
        cost_context_robust_exceed_candidates=cost_contexts["ROBUST_EXCEED_NOMINAL_RAW_ALLOWANCE"],
        cost_context_protocol_envelope_sensitive_candidates=cost_contexts["PROTOCOL_ENVELOPE_SENSITIVE"],
        preferred_development_subset_rows=len(subset),
        preferred_development_subset_ready_rows=sum(_bool(r["first_slice_candidate_ready"]) for r in subset),
        scenarios_with_feasible_candidates=len(scenarios),
    )
    expected = policy["expected"]
    for key, actual in result.__dict__.items():
        if key in expected and actual != int(expected[key]):
            raise ValueError(f"Stage-6A expected {key}={expected[key]}, observed {actual}.")
    return result
