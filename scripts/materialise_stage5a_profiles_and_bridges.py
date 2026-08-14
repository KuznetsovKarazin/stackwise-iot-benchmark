from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.profile_bridge import (
    assess_bridge_readiness,
    assess_profile,
    flatten_profile_fields,
    validate_bridge_contract,
    validate_operating_profile,
)
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


def _load_scenarios(path: Path) -> dict[str, dict[str, Any]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(row["scenario_id"]): row for row in doc.get("scenarios") or []}


def main() -> None:
    ap = argparse.ArgumentParser(description="Materialise Stage-5A operating profiles and typed bridge contracts.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5a_operating_profile_bridge_contracts.yml"))
    ap.add_argument("--stage4f-summary", type=Path, default=Path("results/validation/stage4_feasibility_closure/summary.json"))
    ap.add_argument("--stage4f-blockers", type=Path, default=Path("results/validation/stage4_feasibility_closure/frozen_decision_blockers.csv"))
    ap.add_argument("--stage4f-profile-requirements", type=Path, default=Path("results/validation/stage4_feasibility_closure/stage5_operating_profile_requirements.csv"))
    ap.add_argument("--scenarios", type=Path, default=Path("datasets/stage4_benchmark_scenarios.yml"))
    ap.add_argument("--stage3-state", type=Path, default=Path("data/analysis_ready/core_four_uncertainty/stage3_uncertainty_state.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_operating_profiles"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy.get("expected") or {}
    scientific_policy = policy.get("scientific_policy") or {}
    prior = json.loads(args.stage4f_summary.read_text(encoding="utf-8"))
    blockers = _read_csv(args.stage4f_blockers)
    stage4f_requirements = _read_csv(args.stage4f_profile_requirements)
    scenarios = _load_scenarios(args.scenarios)
    stage3_state = _read_csv(args.stage3_state)
    profiles = list(policy.get("operating_profiles") or [])
    bridges = list(policy.get("bridge_contracts") or [])

    if prior.get("stage4_status") != "closed_with_explicit_profile_and_boundary_unknowns":
        raise SystemExit("Stage-5A requires closed Stage-4F feasibility status.")
    if (int(prior["feasible_rows"]), int(prior["infeasible_rows"]), int(prior["unresolved_rows"])) != (21, 39, 3):
        raise SystemExit("Stage-5A refuses to alter the frozen Stage-4 matrix.")

    blocker_pairs = {(r["scenario_id"], r["stack_id"]) for r in blockers}
    profile_pairs = {(str(p["scenario_id"]), str(p["stack_id"])) for p in profiles}
    if blocker_pairs != profile_pairs:
        raise SystemExit(f"Operating profile pairs must equal frozen blocker pairs: blockers={blocker_pairs} profiles={profile_pairs}")

    profile_errors = {p["profile_id"]: validate_operating_profile(p) for p in profiles}
    bridge_errors = {b["bridge_id"]: validate_bridge_contract(b) for b in bridges}
    bad_profiles = {k: v for k, v in profile_errors.items() if v}
    bad_bridges = {k: v for k, v in bridge_errors.items() if v}
    if bad_profiles or bad_bridges:
        raise SystemExit(f"Stage-5A schema/contract validation failed: profiles={bad_profiles}; bridges={bad_bridges}")

    # Check scenario-derived context rather than trusting duplicated YAML values.
    for profile in profiles:
        scenario = scenarios[str(profile["scenario_id"])]
        context = scenario.get("quantitative_context") or {}
        field_map = {str(f["field_id"]): f for f in profile["fields"]}
        payload = field_map.get("application_payload_bytes")
        if payload and payload.get("status") == "known" and payload.get("provenance_status") == "scenario_derived":
            if int(payload["value"]) != int(context["payload_bytes"]):
                raise SystemExit(f"Scenario payload mismatch for {profile['profile_id']}")
        interval = field_map.get("reporting_interval_s")
        if interval and interval.get("status") == "known" and interval.get("provenance_status") == "scenario_derived":
            if float(interval["value"]) != float(context["reporting_interval_s"]):
                raise SystemExit(f"Scenario reporting interval mismatch for {profile['profile_id']}")

    assessments = [assess_profile(p) for p in profiles]
    field_rows = flatten_profile_fields(profiles)
    profile_index = {(str(p["scenario_id"]), str(p["stack_id"])): p for p in profiles}
    readiness = [assess_bridge_readiness(b, profile_index[(str(b["scenario_id"]), str(b["stack_id"]))]) for b in bridges]

    # Stage-4F minimum required field reconciliation. These 22 fields must all exist in Stage-5A.
    field_lookup = {(r["scenario_id"], r["stack_id"], r["field_id"]): r for r in field_rows}
    required_satisfied = 0
    required_unresolved = 0
    for req in stage4f_requirements:
        key = (req["scenario_id"], req["stack_id"], req["profile_field"])
        row = field_lookup.get(key)
        if row is None:
            raise SystemExit(f"Stage-5A profile omits Stage-4F required field: {key}")
        if row["status"] == "known":
            required_satisfied += 1
        else:
            required_unresolved += 1

    # Verify the only empirical source used by a bridge retains Stage-3 single-trace semantics.
    lrfhss_state = [
        r for r in stage3_state
        if r.get("dataset_id") == "lorawan_lrfhss_energy_2024"
        and r.get("metric_id") == "radio_incremental_transaction_energy_j"
    ]
    if len(lrfhss_state) != 1 or lrfhss_state[0].get("resolution_class") != "explicit_epistemic_gap":
        raise SystemExit("LR-FHSS bridge must inherit Stage-3 explicit_epistemic_gap semantics.")

    known = sum(r["status"] == "known" for r in field_rows)
    unresolved = sum(r["status"] == "unresolved" for r in field_rows)
    complete = sum(a.completeness == "complete" for a in assessments)
    partial = sum(a.completeness == "partial" for a in assessments)
    ready = sum(r.status == "ready" for r in readiness)
    blocked_profile = sum(bool(r.unresolved_profile_fields) for r in readiness)
    no_source = sum((b.get("source_evidence") or {}).get("status") == "no_matched_source" for b in bridges)
    transform_required = sum((b.get("boundary_mapping") or {}).get("status") == "explicit_transform_required" for b in bridges)

    checkpoint = {
        "stage4_feasible_rows": int(prior["feasible_rows"]),
        "stage4_infeasible_rows": int(prior["infeasible_rows"]),
        "stage4_unresolved_rows": int(prior["unresolved_rows"]),
        "operating_profiles": len(profiles),
        "operating_profile_field_rows": len(field_rows),
        "known_profile_fields": known,
        "unresolved_profile_fields": unresolved,
        "stage4f_required_fields": len(stage4f_requirements),
        "stage4f_required_fields_satisfied_from_scenario": required_satisfied,
        "stage4f_required_fields_unresolved": required_unresolved,
        "complete_profiles": complete,
        "partial_profiles": partial,
        "bridge_contracts": len(bridges),
        "bridges_ready_for_numeric_evaluation": ready,
        "bridges_blocked_by_unresolved_profile": blocked_profile,
        "bridges_with_no_matched_source": no_source,
        "bridges_with_boundary_transform_required": transform_required,
        "numeric_bridge_outputs": 0,
    }
    errors = [f"{k}:expected={expected.get(k)}:actual={v}" for k, v in checkpoint.items() if expected.get(k) != v]
    if errors:
        raise SystemExit("Stage-5A checkpoint failed: " + "; ".join(errors))

    if any(bool(scientific_policy.get(k)) for k in ["numeric_bridge_outputs_authorised", "preference_scoring_authorised", "publication_mcda_authorised"]):
        raise SystemExit("Stage-5A policy unexpectedly authorises numerical bridge output or ranking.")

    args.output.mkdir(parents=True, exist_ok=True)
    profiles_csv = args.output / "operating_profiles.csv"
    _write_csv(profiles_csv, [
        {
            "profile_id": a.profile_id,
            "scenario_id": p["scenario_id"],
            "stack_id": p["stack_id"],
            "scientific_status": p["scientific_status"],
            "completeness": a.completeness,
            "known_required_fields": "|".join(a.known_fields),
            "unresolved_required_fields": "|".join(a.unresolved_fields),
            "known_required_field_count": len(a.known_fields),
            "unresolved_required_field_count": len(a.unresolved_fields),
        }
        for p, a in zip(profiles, assessments)
    ], ["profile_id","scenario_id","stack_id","scientific_status","completeness","known_required_fields","unresolved_required_fields","known_required_field_count","unresolved_required_field_count"])

    fields_csv = args.output / "operating_profile_fields.csv"
    _write_csv(fields_csv, field_rows, ["profile_id","scenario_id","stack_id","field_id","status","value","unit","provenance_status","provenance_ref","required_for_numeric_bridge","notes"])

    contracts_csv = args.output / "bridge_contracts.csv"
    contract_rows = []
    for bridge in bridges:
        source = bridge["source_evidence"]
        boundary = bridge["boundary_mapping"]
        contract_rows.append({
            "bridge_id": bridge["bridge_id"], "scenario_id": bridge["scenario_id"], "stack_id": bridge["stack_id"],
            "target_metric_id": bridge["target_metric_id"], "bridge_class": bridge["bridge_class"],
            "source_status": source["status"], "source_dataset_id": source.get("dataset_id"),
            "source_metric_ids": "|".join(source.get("metric_ids") or []), "boundary_mapping_status": boundary["status"],
            "required_profile_fields": "|".join(bridge["required_profile_fields"]),
            "scientific_status": bridge["scientific_status"], "uncertainty_transfer_policy": bridge["uncertainty_transfer_policy"],
        })
    _write_csv(contracts_csv, contract_rows, ["bridge_id","scenario_id","stack_id","target_metric_id","bridge_class","source_status","source_dataset_id","source_metric_ids","boundary_mapping_status","required_profile_fields","scientific_status","uncertainty_transfer_policy"])

    readiness_csv = args.output / "bridge_readiness.csv"
    _write_csv(readiness_csv, [
        {
            "bridge_id": r.bridge_id,
            "status": r.status,
            "unresolved_profile_fields": "|".join(r.unresolved_profile_fields),
            "unresolved_profile_field_count": len(r.unresolved_profile_fields),
            "blocking_reasons": "|".join(r.blocking_reasons),
            "numeric_output_materialised": False,
        }
        for r in readiness
    ], ["bridge_id","status","unresolved_profile_fields","unresolved_profile_field_count","blocking_reasons","numeric_output_materialised"])

    handoff_rows = [
        {"rule_id":"freeze_stage4_matrix","policy_state":"required","rule":"Preserve the Stage-4 result 21 feasible / 39 infeasible / 3 unresolved while Stage-5 bridge contracts are developed."},
        {"rule_id":"version_profile_assumptions","policy_state":"required","rule":"Any future value inserted for an unresolved operating-profile field must carry explicit provenance and versioning."},
        {"rule_id":"bridge_requires_complete_profile","policy_state":"required","rule":"A numerical bridge may run only when all fields required by that bridge are known or a validated model explicitly marginalises them."},
        {"rule_id":"scenario_context_not_evidence","policy_state":"required","rule":"Scenario-derived payload/reporting values are benchmark assumptions, not empirical observations."},
        {"rule_id":"profile_defaults","policy_state":"prohibited","rule":"Protocol defaults or best-case modes may not silently fill unresolved operating-profile fields."},
        {"rule_id":"radio_to_whole_device_coercion","policy_state":"prohibited","rule":"Radio-interface energy may not be treated as whole-device/report energy without a validated accounting bridge."},
        {"rule_id":"preference_scoring","policy_state":"prohibited","rule":"Preference scoring remains blocked at Stage-5A."},
        {"rule_id":"publication_mcda","policy_state":"prohibited","rule":"Publication MCDA/ranking remains blocked at Stage-5A."},
    ]
    handoff_csv = args.output / "stage5b_handoff_rules.csv"
    _write_csv(handoff_csv, handoff_rows, ["rule_id","policy_state","rule"])

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **checkpoint,
        "stage4_matrix_preserved": True,
        "profile_provenance_classes_separated": True,
        "scenario_derived_fields_are_empirical_evidence": False,
        "protocol_defaults_used_to_fill_unknown_profile_fields": False,
        "lrfhss_single_trace_uncertainty_preserved": True,
        "numeric_bridge_outputs_authorised": False,
        "preference_scoring_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 5A materialises three scenario-specific operating-profile records and three typed evidence-to-decision bridge contracts for the frozen Stage-4 blockers. "
            "Two LoRaWAN payload fields are known from the benchmark scenario, but 20 Stage-4F-required profile fields remain unresolved. No bridge is numerically active: Thread latency and classical-LoRa energy lack matched source evidence, while LR-FHSS has radio-only 4-byte evidence requiring an explicit profile/boundary transformation to the 16-byte whole-device/report target."
        ),
        "next_scientific_step": (
            "Stage 5B: resolve operating-profile values only through explicit benchmark refinements or matched primary/test evidence, and define/validate one bridge model at a time. Do not alter the frozen Stage-4 matrix until a bridge contract is actually satisfied."
        ),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = args.output / "run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/materialise_stage5a_profiles_and_bridges.py",
        inputs=[args.policy,args.stage4f_summary,args.stage4f_blockers,args.stage4f_profile_requirements,args.scenarios,args.stage3_state],
        outputs=[summary_path,profiles_csv,fields_csv,contracts_csv,readiness_csv,handoff_csv],
        parameters={"numeric_bridge_outputs_authorised":False,"preference_scoring_authorised":False,"publication_mcda_authorised":False},
    )

    print("Stage-5A operating profiles and bridge contracts: OK")
    print(f"Operating profiles / fields: {len(profiles)} / {len(field_rows)}")
    print(f"Known / unresolved fields: {known} / {unresolved}")
    print(f"Stage-4F required fields satisfied / unresolved: {required_satisfied} / {required_unresolved}")
    print(f"Bridge contracts / ready: {len(bridges)} / {ready}")
    print("Stage-4 matrix preserved: 21 / 39 / 3")
    print("Numeric bridge outputs / preference scoring / publication MCDA: 0 / NO / NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
