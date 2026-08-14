
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.evidence import validate_evidence_record
from stackwise.io import dump_json, read_table, write_table
from stackwise.provenance import write_run_manifest
from stackwise.vomhoff_evidence import build_vomhoff_stage2


DEFAULT_INPUT = Path("data/processed/vomhoff_nbiot_ltem_energy_2023/observations.parquet")
DEFAULT_ANALYSIS_DIR = Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023")
DEFAULT_RESULTS_DIR = Path("results/validation/vomhoff_stage2_materialisation")


def _write_jsonl(records: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _records_for_csv(records: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    for field in ("parent_evidence_ids", "shared_parameter_ids"):
        if field in frame.columns:
            frame[field] = frame[field].map(
                lambda value: "|".join(str(v) for v in value) if isinstance(value, list) else value
            )
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialise validated Stage-2 Vomhoff logical phases and evidence records."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Validated harmonised Vomhoff table not found: {args.input}. "
            "Run 'stackwise harmonize vomhoff_nbiot_ltem_energy_2023 --strict' first."
        )

    frame = read_table(args.input)
    logical, records, comparison, summary = build_vomhoff_stage2(frame)

    evidence_errors: list[str] = []
    evidence_ids: set[str] = set()
    for record in records:
        if record["evidence_id"] in evidence_ids:
            evidence_errors.append(f"duplicate evidence_id: {record['evidence_id']}")
        evidence_ids.add(record["evidence_id"])
        errors = validate_evidence_record(record)
        evidence_errors.extend(f"{record['evidence_id']}: {error}" for error in errors)

    if evidence_errors:
        raise RuntimeError(
            "Vomhoff Stage-2 evidence records failed validation:\n- "
            + "\n- ".join(evidence_errors)
        )

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    logical_path = write_table(
        logical,
        args.analysis_dir / "logical_phase_observations.parquet",
    )
    records_jsonl_path = _write_jsonl(
        records,
        args.analysis_dir / "evidence_records.jsonl",
    )
    records_csv_path = write_table(
        _records_for_csv(records),
        args.analysis_dir / "evidence_records.csv",
    )
    comparison_path = write_table(
        comparison,
        args.results_dir / "source_vs_analysis_ready_comparison.csv",
    )
    summary["logical_phase_artifact"] = str(logical_path)
    summary["evidence_records_jsonl"] = str(records_jsonl_path)
    summary["evidence_records_csv"] = str(records_csv_path)
    summary["source_vs_analysis_ready_comparison"] = str(comparison_path)
    summary["evidence_schema_validation_errors"] = 0
    summary_path = dump_json(summary, args.results_dir / "summary.json")

    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_vomhoff_stage2_evidence.py",
        inputs=[args.input],
        outputs=[
            logical_path,
            records_jsonl_path,
            records_csv_path,
            comparison_path,
            summary_path,
        ],
        parameters={
            "within_run_data_request_aggregation": "sum contiguous source segments",
            "cross_figure_reuse_policy": "collapse exact non-Idle Figure-4/Figure-5 HTTP phase views to one physical run",
            "figure5_http_idle": "retain alternate dependent filtered view",
            "figure5_mqtt_idle": "exclude from decision evidence per source README",
            "figure5_mqtt_standby": "retain source-script value; no invented 10 s normalisation",
            "publication_mcda_authorised": False,
        },
    )

    print(f"Input source segments: {summary['input_source_segment_rows']}")
    print(f"Within-Figure logical phases: {summary['within_figure_logical_phase_rows']}")
    print(f"Within-run additive groups: {summary['within_run_additive_groups']}")
    print(f"Cross-Figure source-reuse run pairs: {summary['cross_figure_reuse_run_pairs']}")
    print(f"Cross-Figure phase views collapsed: {summary['cross_figure_phase_views_collapsed']}")
    print(f"Logical phases after reuse policy: {summary['logical_phase_rows_after_cross_figure_policy']}")
    print(f"Physical/source run units: {summary['physical_run_units']}")
    print(f"Figure-5 MQTT Idle excluded rows: {summary['excluded_figure5_mqtt_idle_rows']}")
    print(f"Figure-5 HTTP Idle alternate rows: {summary['alternate_figure5_http_idle_rows']}")
    print(f"Validated evidence records: {summary['evidence_records']}")
    print(f"Logical phase artifact: {logical_path}")
    print(f"Evidence records: {records_jsonl_path}")
    print(f"Comparison audit: {comparison_path}")
    print(f"Summary: {summary_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
