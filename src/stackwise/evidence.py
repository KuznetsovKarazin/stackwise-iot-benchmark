from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml


DEFAULT_EVIDENCE_SCHEMA = Path("datasets/schema/evidence_record.schema.json")
DEFAULT_METRIC_CATALOG = Path("datasets/evidence_metric_catalog.yml")
DEFAULT_BOUNDARY_TAXONOMY = Path("datasets/evidence_boundary_taxonomy.yml")
DEFAULT_SHARED_PARAMETER_SCHEMA = Path("datasets/schema/shared_parameter.schema.json")


class CompatibilityLevel(str, Enum):
    DIRECT = "C0_DIRECT"
    BRIDGEABLE = "C1_BRIDGEABLE"
    CONDITIONAL = "C2_CONDITIONAL"
    INCOMPATIBLE = "C3_INCOMPATIBLE"


@dataclass(frozen=True)
class CompatibilityAssessment:
    level: CompatibilityLevel
    reasons: tuple[str, ...]

    @property
    def is_direct(self) -> bool:
        return self.level is CompatibilityLevel.DIRECT


def _load_yaml(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data or {}


def load_metric_catalog(path: str | Path = DEFAULT_METRIC_CATALOG) -> dict[str, Any]:
    return _load_yaml(path)


def load_boundary_taxonomy(path: str | Path = DEFAULT_BOUNDARY_TAXONOMY) -> dict[str, Any]:
    return _load_yaml(path)


def validate_evidence_record(
    record: dict[str, Any],
    schema_path: str | Path = DEFAULT_EVIDENCE_SCHEMA,
    metric_catalog_path: str | Path = DEFAULT_METRIC_CATALOG,
) -> list[str]:
    """Validate one Stage-2 evidence record against the schema and metric catalogue.

    This validator is deliberately stricter than the harmonised observation validator.
    A valid record must use the canonical unit and family declared for its metric_id.
    """

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = [error.message for error in validator.iter_errors(record)]

    catalog = load_metric_catalog(metric_catalog_path).get("metrics", {})
    metric_id = record.get("metric_id")
    metric = catalog.get(metric_id)
    if metric is None:
        errors.append(f"metric_id {metric_id!r} is not present in the evidence metric catalogue")
        return sorted(errors)

    if record.get("metric_family") != metric.get("family"):
        errors.append(
            f"metric_family {record.get('metric_family')!r} does not match catalogue family "
            f"{metric.get('family')!r} for {metric_id}"
        )
    if record.get("unit") != metric.get("unit"):
        errors.append(
            f"unit {record.get('unit')!r} does not match canonical unit "
            f"{metric.get('unit')!r} for {metric_id}"
        )
    return sorted(errors)


def validate_shared_parameter_record(
    record: dict[str, Any],
    schema_path: str | Path = DEFAULT_SHARED_PARAMETER_SCHEMA,
) -> list[str]:
    """Validate one shared derivation parameter used by Stage-2 evidence records."""

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(error.message for error in validator.iter_errors(record))


def _normalise_pair(pair: Iterable[str]) -> frozenset[str]:
    return frozenset(str(item) for item in pair)


def _is_unknown(value: Any, unknown_tokens: set[str]) -> bool:
    return value is None or (isinstance(value, str) and value in unknown_tokens)


def assess_compatibility(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    allowed_vary: Iterable[str] = (),
    metric_catalog_path: str | Path = DEFAULT_METRIC_CATALOG,
    boundary_taxonomy_path: str | Path = DEFAULT_BOUNDARY_TAXONOMY,
) -> CompatibilityAssessment:
    """Conservatively classify whether two evidence records are scientifically comparable.

    ``allowed_vary`` names deliberate comparison factors (for example ``technology``,
    ``access_network`` or an implementation field when the compared candidate explicitly
    includes that hardware variation). It never relaxes metric or measurement-boundary
    requirements.

    The function is intentionally conservative: C0 is returned only for the same metric,
    canonical unit, fully specified boundary, and matched workload conditions apart from
    explicit comparison factors. C1 means that an explicit bridge model is required; it
    never authorises pooling by itself.
    """

    catalog = load_metric_catalog(metric_catalog_path).get("metrics", {})
    taxonomy = load_boundary_taxonomy(boundary_taxonomy_path)
    allowed = set(allowed_vary)
    unknown_tokens = set(taxonomy.get("unknown_tokens", ["unknown"]))

    left_metric_id = left.get("metric_id")
    right_metric_id = right.get("metric_id")
    left_metric = catalog.get(left_metric_id, {})
    right_metric = catalog.get(right_metric_id, {})

    hard_pairs = {
        _normalise_pair(pair)
        for pair in taxonomy.get("hard_incompatible_metric_pairs", [])
    }
    metric_pair = frozenset({str(left_metric_id), str(right_metric_id)})
    if metric_pair in hard_pairs:
        return CompatibilityAssessment(
            CompatibilityLevel.INCOMPATIBLE,
            ("hard_incompatible_metric_pair", "missing_required_estimand_bridge_or_denominator"),
        )

    bridgeable_metric_pairs = {
        _normalise_pair(pair)
        for pair in taxonomy.get("bridgeable_metric_pairs", [])
    }
    if metric_pair in bridgeable_metric_pairs:
        return CompatibilityAssessment(
            CompatibilityLevel.BRIDGEABLE,
            ("explicit_metric_bridge_required",),
        )

    conditional_metric_pairs = {
        _normalise_pair(pair)
        for pair in taxonomy.get("conditional_metric_pairs", [])
    }
    if metric_pair in conditional_metric_pairs:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            ("metric_is_model_input_not_target_estimand",),
        )

    if not left_metric or not right_metric:
        return CompatibilityAssessment(
            CompatibilityLevel.INCOMPATIBLE,
            ("unknown_metric_id",),
        )

    if left.get("metric_family") != right.get("metric_family"):
        return CompatibilityAssessment(
            CompatibilityLevel.INCOMPATIBLE,
            ("different_metric_families",),
        )

    if left_metric_id != right_metric_id:
        left_bridge = left_metric.get("bridge_group")
        right_bridge = right_metric.get("bridge_group")
        if left_bridge and left_bridge == right_bridge:
            return CompatibilityAssessment(
                CompatibilityLevel.BRIDGEABLE,
                ("different_metric_semantics", f"shared_bridge_group:{left_bridge}"),
            )
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            ("different_metric_semantics",),
        )

    if left.get("unit") != right.get("unit"):
        return CompatibilityAssessment(
            CompatibilityLevel.INCOMPATIBLE,
            ("noncanonical_or_mismatched_units",),
        )

    boundary_fields = list(taxonomy.get("critical_boundary_fields", []))
    unknown_boundary = [
        field
        for field in boundary_fields
        if _is_unknown(left.get(field), unknown_tokens) or _is_unknown(right.get(field), unknown_tokens)
    ]
    if unknown_boundary:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            tuple(["unknown_critical_boundary"] + [f"unknown:{field}" for field in unknown_boundary]),
        )

    boundary_differences = [field for field in boundary_fields if left.get(field) != right.get(field)]
    if boundary_differences:
        system_pair = frozenset({str(left.get("system_scope")), str(right.get("system_scope"))})
        bridgeable_scope_pairs = {
            _normalise_pair(pair)
            for pair in taxonomy.get("bridgeable_system_scope_pairs", [])
        }
        temporal_pair = frozenset({str(left.get("temporal_scope")), str(right.get("temporal_scope"))})
        bridgeable_temporal_pairs = {
            _normalise_pair(pair)
            for pair in taxonomy.get("bridgeable_energy_temporal_pairs", [])
        }
        family = left.get("metric_family")
        bridgeable = (
            family == "energy"
            and (
                system_pair in bridgeable_scope_pairs
                or temporal_pair in bridgeable_temporal_pairs
                or left.get("accounting_basis") != right.get("accounting_basis")
            )
        )
        level = CompatibilityLevel.BRIDGEABLE if bridgeable else CompatibilityLevel.CONDITIONAL
        return CompatibilityAssessment(
            level,
            tuple(["measurement_boundary_mismatch"] + [f"different:{field}" for field in boundary_differences]),
        )

    required_conditions = list(left_metric.get("direct_condition_fields", []))
    missing_required_conditions = [
        field
        for field in required_conditions
        if _is_unknown(left.get(field), unknown_tokens) or _is_unknown(right.get(field), unknown_tokens)
    ]
    if missing_required_conditions:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            tuple(
                ["unknown_required_direct_condition"]
                + [f"unknown:{field}" for field in missing_required_conditions]
            ),
        )

    workload_fields = list(taxonomy.get("workload_fields", []))
    workload_differences = [
        field
        for field in workload_fields
        if field not in allowed and left.get(field) != right.get(field)
    ]
    if workload_differences:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            tuple(["workload_mismatch"] + [f"different:{field}" for field in workload_differences]),
        )

    stack_fields = [
        "technology",
        "access_network",
        "transport_protocol",
        "application_protocol",
        "security_mode",
        "management_protocol",
    ]
    stack_differences = [
        field
        for field in stack_fields
        if field not in allowed and left.get(field) != right.get(field)
    ]
    if stack_differences:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            tuple(["stack_configuration_mismatch"] + [f"different:{field}" for field in stack_differences]),
        )

    implementation_fields = list(taxonomy.get("implementation_fields", []))
    implementation_differences = [
        field
        for field in implementation_fields
        if field not in allowed and left.get(field) != right.get(field)
    ]
    if implementation_differences:
        return CompatibilityAssessment(
            CompatibilityLevel.CONDITIONAL,
            tuple(
                ["implementation_context_mismatch"]
                + [f"different:{field}" for field in implementation_differences]
            ),
        )

    return CompatibilityAssessment(CompatibilityLevel.DIRECT, ("matched_metric_boundary_and_conditions",))
