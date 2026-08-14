from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .stack_model import StackAssessment, StructuralStatus, assess_stack_structure, validate_stack_component

DEFAULT_CATALOG = Path("datasets/stack_component_catalog.yml")
DEFAULT_EDGE_SCHEMA = Path("datasets/schema/stack_compatibility_edge.schema.json")
DEFAULT_ALIGNMENT_SCHEMA = Path("datasets/schema/stack_evidence_alignment.schema.json")


def load_component_catalog(path: str | Path = DEFAULT_CATALOG) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return payload


def _schema_errors(record: dict[str, Any], schema_path: str | Path) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(error.message for error in validator.iter_errors(record))


def _required_interfaces(component: dict[str, Any]) -> set[str]:
    result = set(map(str, component.get("requires") or []))
    for group in component.get("requires_any") or []:
        result.update(map(str, group))
    return result


def validate_component_catalog(
    catalog: dict[str, Any],
    *,
    edge_schema_path: str | Path = DEFAULT_EDGE_SCHEMA,
    alignment_schema_path: str | Path = DEFAULT_ALIGNMENT_SCHEMA,
) -> list[str]:
    errors: list[str] = []
    sources = catalog.get("sources") or {}
    claims = catalog.get("claims") or {}
    components = catalog.get("components") or []
    edges = catalog.get("compatibility_edges") or []
    alignments = catalog.get("evidence_alignment") or []

    if not isinstance(sources, dict) or not isinstance(claims, dict):
        return ["catalog_sources_or_claims_not_mapping"]

    for source_id, source in sources.items():
        if source.get("verification_status") != "primary_source_verified":
            errors.append(f"source_not_primary_verified:{source_id}")
        if not source.get("authority") or not source.get("identifier") or not source.get("url"):
            errors.append(f"source_incomplete:{source_id}")

    for claim_id, claim in claims.items():
        source_ids = claim.get("source_ids") or []
        if not source_ids:
            errors.append(f"claim_without_source:{claim_id}")
        for source_id in source_ids:
            if source_id not in sources:
                errors.append(f"claim_unknown_source:{claim_id}:{source_id}")
        if claim.get("verification_status") != "primary_source_verified":
            errors.append(f"claim_not_verified:{claim_id}")

    component_map: dict[str, dict[str, Any]] = {}
    for component in components:
        cid = str(component.get("component_id", "<missing>"))
        for err in validate_stack_component(component):
            errors.append(f"component_schema:{cid}:{err}")
        if cid in component_map:
            errors.append(f"duplicate_component_id:{cid}")
        component_map[cid] = component
        for claim_id in component.get("claim_ids") or []:
            if claim_id not in claims:
                errors.append(f"component_unknown_claim:{cid}:{claim_id}")
        if component.get("catalog_status") == "primary_source_verified":
            if component.get("scientific_status") != "verified_component":
                errors.append(f"verified_catalog_component_not_verified_status:{cid}")
            if component.get("provenance_status") != "primary_source_verified":
                errors.append(f"verified_component_bad_provenance:{cid}")
            if not component.get("claim_ids"):
                errors.append(f"verified_component_without_claim:{cid}")
            refs = component.get("standards_refs") or []
            if not refs or any(ref.get("verification_status") != "primary_source_verified" for ref in refs):
                errors.append(f"verified_component_without_primary_ref:{cid}")

    edge_ids: set[str] = set()
    for edge in edges:
        eid = str(edge.get("edge_id", "<missing>"))
        if eid in edge_ids:
            errors.append(f"duplicate_edge_id:{eid}")
        edge_ids.add(eid)
        for err in _schema_errors(edge, edge_schema_path):
            errors.append(f"edge_schema:{eid}:{err}")
        fr = component_map.get(str(edge.get("from_component_id")))
        to = component_map.get(str(edge.get("to_component_id")))
        if fr is None:
            errors.append(f"edge_unknown_source_component:{eid}")
            continue
        if to is None:
            errors.append(f"edge_unknown_target_component:{eid}")
            continue
        interface = str(edge.get("interface"))
        if interface not in set(map(str, fr.get("provides") or [])):
            errors.append(f"edge_interface_not_provided:{eid}:{interface}")
        if interface not in _required_interfaces(to):
            errors.append(f"edge_interface_not_required:{eid}:{interface}")
        for claim_id in edge.get("claim_ids") or []:
            if claim_id not in claims:
                errors.append(f"edge_unknown_claim:{eid}:{claim_id}")
        if edge.get("status") == "primary_source_verified_compatible":
            if fr.get("catalog_status") != "primary_source_verified" or to.get("catalog_status") != "primary_source_verified":
                errors.append(f"verified_edge_uses_unverified_component:{eid}")

    alignment_ids: set[str] = set()
    for alignment in alignments:
        aid = str(alignment.get("alignment_id", "<missing>"))
        if aid in alignment_ids:
            errors.append(f"duplicate_alignment_id:{aid}")
        alignment_ids.add(aid)
        for err in _schema_errors(alignment, alignment_schema_path):
            errors.append(f"alignment_schema:{aid}:{err}")
        if alignment.get("component_id") not in component_map:
            errors.append(f"alignment_unknown_component:{aid}")

    policy = catalog.get("scientific_policy") or {}
    for key in ["mcda_authorised", "ranking_authorised"]:
        if policy.get(key) is not False:
            errors.append(f"catalog_guard_not_false:{key}")
    if policy.get("unknown_or_unverified_binding_is_not_compatible") is not True:
        errors.append("catalog_guard_missing:unknown_or_unverified_binding_is_not_compatible")
    return sorted(set(errors))


def assess_verified_candidate_stack(
    stack: dict[str, Any],
    catalog: dict[str, Any],
) -> StackAssessment:
    """Assess a real Stage-4 candidate against the verified compatibility-edge catalog.

    ``assess_stack_structure`` proves only interface-level composition.  For a
    ``verified_candidate`` every placed component must also be primary-source
    verified and every explicit binding must match one frozen
    ``primary_source_verified_compatible`` catalog edge exactly.  This prevents
    an interface-name match from being promoted to a standards claim.
    """

    base = assess_stack_structure(stack, catalog.get("components") or [])
    errors = list(base.errors)
    warnings = list(base.warnings)

    components = {str(c["component_id"]): c for c in catalog.get("components") or []}
    instances = {str(i["instance_id"]): i for i in stack.get("component_instances") or []}

    if stack.get("scientific_status") == "verified_candidate":
        for instance_id, instance in instances.items():
            component = components.get(str(instance.get("component_id")))
            if component is not None and component.get("catalog_status") != "primary_source_verified":
                errors.append(f"verified_candidate_uses_unverified_component:{instance_id}:{component['component_id']}")

        verified_edges = {
            (
                str(edge.get("from_component_id")),
                str(edge.get("to_component_id")),
                str(edge.get("interface")),
                str(edge.get("relation")),
            )
            for edge in catalog.get("compatibility_edges") or []
            if edge.get("status") == "primary_source_verified_compatible"
        }
        for binding in stack.get("bindings") or []:
            left = instances.get(str(binding.get("from_instance_id")))
            right = instances.get(str(binding.get("to_instance_id")))
            if left is None or right is None:
                continue
            signature = (
                str(left.get("component_id")),
                str(right.get("component_id")),
                str(binding.get("interface")),
                str(binding.get("relation")),
            )
            if signature not in verified_edges:
                errors.append("binding_not_primary_source_verified:" + ":".join(signature))

    status = StructuralStatus.INCOMPATIBLE if errors else base.status
    return StackAssessment(status, tuple(sorted(set(errors))), tuple(sorted(set(warnings))))
