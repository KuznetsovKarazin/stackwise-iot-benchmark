from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.evidence import validate_evidence_record, validate_shared_parameter_record
from stackwise.insectt_evidence import build_insectt_stage2
from stackwise.io import dump_json, read_table, write_table
from stackwise.provenance import write_run_manifest

DEFAULT_INPUT = Path("data/processed/insectt_wsn_power_2023/observations.parquet")
DEFAULT_REFERENCE = Path("datasets/reference/insectt_table1_power_uw.csv")
DEFAULT_ANALYSIS_DIR = Path("data/analysis_ready/insectt_wsn_power_2023")
DEFAULT_RESULTS_DIR = Path("results/validation/insectt_stage2_materialisation")


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
        description="Materialise validated Stage-2 InSecTT configuration evidence with shared-voltage lineage."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Validated harmonised InSecTT table not found: {args.input}. "
            "Run 'stackwise harmonize insectt_wsn_power_2023 --strict' first."
        )
    if not args.reference.exists():
        raise FileNotFoundError(f"Missing publication reference table: {args.reference}")

    frame = read_table(args.input)
    reference = pd.read_csv(args.reference)
    configuration, records, shared_parameters, validation, summary = build_insectt_stage2(frame, reference)

    evidence_errors: list[str] = []
    evidence_ids: set[str] = set()
    for record in records:
        if record["evidence_id"] in evidence_ids:
            evidence_errors.append(f"duplicate evidence_id: {record['evidence_id']}")
        evidence_ids.add(record["evidence_id"])
        evidence_errors.extend(
            f"{record['evidence_id']}: {error}" for error in validate_evidence_record(record)
        )
    if evidence_errors:
        raise RuntimeError("InSecTT evidence validation failed:\n- " + "\n- ".join(evidence_errors))

    parameter_errors: list[str] = []
    parameter_ids: set[str] = set()
    for parameter in shared_parameters:
        pid = parameter["parameter_id"]
        if pid in parameter_ids:
            parameter_errors.append(f"duplicate parameter_id: {pid}")
        parameter_ids.add(pid)
        parameter_errors.extend(
            f"{pid}: {error}" for error in validate_shared_parameter_record(parameter)
        )
    if parameter_errors:
        raise RuntimeError("InSecTT shared-parameter validation failed:\n- " + "\n- ".join(parameter_errors))

    # Fail-fast frozen production checkpoints from the already validated dataset.
    if summary["configurations"] != 20:
        raise RuntimeError(f"Unexpected InSecTT configuration count: {summary['configurations']}")
    if summary["evidence_records"] != 80:
        raise RuntimeError(f"Unexpected InSecTT evidence-record count: {summary['evidence_records']}")
    if summary["direct_empirical_records"] != 40 or summary["validated_derived_records"] != 40:
        raise RuntimeError("Expected 40 direct and 40 validated-derived InSecTT evidence records")
    expected_technologies = {"BLE", "Thread", "EPhESOS", "UWB"}
    if set(summary["technologies"]) != expected_technologies:
        raise RuntimeError(f"Unexpected InSecTT technologies: {summary['technologies']}")
    expected_periods = [100, 200, 400, 800, 1600]
    if summary["reporting_intervals_ms"] != expected_periods:
        raise RuntimeError(f"Unexpected InSecTT reporting periods: {summary['reporting_intervals_ms']}")
    if abs(summary["inferred_source_voltage_v_median"] - 3.300055399919411) > 5e-6:
        raise RuntimeError(
            "Inferred InSecTT source voltage no longer matches the validated scale checkpoint: "
            f"{summary['inferred_source_voltage_v_median']} V"
        )
    if summary["power_mape_pct_using_median_voltage"] > 0.1:
        raise RuntimeError(
            "InSecTT power-scale MAPE exceeds the validated tolerance: "
            f"{summary['power_mape_pct_using_median_voltage']}%"
        )

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    configuration_path = write_table(
        configuration,
        args.analysis_dir / "configuration_observations.parquet",
    )
    records_jsonl_path = _write_jsonl(records, args.analysis_dir / "evidence_records.jsonl")
    records_csv_path = write_table(_records_for_csv(records), args.analysis_dir / "evidence_records.csv")
    shared_parameters_path = dump_json(shared_parameters, args.analysis_dir / "shared_parameters.json")
    validation_path = write_table(validation, args.results_dir / "power_scale_validation.csv")

    summary.update(
        {
            "configuration_artifact": str(configuration_path),
            "evidence_records_jsonl": str(records_jsonl_path),
            "evidence_records_csv": str(records_csv_path),
            "shared_parameters_artifact": str(shared_parameters_path),
            "power_scale_validation": str(validation_path),
            "evidence_schema_validation_errors": 0,
            "shared_parameter_schema_validation_errors": 0,
        }
    )
    summary_path = dump_json(summary, args.results_dir / "summary.json")

    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_insectt_stage2_evidence.py",
        inputs=[args.input, args.reference],
        outputs=[
            configuration_path,
            records_jsonl_path,
            records_csv_path,
            shared_parameters_path,
            validation_path,
            summary_path,
        ],
        parameters={
            "statistical_unit": "one approximately 60 s source trace per technology x reporting period",
            "n_independent_units_per_configuration": 1,
            "voltage_derivation": "median implied voltage from 20 publication Table-1 configuration checks",
            "shared_voltage_parameter": "insectt_ppk2_source_voltage_v",
            "sample_level_confidence_intervals_authorised": False,
            "cross_technology_protocol_only_causal_interpretation_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print(f"Configurations: {summary['configurations']}")
    print(f"Independent units per configuration: {summary['n_independent_units_per_configuration']}")
    print(f"Validated shared source voltage: {summary['inferred_source_voltage_v_median']:.9f} V")
    print(f"Power-scale MAPE: {summary['power_mape_pct_using_median_voltage']:.6f} %")
    print(f"Direct empirical evidence records: {summary['direct_empirical_records']}")
    print(f"Validated-derived evidence records: {summary['validated_derived_records']}")
    print(f"Total evidence records: {summary['evidence_records']}")
    print(f"Shared parameters: {summary['shared_parameters']} ({summary['shared_voltage_parameter_id']})")
    print("Sample-level confidence intervals authorised: NO")
    print("Protocol-only interpretation across different hardware contexts authorised: NO")
    print(f"Configuration artifact: {configuration_path}")
    print(f"Evidence records: {records_csv_path}")
    print(f"Shared parameters: {shared_parameters_path}")
    print(f"Validation: {validation_path}")
    print(f"Summary: {summary_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
