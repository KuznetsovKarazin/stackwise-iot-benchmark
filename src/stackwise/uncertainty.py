from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd
import yaml

from .evidence_matrix import load_jsonl, load_shared_parameters, records_to_frame

DEFAULT_UNCERTAINTY_SCHEMA = Path("datasets/schema/uncertainty_model.schema.json")
DEFAULT_UNCERTAINTY_POLICY = Path("datasets/core_four_uncertainty_policy.yml")


class UncertaintyContractError(RuntimeError):
    pass


def load_uncertainty_policy(path: str | Path = DEFAULT_UNCERTAINTY_POLICY) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UncertaintyContractError("Uncertainty policy must be a mapping")
    return value


def validate_uncertainty_spec(
    record: dict[str, Any],
    *,
    schema_path: str | Path = DEFAULT_UNCERTAINTY_SCHEMA,
) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(record), key=lambda item: list(item.absolute_path))
    ]


def _join_values(values: pd.Series) -> str:
    return "|".join(sorted({str(value) for value in values.dropna() if str(value) not in {"", "nan", "None"}}))


def _join_list(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def audit_core_four_uncertainty(
    evidence_records: list[dict[str, Any]],
    shared_parameters: list[dict[str, Any]],
    *,
    policy_path: str | Path = DEFAULT_UNCERTAINTY_POLICY,
    schema_path: str | Path = DEFAULT_UNCERTAINTY_SCHEMA,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    policy = load_uncertainty_policy(policy_path)
    specs = policy.get("metric_models")
    dependence_groups = policy.get("dependence_groups")
    calibration_gaps = policy.get("calibration_gaps")
    if not isinstance(specs, list) or not isinstance(dependence_groups, list) or not isinstance(calibration_gaps, list):
        raise UncertaintyContractError("Policy must contain metric_models, dependence_groups and calibration_gaps lists")

    errors: list[str] = []
    spec_ids = [str(spec.get("uncertainty_model_id")) for spec in specs]
    duplicate_spec_ids = [value for value, count in Counter(spec_ids).items() if count > 1]
    if duplicate_spec_ids:
        errors.append(f"duplicate uncertainty_model_id values: {duplicate_spec_ids}")

    for spec in specs:
        validation_errors = validate_uncertainty_spec(spec, schema_path=schema_path)
        if validation_errors:
            errors.append(f"{spec.get('uncertainty_model_id')}: {validation_errors}")

    defined_groups = {str(group.get("dependence_group_id")) for group in dependence_groups}
    if None in defined_groups or "None" in defined_groups:
        errors.append("dependence group missing dependence_group_id")
    referenced_groups = {
        str(group_id)
        for spec in specs
        for group_id in (spec.get("dependence_group_ids") or [])
    }
    unresolved_groups = sorted(referenced_groups - defined_groups)
    if unresolved_groups:
        errors.append(f"unresolved dependence groups: {unresolved_groups}")

    parameter_ids = {str(item.get("parameter_id")) for item in shared_parameters}
    referenced_parameters = {
        str(parameter_id)
        for spec in specs
        for parameter_id in (spec.get("shared_parameter_ids") or [])
    }
    unresolved_parameters = sorted(referenced_parameters - parameter_ids)
    if unresolved_parameters:
        errors.append(f"unresolved shared parameters: {unresolved_parameters}")

    frame = records_to_frame(evidence_records)
    evidence_pairs = set(
        frame[["dataset_id", "metric_id"]].drop_duplicates().itertuples(index=False, name=None)
    )
    spec_pairs = [(str(spec["dataset_id"]), str(spec["metric_id"])) for spec in specs]
    duplicate_spec_pairs = [value for value, count in Counter(spec_pairs).items() if count > 1]
    if duplicate_spec_pairs:
        errors.append(f"duplicate dataset/metric uncertainty mappings: {duplicate_spec_pairs}")

    spec_pair_set = set(spec_pairs)
    missing_specs = sorted(evidence_pairs - spec_pair_set)
    extra_specs = sorted(spec_pair_set - evidence_pairs)
    if missing_specs:
        errors.append(f"evidence metric groups without uncertainty spec: {missing_specs}")
    if extra_specs:
        errors.append(f"uncertainty specs without evidence metric group: {extra_specs}")

    mapped_records = int(frame.apply(lambda row: (row["dataset_id"], row["metric_id"]) in spec_pair_set, axis=1).sum())
    if mapped_records != len(frame):
        errors.append(f"only {mapped_records}/{len(frame)} evidence records map to an uncertainty spec")

    # Hard methodological compatibility checks with Stage-2 uncertainty_basis.
    for spec in specs:
        subset = frame[
            (frame["dataset_id"] == spec["dataset_id"]) & (frame["metric_id"] == spec["metric_id"])
        ]
        bases = set(subset["uncertainty_basis"].dropna().astype(str))
        regime = spec["evidence_uncertainty_regime"]
        if regime == "replicated_run_level" and bases != {"replicated_independent_units"}:
            errors.append(f"{spec['uncertainty_model_id']}: replicated regime conflicts with {sorted(bases)}")
        if regime in {"single_configuration_trace", "single_matched_contrast"} and bases != {"single_independent_unit"}:
            errors.append(f"{spec['uncertainty_model_id']}: single-unit regime conflicts with {sorted(bases)}")
        if regime == "shared_parameter_derived" and bases != {"shared_parameter"}:
            errors.append(f"{spec['uncertainty_model_id']}: shared-parameter regime conflicts with {sorted(bases)}")
        if regime == "hierarchical_observational_campaign" and bases != {"hierarchical_observational"}:
            errors.append(f"{spec['uncertainty_model_id']}: hierarchical regime conflicts with {sorted(bases)}")

    if errors:
        raise UncertaintyContractError("; ".join(errors[:15]))

    rows: list[dict[str, Any]] = []
    for spec in specs:
        subset = frame[
            (frame["dataset_id"] == spec["dataset_id"]) & (frame["metric_id"] == spec["metric_id"])
        ].copy()
        n_values = pd.to_numeric(subset["n_independent_units"], errors="coerce")
        implementation_missing = int(subset["implementation_context_id"].isna().sum())
        rows.append({
            "uncertainty_model_id": spec["uncertainty_model_id"],
            "dataset_id": spec["dataset_id"],
            "metric_id": spec["metric_id"],
            "record_count": int(len(subset)),
            "evidence_uncertainty_bases": _join_values(subset["uncertainty_basis"]),
            "n_independent_units_min": None if n_values.dropna().empty else int(n_values.min()),
            "n_independent_units_max": None if n_values.dropna().empty else int(n_values.max()),
            "records_without_independent_n": int(n_values.isna().sum()),
            "implementation_contexts": _join_values(subset["implementation_context_id"]),
            "records_without_implementation_context": implementation_missing,
            "support_domain": spec["support_domain"],
            "evidence_uncertainty_regime": spec["evidence_uncertainty_regime"],
            "population_variability_status": spec["population_variability_status"],
            "calibration_status": spec["calibration_status"],
            "primary_sampling_unit": spec["primary_sampling_unit"],
            "resampling_scheme": spec["resampling_scheme"],
            "distribution_family_status": spec["distribution_family_status"],
            "dependence_group_ids": _join_list(spec["dependence_group_ids"]),
            "shared_parameter_ids": _join_list(spec["shared_parameter_ids"]),
            "study_effect_status": spec["study_effect_status"],
            "implementation_effect_status": spec["implementation_effect_status"],
            "bridge_uncertainty_status": spec["bridge_uncertainty_status"],
            "forbidden_operations": _join_list(spec["forbidden_operations"]),
            "calibration_artifacts": _join_list(spec["calibration_artifacts"]),
            "notes": spec["notes"],
        })
    plan = pd.DataFrame(rows)

    dependence_frame = pd.DataFrame(dependence_groups)
    gap_frame = pd.DataFrame(calibration_gaps)

    calibration_counts = Counter(str(spec["calibration_status"]) for spec in specs)
    variability_counts = Counter(str(spec["population_variability_status"]) for spec in specs)
    regime_counts = Counter(str(spec["evidence_uncertainty_regime"]) for spec in specs)

    vomhoff_missing_impl = int(
        frame.loc[frame["dataset_id"] == "vomhoff_nbiot_ltem_energy_2023", "implementation_context_id"]
        .isna()
        .sum()
    )

    summary = {
        "stage": "Stage-3 uncertainty contract and identifiability audit",
        "evidence_records_mapped": len(frame),
        "dataset_metric_uncertainty_specs": len(specs),
        "dependence_groups": len(dependence_groups),
        "calibration_gaps": len(calibration_gaps),
        "shared_parameters_referenced": len(referenced_parameters),
        "unmapped_evidence_records": 0,
        "unmapped_dataset_metric_groups": 0,
        "unresolved_dependence_groups": 0,
        "unresolved_shared_parameters": 0,
        "calibration_status_counts": dict(sorted(calibration_counts.items())),
        "population_variability_status_counts": dict(sorted(variability_counts.items())),
        "uncertainty_regime_counts": dict(sorted(regime_counts.items())),
        "vomhoff_records_without_implementation_context": vomhoff_missing_impl,
        "generic_study_random_effect_authorised": False,
        "default_sd_or_cv_authorised": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 3 starts by specifying identifiable uncertainty layers and dependence. "
            "Replicated Vomhoff run-level variability and within-block nonparametric mean uncertainty are calibrated; "
            "single-trace InSecTT/LR-FHSS population variability needs external repeatability evidence or priors, "
            "and LoED has a campaign-indexed 3/7/14-day robustness family without a single probability distribution."
        ),
        "next_scientific_step": (
            "Resolve the remaining single-trace InSecTT/LR-FHSS uncertainty gaps with targeted external repeatability evidence or explicit conservative priors; "
            "retain the LoED campaign/block-length family as unweighted robustness scenarios for the later link-feasibility bridge."
        ),
    }
    return summary, plan, dependence_frame, gap_frame


def audit_from_paths(
    evidence_jsonl: str | Path = "data/analysis_ready/core_four_evidence/core_four_evidence_matrix.jsonl",
    shared_parameters_json: str | Path = "data/analysis_ready/core_four_evidence/shared_parameters.json",
    *,
    policy_path: str | Path = DEFAULT_UNCERTAINTY_POLICY,
    schema_path: str | Path = DEFAULT_UNCERTAINTY_SCHEMA,
):
    return audit_core_four_uncertainty(
        load_jsonl(evidence_jsonl),
        load_shared_parameters(shared_parameters_json),
        policy_path=policy_path,
        schema_path=schema_path,
    )
