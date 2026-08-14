from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.stack_model import (
    FeasibilityStatus,
    StructuralStatus,
    assess_stack_structure,
    evaluate_hard_constraints,
    validate_hard_constraint,
    validate_stack_candidate,
    validate_stack_component,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the STACKWISE Stage-4A typed stack and hard-feasibility contract.")
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures_stage4_stack_contract.yml"))
    parser.add_argument("--policy", type=Path, default=Path("datasets/stage4_stack_contract_policy.yml"))
    parser.add_argument("--output", type=Path, default=Path("results/validation/stage4_stack_contract"))
    args = parser.parse_args()

    fixtures = yaml.safe_load(args.fixtures.read_text(encoding="utf-8")) or {}
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy.get("expected") or {}

    components = fixtures.get("components") or []
    stacks = fixtures.get("stacks") or {}
    constraints = fixtures.get("hard_constraints") or []
    cases = fixtures.get("hard_constraint_cases") or {}

    errors: list[str] = []
    for component in components:
        errors.extend(f"component:{component.get('component_id')}:{e}" for e in validate_stack_component(component))
    for name, stack in stacks.items():
        errors.extend(f"stack:{name}:{e}" for e in validate_stack_candidate(stack))
    for constraint in constraints:
        errors.extend(f"constraint:{constraint.get('constraint_id')}:{e}" for e in validate_hard_constraint(constraint))

    structural = {name: assess_stack_structure(stack, components) for name, stack in stacks.items()}
    compatible = sum(result.status is StructuralStatus.COMPATIBLE for result in structural.values())
    incompatible = sum(result.status is StructuralStatus.INCOMPATIBLE for result in structural.values())

    hard_results = {
        name: evaluate_hard_constraints(case.get("facts") or {}, constraints)
        for name, case in cases.items()
    }
    feasible_cases = sum(result.status is FeasibilityStatus.FEASIBLE for result in hard_results.values())
    infeasible_cases = sum(result.status is FeasibilityStatus.INFEASIBLE for result in hard_results.values())
    unresolved_cases = sum(result.status is FeasibilityStatus.UNRESOLVED for result in hard_results.values())

    checkpoints = {
        "contract_fixture_components": len(components),
        "contract_fixture_stacks": len(stacks),
        "structurally_compatible_fixtures": compatible,
        "structurally_incompatible_fixtures": incompatible,
        "hard_constraint_fixture_cases": len(cases),
        "hard_constraint_feasible_cases": feasible_cases,
        "hard_constraint_infeasible_cases": infeasible_cases,
        "hard_constraint_unresolved_cases": unresolved_cases,
    }
    for key, value in checkpoints.items():
        if value != expected.get(key):
            errors.append(f"checkpoint:{key}:expected={expected.get(key)}:actual={value}")

    guards = policy.get("scientific_guards") or {}
    required_false = [
        "real_protocol_catalog_authorised_in_this_patch",
        "standards_claims_authorised_without_primary_source_verification",
        "unknown_hard_fact_counts_as_feasible",
        "mcda_authorised",
        "ranking_authorised",
        "stakeholder_weights_authorised",
        "default_stochastic_priors_authorised",
    ]
    for key in required_false:
        if guards.get(key) is not False:
            errors.append(f"scientific_guard_not_false:{key}")

    if errors:
        raise SystemExit("Stage-4A contract validation failed: " + "; ".join(errors[:30]))

    summary = {
        "stage": policy.get("stage"),
        "stage4_status": policy.get("stage4_status"),
        **checkpoints,
        "structural_status_by_fixture": {name: result.status.value for name, result in structural.items()},
        "hard_feasibility_status_by_fixture": {name: result.status.value for name, result in hard_results.items()},
        "security_model": "compositional_native_plus_end_to_end_allowed",
        "gateway_mediation_model": "explicit_component_graph",
        "unknown_hard_fact_policy": "blocks_feasible_claim",
        "real_protocol_catalog_materialised": False,
        "standards_primary_source_verification_complete": False,
        "mcda_authorised": False,
        "ranking_authorised": False,
        "stakeholder_weights_authorised": False,
        "default_stochastic_priors_authorised": False,
        "next_scientific_step": policy.get("next_scientific_step"),
    }

    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / "summary.json"
    manifest_path = args.output / "run_manifest.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_run_manifest(
        manifest_path,
        command="python scripts/validate_stage4_stack_contract.py",
        inputs=[args.fixtures, args.policy],
        outputs=[summary_path],
        parameters={"stage4_status": summary["stage4_status"], "mcda_authorised": False},
    )

    print("Stage-4A stack contract: OK")
    print(f"Fixture components: {len(components)}")
    print(f"Fixture stacks: {len(stacks)} ({compatible} compatible, {incompatible} incompatible)")
    print(f"Hard feasibility cases: {len(cases)} ({feasible_cases} feasible, {infeasible_cases} infeasible, {unresolved_cases} unresolved)")
    print("Security forced into one exclusive layer: NO")
    print("Unknown hard fact counts as feasible: NO")
    print("Real protocol catalog materialised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
