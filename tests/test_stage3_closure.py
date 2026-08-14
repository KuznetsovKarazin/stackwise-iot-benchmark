from __future__ import annotations

from pathlib import Path

import yaml

from stackwise.stage3_closure import Stage3ClosureError, build_stage3_closure


def _inputs():
    root = Path(__file__).resolve().parents[1]
    uncertainty_policy = yaml.safe_load((root / "datasets/core_four_uncertainty_policy.yml").read_text(encoding="utf-8"))
    closure_policy = yaml.safe_load((root / "datasets/stage3_closure_policy.yml").read_text(encoding="utf-8"))
    core = {
        "evidence_records_mapped": 398,
        "dataset_metric_uncertainty_specs": 14,
        "dependence_groups": 8,
        "calibration_gaps": 6,
        "calibration_status_counts": {
            "calibrated_nonparametric": 2,
            "descriptive_only": 4,
            "external_prior_required": 6,
            "scenario_robustness_materialised": 2,
        },
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
    }
    single = {
        "numeric_population_priors_identified": 0,
        "default_cv_or_sd_authorised": False,
        "infer_cv_from_qualitative_negligible_authorised": False,
        "convert_instrument_accuracy_to_population_sd_authorised": False,
        "publication_mcda_authorised": False,
    }
    vomhoff = {
        "evidence_records_bootstrapped": 52,
        "vomhoff_epistemic_mean_uncertainty_materialised": True,
        "cross_block_joint_distribution_asserted": False,
        "publication_mcda_authorised": False,
    }
    loed = {
        "joint_draw_batches": 6,
        "single_block_length_selected": False,
        "block_length_probability_weights_assigned": False,
        "robustness_envelope_is_probability_interval": False,
        "robustness_family_materialised": True,
        "publication_mcda_authorised": False,
    }
    return uncertainty_policy, closure_policy, core, single, vomhoff, loed


def test_stage3_closure_mixed_semantics():
    uncertainty_policy, closure_policy, core, single, vomhoff, loed = _inputs()
    summary, state, gaps, handoff = build_stage3_closure(
        uncertainty_policy=uncertainty_policy,
        closure_policy=closure_policy,
        core_uncertainty_summary=core,
        single_trace_summary=single,
        vomhoff_bootstrap_summary=vomhoff,
        loed_robustness_summary=loed,
    )
    assert summary["stage3_status"] == "closed_with_explicit_nonidentifiability"
    assert summary["resolution_class_counts"] == {
        "descriptive_nonprobability": 4,
        "empirical_probability": 2,
        "explicit_epistemic_gap": 6,
        "scenario_robustness": 2,
    }
    assert summary["stage3_closure_blocking_gaps"] == 0
    assert summary["stage4_stack_definition_authorised"] is True
    assert summary["publication_mcda_authorised"] is False
    assert len(state) == 14
    assert len(gaps) == 6
    assert not gaps["stage3_closure_blocking"].any()
    assert len(handoff) >= 4


def test_stage3_closure_rejects_fabricated_single_trace_prior():
    uncertainty_policy, closure_policy, core, single, vomhoff, loed = _inputs()
    single["numeric_population_priors_identified"] = 1
    try:
        build_stage3_closure(
            uncertainty_policy=uncertainty_policy,
            closure_policy=closure_policy,
            core_uncertainty_summary=core,
            single_trace_summary=single,
            vomhoff_bootstrap_summary=vomhoff,
            loed_robustness_summary=loed,
        )
    except Stage3ClosureError:
        return
    raise AssertionError("Stage-3 closure must fail if a fabricated/source-unsupported population prior appears")


def test_stage3_closure_rejects_probability_weights_for_loed_scenarios():
    uncertainty_policy, closure_policy, core, single, vomhoff, loed = _inputs()
    loed["block_length_probability_weights_assigned"] = True
    try:
        build_stage3_closure(
            uncertainty_policy=uncertainty_policy,
            closure_policy=closure_policy,
            core_uncertainty_summary=core,
            single_trace_summary=single,
            vomhoff_bootstrap_summary=vomhoff,
            loed_robustness_summary=loed,
        )
    except Stage3ClosureError:
        return
    raise AssertionError("Stage-3 closure must fail if LoED model scenarios receive probability weights")
