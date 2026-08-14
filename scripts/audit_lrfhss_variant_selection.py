from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.variant_selection import (
    audit_variant_family,
    deployment_requirement_rows,
    selection_dimension_rows,
    source_claim_rows,
)


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
    ap = argparse.ArgumentParser(description="Audit LR-FHSS variant-selection identifiability and freeze an unweighted robustness family without selecting a preferred profile.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5d_lrfhss_variant_selection_policy.yml"))
    ap.add_argument("--stage5c-summary", type=Path, default=Path("results/validation/stage5_lrfhss_profile_variants/summary.json"))
    ap.add_argument("--stage5c-variants", type=Path, default=Path("results/validation/stage5_lrfhss_profile_variants/lrfhss_profile_variants.csv"))
    ap.add_argument("--stage5c-implications", type=Path, default=Path("results/validation/stage5_lrfhss_profile_variants/conditional_feasibility_implications.csv"))
    ap.add_argument("--stage5c-generic", type=Path, default=Path("results/validation/stage5_lrfhss_profile_variants/generic_candidate_projection.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_lrfhss_variant_selection"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy["expected"]
    scientific = policy["scientific_policy"]
    stage5c = json.loads(args.stage5c_summary.read_text(encoding="utf-8"))
    variants = _read_csv(args.stage5c_variants)
    implications = _read_csv(args.stage5c_implications)
    generic = _read_csv(args.stage5c_generic)

    if (stage5c["stage4_feasible_rows"], stage5c["stage4_infeasible_rows"], stage5c["stage4_unresolved_rows"]) != (
        int(expected["stage4_feasible_rows"]), int(expected["stage4_infeasible_rows"]), int(expected["stage4_unresolved_rows"])
    ):
        raise SystemExit("Stage-5D refuses to alter the frozen Stage-4 matrix.")
    if stage5c["profile_variants"] != int(expected["profile_variants"]):
        raise SystemExit("Stage-5D expects the complete eight-variant Stage-5C family.")
    if stage5c["variant_probability_weights_assigned"] is not False or stage5c["best_dr_post_hoc_selected"] is not False:
        raise SystemExit("Stage-5D cannot start from weighted or post-hoc selected variants.")
    if stage5c["generic_candidate_status"] != "unresolved":
        raise SystemExit("Generic LR-FHSS candidate must be unresolved at Stage-5D input.")

    projection = audit_variant_family(
        variant_rows=variants,
        implication_rows=implications,
        generic_rows=generic,
        policy=policy,
    )
    source_rows = source_claim_rows(policy)
    dimension_rows = selection_dimension_rows(policy)
    requirement_rows = deployment_requirement_rows(policy)

    if len(source_rows) != int(expected["primary_source_claims"]):
        raise SystemExit("Unexpected Stage-5D primary-source claim count.")
    if len(dimension_rows) != int(expected["selection_dimensions"]):
        raise SystemExit("Unexpected Stage-5D selection-dimension count.")
    if len(requirement_rows) != int(expected["deployment_selection_requirements"]):
        raise SystemExit("Unexpected Stage-5D deployment-selection requirement count.")
    if any(r["deployment_specific_value_available"] for r in dimension_rows):
        raise SystemExit("Stage-5D source review must not invent deployment-specific variant selection.")

    selected_variants = 0
    weighted_variants = 0
    robustness_rows = [{
        "variant_family_id": policy["variant_family_id"],
        "stack_id": policy["stack_id"],
        "scenario_id": policy["scenario_id"],
        "profile_variants": projection.variants,
        "conditionally_infeasible_variants": projection.conditionally_infeasible,
        "conditionally_feasible_variants": projection.conditionally_feasible,
        "unresolved_variants": projection.unresolved,
        "universally_infeasible_within_family": projection.universally_infeasible,
        "universally_feasible_within_family": projection.universally_feasible,
        "mixed_or_unresolved_family": projection.mixed_or_unresolved,
        "variant_probability_weights_assigned": False,
        "variant_family_exhaustive_within_source_model_domain": True,
        "variant_family_exhaustive_for_generic_candidate": False,
        "generic_candidate_status": projection.generic_candidate_status,
        "generic_candidate_status_updated": False,
        "interpretation": "The eight source-aligned variants form an unweighted robustness family with mixed conditional outcomes. Because selection evidence is absent and the family is not exhaustive for the generic candidate, no variant result is projected to the generic candidate.",
    }]

    handoff_rows = [
        {"rule_id":"freeze_stage4_matrix","policy_state":"required","rule":"Preserve the frozen Stage-4 result 21 feasible / 39 infeasible / 3 unresolved."},
        {"rule_id":"retain_unweighted_variant_family","policy_state":"required","rule":"Retain DR8-DR11 x confirmed/unconfirmed as an unweighted robustness family inside the declared Stage-5C source-model domain."},
        {"rule_id":"adr_is_not_selection_evidence","policy_state":"required","rule":"Treat ADR/LinkADRReq as a standards control mechanism only; do not infer a deployment DR without ADR/server policy and observed or declared deployment evidence."},
        {"rule_id":"confirmation_policy_required","policy_state":"required","rule":"Require an application/device policy before selecting confirmed versus unconfirmed operation; energy results cannot choose the message semantics."},
        {"rule_id":"generic_candidate_projection","policy_state":"prohibited","rule":"Do not project the mixed Stage-5C family to the generic LR-FHSS candidate; the family is not exhaustive for generic hardware/TX-power/deployment conditions."},
        {"rule_id":"variant_probability_weights","policy_state":"prohibited","rule":"Do not assign probabilities or frequencies to variants from enumeration, ADR capability, or modeled energy."},
        {"rule_id":"best_case_or_worst_case_selection","policy_state":"prohibited","rule":"Do not select DR9/DR11 as best case or DR8/DR10 as worst case as a substitute for deployment selection evidence."},
        {"rule_id":"whole_device_numeric_bridge","policy_state":"prohibited","rule":"Stage-5D does not activate a whole-device/report energy bridge."},
        {"rule_id":"preference_scoring","policy_state":"prohibited","rule":"Preference scoring remains blocked."},
        {"rule_id":"publication_mcda","policy_state":"prohibited","rule":"Publication MCDA/ranking remains blocked."},
        {"rule_id":"next_stage_focus","policy_state":"authorised","rule":"After freezing LR-FHSS selection uncertainty, Stage 5E may target another unresolved hard bridge (classical LoRa whole-device energy or Thread stack latency) without reopening Stage-4 feasibility results."},
    ]

    args.output.mkdir(parents=True, exist_ok=True)
    source_path = args.output / "primary_source_selection_evidence.csv"
    dimension_path = args.output / "variant_selection_dimensions.csv"
    robustness_path = args.output / "unweighted_robustness_projection.csv"
    requirements_path = args.output / "deployment_selection_requirements.csv"
    handoff_path = args.output / "stage5e_handoff_rules.csv"
    summary_path = args.output / "summary.json"

    _write_csv(source_path, source_rows, ["claim_id","authority","source_type","identifier","source_url","claim","downstream_use"])
    _write_csv(dimension_path, dimension_rows, ["dimension_id","selection_authority_or_mechanism","standards_mechanism_verified","deployment_specific_value_available","selection_identifiability_status","required_deployment_evidence","notes"])
    _write_csv(robustness_path, robustness_rows, list(robustness_rows[0]))
    _write_csv(requirements_path, requirement_rows, ["requirement_id","required_for","current_status","sufficient_evidence"])
    _write_csv(handoff_path, handoff_rows, ["rule_id","policy_state","rule"])

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        "stage4_feasible_rows": int(expected["stage4_feasible_rows"]),
        "stage4_infeasible_rows": int(expected["stage4_infeasible_rows"]),
        "stage4_unresolved_rows": int(expected["stage4_unresolved_rows"]),
        "variant_family_id": policy["variant_family_id"],
        "profile_variants": projection.variants,
        "conditionally_infeasible_variants": projection.conditionally_infeasible,
        "conditionally_feasible_variants": projection.conditionally_feasible,
        "unresolved_variants": projection.unresolved,
        "selection_dimensions_reviewed": len(dimension_rows),
        "primary_source_selection_claims": len(source_rows),
        "deployment_selection_requirements": len(requirement_rows),
        "deployment_selected_variants": selected_variants,
        "weighted_variants": weighted_variants,
        "adr_or_linkadr_control_mechanism_verified": True,
        "adr_deployment_selection_policy_available": False,
        "confirmation_protocol_choices_verified": True,
        "confirmation_deployment_selection_policy_available": False,
        "unweighted_robustness_family_materialised": True,
        "variant_family_universally_infeasible": projection.universally_infeasible,
        "variant_family_universally_feasible": projection.universally_feasible,
        "variant_family_mixed_or_unresolved": projection.mixed_or_unresolved,
        "variant_family_exhaustive_within_declared_source_model_domain": True,
        "variant_family_exhaustive_for_generic_candidate": False,
        "generic_candidate_status": projection.generic_candidate_status,
        "generic_candidate_status_updated": False,
        "stage4_matrix_preserved": True,
        "whole_device_numeric_bridge_materialised": False,
        "preference_scoring_authorised": bool(scientific["preference_scoring_authorised"]),
        "publication_mcda_authorised": bool(scientific["publication_mcda_authorised"]),
        "interpretation": "LoRaWAN standards provide mechanisms that can control data rate/TX power and define confirmed/unconfirmed message semantics, but the benchmark contains no deployment-specific ADR/server policy, link-history/assigned-DR evidence, confirmation policy, TX-power policy, or generic-hardware alignment. The eight Stage-5C variants are therefore frozen as an unweighted robustness family inside the declared source-model domain. Two variants are conditionally infeasible and six remain unresolved; no variant is conditionally feasible. Because the family has mixed/unresolved outcomes and is not exhaustive for the generic candidate, the generic LR-FHSS candidate remains unresolved.",
        "next_scientific_step": "Freeze LR-FHSS variant-selection uncertainty unless deployment evidence becomes available. Stage 5E should pivot to another unresolved hard bridge rather than repeatedly subdividing LR-FHSS; classical-LoRa whole-device energy and Thread stack-level latency remain candidates. Do not rank stacks.",
        "primary_source_selection_evidence_artifact": str(source_path),
        "variant_selection_dimensions_artifact": str(dimension_path),
        "unweighted_robustness_projection_artifact": str(robustness_path),
        "deployment_selection_requirements_artifact": str(requirements_path),
        "stage5e_handoff_rules_artifact": str(handoff_path),
    }
    manifest_path = args.output / "run_manifest.json"
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        manifest_path,
        command="python scripts/audit_lrfhss_variant_selection.py",
        inputs=[args.policy, args.stage5c_summary, args.stage5c_variants, args.stage5c_implications, args.stage5c_generic],
        outputs=[summary_path, source_path, dimension_path, robustness_path, requirements_path, handoff_path],
        parameters={
            "variant_probability_weights_assigned": False,
            "deployment_variant_selected": False,
            "generic_candidate_status_updated": False,
            "whole_device_numeric_bridge_authorised": False,
            "preference_scoring_authorised": False,
            "publication_mcda_authorised": False,
        },
    )
    print("Stage-5D LR-FHSS variant-selection audit: OK")
    print(f"Variants / selected / weighted: {projection.variants} / {selected_variants} / {weighted_variants}")
    print(f"Conditional infeasible / feasible / unresolved: {projection.conditionally_infeasible} / {projection.conditionally_feasible} / {projection.unresolved}")
    print(f"Generic candidate: {projection.generic_candidate_status.upper()}")


if __name__ == "__main__":
    main()
