from pathlib import Path

import yaml

from stackwise.stack_model import (
    FeasibilityStatus,
    StructuralStatus,
    assess_stack_structure,
    evaluate_hard_constraints,
    validate_hard_constraint,
    validate_stack_candidate,
    validate_stack_component,
)


FIXTURE_PATH = Path("tests/fixtures_stage4_stack_contract.yml")


def load_fixture():
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_all_stage4_contract_fixtures_validate_against_schemas():
    data = load_fixture()
    assert len(data["components"]) == 9
    for component in data["components"]:
        assert validate_stack_component(component) == []
    for stack in data["stacks"].values():
        assert validate_stack_candidate(stack) == []
    for constraint in data["hard_constraints"]:
        assert validate_hard_constraint(constraint) == []


def test_security_is_compositional_not_exclusive_layer_slot():
    data = load_fixture()
    assessment = assess_stack_structure(data["stacks"]["valid_composed_security"], data["components"])
    assert assessment.status is StructuralStatus.COMPATIBLE
    access = next(c for c in data["components"] if c["component_id"] == "fixture_access_ip")
    assert "native_access_security" in access["provides"]
    assert any(c["roles"] == ["end_to_end_security"] for c in data["components"])


def test_gateway_mediation_can_be_explicit_in_end_to_end_graph():
    data = load_fixture()
    assessment = assess_stack_structure(data["stacks"]["valid_gateway_mediated"], data["components"])
    assert assessment.status is StructuralStatus.COMPATIBLE


def test_wrong_transport_security_interface_is_hard_incompatible():
    data = load_fixture()
    assessment = assess_stack_structure(data["stacks"]["invalid_transport_security"], data["components"])
    assert assessment.status is StructuralStatus.INCOMPATIBLE
    assert any("binding_interface_not_provided" in error or "binding_interface_not_required" in error for error in assessment.errors)


def test_non_ip_access_cannot_satisfy_ip_transport_without_bridge():
    data = load_fixture()
    assessment = assess_stack_structure(data["stacks"]["invalid_missing_gateway"], data["components"])
    assert assessment.status is StructuralStatus.INCOMPATIBLE
    assert "unsatisfied_requirement:udp:ip_packet_service" in assessment.errors


def test_hard_feasibility_is_tristate_and_unknown_blocks_feasible_claim():
    data = load_fixture()
    constraints = data["hard_constraints"]
    cases = data["hard_constraint_cases"]
    assert evaluate_hard_constraints(cases["feasible"]["facts"], constraints).status is FeasibilityStatus.FEASIBLE
    assert evaluate_hard_constraints(cases["infeasible"]["facts"], constraints).status is FeasibilityStatus.INFEASIBLE
    assert evaluate_hard_constraints(cases["unresolved"]["facts"], constraints).status is FeasibilityStatus.UNRESOLVED
