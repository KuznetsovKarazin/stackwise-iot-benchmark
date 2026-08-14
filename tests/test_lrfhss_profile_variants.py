from __future__ import annotations

import csv
from pathlib import Path

import yaml

from stackwise.profile_variants import assess_lrfhss_variant, build_lrfhss_source_aligned_variants, flatten_variant_fields


def _policy():
    return yaml.safe_load(Path("datasets/stage5c_lrfhss_profile_variants.yml").read_text(encoding="utf-8"))


def _screen_rows():
    rows = []
    for mode in ("unconfirmed", "confirmed"):
        for dr in (8, 9, 10, 11):
            if mode == "unconfirmed":
                energy = 0.2043920784906 if dr in (8, 10) else 0.11410775237565
                status = "matched_variant_infeasible_by_radio_component_lower_bound" if dr in (8, 10) else "whole_device_unresolved_radio_component_below_or_equal_budget"
                valid = True
            else:
                energy = 0.216074 if dr in (8, 10) else 0.123492
                status = "model_not_authorised_for_payload_extrapolation"
                valid = False
            rows.append({
                "confirmation_mode": mode,
                "source_dr_index": str(dr),
                "frm_payload_bytes": "16",
                "tx_power_dbm": "14",
                "modeled_incremental_radio_energy_j": str(energy),
                "whole_device_budget_j": "0.2",
                "source_model_valid_for_payload_extrapolation": str(valid),
                "one_sided_budget_screen_status": status,
            })
    return rows


def test_stage5c_enumerates_complete_source_aligned_dr_mode_domain_without_weights():
    p = _policy()
    variants = build_lrfhss_source_aligned_variants(stage5b_screen_rows=_screen_rows(), policy=p)
    assert len(variants) == 8
    assert {(v["source_dr_index"], v["confirmation_mode"]) for v in variants} == {(dr, mode) for dr in (8,9,10,11) for mode in ("unconfirmed","confirmed")}
    assert p["variant_family"]["probability_weights_assigned"] is False
    assert p["variant_family"]["deployment_selection_evidence_available"] is False
    assert p["scientific_policy"]["choose_best_dr_post_hoc"] is False


def test_stage5c_variant_fields_preserve_provenance_and_partial_whole_device_profiles():
    variants = build_lrfhss_source_aligned_variants(stage5b_screen_rows=_screen_rows(), policy=_policy())
    fields = flatten_variant_fields(variants)
    assert len(fields) == 96
    assert sum(r["status"] == "known" for r in fields) == 72
    assert sum(r["status"] == "unresolved" for r in fields) == 24
    assert all(r["provenance_status"] == "scenario_derived" for r in fields if r["field_id"] in {"application_payload_bytes","reporting_interval_s"})
    assert all(r["provenance_status"] != "empirical_observed" for r in fields if r["field_id"] in {"lrfhss_data_rate","confirmation_mode","tx_power_dbm"})


def test_stage5c_only_unconfirmed_dr8_dr10_inherit_monotone_lower_bound_exclusion():
    p = _policy()
    variants = build_lrfhss_source_aligned_variants(stage5b_screen_rows=_screen_rows(), policy=p)
    decisions = {v["profile_id"]: assess_lrfhss_variant(v, p) for v in variants}
    excluded = {(v["source_dr_index"], v["confirmation_mode"]) for v in variants if decisions[v["profile_id"]].decision_sufficient_for_monotone_lower_bound}
    assert excluded == {(8,"unconfirmed"),(10,"unconfirmed")}
    assert all(not d.whole_device_profile_complete for d in decisions.values())
    assert all(not d.whole_device_numeric_bridge_ready for d in decisions.values())


def test_stage5c_below_budget_and_confirmed_variants_remain_unresolved():
    p = _policy()
    variants = build_lrfhss_source_aligned_variants(stage5b_screen_rows=_screen_rows(), policy=p)
    statuses = {(v["source_dr_index"],v["confirmation_mode"]): assess_lrfhss_variant(v,p).status for v in variants}
    assert statuses[(9,"unconfirmed")] == "unresolved_residual_whole_device_energy"
    assert statuses[(11,"unconfirmed")] == "unresolved_residual_whole_device_energy"
    for dr in (8,9,10,11):
        assert statuses[(dr,"confirmed")] == "unresolved_confirmed_source_model_not_validated"


def test_stage5c_policy_forbids_generic_projection_and_ranking():
    sp = _policy()["scientific_policy"]
    assert sp["preserve_generic_lrfhss_candidate_unresolved"] is True
    assert sp["infer_deployment_variant_from_energy_result"] is False
    assert sp["variant_probability_weights_assigned"] is False
    assert sp["whole_device_numeric_bridge_authorised"] is False
    assert sp["preference_scoring_authorised"] is False
    assert sp["publication_mcda_authorised"] is False
