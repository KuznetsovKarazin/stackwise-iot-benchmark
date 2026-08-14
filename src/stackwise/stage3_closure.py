from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


class Stage3ClosureError(RuntimeError):
    pass


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Stage3ClosureError(f"Expected JSON object: {path}")
    return value


def _load_yaml(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Stage3ClosureError(f"Expected YAML mapping: {path}")
    return value


def build_stage3_closure(
    *,
    uncertainty_policy: dict[str, Any],
    closure_policy: dict[str, Any],
    core_uncertainty_summary: dict[str, Any],
    single_trace_summary: dict[str, Any],
    vomhoff_bootstrap_summary: dict[str, Any],
    loed_robustness_summary: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = uncertainty_policy.get("metric_models")
    gaps = uncertainty_policy.get("calibration_gaps")
    dependence = uncertainty_policy.get("dependence_groups")
    if not isinstance(specs, list) or not isinstance(gaps, list) or not isinstance(dependence, list):
        raise Stage3ClosureError("Uncertainty policy must contain metric_models, calibration_gaps, dependence_groups")

    expected = closure_policy.get("expected") or {}
    resolution_map = closure_policy.get("resolution_by_calibration_status") or {}
    gap_ownership = closure_policy.get("residual_gap_ownership") or {}
    errors: list[str] = []

    if core_uncertainty_summary.get("evidence_records_mapped") != expected.get("evidence_records"):
        errors.append("core uncertainty evidence-record checkpoint mismatch")
    if core_uncertainty_summary.get("dataset_metric_uncertainty_specs") != expected.get("metric_families"):
        errors.append("core uncertainty metric-family checkpoint mismatch")
    if core_uncertainty_summary.get("dependence_groups") != expected.get("dependence_groups"):
        errors.append("dependence-group checkpoint mismatch")
    if core_uncertainty_summary.get("calibration_gaps") != expected.get("residual_gaps"):
        errors.append("residual-gap checkpoint mismatch")
    if core_uncertainty_summary.get("calibration_status_counts") != expected.get("calibration_status_counts"):
        errors.append("calibration-status checkpoint mismatch")

    if single_trace_summary.get("numeric_population_priors_identified") != expected.get("single_trace_numeric_population_priors"):
        errors.append("single-trace numerical prior checkpoint mismatch")
    for key in ("default_cv_or_sd_authorised", "infer_cv_from_qualitative_negligible_authorised", "convert_instrument_accuracy_to_population_sd_authorised"):
        if single_trace_summary.get(key) is not False:
            errors.append(f"single-trace safeguard violated: {key}")

    if vomhoff_bootstrap_summary.get("evidence_records_bootstrapped") != expected.get("vomhoff_bootstrapped_evidence_records"):
        errors.append("Vomhoff bootstrap checkpoint mismatch")
    if vomhoff_bootstrap_summary.get("vomhoff_epistemic_mean_uncertainty_materialised") is not True:
        errors.append("Vomhoff empirical mean uncertainty not materialised")
    if vomhoff_bootstrap_summary.get("cross_block_joint_distribution_asserted") is not False:
        errors.append("Vomhoff cross-block joint distribution must remain unidentified")

    if loed_robustness_summary.get("joint_draw_batches") != expected.get("loed_joint_scenario_batches"):
        errors.append("LoED robustness-batch checkpoint mismatch")
    for key in ("single_block_length_selected", "block_length_probability_weights_assigned", "robustness_envelope_is_probability_interval"):
        if loed_robustness_summary.get(key) is not False:
            errors.append(f"LoED robustness safeguard violated: {key}")
    if loed_robustness_summary.get("robustness_family_materialised") is not True:
        errors.append("LoED robustness family not materialised")

    status_counts = Counter(str(spec.get("calibration_status")) for spec in specs)
    if dict(sorted(status_counts.items())) != expected.get("calibration_status_counts"):
        errors.append("uncertainty-policy calibration statuses do not match closure policy")

    state_rows: list[dict[str, Any]] = []
    for spec in specs:
        status = str(spec.get("calibration_status"))
        resolution = resolution_map.get(status)
        if not isinstance(resolution, dict):
            errors.append(f"no Stage-3 resolution mapping for calibration_status={status}")
            continue
        state_rows.append({
            "uncertainty_model_id": spec["uncertainty_model_id"],
            "dataset_id": spec["dataset_id"],
            "metric_id": spec["metric_id"],
            "calibration_status": status,
            "population_variability_status": spec["population_variability_status"],
            "evidence_uncertainty_regime": spec["evidence_uncertainty_regime"],
            "resolution_class": resolution["resolution_class"],
            "stage3_resolution_status": resolution["stage3_resolution_status"],
            "probability_semantics": resolution["probability_semantics"],
            "future_sampling_rule": resolution["future_sampling_rule"],
            "primary_sampling_unit": spec["primary_sampling_unit"],
            "resampling_scheme": spec["resampling_scheme"],
            "distribution_family_status": spec["distribution_family_status"],
            "bridge_uncertainty_status": spec["bridge_uncertainty_status"],
            "shared_parameter_ids": "|".join(spec.get("shared_parameter_ids") or []),
            "dependence_group_ids": "|".join(spec.get("dependence_group_ids") or []),
            "study_effect_status": spec["study_effect_status"],
            "implementation_effect_status": spec["implementation_effect_status"],
        })
    state = pd.DataFrame(state_rows)

    resolution_counts = dict(sorted(Counter(state["resolution_class"]).items())) if not state.empty else {}
    if resolution_counts != expected.get("resolution_class_counts"):
        errors.append(f"resolution-class checkpoint mismatch: {resolution_counts}")

    gap_rows: list[dict[str, Any]] = []
    policy_gap_ids = {str(g.get("gap_id")) for g in gaps}
    owner_gap_ids = set(map(str, gap_ownership.keys()))
    if policy_gap_ids != owner_gap_ids:
        errors.append(f"residual gap ownership mismatch: policy={sorted(policy_gap_ids)} closure={sorted(owner_gap_ids)}")
    for gap in gaps:
        ownership = gap_ownership.get(str(gap["gap_id"]), {})
        row = dict(gap)
        row["stage3_closure_blocking"] = bool(ownership.get("closure_blocking", True))
        row["deferred_owner"] = ownership.get("deferred_owner", "unassigned")
        gap_rows.append(row)
    residual_gaps = pd.DataFrame(gap_rows)
    blocking_gaps = int(residual_gaps["stage3_closure_blocking"].sum()) if not residual_gaps.empty else 0
    if blocking_gaps != 0:
        errors.append(f"Stage-3 closure has {blocking_gaps} blocking gaps")

    handoff = pd.DataFrame({"rule": closure_policy.get("handoff_rules") or []})
    if handoff.empty:
        errors.append("Stage-4 handoff rules are missing")

    for source in (core_uncertainty_summary, single_trace_summary, vomhoff_bootstrap_summary, loed_robustness_summary):
        if source.get("publication_mcda_authorised") is not False:
            errors.append("publication MCDA must remain unauthorised")
    if core_uncertainty_summary.get("publication_uncertainty_sampling_authorised") is not False:
        errors.append("publication uncertainty sampling must remain unauthorised")

    if errors:
        raise Stage3ClosureError("; ".join(errors[:20]))

    summary = {
        "stage": closure_policy.get("stage", "Stage-3 mixed uncertainty closure"),
        "stage3_status": closure_policy.get("stage3_status"),
        "evidence_records": expected.get("evidence_records"),
        "metric_families": len(specs),
        "dependence_groups": len(dependence),
        "resolution_class_counts": resolution_counts,
        "residual_gaps": len(residual_gaps),
        "stage3_closure_blocking_gaps": blocking_gaps,
        "single_trace_numeric_population_priors_identified": single_trace_summary.get("numeric_population_priors_identified"),
        "vomhoff_empirical_nonparametric_materialised": True,
        "loed_scenario_robustness_materialised": True,
        "insectt_lrfhss_population_variability_identified": False,
        "mixed_uncertainty_semantics_required": True,
        "stage4_stack_definition_authorised": bool(closure_policy.get("stage4_stack_definition_authorised")),
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 3 is closed for the current validated core-four evidence by preserving heterogeneous uncertainty semantics rather than forcing every metric into one probability distribution. "
            "Vomhoff has dependence-preserving empirical nonparametric uncertainty; LoED has unweighted deployment/model robustness scenarios; InSecTT/LR-FHSS retain explicit single-trace epistemic non-identifiability; descriptive metrics remain non-probabilistic."
        ),
        "next_scientific_step": (
            "Stage 4: define layer-aware end-to-end candidate stacks and hard compatibility/feasibility constraints. Do not rank stacks or introduce default stochastic priors."
        ),
    }
    return summary, state, residual_gaps, handoff


def close_stage3_from_paths(
    *,
    uncertainty_policy_path: str | Path = "datasets/core_four_uncertainty_policy.yml",
    closure_policy_path: str | Path = "datasets/stage3_closure_policy.yml",
    core_uncertainty_summary_path: str | Path = "results/validation/core_four_uncertainty/summary.json",
    single_trace_summary_path: str | Path = "results/validation/single_trace_uncertainty_review/summary.json",
    vomhoff_bootstrap_summary_path: str | Path = "results/validation/vomhoff_joint_bootstrap/summary.json",
    loed_robustness_summary_path: str | Path = "results/validation/loed_uncertainty_robustness/summary.json",
):
    return build_stage3_closure(
        uncertainty_policy=_load_yaml(uncertainty_policy_path),
        closure_policy=_load_yaml(closure_policy_path),
        core_uncertainty_summary=_load_json(core_uncertainty_summary_path),
        single_trace_summary=_load_json(single_trace_summary_path),
        vomhoff_bootstrap_summary=_load_json(vomhoff_bootstrap_summary_path),
        loed_robustness_summary=_load_json(loed_robustness_summary_path),
    )
