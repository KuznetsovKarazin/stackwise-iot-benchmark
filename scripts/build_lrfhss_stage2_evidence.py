from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.evidence import validate_evidence_record
from stackwise.io import dump_json, read_table, write_table
from stackwise.lrfhss_evidence import build_lrfhss_stage2
from stackwise.provenance import write_run_manifest

DEFAULT_INPUT = Path("data/processed/lorawan_lrfhss_energy_2024/observations.parquet")
DEFAULT_ANALYSIS_DIR = Path("data/analysis_ready/lorawan_lrfhss_energy_2024")
DEFAULT_RESULTS_DIR = Path("results/validation/lrfhss_stage2_materialisation")


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
        description="Materialise LR-FHSS Stage-2 full-capture, incremental-transaction and ACK/RX contrast evidence."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Validated harmonised LR-FHSS table not found: {args.input}. "
            "Run 'stackwise harmonize lorawan_lrfhss_energy_2024 --strict' first."
        )

    frame = read_table(args.input)
    configuration, records, transaction_validation, contrasts, summary = build_lrfhss_stage2(frame)

    evidence_errors: list[str] = []
    ids: set[str] = set()
    for record in records:
        eid = record["evidence_id"]
        if eid in ids:
            evidence_errors.append(f"duplicate evidence_id: {eid}")
        ids.add(eid)
        evidence_errors.extend(f"{eid}: {error}" for error in validate_evidence_record(record))
    if evidence_errors:
        raise RuntimeError("LR-FHSS evidence validation failed:\n- " + "\n- ".join(evidence_errors))

    # Frozen production checkpoints from the validated source.
    if summary["configurations"] != 8:
        raise RuntimeError(f"Unexpected LR-FHSS configuration count: {summary['configurations']}")
    if summary["tx_burst_count_values"] != [1]:
        raise RuntimeError(f"Expected exactly one TX burst in every trace: {summary['tx_burst_count_values']}")
    if summary["evidence_records"] != 20:
        raise RuntimeError(f"Expected 20 LR-FHSS evidence records, found {summary['evidence_records']}")
    if summary["full_capture_evidence_records"] != 8 or summary["incremental_transaction_evidence_records"] != 8:
        raise RuntimeError("Expected 8 full-capture and 8 incremental-transaction records")
    if summary["ack_rx_contrast_evidence_records"] != 4:
        raise RuntimeError("Expected 4 matched-DR ACK/RX contrast records")
    if not (0.0 < summary["baseline_energy_fraction_pct_min"] < 0.2):
        raise RuntimeError("Unexpected minimum LR-FHSS baseline-energy fraction")
    if not (0.0 < summary["baseline_energy_fraction_pct_max"] < 0.2):
        raise RuntimeError("Unexpected maximum LR-FHSS baseline-energy fraction")

    expected_overheads = {
        "DR8": 117.767643,
        "DR9": 93.659993,
        "DR10": 114.861687,
        "DR11": 126.524962,
    }
    for dr, expected in expected_overheads.items():
        actual = summary["ack_rx_overhead_pct_by_dr"][dr]
        if abs(actual - expected) > 0.01:
            raise RuntimeError(f"{dr} ACK/RX contrast changed unexpectedly: {actual}% vs checkpoint {expected}%")

    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    configuration_path = write_table(configuration, args.analysis_dir / "configuration_observations.parquet")
    records_jsonl_path = _write_jsonl(records, args.analysis_dir / "evidence_records.jsonl")
    records_csv_path = write_table(_records_for_csv(records), args.analysis_dir / "evidence_records.csv")
    transaction_path = write_table(transaction_validation, args.analysis_dir / "transaction_derivation.csv")
    contrasts_path = write_table(contrasts, args.analysis_dir / "ack_rx_contrasts.csv")

    summary.update(
        {
            "configuration_artifact": str(configuration_path),
            "evidence_records_jsonl": str(records_jsonl_path),
            "evidence_records_csv": str(records_csv_path),
            "transaction_derivation": str(transaction_path),
            "ack_rx_contrasts": str(contrasts_path),
            "evidence_schema_validation_errors": 0,
        }
    )
    summary_path = dump_json(summary, args.results_dir / "summary.json")
    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_lrfhss_stage2_evidence.py",
        inputs=[args.input],
        outputs=[
            configuration_path, records_jsonl_path, records_csv_path, transaction_path, contrasts_path, summary_path
        ],
        parameters={
            "statistical_unit": "one source trace per confirmation-mode x DR configuration",
            "n_independent_units_per_configuration": 1,
            "transaction_derivation": "full capture minus trace-specific low-current baseline over capture duration",
            "transaction_count_requirement": "exactly one detected TX burst",
            "ack_rx_contrast": "confirmed minus unconfirmed incremental transaction energy at matched DR",
            "population_ack_overhead_estimate_authorised": False,
            "sample_level_confidence_intervals_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print(f"Configurations: {summary['configurations']}")
    print(f"Independent units per configuration: {summary['n_independent_units_per_configuration']}")
    print(f"TX bursts per capture: {summary['tx_burst_count_values']}")
    print(f"Full-capture evidence records: {summary['full_capture_evidence_records']}")
    print(f"Incremental-transaction evidence records: {summary['incremental_transaction_evidence_records']}")
    print(f"ACK/RX contrast records: {summary['ack_rx_contrast_evidence_records']}")
    print(f"Total evidence records: {summary['evidence_records']}")
    print(
        "Baseline energy fraction of full capture: "
        f"{summary['baseline_energy_fraction_pct_min']:.6f}%..{summary['baseline_energy_fraction_pct_max']:.6f}%"
    )
    for dr, pct in summary["ack_rx_overhead_pct_by_dr"].items():
        print(f"{dr} capture-specific confirmed-minus-unconfirmed overhead: {pct:.3f}%")
    print("Population ACK-overhead estimate authorised: NO")
    print("Sample-level confidence intervals authorised: NO")
    print(f"Evidence records: {records_csv_path}")
    print(f"Transaction derivation: {transaction_path}")
    print(f"ACK/RX contrasts: {contrasts_path}")
    print(f"Summary: {summary_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
