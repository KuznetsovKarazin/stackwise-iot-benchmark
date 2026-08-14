from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.profile_variants import (
    assess_lrfhss_variant,
    build_lrfhss_source_aligned_variants,
    flatten_variant_fields,
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


def _b(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Materialise versioned source-aligned LR-FHSS operating-profile variants without selecting a preferred DR/mode.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5c_lrfhss_profile_variants.yml"))
    ap.add_argument("--stage5a-summary", type=Path, default=Path("results/validation/stage5_operating_profiles/summary.json"))
    ap.add_argument("--stage5a-fields", type=Path, default=Path("results/validation/stage5_operating_profiles/operating_profile_fields.csv"))
    ap.add_argument("--stage5b-summary", type=Path, default=Path("results/validation/stage5_lrfhss_bridge_audit/summary.json"))
    ap.add_argument("--stage5b-screen", type=Path, default=Path("results/validation/stage5_lrfhss_bridge_audit/one_sided_budget_screen.csv"))
    ap.add_argument("--stage5b-variants", type=Path, default=Path("results/validation/stage5_lrfhss_bridge_audit/benchmark_radio_model_variants_16byte.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_lrfhss_profile_variants"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy["expected"]
    scientific = policy["scientific_policy"]
    family = policy["variant_family"]
    stage5a = json.loads(args.stage5a_summary.read_text(encoding="utf-8"))
    stage5a_fields = _read_csv(args.stage5a_fields)
    stage5b = json.loads(args.stage5b_summary.read_text(encoding="utf-8"))
    screen = _read_csv(args.stage5b_screen)
    model_variants = _read_csv(args.stage5b_variants)

    frozen = (stage5a["stage4_feasible_rows"], stage5a["stage4_infeasible_rows"], stage5a["stage4_unresolved_rows"])
    if frozen != (21, 39, 3):
        raise SystemExit("Stage-5C refuses to alter the frozen Stage-4 matrix.")
    if (stage5b["stage4_feasible_rows"], stage5b["stage4_infeasible_rows"], stage5b["stage4_unresolved_rows"]) != frozen:
        raise SystemExit("Stage-5B did not preserve the frozen Stage-4 matrix.")
    if stage5b["generic_lrfhss_candidate_feasibility_resolved"] is not False:
        raise SystemExit("Stage-5C expects the generic LR-FHSS candidate to remain unresolved before variant materialisation.")
    if stage5b["whole_device_energy_estimate_materialised"] is not False or stage5b["numeric_target_bridge_output_authorised"] is not False:
        raise SystemExit("Stage-5C cannot start from an already-activated whole-device bridge.")

    base_profile = [r for r in stage5a_fields if r.get("profile_id") == family["parent_profile_id"]]
    if len(base_profile) != 9:
        raise SystemExit("Expected the nine-field Stage-5A LR-FHSS parent operating profile.")
    payload = [r for r in base_profile if r.get("field_id") == "application_payload_bytes"]
    reporting = [r for r in base_profile if r.get("field_id") == "reporting_interval_s"]
    if len(payload) != 1 or payload[0].get("status") != "known" or int(float(payload[0]["value"])) != int(family["source_model_domain"]["application_payload_bytes"]):
        raise SystemExit("Stage-5C parent profile payload does not match the declared variant family.")
    if len(reporting) != 1 or reporting[0].get("status") != "known" or int(float(reporting[0]["value"])) != int(family["source_model_domain"]["reporting_interval_s"]):
        raise SystemExit("Stage-5C parent reporting interval does not match the declared variant family.")

    model_map = {(r["confirmation_mode"], int(float(r["source_dr_index"]))): r for r in model_variants}
    for row in screen:
        key = (row["confirmation_mode"], int(float(row["source_dr_index"])))
        peer = model_map.get(key)
        if peer is None:
            raise SystemExit(f"Missing Stage-5B model variant for {key}.")
        if abs(float(row["modeled_incremental_radio_energy_j"]) - float(peer["modeled_incremental_radio_energy_j"])) > 1e-12:
            raise SystemExit(f"Stage-5B model/screen energy mismatch for {key}.")
        if int(float(row["frm_payload_bytes"])) != int(family["source_model_domain"]["application_payload_bytes"]):
            raise SystemExit(f"Unexpected payload in Stage-5B screen for {key}.")
        if int(float(row["tx_power_dbm"])) != int(family["source_model_domain"]["tx_power_dbm"]):
            raise SystemExit(f"Unexpected TX power in Stage-5B screen for {key}.")

    variants = build_lrfhss_source_aligned_variants(stage5b_screen_rows=screen, policy=policy)
    decisions = [assess_lrfhss_variant(v, policy) for v in variants]
    decision_map = {d.variant_id: d for d in decisions}
    field_rows = flatten_variant_fields(variants)

    variant_rows: list[dict[str, Any]] = []
    implication_rows: list[dict[str, Any]] = []
    for v in variants:
        d = decision_map[v["profile_id"]]
        variant_rows.append({
            "variant_id": v["profile_id"],
            "variant_family_id": v["variant_family_id"],
            "variant_version": v["variant_version"],
            "parent_profile_id": v["parent_profile_id"],
            "scenario_id": v["scenario_id"],
            "stack_id": v["stack_id"],
            "source_dr_index": v["source_dr_index"],
            "confirmation_mode": v["confirmation_mode"],
            "tx_power_dbm": family["source_model_domain"]["tx_power_dbm"],
            "application_payload_bytes": family["source_model_domain"]["application_payload_bytes"],
            "reporting_interval_s": family["source_model_domain"]["reporting_interval_s"],
            "radio_hardware": family["source_model_domain"]["radio_hardware"],
            "source_model_valid_for_payload_extrapolation": v["source_model_valid_for_payload_extrapolation"],
            "modeled_incremental_radio_energy_j": v["modeled_incremental_radio_energy_j"],
            "whole_device_budget_j": v["whole_device_budget_j"],
            "whole_device_profile_complete": d.whole_device_profile_complete,
            "decision_sufficient_for_monotone_lower_bound": d.decision_sufficient_for_monotone_lower_bound,
            "conditional_feasibility_status": d.status,
            "whole_device_numeric_bridge_ready": d.whole_device_numeric_bridge_ready,
            "deployment_selection_evidence": False,
            "probability_weight_assigned": False,
        })
        implication_rows.append({
            "variant_id": v["profile_id"],
            "source_dr_index": v["source_dr_index"],
            "confirmation_mode": v["confirmation_mode"],
            "radio_component_energy_j": v["modeled_incremental_radio_energy_j"],
            "whole_device_budget_j": v["whole_device_budget_j"],
            "source_model_valid_for_payload_extrapolation": v["source_model_valid_for_payload_extrapolation"],
            "decision_sufficient_for_monotone_lower_bound": d.decision_sufficient_for_monotone_lower_bound,
            "conditional_feasibility_status": d.status,
            "whole_device_energy_estimate_materialised": False,
            "generic_candidate_status_updated": False,
        })

    generic_rows = [{
        "stack_id": family["stack_id"],
        "scenario_id": family["scenario_id"],
        "generic_candidate_status": "unresolved",
        "variant_family_id": family["family_id"],
        "variant_family_exhaustive_for_generic_candidate": bool(family["exhaustive_for_generic_candidate"]),
        "deployment_selection_evidence_available": bool(family["deployment_selection_evidence_available"]),
        "probability_weights_assigned": bool(family["probability_weights_assigned"]),
        "conditionally_infeasible_variants": sum(d.status == "conditionally_infeasible_by_validated_radio_lower_bound" for d in decisions),
        "conditionally_feasible_variants": 0,
        "unresolved_variants": sum(d.status != "conditionally_infeasible_by_validated_radio_lower_bound" for d in decisions),
        "reason": "Variant outcomes cannot be projected to the generic candidate without deployment/profile selection evidence or an explicitly versioned benchmark refinement.",
    }]

    handoff_rows = [
        {"rule_id":"freeze_stage4_matrix","policy_state":"required","rule":"Preserve the frozen Stage-4 result 21 feasible / 39 infeasible / 3 unresolved; Stage-5C adds conditional profile variants only."},
        {"rule_id":"generic_candidate_projection","policy_state":"prohibited","rule":"Do not project a variant-level result to the generic LR-FHSS candidate without explicit deployment/profile selection evidence."},
        {"rule_id":"variant_probability_weights","policy_state":"prohibited","rule":"Do not assign probabilities or frequencies to DR/confirmation variants from this enumeration."},
        {"rule_id":"best_case_variant_selection","policy_state":"prohibited","rule":"Do not select DR9/DR11 or unconfirmed mode post hoc because they have lower modeled radio energy."},
        {"rule_id":"lower_bound_inheritance","policy_state":"conditional","rule":"Only source-aligned unconfirmed DR8/DR10 variants inherit one-sided infeasibility because their validated radio lower bound alone exceeds the whole-device budget."},
        {"rule_id":"below_budget_feasibility","policy_state":"prohibited","rule":"Unconfirmed DR9/DR11 radio energy below the budget does not establish whole-device feasibility; residual device/report energy remains unresolved."},
        {"rule_id":"confirmed_variant_extrapolation","policy_state":"prohibited","rule":"All confirmed variants remain unresolved because the Stage-5B source-model reproduction gate failed."},
        {"rule_id":"whole_device_numeric_bridge","policy_state":"prohibited","rule":"Stage-5C does not materialise a whole-device/report energy estimate for any variant."},
        {"rule_id":"population_sampling","policy_state":"prohibited","rule":"Variant enumeration and deterministic lower bounds do not resolve the LR-FHSS single-trace population-uncertainty gap."},
        {"rule_id":"preference_scoring","policy_state":"prohibited","rule":"Preference scoring remains blocked."},
        {"rule_id":"publication_mcda","policy_state":"prohibited","rule":"Publication MCDA/ranking remains blocked."},
    ]

    args.output.mkdir(parents=True, exist_ok=True)
    variants_csv = args.output / "lrfhss_profile_variants.csv"
    fields_csv = args.output / "lrfhss_profile_variant_fields.csv"
    implications_csv = args.output / "conditional_feasibility_implications.csv"
    generic_csv = args.output / "generic_candidate_projection.csv"
    handoff_csv = args.output / "stage5d_handoff_rules.csv"

    _write_csv(variants_csv, variant_rows, [
        "variant_id","variant_family_id","variant_version","parent_profile_id","scenario_id","stack_id","source_dr_index","confirmation_mode",
        "tx_power_dbm","application_payload_bytes","reporting_interval_s","radio_hardware","source_model_valid_for_payload_extrapolation",
        "modeled_incremental_radio_energy_j","whole_device_budget_j","whole_device_profile_complete","decision_sufficient_for_monotone_lower_bound",
        "conditional_feasibility_status","whole_device_numeric_bridge_ready","deployment_selection_evidence","probability_weight_assigned"
    ])
    _write_csv(fields_csv, field_rows, [
        "variant_id","parent_profile_id","scenario_id","stack_id","source_dr_index","confirmation_mode","field_id","status","value","unit",
        "provenance_status","provenance_ref","required_for_numeric_bridge","notes"
    ])
    _write_csv(implications_csv, implication_rows, [
        "variant_id","source_dr_index","confirmation_mode","radio_component_energy_j","whole_device_budget_j","source_model_valid_for_payload_extrapolation",
        "decision_sufficient_for_monotone_lower_bound","conditional_feasibility_status","whole_device_energy_estimate_materialised","generic_candidate_status_updated"
    ])
    _write_csv(generic_csv, generic_rows, [
        "stack_id","scenario_id","generic_candidate_status","variant_family_id","variant_family_exhaustive_for_generic_candidate",
        "deployment_selection_evidence_available","probability_weights_assigned","conditionally_infeasible_variants","conditionally_feasible_variants","unresolved_variants","reason"
    ])
    _write_csv(handoff_csv, handoff_rows, ["rule_id","policy_state","rule"])

    known = sum(r["status"] == "known" for r in field_rows)
    unresolved = sum(r["status"] == "unresolved" for r in field_rows)
    sufficient = sum(d.decision_sufficient_for_monotone_lower_bound for d in decisions)
    conditional_infeasible = sum(d.status == "conditionally_infeasible_by_validated_radio_lower_bound" for d in decisions)
    residual_unresolved = sum(d.status == "unresolved_residual_whole_device_energy" for d in decisions)
    confirmed_unresolved = sum(d.status == "unresolved_confirmed_source_model_not_validated" for d in decisions)

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        "stage4_feasible_rows": frozen[0],
        "stage4_infeasible_rows": frozen[1],
        "stage4_unresolved_rows": frozen[2],
        "variant_family_id": family["family_id"],
        "profile_variants": len(variants),
        "profile_variant_field_rows": len(field_rows),
        "known_variant_fields": known,
        "unresolved_variant_fields": unresolved,
        "whole_device_complete_variants": sum(d.whole_device_profile_complete for d in decisions),
        "lower_bound_decision_sufficient_variants": sufficient,
        "conditionally_infeasible_variants": conditional_infeasible,
        "unresolved_residual_energy_variants": residual_unresolved,
        "unresolved_confirmed_model_variants": confirmed_unresolved,
        "conditionally_feasible_variants": 0,
        "generic_candidate_status": "unresolved",
        "variant_family_exhaustive_within_declared_source_model_domain": bool(family["exhaustive_within_declared_source_model_domain"]),
        "variant_family_exhaustive_for_generic_candidate": bool(family["exhaustive_for_generic_candidate"]),
        "deployment_selection_evidence_available": bool(family["deployment_selection_evidence_available"]),
        "variant_probability_weights_assigned": bool(family["probability_weights_assigned"]),
        "best_dr_post_hoc_selected": False,
        "whole_device_numeric_bridge_materialised": False,
        "population_uncertainty_sampling_authorised": False,
        "stage4_matrix_preserved": True,
        "preference_scoring_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": "Stage 5C enumerates all eight DR8-DR11 x confirmed/unconfirmed variants inside the explicitly source-aligned LR1121/+14 dBm model domain without choosing among them. Only unconfirmed DR8/DR10 are decision-sufficient for conditional infeasibility because the validated radio-component lower bound already exceeds the whole-device budget. DR9/DR11 remain whole-device unresolved, confirmed variants remain model-gated, and the generic candidate remains unresolved because no deployment/profile selection evidence or variant probabilities exist.",
        "next_scientific_step": "Stage 5D should either obtain deployment/profile selection evidence or treat the source-aligned variants as an unweighted robustness family. For unconfirmed DR9/DR11, a residual whole-device energy bridge would be required before any feasibility claim; confirmed variants require source-model reconciliation/new evidence. Do not rank variants.",
        "lrfhss_profile_variants_artifact": str(variants_csv),
        "lrfhss_profile_variant_fields_artifact": str(fields_csv),
        "conditional_feasibility_implications_artifact": str(implications_csv),
        "generic_candidate_projection_artifact": str(generic_csv),
        "stage5d_handoff_rules_artifact": str(handoff_csv),
    }

    for key, value in expected.items():
        if key == "generic_candidate_status":
            actual = summary[key]
        else:
            actual = summary.get(key)
        if actual != value:
            raise SystemExit(f"Stage-5C checkpoint mismatch for {key}: expected {value!r}, got {actual!r}")

    summary_path = args.output / "summary.json"
    manifest_path = args.output / "run_manifest.json"
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    write_run_manifest(
        manifest_path,
        command="python scripts/materialise_lrfhss_profile_variants.py",
        inputs=[args.policy,args.stage5a_summary,args.stage5a_fields,args.stage5b_summary,args.stage5b_screen,args.stage5b_variants],
        outputs=[summary_path,variants_csv,fields_csv,implications_csv,generic_csv,handoff_csv],
        parameters={
            "variant_probability_weights_assigned": False,
            "generic_candidate_status_updated": False,
            "whole_device_numeric_bridge_authorised": False,
            "preference_scoring_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5C LR-FHSS profile variants: OK")
    print(f"Variants / fields: {len(variants)} / {len(field_rows)}")
    print(f"Conditional infeasible / residual unresolved / confirmed unresolved: {conditional_infeasible} / {residual_unresolved} / {confirmed_unresolved}")
    print("Generic candidate: unresolved")


if __name__ == "__main__":
    main()
