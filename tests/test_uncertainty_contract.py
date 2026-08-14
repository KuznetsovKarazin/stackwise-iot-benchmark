from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from stackwise.evidence_matrix import load_jsonl, load_shared_parameters
from stackwise.uncertainty import audit_core_four_uncertainty, load_uncertainty_policy, validate_uncertainty_spec


ROOT = Path(__file__).resolve().parents[1]
CORE_FOUR_MATRIX = ROOT / "data/analysis_ready/core_four_evidence/core_four_evidence_matrix.jsonl"
INSECTT_SHARED = ROOT / "data/analysis_ready/insectt_wsn_power_2023/shared_parameters.json"
SOURCE_ONLY_SKIP = pytest.mark.skipif(
    not CORE_FOUR_MATRIX.exists() or not INSECTT_SHARED.exists(),
    reason="source-only archive excludes materialised data/ analysis-ready artifacts",
)


def test_uncertainty_schema_and_policy_are_valid():
    schema = json.loads((ROOT / "datasets/schema/uncertainty_model.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)

    policy = load_uncertainty_policy(ROOT / "datasets/core_four_uncertainty_policy.yml")
    assert len(policy["metric_models"]) == 14
    assert len(policy["dependence_groups"]) == 8
    assert len(policy["calibration_gaps"]) == 6
    assert policy["publication_mcda_authorised"] is False

    for spec in policy["metric_models"]:
        assert validate_uncertainty_spec(
            spec, schema_path=ROOT / "datasets/schema/uncertainty_model.schema.json"
        ) == []


@SOURCE_ONLY_SKIP
def test_uncertainty_policy_covers_every_core_four_dataset_metric_once():
    records = load_jsonl(
        CORE_FOUR_MATRIX
    )
    shared = load_shared_parameters(
        INSECTT_SHARED
    )
    summary, plan, dependence, gaps = audit_core_four_uncertainty(
        records,
        shared,
        policy_path=ROOT / "datasets/core_four_uncertainty_policy.yml",
        schema_path=ROOT / "datasets/schema/uncertainty_model.schema.json",
    )

    assert summary["evidence_records_mapped"] == 398
    assert summary["dataset_metric_uncertainty_specs"] == 14
    assert summary["unmapped_evidence_records"] == 0
    assert summary["unresolved_dependence_groups"] == 0
    assert summary["unresolved_shared_parameters"] == 0
    assert len(plan) == 14
    assert len(dependence) == 8
    assert len(gaps) == 6


@SOURCE_ONLY_SKIP
def test_stage3_identifiability_safeguards():
    records = load_jsonl(
        CORE_FOUR_MATRIX
    )
    shared = load_shared_parameters(
        INSECTT_SHARED
    )
    summary, plan, _, _ = audit_core_four_uncertainty(
        records,
        shared,
        policy_path=ROOT / "datasets/core_four_uncertainty_policy.yml",
        schema_path=ROOT / "datasets/schema/uncertainty_model.schema.json",
    )

    assert summary["calibration_status_counts"] == {
        "calibrated_nonparametric": 2,
        "descriptive_only": 4,
        "external_prior_required": 6,
        "scenario_robustness_materialised": 2,
    }
    assert summary["population_variability_status_counts"] == {
        "conditional_scenario_uncertainty_materialised": 2,
        "empirically_calibratable": 2,
        "not_applicable_descriptive": 4,
        "not_identified_single_unit": 6,
    }
    assert summary["generic_study_random_effect_authorised"] is False
    assert summary["default_sd_or_cv_authorised"] is False
    assert summary["publication_uncertainty_sampling_authorised"] is False
    assert summary["publication_mcda_authorised"] is False

    single = plan[plan["population_variability_status"] == "not_identified_single_unit"]
    assert set(single["calibration_status"]) <= {"external_prior_required", "descriptive_only"}
    assert "calibrated_nonparametric" not in set(single["calibration_status"])

    loed = plan[plan["dataset_id"] == "loed_lorawan_edge_2020"]
    assert len(loed) == 5
    assert set(loed["evidence_uncertainty_regime"]) == {"hierarchical_observational_campaign"}
    assert loed["n_independent_units_min"].isna().all()
    assert loed["n_independent_units_max"].isna().all()


def test_shared_voltage_is_explicitly_correlated_not_independent():
    policy = yaml.safe_load(
        (ROOT / "datasets/core_four_uncertainty_policy.yml").read_text(encoding="utf-8")
    )
    derived = [
        spec for spec in policy["metric_models"]
        if spec["dataset_id"] == "insectt_wsn_power_2023"
        and spec["metric_id"] in {"derived_mean_power_w", "derived_capture_energy_j"}
    ]
    assert len(derived) == 2
    for spec in derived:
        assert spec["shared_parameter_ids"] == ["insectt_ppk2_source_voltage_v"]
        assert "insectt_shared_source_voltage" in spec["dependence_group_ids"]
        assert "independent_sampling_of_shared_parameter_derivatives" in spec["forbidden_operations"]


def test_vomhoff_device_effect_is_not_invented():
    policy = yaml.safe_load(
        (ROOT / "datasets/core_four_uncertainty_policy.yml").read_text(encoding="utf-8")
    )
    specs = [
        spec for spec in policy["metric_models"]
        if spec["dataset_id"] == "vomhoff_nbiot_ltem_energy_2023"
    ]
    assert len(specs) == 2
    assert {spec["implementation_effect_status"] for spec in specs} == {"implementation_context_unknown"}
    assert all(spec["resampling_scheme"] == "cluster_bootstrap_physical_run" for spec in specs)


def test_generic_study_random_effect_is_explicitly_blocked():
    taxonomy = yaml.safe_load(
        (ROOT / "datasets/uncertainty_taxonomy.yml").read_text(encoding="utf-8")
    )
    assert "generic_study_random_effect_from_confounded_core_four" in taxonomy["forbidden_shortcuts"]
