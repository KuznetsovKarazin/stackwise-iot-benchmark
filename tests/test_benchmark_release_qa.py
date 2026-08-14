from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from stackwise.benchmark_release_qa import audit_benchmark_release, audit_benchmark_release_candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_qa_checks_equivalence_product_and_checksums(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    root = tmp_path / "release"
    evidence_dir = root / "tables/L1_evidence_records"
    scenario_dir = root / "tables/L3_benchmark_definitions"
    feasibility_dir = root / "tables/L4_feasibility_and_support"
    evidence_dir.mkdir(parents=True)
    scenario_dir.mkdir(parents=True)
    feasibility_dir.mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "source_dataset_cards").mkdir()

    evidence = pd.DataFrame(
        [
            {
                "evidence_id": "e1",
                "dataset_id": "d1",
                "metric_id": "m1",
                "technology": "T1",
                "source_license": "CC-BY-4.0",
            },
            {
                "evidence_id": "e2",
                "dataset_id": "d2",
                "metric_id": "m2",
                "technology": "T2",
                "source_license": "CC-BY-4.0",
            },
        ]
    )
    evidence.to_csv(evidence_dir / "core_four_evidence_matrix.csv", index=False)
    evidence.to_json(evidence_dir / "core_four_evidence_matrix.jsonl", orient="records", lines=True)
    evidence.to_parquet(evidence_dir / "core_four_evidence_matrix.parquet", index=False)

    scenarios = pd.DataFrame([{"scenario_id": "s1"}, {"scenario_id": "s2"}])
    stacks = pd.DataFrame([{"stack_id": "a"}, {"stack_id": "b"}])
    feasibility = pd.DataFrame(
        [
            {"scenario_id": scenario, "stack_id": stack, "status": "feasible"}
            for scenario in ["s1", "s2"]
            for stack in ["a", "b"]
        ]
    )
    scenarios.to_csv(scenario_dir / "benchmark_scenarios.csv", index=False)
    stacks.to_csv(scenario_dir / "candidate_stack_catalog.csv", index=False)
    feasibility.to_csv(feasibility_dir / "refined_hard_feasibility_matrix.csv", index=False)

    licences = pd.DataFrame(
        [
            {
                "dataset_id": f"d{i}",
                "license_status": "verified",
                "redistribution": True,
            }
            for i in range(1, 5)
        ]
    )
    licences.to_csv(root / "SOURCE_LICENSES.csv", index=False)
    pd.DataFrame([]).to_csv(root / "LICENSE_METADATA_CORRECTIONS.csv", index=False)
    (root / "README.md").write_text("# RC\n", encoding="utf-8")
    (root / "DATASET_CARD.md").write_text("# Dataset card\n", encoding="utf-8")
    for i in range(8):
        (root / "schemas" / f"schema_{i}.json").write_text("{}\n", encoding="utf-8")
    for i in range(4):
        (root / "source_dataset_cards" / f"d{i}.md").write_text("# source\n", encoding="utf-8")

    table_paths = [
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.csv", 2),
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.jsonl", 2),
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.parquet", 2),
        ("L3_benchmark_definitions", scenario_dir / "benchmark_scenarios.csv", 2),
        ("L3_benchmark_definitions", scenario_dir / "candidate_stack_catalog.csv", 2),
        ("L4_feasibility_and_support", feasibility_dir / "refined_hard_feasibility_matrix.csv", 4),
    ]
    manifest_rows = []
    for layer, path, rows in table_paths:
        manifest_rows.append(
            {
                "layer": layer,
                "source_path": "fixture",
                "release_path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "rows": rows,
                "sha256": _sha256(path),
                "raw_external_data": False,
            }
        )
    pd.DataFrame(manifest_rows).to_csv(root / "RELEASE_TABLE_MANIFEST.csv", index=False)
    (root / "release_summary.json").write_text(
        json.dumps(
            {
                "benchmark_version": "1.0.0-rc1",
                "project_version": "0.1.50.post2",
                "release_artifact_files": len(manifest_rows),
            }
        ),
        encoding="utf-8",
    )

    checksum_lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256"):
        checksum_lines.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "CHECKSUMS.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    result = audit_benchmark_release_candidate(root)
    assert result["release_integrity_passed"] is True
    assert result["checks_failed"] == 0
    assert result["checks"]["canonical_evidence_formats_semantically_equivalent"] is True
    assert result["checks"]["feasibility_is_complete_scenario_stack_product"] is True
    assert result["checks"]["parquet_rows_are_materialised_not_false_zero"] is True
    assert result["benchmark_release_license_declared"] is False
    assert result["zenodo_finalisation_ready"] is False
    assert "benchmark_release_license_not_declared" in result["manual_finalisation_blockers"]


