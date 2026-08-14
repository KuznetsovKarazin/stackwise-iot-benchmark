from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from stackwise.benchmark_release import (
    _materialise_refined_stage4_scenarios,
    build_benchmark_release,
    build_benchmark_release_candidate,
)


CORE_IDS = [
    "insectt_wsn_power_2023",
    "vomhoff_nbiot_ltem_energy_2023",
    "loed_lorawan_edge_2020",
    "lorawan_lrfhss_energy_2024",
]


def _write_fixture_project(root: Path, *, bad_license: bool = False) -> tuple[Path, Path]:
    (root / "data/analysis_ready/core_four_evidence").mkdir(parents=True)
    (root / "results/validation/stage4_hard_scenarios").mkdir(parents=True)
    (root / "results/validation/stage4_candidate_stacks").mkdir(parents=True)
    (root / "results/validation/stage4_hard_capability_review").mkdir(parents=True)
    (root / "datasets").mkdir(parents=True)
    (root / "datasets/schema").mkdir(parents=True)
    (root / "docs/DATASET_CARDS").mkdir(parents=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs/BENCHMARK_DATASET_RELEASE_CANDIDATE.md").write_text("# Fixture dataset card\n", encoding="utf-8")
    (root / "docs/BENCHMARK_DATASET.md").write_text("# Final fixture dataset card\n", encoding="utf-8")
    (root / "docs/BENCHMARK_LICENSE_CC_BY_4.0.md").write_text(
        "# CC BY 4.0\nhttps://creativecommons.org/licenses/by/4.0/\n", encoding="utf-8"
    )
    (root / "docs/BENCHMARK_CITATION.cff").write_text("cff-version: 1.2.0\ntitle: fixture\n", encoding="utf-8")
    (root / "docs/BENCHMARK_ZENODO_METADATA.json").write_text("{}\n", encoding="utf-8")
    for schema_name in [
        "evidence_record.schema.json",
        "canonical_observation.schema.json",
        "shared_parameter.schema.json",
        "benchmark_scenario.schema.json",
        "stack_candidate.schema.json",
        "stack_component.schema.json",
        "uncertainty_model.schema.json",
        "hard_constraint.schema.json",
    ]:
        (root / "datasets/schema" / schema_name).write_text("{}\n", encoding="utf-8")
    for dataset_id in CORE_IDS:
        (root / "docs/DATASET_CARDS" / f"{dataset_id}.md").write_text(
            f"# {dataset_id}\n", encoding="utf-8"
        )

    evidence = pd.DataFrame(
        [
            {
                "evidence_id": f"e{i}",
                "dataset_id": dataset_id,
                "technology": f"T{i}",
                "metric_id": "trace_mean_current_a" if i < 2 else "gateway_rssi_dbm",
                "source_grade": "A",
                "derivation_class": ["direct_empirical", "source_reproduced", "validated_derived", "validated_derived"][i],
                "source_license": "unknown" if dataset_id == "loed_lorawan_edge_2020" else "CC-BY-4.0",
            }
            for i, dataset_id in enumerate(CORE_IDS)
        ]
    )
    evidence.to_csv(
        root / "data/analysis_ready/core_four_evidence/core_four_evidence_matrix.csv",
        index=False,
    )
    pd.DataFrame([{"scenario_id": "s1"}]).to_csv(
        root / "results/validation/stage4_hard_scenarios/benchmark_scenarios.csv", index=False
    )
    pd.DataFrame([{"stack_id": "a"}, {"stack_id": "b"}]).to_csv(
        root / "results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv", index=False
    )
    pd.DataFrame(
        [
            {"scenario_id": "s1", "stack_id": "a", "status": "feasible"},
            {"scenario_id": "s1", "stack_id": "b", "status": "unresolved"},
        ]
    ).to_csv(
        root / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv",
        index=False,
    )

    registry = {
        "datasets": [
            {
                "id": dataset_id,
                "title": dataset_id,
                "doi": f"10.example/{i}",
                "landing_url": f"https://example.test/{i}",
                "licence": {
                    "id": "CC-BY-4.0",
                    "status": "unknown" if bad_license and i == 0 else "verified",
                    "redistribution": not (bad_license and i == 0),
                },
            }
            for i, dataset_id in enumerate(CORE_IDS)
        ]
    }
    registry_path = root / "datasets/registry.yml"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    attribution = {
        "reviewed_on": "2026-08-12",
        "review_status": "passed",
        "sources": [
            {
                "dataset_id": dataset_id,
                "dataset_title": dataset_id,
                "creators": [f"Author {i}"],
                "dataset_doi": f"10.example/{i}",
                "related_publication_title": f"Paper {i}",
                "related_publication_doi": f"10.paper/{i}",
                "upstream_license": "CC-BY-4.0",
                "stackwise_role": "fixture",
                "attribution_status": "verified",
                "verification_basis": "fixture",
            }
            for i, dataset_id in enumerate(CORE_IDS)
        ],
    }
    (root / "datasets/benchmark_source_attribution.yml").write_text(
        yaml.safe_dump(attribution, sort_keys=False), encoding="utf-8"
    )

    policy = {
        "benchmark_id": "fixture",
        "benchmark_version": "1.0.0-rc1",
        "project_version": "0.1.50",
        "prepared_on": "2026-08-12",
        "release_profile": "fixture",
        "core_source_ids": CORE_IDS,
        "expected": {
            "core_evidence_records": 4,
            "core_datasets": 4,
            "core_metrics": 2,
            "source_grade_A_records": 4,
            "benchmark_scenarios": 1,
            "candidate_stacks": 2,
            "feasibility_rows": 2,
            "feasible_rows": 1,
            "infeasible_rows": 0,
            "unresolved_rows": 1,
        },
        "artifacts": [
            {
                "source": "data/analysis_ready/core_four_evidence/core_four_evidence_matrix.csv",
                "destination": "tables/L1_evidence_records/core_four_evidence_matrix.csv",
                "layer": "L1_evidence_records",
                "required": True,
                "row_count": 4,
            },
            {
                "source": "results/validation/stage4_hard_scenarios/benchmark_scenarios.csv",
                "destination": "tables/L3_benchmark_definitions/benchmark_scenarios.csv",
                "layer": "L3_benchmark_definitions",
                "required": True,
                "row_count": 1,
            },
            {
                "source": "results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv",
                "destination": "tables/L3_benchmark_definitions/candidate_stack_catalog.csv",
                "layer": "L3_benchmark_definitions",
                "required": True,
                "row_count": 2,
            },
            {
                "source": "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv",
                "destination": "tables/L4_feasibility_and_support/refined_hard_feasibility_matrix.csv",
                "layer": "L4_feasibility_and_support",
                "required": True,
                "row_count": 2,
            },
        ],
    }
    policy_path = root / "datasets/benchmark_release_candidate.yml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return policy_path, registry_path


def test_release_builder_materialises_and_resolves_source_license(tmp_path: Path) -> None:
    policy, registry = _write_fixture_project(tmp_path)
    result = build_benchmark_release_candidate(
        tmp_path,
        policy_path=policy.relative_to(tmp_path),
        registry_path=registry.relative_to(tmp_path),
        output_dir="release/test_rc",
    )
    output = Path(result["output_dir"])
    summary = json.loads((output / "release_summary.json").read_text(encoding="utf-8"))
    assert summary["core_evidence_records"] == 4
    assert summary["raw_external_data_included"] is False
    assert summary["zenodo_upload_authorised"] is False
    assert (output / "CHECKSUMS.sha256").exists()
    assert summary["release_metadata_files"] == 13
    assert summary["benchmark_release_license_declared"] is False
    assert (output / "DATASET_CARD.md").exists()
    assert len(list((output / "schemas").glob("*.json"))) == 8
    assert len(list((output / "source_dataset_cards").glob("*.md"))) == 4

    released = pd.read_csv(output / "tables/L1_evidence_records/core_four_evidence_matrix.csv")
    loed = released.loc[released["dataset_id"] == "loed_lorawan_edge_2020"].iloc[0]
    assert loed["source_license"] == "CC-BY-4.0"
    corrections = pd.read_csv(output / "LICENSE_METADATA_CORRECTIONS.csv")
    loed_fix = corrections.loc[corrections["dataset_id"] == "loed_lorawan_edge_2020"].iloc[0]
    assert loed_fix["source_license_at_materialisation"] == "unknown"
    assert loed_fix["resolved_release_license"] == "CC-BY-4.0"


def test_release_builder_fails_closed_on_unverified_core_license(tmp_path: Path) -> None:
    policy, registry = _write_fixture_project(tmp_path, bad_license=True)
    with pytest.raises(RuntimeError, match="verified redistributable licences"):
        build_benchmark_release_candidate(
            tmp_path,
            policy_path=policy.relative_to(tmp_path),
            registry_path=registry.relative_to(tmp_path),
            output_dir="release/test_rc",
        )


def test_production_policy_freezes_expected_release_counts() -> None:
    policy = yaml.safe_load(Path("datasets/benchmark_release_candidate.yml").read_text(encoding="utf-8"))
    assert policy["benchmark_version"] == "1.0.0-rc1"
    assert policy["project_version"] == "0.1.50.post2"
    assert policy["expected"]["core_evidence_records"] == 398
    assert policy["expected"]["benchmark_scenarios"] == 7
    assert policy["expected"]["candidate_stacks"] == 9
    assert policy["expected"]["feasibility_rows"] == 63
    assert policy["raw_external_data_included"] is False
    assert policy["zenodo_upload_authorised"] is False


def test_loed_registry_license_is_verified_for_derived_release() -> None:
    registry = yaml.safe_load(Path("datasets/registry.yml").read_text(encoding="utf-8"))
    loed = next(item for item in registry["datasets"] if item["id"] == "loed_lorawan_edge_2020")
    assert loed["licence"] == {
        "id": "CC-BY-4.0",
        "status": "verified",
        "redistribution": True,
    }


def test_production_release_materialises_canonical_refined_scenarios(tmp_path: Path) -> None:
    policy = yaml.safe_load(Path("datasets/benchmark_release_candidate.yml").read_text(encoding="utf-8"))
    scenario_artifact = next(
        item for item in policy["artifacts"]
        if item["destination"] == "tables/L3_benchmark_definitions/benchmark_scenarios.csv"
    )
    assert scenario_artifact["source"] == "datasets/stage4_benchmark_scenarios.yml"
    assert scenario_artifact["transform"] == "stage4_refined_scenarios"
    assert scenario_artifact["row_count"] == 7

    output = tmp_path / "benchmark_scenarios.csv"
    _materialise_refined_stage4_scenarios(Path(scenario_artifact["source"]), output)
    frame = pd.read_csv(output)
    assert len(frame) == 7
    assert "asset_tracking_mobility" not in set(frame["scenario_id"])
    assert {
        "asset_tracking_periodic_cross_cell",
        "asset_tracking_connected_handover",
    }.issubset(set(frame["scenario_id"]))
    assert set(frame.loc[frame["scenario_id"].str.startswith("asset_tracking_"), "payload_bytes"]) == {64}
    assert set(frame.loc[frame["scenario_id"].str.startswith("asset_tracking_"), "reporting_interval_s"]) == {60}


def test_parquet_row_count_uses_real_metadata_not_false_zero(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    from stackwise.benchmark_release import _count_rows

    path = tmp_path / "rows.parquet"
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(path, index=False)
    assert _count_rows(path) == 3


def test_final_release_builder_declares_dataset_license_and_attribution(tmp_path: Path) -> None:
    policy_path, registry = _write_fixture_project(tmp_path)
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    policy.update({
        "benchmark_version": "1.0.0",
        "project_version": "0.1.51",
        "release_status": "final",
        "zenodo_upload_authorised": True,
        "dataset_card_source": "docs/BENCHMARK_DATASET.md",
        "benchmark_license": {
            "id": "CC-BY-4.0",
            "source": "docs/BENCHMARK_LICENSE_CC_BY_4.0.md",
            "destination": "LICENSE.md",
        },
        "attribution_review": {
            "status": "passed",
            "reviewed_on": "2026-08-12",
            "source": "datasets/benchmark_source_attribution.yml",
        },
        "metadata_assets": [
            {"source": "docs/BENCHMARK_CITATION.cff", "destination": "CITATION.cff"},
            {"source": "docs/BENCHMARK_ZENODO_METADATA.json", "destination": "ZENODO_METADATA.json"},
        ],
    })
    final_policy = tmp_path / "datasets/benchmark_release.yml"
    final_policy.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    result = build_benchmark_release(
        tmp_path,
        policy_path=final_policy.relative_to(tmp_path),
        registry_path=registry.relative_to(tmp_path),
        output_dir="release/final",
    )
    output = Path(result["output_dir"])
    summary = json.loads((output / "release_summary.json").read_text(encoding="utf-8"))
    assert summary["benchmark_version"] == "1.0.0"
    assert summary["benchmark_release_license_id"] == "CC-BY-4.0"
    assert summary["scientific_attribution_review_passed"] is True
    assert summary["zenodo_upload_authorised"] is True
    assert (output / "LICENSE.md").exists()
    assert len(pd.read_csv(output / "SOURCE_ATTRIBUTION.csv")) == 4
    assert json.loads((output / "ATTRIBUTION_REVIEW.json").read_text())["status"] == "passed"
    assert (output / "CITATION.cff").exists()
    assert (output / "ZENODO_METADATA.json").exists()


def test_production_final_policy_freezes_v1_release_and_cc_by() -> None:
    policy = yaml.safe_load(Path("datasets/benchmark_release.yml").read_text(encoding="utf-8"))
    assert policy["benchmark_version"] == "1.0.0"
    assert policy["project_version"] == "0.1.51"
    assert policy["release_status"] == "final"
    assert policy["benchmark_license"]["id"] == "CC-BY-4.0"
    assert policy["attribution_review"]["status"] == "passed"
    assert policy["zenodo_upload_authorised"] is True
    assert policy["publication_mcda_authorised"] is False


def test_production_source_attribution_covers_exactly_core_four() -> None:
    payload = yaml.safe_load(Path("datasets/benchmark_source_attribution.yml").read_text(encoding="utf-8"))
    rows = payload["sources"]
    assert payload["review_status"] == "passed"
    assert {row["dataset_id"] for row in rows} == set(CORE_IDS)
    assert all(row["attribution_status"] == "verified" for row in rows)
    assert all(row["upstream_license"] == "CC-BY-4.0" for row in rows)
    assert all(row["creators"] for row in rows)
    assert all(row["dataset_doi"] for row in rows)
