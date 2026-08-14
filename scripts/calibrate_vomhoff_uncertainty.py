from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from stackwise.vomhoff_uncertainty import (
    build_vomhoff_uncertainty_calibration,
    load_evidence_jsonl,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate identifiable Vomhoff run-level uncertainty without artificial replication."
    )
    parser.add_argument(
        "--logical-phases",
        type=Path,
        default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/logical_phase_observations.parquet"),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/evidence_records.jsonl"),
    )
    parser.add_argument(
        "--analysis-output",
        type=Path,
        default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty"),
    )
    parser.add_argument(
        "--validation-output",
        type=Path,
        default=Path("results/validation/vomhoff_uncertainty_calibration"),
    )
    args = parser.parse_args()

    logical = pd.read_parquet(args.logical_phases)
    evidence_records = load_evidence_jsonl(args.evidence)
    samples, marginal, blocks, overlaps, dependence, summary = build_vomhoff_uncertainty_calibration(
        logical, evidence_records
    )

    args.analysis_output.mkdir(parents=True, exist_ok=True)
    args.validation_output.mkdir(parents=True, exist_ok=True)

    samples_path = args.analysis_output / "run_level_samples.parquet"
    marginal_path = args.analysis_output / "marginal_calibration.csv"
    blocks_path = args.analysis_output / "resampling_blocks.csv"
    overlap_path = args.analysis_output / "run_set_overlap.csv"
    dependence_path = args.analysis_output / "paired_dependence.csv"
    summary_path = args.validation_output / "summary.json"
    manifest_path = args.validation_output / "run_manifest.json"

    samples.to_parquet(samples_path, index=False)
    marginal.to_csv(marginal_path, index=False)
    blocks.to_csv(blocks_path, index=False)
    overlaps.to_csv(overlap_path, index=False)
    dependence.to_csv(dependence_path, index=False)

    summary.update(
        {
            "run_level_samples_artifact": str(samples_path),
            "marginal_calibration_artifact": str(marginal_path),
            "resampling_blocks_artifact": str(blocks_path),
            "run_set_overlap_artifact": str(overlap_path),
            "paired_dependence_artifact": str(dependence_path),
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": summary["stage"],
        "inputs": {
            str(args.logical_phases): sha256(args.logical_phases),
            str(args.evidence): sha256(args.evidence),
        },
        "outputs": [
            str(samples_path),
            str(marginal_path),
            str(blocks_path),
            str(overlap_path),
            str(dependence_path),
            str(summary_path),
        ],
        "scientific_safeguards": [
            "Physical/source run is the only replication unit.",
            "Source segments are never bootstrapped or counted as independent runs.",
            "Observed run-level values calibrate conditional within-study variability only.",
            "No parametric distribution is fitted.",
            "No generic device or study random effect is fitted.",
            "No final joint bootstrap is authorised before run-set overlap review.",
            "Publication uncertainty sampling and MCDA remain unauthorised.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Evidence records calibrated: {summary['evidence_records_calibrated']}")
    print(f"Run-level metric samples: {summary['run_level_metric_samples']}")
    print(f"Physical/source runs: {summary['physical_run_units']}")
    print(f"Independent runs per evidence record: {summary['n_independent_runs_min']}..{summary['n_independent_runs_max']}")
    print(f"Experimental resampling blocks: {summary['experimental_blocks']}")
    print(f"Complete rectangular blocks: {summary['complete_rectangular_blocks']}")
    print(f"Partial-overlap blocks: {summary['partial_overlap_blocks']}")
    print(f"Paired dependence diagnostics (n>=5): {summary['paired_dependence_pairs_n_ge_5']}")
    print("Aleatory run-level variability calibrated: YES")
    print(f"Joint block bootstrap authorised: {'YES' if summary['joint_block_bootstrap_authorised'] else 'NO (review required)'}")
    print("Parametric distribution fitted: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Marginal calibration: {marginal_path}")
    print(f"Resampling blocks: {blocks_path}")
    print(f"Run-set overlap: {overlap_path}")


if __name__ == "__main__":
    main()
