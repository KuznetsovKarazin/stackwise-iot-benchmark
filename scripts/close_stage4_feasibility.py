from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.feasibility_closure import freeze_decision_blockers, lrfhss_radio_bound_diagnostic
from stackwise.provenance import write_run_manifest


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Close Stage 4 hard feasibility with explicit unresolved profile/boundary gaps.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage4f_feasibility_closure.yml"))
    ap.add_argument("--stage4e-summary", type=Path, default=Path("results/validation/stage4_hard_capability_review/summary.json"))
    ap.add_argument("--stage4e-matrix", type=Path, default=Path("results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv"))
    ap.add_argument("--stage4e-blockers", type=Path, default=Path("results/validation/stage4_hard_capability_review/remaining_decision_blockers.csv"))
    ap.add_argument("--lrfhss-evidence", type=Path, default=Path("data/analysis_ready/lorawan_lrfhss_energy_2024/evidence_records.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage4_feasibility_closure"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy.get("expected") or {}
    prior_summary = json.loads(args.stage4e_summary.read_text(encoding="utf-8"))
    matrix = _read_csv(args.stage4e_matrix)
    blockers = _read_csv(args.stage4e_blockers)
    lrfhss = _read_csv(args.lrfhss_evidence)

    frozen = freeze_decision_blockers(blockers, policy)
    budget_j = 0.2
    scenario_payload_bytes = 16
    bounds = lrfhss_radio_bound_diagnostic(
        lrfhss, budget_j=budget_j, scenario_payload_bytes=scenario_payload_bytes
    )

    counts = {"feasible": 0, "infeasible": 0, "unresolved": 0}
    for row in matrix:
        counts[str(row["status"])] += 1
    checkpoint = {
        "refined_scenarios": int(prior_summary["refined_scenarios"]),
        "candidates": int(prior_summary["candidates"]),
        "screening_rows": len(matrix),
        "feasible_rows": counts["feasible"],
        "infeasible_rows": counts["infeasible"],
        "unresolved_rows": counts["unresolved"],
        "frozen_decision_blockers": len(frozen),
        "blockers_resolved_by_stage4f": sum(bool(r["resolved_from_existing_evidence"]) for r in frozen),
        "blocker_dimensions": len({str(r["constraint_id"]) for r in frozen}),
        "blockers_requiring_operating_profile": sum(bool(r["operating_profile_required"]) for r in frozen),
        "lrfhss_radio_bound_rows": len(bounds),
        "lrfhss_radio_energy_exceeds_budget_rows": sum(bool(r["measured_radio_energy_exceeds_budget"]) for r in bounds),
        "lrfhss_same_payload_as_scenario_rows": sum(bool(r["payload_matches_scenario"]) for r in bounds),
        "lrfhss_whole_device_feasibility_resolved_rows": sum(bool(r["whole_device_feasibility_resolved"]) for r in bounds),
    }
    errors = [f"{k}:expected={expected.get(k)}:actual={v}" for k, v in checkpoint.items() if expected.get(k) != v]
    if errors:
        raise SystemExit("Stage-4F closure checkpoint failed: " + "; ".join(errors))

    args.output.mkdir(parents=True, exist_ok=True)
    frozen_csv = args.output / "frozen_decision_blockers.csv"
    _write_csv(frozen_csv, frozen, [
        "blocker_id","scenario_id","stack_id","constraint_id","stage4e_status","stage4f_status",
        "resolution_class","reason","operating_profile_required","operating_profile_fields",
        "future_resolution_evidence","source_authority","source_identifier","source_url",
        "resolved_from_existing_evidence",
    ])
    bound_csv = args.output / "lrfhss_radio_bound_diagnostic.csv"
    _write_csv(bound_csv, bounds, [
        "data_rate_mode","confirmation_mode","measured_payload_bytes","scenario_payload_bytes",
        "tx_power_dbm","radio_incremental_transaction_energy_j","whole_device_budget_j",
        "measured_radio_energy_exceeds_budget","payload_matches_scenario","measurement_boundary",
        "scenario_boundary","whole_device_feasibility_resolved","interpretation",
    ])
    profile_rows = []
    for row in frozen:
        for field in str(row["operating_profile_fields"]).split("|"):
            if field:
                profile_rows.append({
                    "blocker_id": row["blocker_id"], "scenario_id": row["scenario_id"],
                    "stack_id": row["stack_id"], "profile_field": field,
                    "required_before_numeric_bridge": True,
                })
    profile_csv = args.output / "stage5_operating_profile_requirements.csv"
    _write_csv(profile_csv, profile_rows, ["blocker_id","scenario_id","stack_id","profile_field","required_before_numeric_bridge"])

    handoff_rows = [
        {"rule_id":"freeze_stage4_statuses","rule":"Preserve the 21/39/3 Stage-4E tri-state matrix as the Stage-4 feasibility result.","authorised":True},
        {"rule_id":"do_not_coerce_unresolved","rule":"Do not convert the three frozen unresolved rows to feasible/infeasible without matched evidence or an explicit benchmark-profile refinement.","authorised":False},
        {"rule_id":"define_operating_profiles","rule":"Stage 5 may parameterise operating profiles for latency/energy bridges while preserving source boundaries.","authorised":True},
        {"rule_id":"lrfhss_bound_is_diagnostic","rule":"LR-FHSS radio-energy comparisons to 0.2 J are diagnostics only because payload and system boundary do not match the benchmark.","authorised":True},
        {"rule_id":"preference_compensation","rule":"Preference scores may not compensate for hard infeasibility or unresolved hard facts.","authorised":False},
        {"rule_id":"publication_mcda","rule":"Publication MCDA/ranking remains unauthorised at Stage-4F closure.","authorised":False},
    ]
    handoff_csv = args.output / "stage5_handoff_rules.csv"
    _write_csv(handoff_csv, handoff_rows, ["rule_id","rule","authorised"])

    summary = {
        "stage": policy["stage"],
        "stage4_status": policy["stage4_status"],
        **checkpoint,
        "stage4_feasibility_layer_closed": True,
        "unresolved_hard_rows_preserved": 3,
        "existing_core_four_fully_resolves_remaining_blockers": False,
        "candidate_operating_profile_parameterisation_required": True,
        "stage5_operating_profile_contract_authorised": True,
        "preference_scoring_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 4 closes with three explicit hard-feasibility unknowns rather than forcing scalar capabilities. "
            "The remaining Thread latency and LoRaWAN whole-device energy predicates are both boundary- and/or "
            "operating-profile dependent. Existing core-four evidence is insufficient to resolve them without a matched "
            "test/model or a versioned profile refinement."
        ),
        "next_scientific_step": (
            "Stage 5A: define explicit operating-profile records and bridge contracts for the frozen benchmark scenarios; "
            "retain the Stage-4 tri-state matrix and do not rank candidates."
        ),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = args.output / "run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/close_stage4_feasibility.py",
        inputs=[args.policy,args.stage4e_summary,args.stage4e_matrix,args.stage4e_blockers,args.lrfhss_evidence],
        outputs=[summary_path,frozen_csv,bound_csv,profile_csv,handoff_csv],
        parameters={"publication_mcda_authorised":False,"force_resolution_of_remaining_blockers":False},
    )

    print("Stage-4F hard-feasibility closure: OK")
    print(f"Feasible / infeasible / unresolved: {counts['feasible']} / {counts['infeasible']} / {counts['unresolved']}")
    print(f"Frozen decision blockers: {len(frozen)}")
    print(f"LR-FHSS profile diagnostics / >0.2 J radio rows: {len(bounds)} / {checkpoint['lrfhss_radio_energy_exceeds_budget_rows']}")
    print("Remaining blockers resolved from existing core-four evidence: NO")
    print("Operating-profile parameterisation required: YES")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
