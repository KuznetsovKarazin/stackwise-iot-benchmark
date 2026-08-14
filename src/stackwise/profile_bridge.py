from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema


DEFAULT_OPERATING_PROFILE_SCHEMA = Path("datasets/schema/operating_profile.schema.json")
DEFAULT_BRIDGE_CONTRACT_SCHEMA = Path("datasets/schema/bridge_contract.schema.json")


@dataclass(frozen=True)
class ProfileAssessment:
    profile_id: str
    completeness: str
    known_fields: tuple[str, ...]
    unresolved_fields: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class BridgeReadiness:
    bridge_id: str
    status: str
    unresolved_profile_fields: tuple[str, ...]
    blocking_reasons: tuple[str, ...]


def _load_schema(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _schema_errors(record: dict[str, Any], schema_path: str | Path) -> list[str]:
    validator = jsonschema.Draft202012Validator(_load_schema(schema_path))
    return sorted(error.message for error in validator.iter_errors(record))


def validate_operating_profile(
    profile: dict[str, Any],
    schema_path: str | Path = DEFAULT_OPERATING_PROFILE_SCHEMA,
) -> list[str]:
    errors = _schema_errors(profile, schema_path)
    seen: set[str] = set()
    for field in profile.get("fields") or []:
        field_id = str(field.get("field_id", ""))
        if field_id in seen:
            errors.append(f"duplicate_field_id:{field_id}")
        seen.add(field_id)
        status = field.get("status")
        provenance = field.get("provenance_status")
        has_value = "value" in field
        if status == "known" and not has_value:
            errors.append(f"known_field_missing_value:{field_id}")
        if status == "unresolved" and provenance != "unresolved":
            errors.append(f"unresolved_field_nonunresolved_provenance:{field_id}:{provenance}")
        if status == "known" and provenance == "unresolved":
            errors.append(f"known_field_unresolved_provenance:{field_id}")
    return sorted(set(errors))


def validate_bridge_contract(
    bridge: dict[str, Any],
    schema_path: str | Path = DEFAULT_BRIDGE_CONTRACT_SCHEMA,
) -> list[str]:
    errors = _schema_errors(bridge, schema_path)
    fields = list(map(str, bridge.get("required_profile_fields") or []))
    if len(fields) != len(set(fields)):
        errors.append("duplicate_required_profile_field")
    source = bridge.get("source_evidence") or {}
    if source.get("status") == "matched_source_available" and not source.get("metric_ids"):
        errors.append("matched_source_available_without_metric_ids")
    if bridge.get("scientific_status") == "validated_bridge_ready":
        if (bridge.get("boundary_mapping") or {}).get("status") == "unavailable":
            errors.append("validated_bridge_ready_with_unavailable_boundary_mapping")
    return sorted(set(errors))


def assess_profile(profile: dict[str, Any]) -> ProfileAssessment:
    errors = validate_operating_profile(profile)
    known: list[str] = []
    unresolved: list[str] = []
    for field in profile.get("fields") or []:
        if not bool(field.get("required_for_numeric_bridge")):
            continue
        if field.get("status") == "known":
            known.append(str(field["field_id"]))
        elif field.get("status") == "unresolved":
            unresolved.append(str(field["field_id"]))
    completeness = "invalid" if errors else ("complete" if not unresolved else "partial")
    return ProfileAssessment(
        profile_id=str(profile.get("profile_id", "")),
        completeness=completeness,
        known_fields=tuple(sorted(known)),
        unresolved_fields=tuple(sorted(unresolved)),
        errors=tuple(errors),
    )


def assess_bridge_readiness(bridge: dict[str, Any], profile: dict[str, Any]) -> BridgeReadiness:
    errors = validate_bridge_contract(bridge)
    profile_errors = validate_operating_profile(profile)
    reasons: list[str] = []
    if errors:
        reasons.extend(f"bridge_contract_error:{e}" for e in errors)
    if profile_errors:
        reasons.extend(f"profile_error:{e}" for e in profile_errors)
    if str(bridge.get("scenario_id")) != str(profile.get("scenario_id")):
        reasons.append("scenario_mismatch")
    if str(bridge.get("stack_id")) != str(profile.get("stack_id")):
        reasons.append("stack_mismatch")

    field_map = {str(f["field_id"]): f for f in profile.get("fields") or []}
    unresolved: list[str] = []
    for field_id in map(str, bridge.get("required_profile_fields") or []):
        field = field_map.get(field_id)
        if field is None:
            unresolved.append(field_id)
            reasons.append(f"required_profile_field_missing:{field_id}")
        elif field.get("status") != "known":
            unresolved.append(field_id)
    if unresolved:
        reasons.append("unresolved_required_profile_fields")

    source_status = (bridge.get("source_evidence") or {}).get("status")
    if source_status == "no_matched_source":
        reasons.append("no_matched_source_evidence")
    boundary_status = (bridge.get("boundary_mapping") or {}).get("status")
    if boundary_status == "unavailable":
        reasons.append("boundary_mapping_unavailable")
    elif boundary_status == "explicit_transform_required":
        reasons.append("validated_boundary_transform_not_materialised")

    # A contract is ready only when there are no blockers and the author explicitly marks it ready.
    if bridge.get("scientific_status") != "validated_bridge_ready":
        reasons.append("bridge_not_validated_ready")

    status = "ready" if not reasons else "blocked"
    return BridgeReadiness(
        bridge_id=str(bridge.get("bridge_id", "")),
        status=status,
        unresolved_profile_fields=tuple(sorted(set(unresolved))),
        blocking_reasons=tuple(sorted(set(reasons))),
    )


def flatten_profile_fields(profiles: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        for field in profile.get("fields") or []:
            rows.append({
                "profile_id": profile["profile_id"],
                "scenario_id": profile["scenario_id"],
                "stack_id": profile["stack_id"],
                "field_id": field["field_id"],
                "status": field["status"],
                "value": field.get("value"),
                "unit": field.get("unit"),
                "provenance_status": field["provenance_status"],
                "provenance_ref": field.get("provenance_ref"),
                "required_for_numeric_bridge": bool(field["required_for_numeric_bridge"]),
                "notes": field.get("notes"),
            })
    return rows
