from __future__ import annotations

from pathlib import Path

import yaml

from stackwise.variant_selection import audit_variant_family, deployment_requirement_rows, selection_dimension_rows, source_claim_rows

ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage5d_lrfhss_variant_selection_policy.yml").read_text(encoding="utf-8"))


def _variants():
    rows = []
    for mode in ("unconfirmed", "confirmed"):
        for dr in (8, 9, 10, 11):
            rows.append({
                "variant_id": f"v_{dr}_{mode}",
                "deployment_selection_evidence": False,
                "probability_weight_assigned": False,
                "whole_device_profile_complete": False,
            })
    return rows


def _implications():
    rows = []
    for mode in ("unconfirmed", "confirmed"):
        for dr in (8, 9, 10, 11):
            if mode == "unconfirmed" and dr in (8, 10):
                status = "conditionally_infeasible_by_validated_radio_lower_bound"
            elif mode == "unconfirmed":
                status = "unresolved_residual_whole_device_energy"
            else:
                status = "unresolved_confirmed_source_model_not_validated"
            rows.append({"variant_id": f"v_{dr}_{mode}", "conditional_feasibility_status": status})
    return rows


def _generic():
    return [{
        "generic_candidate_status": "unresolved",
        "deployment_selection_evidence_available": False,
        "probability_weights_assigned": False,
    }]


def test_stage5d_robustness_projection_keeps_generic_unresolved():
    p = _policy()
    r = audit_variant_family(variant_rows=_variants(), implication_rows=_implications(), generic_rows=_generic(), policy=p)
    assert r.variants == 8
    assert r.conditionally_infeasible == 2
    assert r.conditionally_feasible == 0
    assert r.unresolved == 6
    assert r.universally_infeasible is False
    assert r.universally_feasible is False
    assert r.mixed_or_unresolved is True
    assert r.generic_candidate_status == "unresolved"


def test_stage5d_selection_dimensions_require_deployment_evidence():
    rows = selection_dimension_rows(_policy())
    assert len(rows) == 4
    assert all(r["deployment_specific_value_available"] is False for r in rows)
    dr = next(r for r in rows if r["dimension_id"] == "lrfhss_data_rate")
    assert dr["standards_mechanism_verified"] is True
    assert dr["selection_identifiability_status"] == "mechanism_known_selection_unidentified"
    mode = next(r for r in rows if r["dimension_id"] == "confirmation_mode")
    assert mode["standards_mechanism_verified"] is True
    assert mode["selection_identifiability_status"] == "protocol_choices_known_selection_unidentified"


def test_stage5d_primary_sources_and_selection_requirements_materialise():
    p = _policy()
    claims = source_claim_rows(p)
    reqs = deployment_requirement_rows(p)
    assert len(claims) == 4
    assert len(reqs) == 5
    assert all(str(c["source_url"]).startswith("https://") for c in claims)
    assert all(r["current_status"] == "unresolved" for r in reqs)


def test_stage5d_policy_forbids_selection_weights_projection_and_mcda():
    sp = _policy()["scientific_policy"]
    assert sp["treat_variants_as_unweighted_robustness_family"] is True
    assert sp["variant_probability_weights_assigned"] is False
    assert sp["infer_variant_frequency_from_adr"] is False
    assert sp["infer_dr_from_energy_result"] is False
    assert sp["infer_confirmation_mode_from_energy_result"] is False
    assert sp["assume_adr_selects_lowest_energy_dr"] is False
    assert sp["project_family_to_generic_candidate"] is False
    assert sp["update_frozen_stage4_matrix"] is False
    assert sp["whole_device_numeric_bridge_authorised"] is False
    assert sp["preference_scoring_authorised"] is False
    assert sp["publication_mcda_authorised"] is False


def test_stage5d_rejects_weighted_or_selected_input():
    p = _policy()
    variants = _variants()
    variants[0]["probability_weight_assigned"] = True
    try:
        audit_variant_family(variant_rows=variants, implication_rows=_implications(), generic_rows=_generic(), policy=p)
    except ValueError as exc:
        assert "weighted" in str(exc).lower()
    else:
        raise AssertionError("Weighted Stage-5C input must be rejected")
