from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


VALID_COST_MODES = {
    "operator_managed_access",
    "private_owned_access",
    "managed_service_access",
    "unresolved_ownership_mode",
}


@dataclass(frozen=True)
class LifecycleCostAuditSummary:
    feasible_candidate_rows: int
    operator_managed_rows: int
    private_owned_rows: int
    unresolved_ownership_rows: int
    rows_with_complete_required_price_evidence: int
    rows_requiring_shared_cost_scale: int
    canonical_target_ready_rows: int
    smoke_price_rows_authorised: int


def _component_catalog(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = policy["accounting_boundary"]["included_if_differential"]
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row["component_id"])
        if cid in out:
            raise ValueError(f"Duplicate lifecycle-cost component {cid!r}.")
        out[cid] = dict(row)
    return out


def _scenario_mode(policy: dict[str, Any], scenario_id: str, access_family: str) -> str:
    scenario = policy.get("scenario_cost_modes", {}).get(scenario_id, {})
    mode = scenario.get(access_family)
    if mode is None:
        return "unresolved_ownership_mode"
    mode = str(mode)
    if mode not in VALID_COST_MODES:
        raise ValueError(f"Unsupported cost mode {mode!r} for {scenario_id}/{access_family}.")
    return mode


def required_components_for_mode(policy: dict[str, Any], mode: str) -> list[str]:
    catalog = _component_catalog(policy)
    return sorted(
        cid
        for cid, row in catalog.items()
        if mode in {str(x) for x in row.get("mandatory_for_modes", [])}
    )


def cost_component_contract_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid, row in _component_catalog(policy).items():
        rows.append({
            "component_id": cid,
            "scope": str(row["scope"]),
            "mandatory_for_modes": "|".join(map(str, row.get("mandatory_for_modes", []))),
            "description": str(row["description"]),
            "numeric_evidence_materialised": False,
        })
    return rows


def _price_evidence_lookup(policy: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    # A future evidence row may target a stack ID or an access family. Stage 5H intentionally has none.
    out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in policy.get("price_evidence", []):
        component = str(row["component_id"])
        scope = str(row["technology_or_stack_scope"])
        out[(component, scope)].append(dict(row))
    return out


def build_candidate_cost_readiness(
    feasibility_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence = _price_evidence_lookup(policy)
    scale_cfg = policy.get("deployment_scale", {})
    rows: list[dict[str, Any]] = []

    seen: set[tuple[str, str]] = set()
    for frow in feasibility_rows:
        if str(frow["status"]) != "feasible":
            continue
        scenario_id = str(frow["scenario_id"])
        stack_id = str(frow["stack_id"])
        access_family = str(frow["access_family"])
        key = (scenario_id, stack_id)
        if key in seen:
            raise ValueError(f"Duplicate feasible scenario/stack row {key}.")
        seen.add(key)

        mode = _scenario_mode(policy, scenario_id, access_family)
        required = required_components_for_mode(policy, mode) if mode != "unresolved_ownership_mode" else []

        missing: list[str] = []
        evidenced: list[str] = []
        for component in required:
            component_rows = evidence.get((component, stack_id), []) + evidence.get((component, access_family), [])
            if component_rows:
                evidenced.append(component)
            else:
                missing.append(component)

        shared_components = [
            c for c in required
            if _component_catalog(policy)[c]["scope"] in {"per_site_one_time_shared", "per_site_recurring_shared"}
        ]
        scale = scale_cfg.get(scenario_id, {})
        reference_device_count = scale.get("reference_device_count")
        shared_scale_required = bool(shared_components)
        shared_scale_ready = (not shared_scale_required) or (reference_device_count not in {None, ""})

        ownership_ready = mode != "unresolved_ownership_mode"
        price_ready = ownership_ready and len(missing) == 0
        canonical_ready = ownership_ready and price_ready and shared_scale_ready

        blockers: list[str] = []
        if not ownership_ready:
            blockers.append("ownership_mode_not_frozen")
        if missing:
            blockers.append("required_price_evidence_missing")
        if shared_scale_required and not shared_scale_ready:
            blockers.append("shared_infrastructure_allocation_scale_missing")

        rows.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "access_family": access_family,
            "cost_mode": mode,
            "analysis_horizon_years": int(policy["scientific_policy"]["analysis_horizon_years"]),
            "base_currency": str(policy["scientific_policy"]["base_currency"]),
            "price_basis_date": str(policy["scientific_policy"]["price_basis_date"]),
            "required_component_count": len(required),
            "required_components": "|".join(required),
            "evidenced_component_count": len(evidenced),
            "evidenced_components": "|".join(evidenced),
            "missing_components": "|".join(missing),
            "ownership_boundary_ready": ownership_ready,
            "shared_cost_scale_required": shared_scale_required,
            "reference_device_count": "" if reference_device_count is None else reference_device_count,
            "shared_cost_scale_ready": shared_scale_ready,
            "required_price_evidence_complete": price_ready,
            "canonical_lifecycle_cost_ready": canonical_ready,
            "readiness_status": "READY" if canonical_ready else "BLOCKED",
            "blocking_reasons": "|".join(blockers),
        })
    return rows


def cost_gap_rows(candidate_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(candidate_rows)
    gaps: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for gap in str(row.get("blocking_reasons", "")).split("|"):
            if gap:
                gaps[gap].append(row)
    out: list[dict[str, Any]] = []
    order = {
        "required_price_evidence_missing": 1,
        "ownership_mode_not_frozen": 2,
        "shared_infrastructure_allocation_scale_missing": 3,
    }
    for gap, grows in gaps.items():
        out.append({
            "gap_id": gap,
            "priority_order": order.get(gap, 99),
            "affected_feasible_candidate_rows": len(grows),
            "affected_scenarios": len({str(r["scenario_id"]) for r in grows}),
            "scenario_ids": "|".join(sorted({str(r["scenario_id"]) for r in grows})),
            "stack_ids": "|".join(sorted({str(r["stack_id"]) for r in grows})),
        })
    return sorted(out, key=lambda r: (int(r["priority_order"]), str(r["gap_id"])))


def audit_summary(candidate_rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> LifecycleCostAuditSummary:
    rows = list(candidate_rows)
    modes = Counter(str(r["cost_mode"]) for r in rows)
    result = LifecycleCostAuditSummary(
        feasible_candidate_rows=len(rows),
        operator_managed_rows=modes["operator_managed_access"],
        private_owned_rows=modes["private_owned_access"],
        unresolved_ownership_rows=modes["unresolved_ownership_mode"],
        rows_with_complete_required_price_evidence=sum(bool(r["required_price_evidence_complete"]) for r in rows),
        rows_requiring_shared_cost_scale=sum(bool(r["shared_cost_scale_required"]) for r in rows),
        canonical_target_ready_rows=sum(bool(r["canonical_lifecycle_cost_ready"]) for r in rows),
        smoke_price_rows_authorised=0,
    )
    expected = policy.get("expected", {})
    for field in result.__dataclass_fields__:
        if field in expected:
            actual = getattr(result, field)
            if actual != int(expected[field]):
                raise ValueError(f"Stage-5H expected {field}={expected[field]}, observed {actual}.")
    return result
