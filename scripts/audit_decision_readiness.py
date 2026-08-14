from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.decision_readiness import (
    audit_summary,
    build_candidate_target_readiness,
    build_gap_priority_rows,
    feasibility_counts,
    scenario_readiness_rows,
)
from stackwise.provenance import write_run_manifest


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit scenario x candidate x decision-target readiness without scoring or ranking stacks.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5e_decision_readiness_policy.yml"))
    ap.add_argument("--feasibility", type=Path, default=Path("results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv"))
    ap.add_argument("--candidates", type=Path, default=Path("results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv"))
    ap.add_argument("--profiles", type=Path, default=Path("results/validation/stage5_operating_profiles/operating_profiles.csv"))
    ap.add_argument("--bridges", type=Path, default=Path("results/validation/stage5_operating_profiles/bridge_contracts.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_decision_readiness"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    feasibility = _read_csv(args.feasibility)
    candidates = _read_csv(args.candidates)
    profiles = _read_csv(args.profiles)
    bridges = _read_csv(args.bridges)

    counts = feasibility_counts(feasibility)
    expected = policy["expected"]
    for status in ("feasible", "infeasible", "unresolved"):
        key = f"stage4_{status}_rows"
        if counts[status] != int(expected[key]):
            raise ValueError(f"Frozen Stage-4 matrix drift: expected {status}={expected[key]}, observed {counts[status]}.")
    if len(candidates) != int(expected["candidate_stacks"]):
        raise ValueError("Candidate-stack count drifted from the Stage-5E contract.")
    if len(policy["decision_targets"]) != int(expected["decision_targets"]):
        raise ValueError("Decision-target count drifted from the Stage-5E contract.")

    readiness = build_candidate_target_readiness(
        feasibility_rows=feasibility,
        candidate_rows=candidates,
        profile_rows=profiles,
        bridge_rows=bridges,
        policy=policy,
    )
    scenarios = scenario_readiness_rows(readiness)
    gaps = build_gap_priority_rows(readiness, policy)
    summary_obj = audit_summary(readiness, scenarios, policy)

    args.output.mkdir(parents=True, exist_ok=True)
    readiness_path = args.output / "candidate_target_readiness.csv"
    scenario_path = args.output / "scenario_readiness.csv"
    gaps_path = args.output / "gap_priorities.csv"
    handoff_path = args.output / "stage5f_handoff_rules.csv"
    summary_path = args.output / "summary.json"

    _write_csv(readiness_path, readiness)
    _write_csv(scenario_path, scenarios)
    _write_csv(gaps_path, gaps)

    handoff = [
        {"rule_id": "freeze_stage4_matrix", "policy_state": "required", "rule": "Preserve the frozen Stage-4 feasibility result 21 feasible / 39 infeasible / 3 unresolved."},
        {"rule_id": "bridgeable_is_not_ready", "policy_state": "required", "rule": "C1/BRIDGEABLE source evidence is not a decision-ready target until the target bridge is validated and materialised under an explicit profile."},
        {"rule_id": "first_decision_slice", "policy_state": "authorised_for_gap_planning_only", "rule": "Use feasibility-conditioned energy/report + lifecycle cost as the first minimal decision-readiness lens; this does not authorise scoring."},
        {"rule_id": "next_existing_evidence_bridge", "policy_state": "authorised", "rule": "Stage 5F may implement the cellular IP whole-device/application-report energy bridge from Vomhoff evidence for the four IP cellular candidate stacks."},
        {"rule_id": "cellular_bridge_profile_first", "policy_state": "required", "rule": "Before numerical cellular report-energy composition, freeze scenario-specific reporting/session/accounting profiles and source-to-candidate application-context assumptions."},
        {"rule_id": "lifecycle_cost_separate_contract", "policy_state": "required", "rule": "Build lifecycle cost as a separate dated evidence contract; do not reuse configs/fleet.yml smoke costs as publication evidence."},
        {"rule_id": "soft_latency_reuse", "policy_state": "prohibited", "rule": "Do not automatically re-score latency/coverage after they have already acted as hard feasibility constraints; include them as soft criteria only with a separate justified decision role and comparable evidence."},
        {"rule_id": "publication_mcda", "policy_state": "prohibited", "rule": "Publication MCDA/ranking remains blocked after Stage 5E."},
        {"rule_id": "fleet_optimisation", "policy_state": "prohibited", "rule": "Publication fleet optimisation remains blocked until at least one decision-ready multi-candidate slice and lifecycle-cost contract exist."},
    ]
    _write_csv(handoff_path, handoff)

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        "stage4_feasible_rows": counts["feasible"],
        "stage4_infeasible_rows": counts["infeasible"],
        "stage4_unresolved_rows": counts["unresolved"],
        "candidate_stacks": len(candidates),
        "decision_targets": len(policy["decision_targets"]),
        "audited_candidate_rows": summary_obj.audited_candidate_rows,
        "audited_target_rows": summary_obj.audited_target_rows,
        "ready_target_rows": summary_obj.ready_target_rows,
        "feasible_candidate_rows": summary_obj.feasible_candidate_rows,
        "feasible_first_slice_fully_ready_rows": summary_obj.feasible_first_slice_fully_ready_rows,
        "feasible_cellular_ip_rows": summary_obj.feasible_cellular_ip_rows,
        "cellular_ip_energy_unlock_scenarios": summary_obj.cellular_ip_energy_unlock_scenarios,
        "first_decision_slice_id": policy["priority_policy"]["first_decision_slice_id"],
        "preferred_next_existing_evidence_bridge": policy["priority_policy"]["preferred_next_existing_evidence_bridge"],
        "preference_scoring_authorised": bool(policy["scientific_policy"]["preference_scoring_authorised"]),
        "publication_mcda_authorised": bool(policy["scientific_policy"]["publication_mcda_authorised"]),
        "fleet_optimisation_authorised": bool(policy["scientific_policy"]["fleet_optimisation_authorised"]),
        "interpretation": "The frozen feasibility layer already contains multi-candidate scenarios, but no target row is currently decision-ready at the canonical target boundary. Bridgeable source evidence must not be mistaken for a materialised decision estimand. For a feasibility-conditioned first decision slice, lifecycle cost is a cross-cutting missing target and the highest-leverage bridge using only existing empirical evidence is cellular IP application-report energy from Vomhoff: it affects 10 feasible candidate incidences and would create an energy-comparable set of at least two feasible candidates in three scenarios. This remains gap planning, not ranking.",
        "next_scientific_step": "Stage 5F: define scenario-specific cellular IP report profiles and validate a Vomhoff phase-to-application-report energy bridge for the four IP cellular candidates. Preserve physical-run bootstrap dependence, explicitly model application-context mismatch, and do not yet score or rank stacks. In parallel/next, define a separate lifecycle-cost evidence contract.",
        "candidate_target_readiness_artifact": str(readiness_path),
        "scenario_readiness_artifact": str(scenario_path),
        "gap_priorities_artifact": str(gaps_path),
        "stage5f_handoff_rules_artifact": str(handoff_path),
    }
    manifest_path = args.output / "run_manifest.json"
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        manifest_path,
        command="python scripts/audit_decision_readiness.py",
        inputs=[args.policy, args.feasibility, args.candidates, args.profiles, args.bridges],
        outputs=[readiness_path, scenario_path, gaps_path, handoff_path, summary_path],
        parameters={
            "preserve_stage4_matrix": True,
            "first_decision_slice": policy["priority_policy"]["first_decision_slice_id"],
            "preference_scoring_authorised": False,
            "publication_mcda_authorised": False,
            "fleet_optimisation_authorised": False,
        },
    )

    print("Stage-5E decision-readiness audit: OK")
    print(f"Audited candidates / target rows: {summary_obj.audited_candidate_rows} / {summary_obj.audited_target_rows}")
    print(f"Ready target rows: {summary_obj.ready_target_rows}")
    print(f"Feasible first-slice-ready candidates: {summary_obj.feasible_first_slice_fully_ready_rows}")
    print(f"Cellular-IP feasible incidences / energy-unlock scenarios: {summary_obj.feasible_cellular_ip_rows} / {summary_obj.cellular_ip_energy_unlock_scenarios}")


if __name__ == "__main__":
    main()
