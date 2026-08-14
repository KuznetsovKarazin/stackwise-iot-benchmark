from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml

from .stack_model import FeasibilityAssessment, evaluate_hard_constraints, validate_hard_constraint

DEFAULT_SCENARIOS = Path("datasets/stage4_benchmark_scenarios.yml")
DEFAULT_SCENARIO_SCHEMA = Path("datasets/schema/benchmark_scenario.schema.json")


def load_benchmark_scenarios(path: str | Path = DEFAULT_SCENARIOS) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return payload


def validate_benchmark_scenario(
    scenario: dict[str, Any], schema_path: str | Path = DEFAULT_SCENARIO_SCHEMA
) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = [error.message for error in validator.iter_errors(scenario)]
    for constraint in scenario.get("hard_constraints") or []:
        errors.extend(f"hard_constraint:{message}" for message in validate_hard_constraint(constraint))
    return sorted(errors)


def _component_ids(stack: dict[str, Any]) -> set[str]:
    return {str(instance["component_id"]) for instance in stack.get("component_instances") or []}


def derive_candidate_hard_capabilities(stack: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Derive only hard-screening facts supported by the frozen component graph.

    Numeric performance facts remain ``None`` unless a later Stage-4 capability bridge
    materialises them.  ``None`` is intentional: the hard-feasibility engine maps it to
    ``unresolved`` rather than silently passing a candidate.
    """

    component_map = {str(c["component_id"]): c for c in catalog.get("components") or []}
    instances = {str(i["instance_id"]): i for i in stack.get("component_instances") or []}
    primary = instances[str(stack["primary_access_instance_id"])]
    primary_component = component_map[str(primary["component_id"])]
    component_ids = _component_ids(stack)
    provides = set(map(str, primary_component.get("provides") or []))

    if "operator_managed_access" in provides:
        access_family = "cellular"
        requires_operator_service = True
        requires_lorawan_service = False
        requires_thread_border_router = False
    elif str(primary_component["component_id"]).startswith("lorawan_"):
        access_family = "lorawan"
        requires_operator_service = False
        requires_lorawan_service = True
        requires_thread_border_router = False
    elif str(primary_component["component_id"]) == "thread_ipv6_mesh":
        access_family = "thread"
        requires_operator_service = False
        requires_lorawan_service = False
        requires_thread_border_router = "thread_border_router" in component_ids
    else:
        access_family = "other"
        requires_operator_service = False
        requires_lorawan_service = False
        requires_thread_border_router = False

    if "ip_packet_service" in provides:
        device_network_mode: str | None = "ip"
    elif "ciot_nonip_service" in provides or "lorawan_nonip_transport_service" in provides:
        device_network_mode = "nonip"
    else:
        device_network_mode = None

    return {
        "stack_id": str(stack["stack_id"]),
        "access_family": access_family,
        "requires_operator_service": requires_operator_service,
        "requires_lorawan_service": requires_lorawan_service,
        "requires_thread_border_router": requires_thread_border_router,
        "device_network_mode": device_network_mode,
        "explicit_tls_or_dtls_present": bool({"tls13", "dtls13"} & component_ids),
        "lwm2m_management_available": "lwm2m12" in component_ids,
        # Deliberately unresolved in Stage-4D. These are not inferred from names or raw rows.
        "max_application_payload_bytes": None,
        "guaranteed_max_end_to_end_latency_ms": None,
        "expected_device_energy_per_report_j": None,
        "mobility_supported_verified": None,
    }


def compose_scenario_candidate_facts(
    candidate_capabilities: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    deployment = scenario["deployment_facts"]

    required_checks: list[bool | None] = []
    if candidate_capabilities["requires_operator_service"]:
        required_checks.append(deployment.get("cellular_access_service_available_at_site"))
    if candidate_capabilities["requires_lorawan_service"]:
        required_checks.append(deployment.get("lorawan_access_service_available_at_site"))
    if candidate_capabilities["requires_thread_border_router"]:
        required_checks.append(deployment.get("thread_border_router_available_at_site"))

    if not required_checks:
        access_satisfied: bool | None = True
    elif any(value is False for value in required_checks):
        access_satisfied = False
    elif any(value is None for value in required_checks):
        access_satisfied = None
    else:
        access_satisfied = True

    return {
        **candidate_capabilities,
        "access_infrastructure_satisfied": access_satisfied,
        # Quantitative scenario context is retained separately from candidate capabilities.
        "scenario_payload_bytes": scenario["quantitative_context"]["payload_bytes"],
        "scenario_reporting_interval_s": scenario["quantitative_context"]["reporting_interval_s"],
        "scenario_target_end_to_end_latency_ms": scenario["quantitative_context"][
            "target_end_to_end_latency_ms"
        ],
        "scenario_energy_budget_per_report_j": scenario["quantitative_context"].get(
            "whole_device_energy_budget_per_report_j"
        ),
    }


def screen_candidate_against_scenario(
    stack: dict[str, Any], catalog: dict[str, Any], scenario: dict[str, Any]
) -> tuple[dict[str, Any], FeasibilityAssessment]:
    candidate = derive_candidate_hard_capabilities(stack, catalog)
    facts = compose_scenario_candidate_facts(candidate, scenario)
    assessment = evaluate_hard_constraints(facts, scenario.get("hard_constraints") or [])
    return facts, assessment


def screening_matrix(
    stacks: Iterable[dict[str, Any]], catalog: dict[str, Any], scenarios: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for stack in stacks:
            facts, assessment = screen_candidate_against_scenario(stack, catalog, scenario)
            rows.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "stack_id": stack["stack_id"],
                    "status": assessment.status.value,
                    "facts": facts,
                    "constraint_results": [
                        {
                            "constraint_id": result.constraint_id,
                            "status": result.status,
                            "reason": result.reason,
                        }
                        for result in assessment.results
                    ],
                }
            )
    return rows
