from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stackwise.evidence_matrix import (
    CORE_FOUR_DATASET_IDS,
    EXPECTED_CORE_FOUR_RECORD_COUNTS,
    build_boundary_profile,
    build_matrix_summary,
    build_metric_coverage,
    build_nonmetric_gap_table,
    build_target_gap_matrix,
    load_jsonl,
    load_shared_parameters,
    records_to_csv_frame,
    records_to_frame,
    validate_core_four_matrix,
)
from stackwise.io import dump_json, write_table
from stackwise.provenance import write_run_manifest


DEFAULT_EVIDENCE_PATHS = {
    "vomhoff_nbiot_ltem_energy_2023": Path(
        "data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/evidence_records.jsonl"
    ),
    "insectt_wsn_power_2023": Path(
        "data/analysis_ready/insectt_wsn_power_2023/evidence_records.jsonl"
    ),
    "lorawan_lrfhss_energy_2024": Path(
        "data/analysis_ready/lorawan_lrfhss_energy_2024/evidence_records.jsonl"
    ),
    "loed_lorawan_edge_2020": Path(
        "data/analysis_ready/loed_lorawan_edge_2020/evidence_records.jsonl"
    ),
}
DEFAULT_SHARED_PARAMETER_PATHS = [
    Path("data/analysis_ready/insectt_wsn_power_2023/shared_parameters.json"),
]


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble and validate the canonical Stage-2 core-four empirical evidence matrix."
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("data/analysis_ready/core_four_evidence"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/core_four_evidence_matrix"),
    )
    args = parser.parse_args()

    evidence_paths = dict(DEFAULT_EVIDENCE_PATHS)
    missing = [str(path) for path in evidence_paths.values() if not path.exists()]
    missing += [str(path) for path in DEFAULT_SHARED_PARAMETER_PATHS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required Stage-2 artifacts are missing: {missing}")

    records: list[dict[str, Any]] = []
    for dataset_id in CORE_FOUR_DATASET_IDS:
        source_records = load_jsonl(evidence_paths[dataset_id])
        wrong_dataset = [
            record.get("evidence_id")
            for record in source_records
            if record.get("dataset_id") != dataset_id
        ]
        if wrong_dataset:
            raise RuntimeError(
                f"Evidence artifact {evidence_paths[dataset_id]} contains wrong dataset_id values: "
                f"{wrong_dataset[:5]}"
            )
        records.extend(source_records)

    shared_parameters: list[dict[str, Any]] = []
    for path in DEFAULT_SHARED_PARAMETER_PATHS:
        shared_parameters.extend(load_shared_parameters(path))

    validation = validate_core_four_matrix(
        records,
        shared_parameters,
        expected_counts=EXPECTED_CORE_FOUR_RECORD_COUNTS,
    )
    if validation["records"] != 398:
        raise RuntimeError(f"Frozen core-four record checkpoint failed: {validation['records']} != 398")
    if validation["metrics"] != 14:
        raise RuntimeError(f"Frozen core-four metric checkpoint failed: {validation['metrics']} != 14")
    if validation["shared_parameters"] != 1:
        raise RuntimeError(
            f"Frozen core-four shared-parameter checkpoint failed: "
            f"{validation['shared_parameters']} != 1"
        )

    metric_coverage = build_metric_coverage(records)
    boundary_profile = build_boundary_profile(records)
    target_gaps = build_target_gap_matrix(records)
    nonmetric_gaps = build_nonmetric_gap_table()
    summary = build_matrix_summary(
        records,
        shared_parameters,
        target_gaps,
        boundary_profile,
        validation,
    )

    # Frozen Stage-2 scientific safeguards.
    if summary["target_only_empirical_records"] != 0:
        raise RuntimeError("Target-only decision metrics must not be present in empirical evidence")
    if summary["loed_records_without_independent_n"] != 246:
        raise RuntimeError(
            "All 246 LoED records must retain n_independent_units=null under the hierarchical policy"
        )
    if len(target_gaps) != 20:
        raise RuntimeError(f"Expected 5 target metrics x 4 core datasets = 20 gap rows, got {len(target_gaps)}")
    if len(nonmetric_gaps) < 3:
        raise RuntimeError("Non-metric evidence-gap audit is unexpectedly incomplete")

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = _write_jsonl(records, args.analysis_dir / "core_four_evidence_matrix.jsonl")
    csv_path = write_table(records_to_csv_frame(records), args.analysis_dir / "core_four_evidence_matrix.csv")
    parquet_path = write_table(records_to_frame(records), args.analysis_dir / "core_four_evidence_matrix.parquet")
    shared_path = dump_json(shared_parameters, args.analysis_dir / "shared_parameters.json")
    coverage_path = write_table(metric_coverage, args.results_dir / "metric_coverage.csv")
    boundary_path = write_table(boundary_profile, args.results_dir / "boundary_profile.csv")
    target_gap_path = write_table(target_gaps, args.results_dir / "decision_target_gap_matrix.csv")
    nonmetric_gap_path = write_table(nonmetric_gaps, args.results_dir / "nonmetric_evidence_gaps.csv")

    summary.update(
        {
            "core_four_evidence_jsonl": str(jsonl_path),
            "core_four_evidence_csv": str(csv_path),
            "core_four_evidence_parquet": str(parquet_path),
            "shared_parameters_artifact": str(shared_path),
            "metric_coverage": str(coverage_path),
            "boundary_profile": str(boundary_path),
            "decision_target_gap_matrix": str(target_gap_path),
            "nonmetric_evidence_gaps": str(nonmetric_gap_path),
        }
    )
    summary_path = dump_json(summary, args.results_dir / "summary.json")
    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_core_four_evidence_matrix.py",
        inputs=list(evidence_paths.values()) + DEFAULT_SHARED_PARAMETER_PATHS,
        outputs=[
            jsonl_path,
            csv_path,
            parquet_path,
            shared_path,
            coverage_path,
            boundary_path,
            target_gap_path,
            nonmetric_gap_path,
            summary_path,
        ],
        parameters={
            "stage": "Stage 2 unified core-four empirical evidence matrix",
            "expected_records": 398,
            "expected_metrics": 14,
            "expected_shared_parameters": 1,
            "target_metrics_assessed": 5,
            "publication_mcda_authorised": False,
            "imputation_of_missing_evidence_authorised": False,
            "stage3_uncertainty_next": True,
        },
    )

    print(f"Core datasets: {summary['datasets']}")
    print(f"Evidence records: {summary['records']}")
    for dataset_id, count in summary["records_by_dataset"].items():
        print(f"  {dataset_id}: {count}")
    print(f"Distinct empirical metrics: {summary['metrics']}")
    print(f"Boundary signatures: {summary['boundary_signatures']}")
    print(f"Shared uncertain/calibration parameters: {summary['shared_parameters']}")
    print(f"Decision target gap rows: {len(target_gaps)}")
    print("Unresolved parent evidence references: 0")
    print("Unresolved shared parameter references: 0")
    print("Target-only metrics materialised as empirical evidence: 0")
    print("Missing-evidence imputation authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Matrix: {parquet_path}")
    print(f"Gap matrix: {target_gap_path}")
    print(f"Summary: {summary_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
