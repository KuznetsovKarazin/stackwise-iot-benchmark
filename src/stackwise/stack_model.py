from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml


DEFAULT_COMPONENT_SCHEMA = Path("datasets/schema/stack_component.schema.json")
DEFAULT_STACK_SCHEMA = Path("datasets/schema/stack_candidate.schema.json")
DEFAULT_HARD_CONSTRAINT_SCHEMA = Path("datasets/schema/hard_constraint.schema.json")
DEFAULT_STACK_TAXONOMY = Path("datasets/stack_taxonomy.yml")


class StructuralStatus(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNRESOLVED = "unresolved"


class FeasibilityStatus(str, Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class StackAssessment:
    status: StructuralStatus
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ConstraintResult:
    constraint_id: str
    status: str
    reason: str


@dataclass(frozen=True)
class FeasibilityAssessment:
    status: FeasibilityStatus
    results: tuple[ConstraintResult, ...]


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def load_stack_taxonomy(path: str | Path = DEFAULT_STACK_TAXONOMY) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _schema_errors(record: dict[str, Any], schema_path: str | Path) -> list[str]:
    schema = _load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(error.message for error in validator.iter_errors(record))


def validate_stack_component(
    component: dict[str, Any],
    schema_path: str | Path = DEFAULT_COMPONENT_SCHEMA,
) -> list[str]:
    return _schema_errors(component, schema_path)


def validate_stack_candidate(
    stack: dict[str, Any],
    schema_path: str | Path = DEFAULT_STACK_SCHEMA,
) -> list[str]:
    return _schema_errors(stack, schema_path)


def validate_hard_constraint(
    constraint: dict[str, Any],
    schema_path: str | Path = DEFAULT_HARD_CONSTRAINT_SCHEMA,
) -> list[str]:
    return _schema_errors(constraint, schema_path)


def _has_cycle(edges: Iterable[tuple[str, str]]) -> bool:
    adjacency: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for left, right in edges:
        adjacency.setdefault(left, []).append(right)
        nodes.add(left)
        nodes.add(right)

    state: dict[str, int] = {node: 0 for node in nodes}

    def visit(node: str) -> bool:
        state[node] = 1
        for nxt in adjacency.get(node, []):
            if state.get(nxt, 0) == 1:
                return True
            if state.get(nxt, 0) == 0 and visit(nxt):
                return True
        state[node] = 2
        return False

    return any(state[node] == 0 and visit(node) for node in nodes)


def assess_stack_structure(
    stack: dict[str, Any],
    components: Iterable[dict[str, Any]],
    *,
    taxonomy_path: str | Path = DEFAULT_STACK_TAXONOMY,
) -> StackAssessment:
    """Validate a placed stack graph without evaluating scenario preference.

    The assessment is deliberately non-compensatory. Missing component requirements are
    structural incompatibilities, not weak scores. Security and management are handled as
    ordinary compositional components, so multiple security mechanisms may coexist.
    """

    schema_errors = validate_stack_candidate(stack)
    if schema_errors:
        return StackAssessment(
            StructuralStatus.INCOMPATIBLE,
            tuple(f"schema:{message}" for message in schema_errors),
            (),
        )

    catalog: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for component in components:
        component_errors = validate_stack_component(component)
        component_id = str(component.get("component_id", "<missing>"))
        if component_errors:
            errors.extend(f"component:{component_id}:{message}" for message in component_errors)
            continue
        if component_id in catalog:
            errors.append(f"duplicate_component_id:{component_id}")
        catalog[component_id] = component

    instances = stack.get("component_instances") or []
    instance_map: dict[str, dict[str, Any]] = {}
    for instance in instances:
        instance_id = str(instance["instance_id"])
        if instance_id in instance_map:
            errors.append(f"duplicate_instance_id:{instance_id}")
        instance_map[instance_id] = instance

        component = catalog.get(str(instance["component_id"]))
        if component is None:
            errors.append(f"unknown_component:{instance_id}:{instance['component_id']}")
            continue
        if instance["placement"] not in set(component.get("supported_placements") or []):
            errors.append(
                f"unsupported_placement:{instance_id}:{instance['placement']}:{component['component_id']}"
            )

    primary_id = str(stack.get("primary_access_instance_id"))
    primary = instance_map.get(primary_id)
    if primary is None:
        errors.append(f"missing_primary_access_instance:{primary_id}")
    else:
        component = catalog.get(str(primary["component_id"]))
        if component is not None and "access_link" not in set(component.get("roles") or []):
            errors.append(f"primary_access_is_not_access_link:{primary_id}")

    taxonomy = load_stack_taxonomy(taxonomy_path)
    acyclic_relations = set((taxonomy.get("cycle_policy") or {}).get("acyclic_relations") or [])

    incoming_interfaces: dict[str, set[str]] = {instance_id: set() for instance_id in instance_map}
    graph_edges: list[tuple[str, str]] = []
    for binding in stack.get("bindings") or []:
        left = str(binding["from_instance_id"])
        right = str(binding["to_instance_id"])
        interface = str(binding["interface"])
        relation = str(binding["relation"])
        if left not in instance_map:
            errors.append(f"binding_unknown_source:{left}")
            continue
        if right not in instance_map:
            errors.append(f"binding_unknown_target:{right}")
            continue
        if left == right:
            errors.append(f"self_binding:{left}:{interface}")
            continue

        left_component = catalog.get(str(instance_map[left]["component_id"]))
        right_component = catalog.get(str(instance_map[right]["component_id"]))
        if left_component is None or right_component is None:
            continue
        if interface not in set(left_component.get("provides") or []):
            errors.append(f"binding_interface_not_provided:{left}:{interface}")
        required_interfaces = set(right_component.get("requires") or [])
        for group in right_component.get("requires_any") or []:
            required_interfaces.update(map(str, group))
        if interface not in required_interfaces:
            errors.append(f"binding_interface_not_required:{right}:{interface}")
        incoming_interfaces.setdefault(right, set()).add(interface)
        if relation in acyclic_relations:
            graph_edges.append((left, right))

    if _has_cycle(graph_edges):
        errors.append("cycle_in_data_or_security_binding_graph")

    environment = set(map(str, stack.get("environment_capabilities") or []))
    global_provided: set[str] = set(environment)
    for instance in instances:
        component = catalog.get(str(instance["component_id"]))
        if component is not None:
            global_provided.update(map(str, component.get("provides") or []))

    for instance_id, instance in instance_map.items():
        component = catalog.get(str(instance["component_id"]))
        if component is None:
            continue
        requirements = set(map(str, component.get("requires") or []))
        satisfied = incoming_interfaces.get(instance_id, set()) | environment
        for requirement in sorted(requirements - satisfied):
            errors.append(f"unsatisfied_requirement:{instance_id}:{requirement}")
        for alternatives in component.get("requires_any") or []:
            alternatives_set = set(map(str, alternatives))
            if alternatives_set and not (alternatives_set & satisfied):
                errors.append(
                    f"unsatisfied_requirement_alternative:{instance_id}:"
                    + "|".join(sorted(alternatives_set))
                )
        conflicts = set(map(str, component.get("forbids") or [])) & global_provided
        for conflict in sorted(conflicts):
            errors.append(f"forbidden_capability_present:{instance_id}:{conflict}")

    # Contract fixtures are allowed in tests only; warn if they appear in a non-fixture stack.
    if stack.get("scientific_status") != "contract_fixture":
        fixture_components = [
            instance_id
            for instance_id, instance in instance_map.items()
            if catalog.get(str(instance["component_id"]), {}).get("scientific_status") == "contract_fixture"
        ]
        if fixture_components:
            warnings.append("contract_fixture_components_in_nonfixture_stack:" + ",".join(sorted(fixture_components)))

    status = StructuralStatus.INCOMPATIBLE if errors else StructuralStatus.COMPATIBLE
    return StackAssessment(status, tuple(sorted(set(errors))), tuple(sorted(set(warnings))))


def _evaluate_operator(fact: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return fact == expected
    if operator == "ne":
        return fact != expected
    if operator == "in":
        return fact in expected
    if operator == "not_in":
        return fact not in expected
    if operator == "gte":
        return fact >= expected
    if operator == "lte":
        return fact <= expected
    if operator == "exists":
        return fact is not None
    if operator == "truthy":
        return bool(fact)
    raise ValueError(f"Unsupported hard-constraint operator: {operator}")


def evaluate_hard_constraints(
    facts: dict[str, Any],
    constraints: Iterable[dict[str, Any]],
) -> FeasibilityAssessment:
    """Evaluate non-compensatory scenario constraints with explicit unknown handling.

    Missing facts never pass silently. If at least one hard constraint fails the stack is
    infeasible; otherwise any unknown fact makes the result unresolved. Only an all-pass
    set is feasible.
    """

    results: list[ConstraintResult] = []
    saw_fail = False
    saw_unknown = False

    for constraint in constraints:
        schema_errors = validate_hard_constraint(constraint)
        if schema_errors:
            raise ValueError(f"Invalid hard constraint {constraint.get('constraint_id')}: {schema_errors}")
        constraint_id = str(constraint["constraint_id"])
        key = str(constraint["fact_key"])
        if key not in facts or facts[key] is None:
            saw_unknown = True
            results.append(ConstraintResult(constraint_id, "unknown", f"missing_fact:{key}"))
            continue
        fact = facts[key]
        expected = constraint.get("value")
        try:
            passed = _evaluate_operator(fact, str(constraint["operator"]), expected)
        except (TypeError, ValueError) as exc:
            saw_unknown = True
            results.append(ConstraintResult(constraint_id, "unknown", f"noncomparable_fact:{key}:{exc}"))
            continue
        if passed:
            results.append(ConstraintResult(constraint_id, "pass", f"predicate_passed:{key}"))
        else:
            saw_fail = True
            results.append(ConstraintResult(constraint_id, "fail", f"predicate_failed:{key}"))

    if saw_fail:
        status = FeasibilityStatus.INFEASIBLE
    elif saw_unknown:
        status = FeasibilityStatus.UNRESOLVED
    else:
        status = FeasibilityStatus.FEASIBLE
    return FeasibilityAssessment(status, tuple(results))
