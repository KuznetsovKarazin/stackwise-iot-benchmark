from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.scenario_screening import compose_scenario_candidate_facts, load_benchmark_scenarios, validate_benchmark_scenario
from stackwise.hard_capability_review import build_refined_scenarios, overlay_reviewed_capabilities
from stackwise.stack_catalog import load_component_catalog
from stackwise.stack_model import evaluate_hard_constraints


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Review Stage-4D decision blockers with primary-source hard-capability evidence.")
    ap.add_argument("--catalog", type=Path, default=Path("datasets/stack_component_catalog.yml"))
    ap.add_argument("--candidates", type=Path, default=Path("datasets/stage4_candidate_stacks.yml"))
    ap.add_argument("--scenarios", type=Path, default=Path("datasets/stage4_benchmark_scenarios.yml"))
    ap.add_argument("--review", type=Path, default=Path("datasets/stage4e_hard_capability_review.yml"))
    ap.add_argument("--stage4d-unresolved", type=Path, default=Path("results/validation/stage4_hard_scenarios/unresolved_hard_facts.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage4_hard_capability_review"))
    args = ap.parse_args()

    catalog = load_component_catalog(args.catalog)
    candidate_payload = yaml.safe_load(args.candidates.read_text(encoding="utf-8")) or {}
    scenario_payload = load_benchmark_scenarios(args.scenarios)
    review = yaml.safe_load(args.review.read_text(encoding="utf-8")) or {}
    stacks = candidate_payload.get("candidate_stacks") or []
    expected = review.get("expected") or {}

    with args.stage4d_unresolved.open(newline="", encoding="utf-8") as handle:
        prior_unknowns = list(csv.DictReader(handle))
    prior_blockers = [r for r in prior_unknowns if str(r.get("decision_blocking")).lower() == "true"]

    scenarios, refinement_rows = build_refined_scenarios(scenario_payload)
    errors: list[str] = []
    for s in scenarios:
        errors.extend(f"scenario:{s['scenario_id']}:{e}" for e in validate_benchmark_scenario(s))

    capabilities: list[dict[str, Any]] = []
    for stack in stacks:
        capabilities.append(overlay_reviewed_capabilities(stack, catalog, review))
    cap_by_id = {r["stack_id"]: r for r in capabilities}

    matrix_rows: list[dict[str, Any]] = []
    constraint_rows: list[dict[str, Any]] = []
    unknown_rows: list[dict[str, Any]] = []
    counts = {"feasible": 0, "infeasible": 0, "unresolved": 0}
    for scenario in scenarios:
        for stack in stacks:
            caps = cap_by_id[str(stack["stack_id"])]
            facts = compose_scenario_candidate_facts(caps, scenario)
            assessment = evaluate_hard_constraints(facts, scenario.get("hard_constraints") or [])
            status = assessment.status.value
            counts[status] += 1
            blocking = status == "unresolved"
            matrix_rows.append({
                "scenario_id": scenario["scenario_id"],
                "stack_id": stack["stack_id"],
                "status": status,
                "access_family": caps["access_family"],
                "device_network_mode": caps["device_network_mode"],
                "idle_cell_reselection_supported_verified": caps.get("idle_cell_reselection_supported_verified"),
                "connected_mode_handover_supported_verified": caps.get("connected_mode_handover_supported_verified"),
                "guaranteed_max_end_to_end_latency_ms": caps.get("guaranteed_max_end_to_end_latency_ms"),
                "expected_device_energy_per_report_j": caps.get("expected_device_energy_per_report_j"),
            })
            for result in assessment.results:
                row = {
                    "scenario_id": scenario["scenario_id"],
                    "stack_id": stack["stack_id"],
                    "overall_status": status,
                    "constraint_id": result.constraint_id,
                    "constraint_status": result.status,
                    "reason": result.reason,
                    "decision_blocking": bool(blocking and result.status == "unknown"),
                }
                constraint_rows.append(row)
                if result.status == "unknown":
                    unknown_rows.append(row)

    blocking_unknowns = [r for r in unknown_rows if r["decision_blocking"]]
    blocker_dims = sorted({r["constraint_id"] for r in blocking_unknowns})
    checkpoints = {
        "original_decision_blockers": len(prior_blockers),
        "reviewed_claims": len(review.get("capability_claims") or []),
        "refined_scenarios": len(scenarios),
        "candidates": len(stacks),
        "screening_rows": len(matrix_rows),
        "feasible_rows": counts["feasible"],
        "infeasible_rows": counts["infeasible"],
        "unresolved_rows": counts["unresolved"],
        "unknown_hard_results": len(unknown_rows),
        "decision_blocking_unknown_results": len(blocking_unknowns),
        "remaining_blocker_dimensions": len(blocker_dims),
    }
    for key, actual in checkpoints.items():
        if expected.get(key) != actual:
            errors.append(f"checkpoint:{key}:expected={expected.get(key)}:actual={actual}")
    if errors:
        raise SystemExit("Stage-4E blocker review failed: " + "; ".join(sorted(set(errors))[:100]))

    args.output.mkdir(parents=True, exist_ok=True)
    review_rows = []
    for c in review.get("capability_claims") or []:
        review_rows.append({
            "claim_id": c["claim_id"], "access_family": c["access_family"], "capability_key": c["capability_key"],
            "value": c.get("value"), "verification_status": c["verification_status"],
            "source_authority": c["source_authority"], "source_identifier": c["source_identifier"],
            "source_url": c.get("source_url"), "interpretation": c["interpretation"],
        })
    review_csv = args.output / "hard_capability_evidence_review.csv"
    _write_csv(review_csv, review_rows, ["claim_id","access_family","capability_key","value","verification_status","source_authority","source_identifier","source_url","interpretation"])

    refinement_csv = args.output / "scenario_semantics_refinement.csv"
    _write_csv(refinement_csv, refinement_rows, ["original_scenario_id","refined_scenario_id","mobility_semantics","post_hoc_preference_choice"])

    cap_csv = args.output / "reviewed_candidate_hard_capabilities.csv"
    _write_csv(cap_csv, capabilities, ["stack_id","access_family","requires_operator_service","requires_lorawan_service","requires_thread_border_router","device_network_mode","explicit_tls_or_dtls_present","lwm2m_management_available","max_application_payload_bytes","guaranteed_max_end_to_end_latency_ms","expected_device_energy_per_report_j","mobility_supported_verified","idle_cell_reselection_supported_verified","connected_mode_handover_supported_verified"])

    matrix_csv = args.output / "refined_hard_feasibility_matrix.csv"
    _write_csv(matrix_csv, matrix_rows, ["scenario_id","stack_id","status","access_family","device_network_mode","idle_cell_reselection_supported_verified","connected_mode_handover_supported_verified","guaranteed_max_end_to_end_latency_ms","expected_device_energy_per_report_j"])

    remaining_csv = args.output / "remaining_decision_blockers.csv"
    _write_csv(remaining_csv, blocking_unknowns, ["scenario_id","stack_id","overall_status","constraint_id","constraint_status","reason","decision_blocking"])

    by_scenario: dict[str, dict[str, int]] = {}
    for row in matrix_rows:
        by_scenario.setdefault(row["scenario_id"], {"feasible":0,"infeasible":0,"unresolved":0})[row["status"]] += 1
    summary = {
        "stage": review["stage"],
        "stage4_status": review["stage4_status"],
        **checkpoints,
        "status_by_scenario": by_scenario,
        "mobility_boolean_superseded_by_explicit_variants": True,
        "single_mobility_semantics_selected": False,
        "thread_500ms_latency_guarantee_verified": False,
        "lorawan_whole_device_energy_budget_verified": False,
        "publication_mcda_authorised": False,
        "ranking_authorised": False,
        "next_scientific_step": "Stage-4F address the three remaining decision blockers (Thread stack-level latency and two LoRaWAN whole-device energy facts) only if defensible bridge/test evidence is available; otherwise freeze them unresolved and proceed to non-preference feasibility analysis.",
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = args.output / "run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/review_stage4_hard_blockers.py",
        inputs=[args.catalog,args.candidates,args.scenarios,args.review,args.stage4d_unresolved],
        outputs=[summary_path,review_csv,refinement_csv,cap_csv,matrix_csv,remaining_csv],
        parameters={"publication_mcda_authorised":False,"single_mobility_semantics_selected":False},
    )

    print("Stage-4E decision-blocker review: OK")
    print(f"Original blockers / remaining blockers: {len(prior_blockers)} / {len(blocking_unknowns)}")
    print(f"Refined scenarios / screening rows: {len(scenarios)} / {len(matrix_rows)}")
    print(f"Feasible / infeasible / unresolved: {counts['feasible']} / {counts['infeasible']} / {counts['unresolved']}")
    print("Single mobility semantics selected: NO")
    print("Thread 500 ms guarantee inferred from 'low latency': NO")
    print("Whole-device energy inferred from radio-only LR-FHSS energy: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
