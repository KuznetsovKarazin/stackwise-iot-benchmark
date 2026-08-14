from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RobustnessProjection:
    variants: int
    conditionally_infeasible: int
    conditionally_feasible: int
    unresolved: int
    universally_infeasible: bool
    universally_feasible: bool
    mixed_or_unresolved: bool
    generic_candidate_status: str


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def audit_variant_family(
    *,
    variant_rows: Iterable[dict[str, Any]],
    implication_rows: Iterable[dict[str, Any]],
    generic_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> RobustnessProjection:
    variants = list(variant_rows)
    implications = list(implication_rows)
    generic = list(generic_rows)
    expected = policy["expected"]

    if len(variants) != int(expected["profile_variants"]):
        raise ValueError("Stage-5D expects the complete frozen Stage-5C variant family.")
    if len(implications) != len(variants):
        raise ValueError("Each Stage-5C variant must have one feasibility implication row.")
    if len(generic) != 1:
        raise ValueError("Stage-5D expects exactly one generic-candidate projection row.")

    variant_ids = {str(r["variant_id"]) for r in variants}
    implication_ids = {str(r["variant_id"]) for r in implications}
    if variant_ids != implication_ids:
        raise ValueError("Variant and implication identifiers do not reconcile.")

    if any(_bool(r.get("deployment_selection_evidence")) for r in variants):
        raise ValueError("Stage-5D cannot start from variants already marked as deployment-selected.")
    if any(_bool(r.get("probability_weight_assigned")) for r in variants):
        raise ValueError("Stage-5D cannot start from weighted variants.")
    if any(_bool(r.get("whole_device_profile_complete")) for r in variants):
        raise ValueError("Stage-5D expects all Stage-5C variants to remain whole-device incomplete.")

    statuses = [str(r["conditional_feasibility_status"]) for r in implications]
    infeasible_label = "conditionally_infeasible_by_validated_radio_lower_bound"
    feasible_label = "conditionally_feasible"
    allowed_unresolved = {
        "unresolved_residual_whole_device_energy",
        "unresolved_confirmed_source_model_not_validated",
    }
    allowed = {infeasible_label, feasible_label} | allowed_unresolved
    unexpected = sorted(set(statuses) - allowed)
    if unexpected:
        raise ValueError(f"Unexpected Stage-5C implication statuses: {unexpected}")

    n_infeasible = sum(s == infeasible_label for s in statuses)
    n_feasible = sum(s == feasible_label for s in statuses)
    n_unresolved = sum(s in allowed_unresolved for s in statuses)

    g = generic[0]
    if str(g["generic_candidate_status"]) != "unresolved":
        raise ValueError("Generic LR-FHSS candidate must remain unresolved at Stage-5D input.")
    if _bool(g.get("deployment_selection_evidence_available")):
        raise ValueError("Stage-5D expects no deployment selection evidence at input.")
    if _bool(g.get("probability_weights_assigned")):
        raise ValueError("Stage-5D expects no variant probability weights at input.")

    universally_infeasible = n_infeasible == len(variants)
    universally_feasible = n_feasible == len(variants)
    mixed_or_unresolved = not universally_infeasible and not universally_feasible
    generic_status = "unresolved"

    return RobustnessProjection(
        variants=len(variants),
        conditionally_infeasible=n_infeasible,
        conditionally_feasible=n_feasible,
        unresolved=n_unresolved,
        universally_infeasible=universally_infeasible,
        universally_feasible=universally_feasible,
        mixed_or_unresolved=mixed_or_unresolved,
        generic_candidate_status=generic_status,
    )


def selection_dimension_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in policy["selection_dimensions"]:
        rows.append({
            "dimension_id": item["dimension_id"],
            "selection_authority_or_mechanism": item["selection_authority_or_mechanism"],
            "standards_mechanism_verified": bool(item["standards_mechanism_verified"]),
            "deployment_specific_value_available": bool(item["deployment_specific_value_available"]),
            "selection_identifiability_status": item["selection_identifiability_status"],
            "required_deployment_evidence": item["required_deployment_evidence"],
            "notes": item["notes"],
        })
    return rows


def source_claim_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in policy["primary_source_review"]]


def deployment_requirement_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in policy["deployment_selection_requirements"]]
