from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from stackwise.evidence import validate_evidence_record
from stackwise.io import dump_json, write_table
from stackwise.loed_evidence import (
    build_evidence_records,
    build_overall_descriptive_records,
    build_streaming_summaries,
    build_summary,
)
from stackwise.provenance import write_run_manifest


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _records_for_csv(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = dict(record)
        row["parent_evidence_ids"] = "|".join(record.get("parent_evidence_ids") or [])
        row["shared_parameter_ids"] = "|".join(record.get("shared_parameter_ids") or [])
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialise validated full-LoED Stage-2 evidence summaries.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/loed_lorawan_edge_2020/observations.parquet"),
    )
    parser.add_argument(
        "--logical-frames",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/logical_frame_reception_clusters.parquet"),
    )
    parser.add_argument(
        "--validation-summary",
        type=Path,
        default=Path("results/validation/loed/loed_validation_summary.json"),
    )
    parser.add_argument(
        "--analysis-dir",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/loed_stage2_materialisation"),
    )
    args = parser.parse_args()

    for path in [args.input, args.logical_frames, args.validation_summary]:
        if not path.exists():
            raise FileNotFoundError(path)

    validated = json.loads(args.validation_summary.read_text(encoding="utf-8"))
    if not validated.get("structural_checks_passed"):
        raise RuntimeError("LoED structural validation checkpoint is not passing")
    if validated.get("source_profile") != "full":
        raise RuntimeError("Stage-2 LoED materialisation requires the validated full corpus")

    phy, gateway_phy, logical_phy, diagnostics = build_streaming_summaries(args.input, args.logical_frames)
    records = build_evidence_records(phy, logical_phy)
    records.extend(build_overall_descriptive_records(diagnostics, logical_phy))

    validation_errors = []
    for record in records:
        errors = validate_evidence_record(record)
        if errors:
            validation_errors.append({"evidence_id": record.get("evidence_id"), "errors": errors})
    if validation_errors:
        raise RuntimeError(f"LoED evidence schema errors: {validation_errors[:3]}")
    if len({r["evidence_id"] for r in records}) != len(records):
        raise RuntimeError("Duplicate LoED evidence_id values detected")
    if any(r.get("metric_id") == "delivery_probability" for r in records):
        raise RuntimeError("LoED must not materialise delivery_probability/PDR")
    if any(r.get("n_independent_units") is not None for r in records):
        raise RuntimeError("LoED Stage-2 records must not invent independent-unit counts")

    summary = build_summary(phy, gateway_phy, logical_phy, diagnostics, records)

    # Frozen full-corpus checkpoints from the validated source and logical-frame artifact.
    expected = {
        "raw_reception_rows": int(validated["rows"]),
        "crc_valid_receptions": int(validated["crc_valid_receptions"]),
        "crc_invalid_receptions": int(validated["crc_invalid_receptions"]),
        "logical_frame_clusters": int(validated["logical_frame_clusters"]),
        "multi_gateway_logical_frames": int(validated["multi_gateway_logical_frames"]),
        "gateway_count_max_per_logical_frame": int(validated["gateway_count_max_per_logical_frame"]),
        "logical_frames_with_repeat_receptions": int(validated["logical_frames_with_repeat_receptions"]),
        "logical_frame_spans_over_1s": int(validated["logical_frame_spans_over_1s"]),
    }
    for key, expected_value in expected.items():
        actual = int(summary[key])
        if actual != expected_value:
            raise RuntimeError(f"LoED Stage-2 checkpoint mismatch for {key}: {actual} != {expected_value}")

    if summary["canonical_snr_observations"] > summary["raw_reception_rows"]:
        raise RuntimeError("Canonical SNR observation count exceeds reception rows")
    expected_snr_upper = summary["raw_reception_rows"] - int(validated.get("source_snr_out_of_range_count", 0))
    if summary["canonical_snr_observations"] > expected_snr_upper:
        raise RuntimeError("Canonical SNR count is inconsistent with validated out-of-range source SNR count")

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    phy_path = write_table(phy, args.analysis_dir / "reception_phy_summary.csv")
    gateway_phy_path = write_table(gateway_phy, args.analysis_dir / "gateway_phy_summary.csv")
    logical_phy_path = write_table(logical_phy, args.analysis_dir / "logical_frame_phy_summary.csv")
    records_jsonl_path = _write_jsonl(records, args.analysis_dir / "evidence_records.jsonl")
    records_csv_path = write_table(_records_for_csv(records), args.analysis_dir / "evidence_records.csv")

    summary.update({
        "reception_phy_summary": str(phy_path),
        "gateway_phy_summary": str(gateway_phy_path),
        "logical_frame_phy_summary": str(logical_phy_path),
        "gateway_day_summary_existing": str(args.analysis_dir / "gateway_day_summary.csv"),
        "evidence_records_jsonl": str(records_jsonl_path),
        "evidence_records_csv": str(records_csv_path),
        "evidence_schema_validation_errors": 0,
        "publication_mcda_authorised": False,
    })
    summary_path = dump_json(summary, args.results_dir / "summary.json")
    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_loed_stage2_evidence.py",
        inputs=[args.input, args.logical_frames, args.validation_summary],
        outputs=[phy_path, gateway_phy_path, logical_phy_path, records_jsonl_path, records_csv_path, summary_path],
        parameters={
            "reception_stratum": "spreading_factor x frequency x bandwidth",
            "statistical_unit": "recorded gateway reception / CRC-valid exact-PHY logical frame",
            "n_independent_units": None,
            "hierarchical_dependence": True,
            "pdr_materialisation_authorised": False,
            "sqrt_n_confidence_intervals_authorised": False,
            "logical_frame_identity": "CRC-valid exact-PHY fingerprint within source day; no wall-clock gap",
            "publication_mcda_authorised": False,
        },
    )

    print(f"Reception rows: {summary['raw_reception_rows']:,}")
    print(f"Canonical SNR observations: {summary['canonical_snr_observations']:,}")
    print(f"Reception PHY strata: {summary['phy_strata']}")
    print(f"Gateway x PHY strata: {summary['gateway_phy_strata']}")
    print(f"Logical-frame PHY strata: {summary['logical_frame_phy_strata']}")
    print(f"Logical frames: {summary['logical_frame_clusters']:,}")
    print(
        "Multi-gateway logical frames: "
        f"{summary['multi_gateway_logical_frames']:,} ({100*summary['multi_gateway_logical_frame_fraction']:.4f}%)"
    )
    print(f"Evidence records: {summary['evidence_records']}")
    for metric, count in summary["evidence_records_by_metric"].items():
        print(f"  {metric}: {count}")
    print("Independent-unit count assigned: NO")
    print("Absolute PDR/delivery probability materialised: NO")
    print("sqrt(n) confidence intervals authorised: NO")
    print(f"Evidence records: {records_csv_path}")
    print(f"Summary: {summary_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