def test_final_release_qa_closes_license_and_attribution_gates(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    root = tmp_path / "release"
    evidence_dir = root / "tables/L1_evidence_records"
    scenario_dir = root / "tables/L3_benchmark_definitions"
    feasibility_dir = root / "tables/L4_feasibility_and_support"
    evidence_dir.mkdir(parents=True)
    scenario_dir.mkdir(parents=True)
    feasibility_dir.mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "source_dataset_cards").mkdir()

    evidence = pd.DataFrame([
        {"evidence_id": "e1", "dataset_id": "d1", "metric_id": "m1", "technology": "T1", "source_license": "CC-BY-4.0"},
        {"evidence_id": "e2", "dataset_id": "d2", "metric_id": "m2", "technology": "T2", "source_license": "CC-BY-4.0"},
    ])
    evidence.to_csv(evidence_dir / "core_four_evidence_matrix.csv", index=False)
    evidence.to_json(evidence_dir / "core_four_evidence_matrix.jsonl", orient="records", lines=True)
    evidence.to_parquet(evidence_dir / "core_four_evidence_matrix.parquet", index=False)
    pd.DataFrame([{"scenario_id":"s1"},{"scenario_id":"s2"}]).to_csv(scenario_dir / "benchmark_scenarios.csv", index=False)
    pd.DataFrame([{"stack_id":"a"},{"stack_id":"b"}]).to_csv(scenario_dir / "candidate_stack_catalog.csv", index=False)
    pd.DataFrame([
        {"scenario_id":s,"stack_id":t,"status":"feasible"}
        for s in ["s1","s2"] for t in ["a","b"]
    ]).to_csv(feasibility_dir / "refined_hard_feasibility_matrix.csv", index=False)

    licences = pd.DataFrame([
        {"dataset_id":f"d{i}","license_status":"verified","redistribution":True}
        for i in range(1,5)
    ])
    licences.to_csv(root / "SOURCE_LICENSES.csv", index=False)
    pd.DataFrame([]).to_csv(root / "LICENSE_METADATA_CORRECTIONS.csv", index=False)
    attribution = pd.DataFrame([
        {"dataset_id":f"d{i}","dataset_title":f"D{i}","creators":f"A{i}","dataset_doi":f"10.d/{i}",
         "related_publication_title":f"P{i}","related_publication_doi":f"10.p/{i}",
         "upstream_license":"CC-BY-4.0","stackwise_role":"fixture","attribution_status":"verified","verification_basis":"fixture"}
        for i in range(1,5)
    ])
    attribution.to_csv(root / "SOURCE_ATTRIBUTION.csv", index=False)
    (root / "ATTRIBUTION_REVIEW.json").write_text(json.dumps({"status":"passed","core_source_rows":4}), encoding="utf-8")
    (root / "README.md").write_text("# final\n", encoding="utf-8")
    (root / "DATASET_CARD.md").write_text("# final card\n", encoding="utf-8")
    (root / "LICENSE.md").write_text("CC BY 4.0 https://creativecommons.org/licenses/by/4.0/\n", encoding="utf-8")
    (root / "CITATION.cff").write_text("cff-version: 1.2.0\n", encoding="utf-8")
    (root / "ZENODO_METADATA.json").write_text("{}\n", encoding="utf-8")
    for i in range(8):
        (root / "schemas" / f"schema_{i}.json").write_text("{}\n", encoding="utf-8")
    for i in range(4):
        (root / "source_dataset_cards" / f"d{i}.md").write_text("# source\n", encoding="utf-8")

    table_paths = [
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.csv", 2),
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.jsonl", 2),
        ("L1_evidence_records", evidence_dir / "core_four_evidence_matrix.parquet", 2),
        ("L3_benchmark_definitions", scenario_dir / "benchmark_scenarios.csv", 2),
        ("L3_benchmark_definitions", scenario_dir / "candidate_stack_catalog.csv", 2),
        ("L4_feasibility_and_support", feasibility_dir / "refined_hard_feasibility_matrix.csv", 4),
    ]
    manifest=[]
    for layer,path,rows in table_paths:
        manifest.append({"layer":layer,"source_path":"fixture","release_path":path.relative_to(root).as_posix(),
                         "bytes":path.stat().st_size,"rows":rows,"sha256":_sha256(path),"raw_external_data":False})
    pd.DataFrame(manifest).to_csv(root / "RELEASE_TABLE_MANIFEST.csv", index=False)
    (root / "release_summary.json").write_text(json.dumps({
        "benchmark_version":"1.0.0","project_version":"0.1.51","release_status":"final",
        "release_artifact_files":len(manifest),"benchmark_release_license_id":"CC-BY-4.0",
        "zenodo_upload_authorised":True
    }), encoding="utf-8")
    checksum_lines=[]
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256"):
        checksum_lines.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "CHECKSUMS.sha256").write_text("\n".join(checksum_lines)+"\n", encoding="utf-8")

    result = audit_benchmark_release(root)
    assert result["release_integrity_passed"] is True
    assert result["manual_finalisation_blockers"] == []
    assert result["zenodo_finalisation_ready"] is True
    assert result["checks"]["four_core_source_attributions_verified"] is True
    assert result["checks"]["benchmark_release_license_is_cc_by_4_0"] is True
