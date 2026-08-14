from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.scenario_screening import (
    derive_candidate_hard_capabilities,
    load_benchmark_scenarios,
    screening_matrix,
    validate_benchmark_scenario,
)
from stackwise.stack_catalog import load_component_catalog


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate Stage-4D benchmark hard-feasibility scenarios.")
    ap.add_argument("--catalog", type=Path, default=Path("datasets/stack_component_catalog.yml"))
    ap.add_argument("--candidates", type=Path, default=Path("datasets/stage4_candidate_stacks.yml"))
    ap.add_argument("--scenarios", type=Path, default=Path("datasets/stage4_benchmark_scenarios.yml"))
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage4_hard_scenario_policy.yml"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage4_hard_scenarios"))
    args = ap.parse_args()

    catalog = load_component_catalog(args.catalog)
    candidate_payload = yaml.safe_load(args.candidates.read_text(encoding="utf-8")) or {}
    scenario_payload = load_benchmark_scenarios(args.scenarios)
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    stacks = candidate_payload.get("candidate_stacks") or []
    scenarios = scenario_payload.get("scenarios") or []
    errors: list[str] = []

    if scenario_payload.get("scientific_policy", {}).get("quantitative_context_implies_hard_constraint") is not False:
        errors.append("quantitative_context_must_not_auto_promote_to_hard")
    for scenario in scenarios:
        for err in validate_benchmark_scenario(scenario):
            errors.append(f"scenario_schema:{scenario.get('scenario_id')}:{err}")

    capabilities = [derive_candidate_hard_capabilities(stack, catalog) for stack in stacks]
    cap_by_id = {row["stack_id"]: row for row in capabilities}
    if len(cap_by_id) != len(stacks):
        errors.append("candidate_capability_mapping_not_one_to_one")

    matrix = screening_matrix(stacks, catalog, scenarios)
    counts = {"feasible": 0, "infeasible": 0, "unresolved": 0}
    unknown_rows: list[dict] = []
    constraint_rows: list[dict] = []
    for row in matrix:
        counts[row["status"]] += 1
        blocking = row["status"] == "unresolved"
        for result in row["constraint_results"]:
            constraint_rows.append(
                {
                    "scenario_id": row["scenario_id"],
                    "stack_id": row["stack_id"],
                    "overall_status": row["status"],
                    "constraint_id": result["constraint_id"],
                    "constraint_status": result["status"],
                    "reason": result["reason"],
                    "decision_blocking_unknown": blocking and result["status"] == "unknown",
                }
            )
            if result["status"] == "unknown":
                unknown_rows.append(
                    {
                        "scenario_id": row["scenario_id"],
                        "stack_id": row["stack_id"],
                        "overall_status": row["status"],
                        "constraint_id": result["constraint_id"],
                        "reason": result["reason"],
                        "decision_blocking": blocking,
                    }
                )

    blocking_unknowns = sum(bool(row["decision_blocking"]) for row in unknown_rows)
    expected = policy.get("expected") or {}
    checkpoints = {
        "scenarios": len(scenarios),
        "candidates": len(stacks),
        "screening_rows": len(matrix),
        "feasible_rows": counts["feasible"],
        "infeasible_rows": counts["infeasible"],
        "unresolved_rows": counts["unresolved"],
        "unknown_hard_results": len(unknown_rows),
        "decision_blocking_unknown_results": blocking_unknowns,
        "candidate_capability_rows": len(capabilities),
    }
    for key, actual in checkpoints.items():
        if expected.get(key) != actual:
            errors.append(f"checkpoint:{key}:expected={expected.get(key)}:actual={actual}")
    for key, value in (policy.get("scientific_guards") or {}).items():
        if value is not False:
            errors.append(f"scientific_guard_not_false:{key}")

    if errors:
        raise SystemExit("Stage-4D hard-scenario validation failed: " + "; ".join(sorted(set(errors))[:100]))

    args.output.mkdir(parents=True, exist_ok=True)

    scenario_rows = []
    for scenario in scenarios:
        q = scenario["quantitative_context"]
        d = scenario["deployment_facts"]
        scenario_rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "name": scenario["name"],
                "archetype": scenario["archetype"],
                "payload_bytes": q["payload_bytes"],
                "reporting_interval_s": q["reporting_interval_s"],
                "target_end_to_end_latency_ms": q["target_end_to_end_latency_ms"],
                "whole_device_energy_budget_per_report_j": q.get("whole_device_energy_budget_per_report_j"),
                "cellular_access_service_available_at_site": d["cellular_access_service_available_at_site"],
                "lorawan_access_service_available_at_site": d["lorawan_access_service_available_at_site"],
                "thread_border_router_available_at_site": d["thread_border_router_available_at_site"],
                "hard_constraint_ids": "|".join(c["constraint_id"] for c in scenario["hard_constraints"]),
                "assumption_status": scenario["assumption_status"],
            }
        )
    scenario_csv = args.output / "benchmark_scenarios.csv"
    _write_csv(
        scenario_csv,
        scenario_rows,
        [
            "scenario_id", "name", "archetype", "payload_bytes", "reporting_interval_s",
            "target_end_to_end_latency_ms", "whole_device_energy_budget_per_report_j",
            "cellular_access_service_available_at_site", "lorawan_access_service_available_at_site",
            "thread_border_router_available_at_site", "hard_constraint_ids", "assumption_status",
        ],
    )

    capability_csv = args.output / "candidate_hard_capabilities.csv"
    _write_csv(
        capability_csv,
        capabilities,
        [
            "stack_id", "access_family", "requires_operator_service", "requires_lorawan_service",
            "requires_thread_border_router", "device_network_mode", "explicit_tls_or_dtls_present",
            "lwm2m_management_available", "max_application_payload_bytes",
            "guaranteed_max_end_to_end_latency_ms", "expected_device_energy_per_report_j",
            "mobility_supported_verified",
        ],
    )

    matrix_rows = []
    for row in matrix:
        scenario = next(x for x in scenarios if x["scenario_id"] == row["scenario_id"])
        matrix_rows.append(
            {
                "scenario_id": row["scenario_id"],
                "stack_id": row["stack_id"],
                "status": row["status"],
                "payload_bytes": scenario["quantitative_context"]["payload_bytes"],
                "reporting_interval_s": scenario["quantitative_context"]["reporting_interval_s"],
                "target_end_to_end_latency_ms": scenario["quantitative_context"]["target_end_to_end_latency_ms"],
                "whole_device_energy_budget_per_report_j": scenario["quantitative_context"].get("whole_device_energy_budget_per_report_j"),
                "access_family": row["facts"]["access_family"],
                "device_network_mode": row["facts"]["device_network_mode"],
                "access_infrastructure_satisfied": row["facts"]["access_infrastructure_satisfied"],
                "full_end_to_end_empirical_support": False,
            }
        )
    matrix_csv = args.output / "hard_feasibility_matrix.csv"
    _write_csv(
        matrix_csv,
        matrix_rows,
        [
            "scenario_id", "stack_id", "status", "payload_bytes", "reporting_interval_s",
            "target_end_to_end_latency_ms", "whole_device_energy_budget_per_report_j",
            "access_family", "device_network_mode", "access_infrastructure_satisfied",
            "full_end_to_end_empirical_support",
        ],
    )

    constraint_csv = args.output / "hard_constraint_results.csv"
    _write_csv(
        constraint_csv,
        constraint_rows,
        ["scenario_id", "stack_id", "overall_status", "constraint_id", "constraint_status", "reason", "decision_blocking_unknown"],
    )
    unresolved_csv = args.output / "unresolved_hard_facts.csv"
    _write_csv(
        unresolved_csv,
        unknown_rows,
        ["scenario_id", "stack_id", "overall_status", "constraint_id", "reason", "decision_blocking"],
    )

    by_scenario: dict[str, dict[str, int]] = {}
    for row in matrix:
        entry = by_scenario.setdefault(row["scenario_id"], {"feasible": 0, "infeasible": 0, "unresolved": 0})
        entry[row["status"]] += 1

    summary = {
        "stage": policy.get("stage"),
        "stage4_status": policy.get("stage4_status"),
        **checkpoints,
        "status_by_scenario": by_scenario,
        "scenarios_are_synthetic_reproducible_benchmarks": True,
        "quantitative_context_auto_promoted_to_hard": False,
        "feasible_means_passed_declared_hard_constraints_only": True,
        "feasible_means_full_empirical_support": False,
        "hard_scenario_screening_complete": True,
        "mcda_authorised": False,
        "ranking_authorised": False,
        "next_scientific_step": policy.get("next_scientific_step"),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = args.output / "run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/evaluate_stage4_hard_scenarios.py",
        inputs=[args.catalog, args.candidates, args.scenarios, args.policy],
        outputs=[summary_path, scenario_csv, capability_csv, matrix_csv, constraint_csv, unresolved_csv],
        parameters={"mcda_authorised": False, "ranking_authorised": False},
    )

    print("Stage-4D quantitative benchmark hard screening: OK")
    print(f"Scenarios / candidates / rows: {len(scenarios)} / {len(stacks)} / {len(matrix)}")
    print(f"Feasible / infeasible / unresolved: {counts['feasible']} / {counts['infeasible']} / {counts['unresolved']}")
    print(f"Unknown hard results / decision-blocking: {len(unknown_rows)} / {blocking_unknowns}")
    print("Quantitative context auto-promoted to hard: NO")
    print("Feasible implies full empirical support: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
