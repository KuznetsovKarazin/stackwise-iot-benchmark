from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from stackwise.vomhoff_bootstrap import build_vomhoff_joint_bootstrap


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialise Vomhoff joint physical-run bootstrap of conditional means.")
    parser.add_argument("--uncertainty-dir", type=Path, default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty"))
    parser.add_argument("--validation-output", type=Path, default=Path("results/validation/vomhoff_joint_bootstrap"))
    parser.add_argument("--policy", type=Path, default=Path("datasets/vomhoff_bootstrap_policy.yml"))
    args = parser.parse_args()

    samples_path = args.uncertainty_dir / "run_level_samples.parquet"
    blocks_path = args.uncertainty_dir / "resampling_blocks.csv"
    marginal_path = args.uncertainty_dir / "marginal_calibration.csv"

    samples = pd.read_parquet(samples_path)
    blocks = pd.read_csv(blocks_path)
    marginal = pd.read_csv(marginal_path)
    draws, bootstrap_summary, block_policy, sensitivity, dependence, summary = build_vomhoff_joint_bootstrap(
        samples, blocks, marginal, policy_path=args.policy
    )

    args.uncertainty_dir.mkdir(parents=True, exist_ok=True)
    args.validation_output.mkdir(parents=True, exist_ok=True)

    draws_path = args.uncertainty_dir / "block_bootstrap_means.parquet"
    bootstrap_summary_path = args.uncertainty_dir / "bootstrap_mean_summary.csv"
    block_policy_path = args.uncertainty_dir / "bootstrap_block_policy.csv"
    sensitivity_path = args.uncertainty_dir / "complete_case_sensitivity.csv"
    dependence_path = args.uncertainty_dir / "bootstrap_mean_dependence.csv"
    summary_path = args.validation_output / "summary.json"
    manifest_path = args.validation_output / "run_manifest.json"

    draws.to_parquet(draws_path, index=False)
    bootstrap_summary.to_csv(bootstrap_summary_path, index=False)
    block_policy.to_csv(block_policy_path, index=False)
    sensitivity.to_csv(sensitivity_path, index=False)
    dependence.to_csv(dependence_path, index=False)

    summary.update({
        "bootstrap_means_artifact": str(draws_path),
        "bootstrap_mean_summary_artifact": str(bootstrap_summary_path),
        "bootstrap_block_policy_artifact": str(block_policy_path),
        "complete_case_sensitivity_artifact": str(sensitivity_path),
        "bootstrap_mean_dependence_artifact": str(dependence_path),
    })
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": summary["stage"],
        "inputs": {
            str(samples_path): sha256(samples_path),
            str(blocks_path): sha256(blocks_path),
            str(marginal_path): sha256(marginal_path),
            str(args.policy): sha256(args.policy),
        },
        "outputs": [
            str(draws_path), str(bootstrap_summary_path), str(block_policy_path),
            str(sensitivity_path), str(dependence_path), str(summary_path),
        ],
        "scientific_safeguards": [
            "Physical/source runs are the only resampling units.",
            "All evidence records within a block share the same sampled run indices.",
            "Partial overlap preserves structural missingness without imputation or listwise deletion.",
            "Bootstrap replicate IDs have no cross-block joint meaning.",
            "No parametric family, generic device effect or study random effect is fitted.",
            "Publication uncertainty sampling and MCDA remain unauthorised.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Experimental blocks: {summary['experimental_blocks']}")
    print(f"Rectangular blocks: {summary['rectangular_blocks']}")
    print(f"Partial-overlap blocks: {summary['partial_overlap_blocks']}")
    print(f"Evidence records bootstrapped: {summary['evidence_records_bootstrapped']}")
    print(f"Bootstrap replicates per block: {summary['bootstrap_replicates_per_block']}")
    print(f"Bootstrap mean draw rows: {summary['bootstrap_mean_draw_rows']}")
    print(f"Partial block union/complete-case runs: {summary['partial_overlap_union_runs']}/{summary['partial_overlap_complete_case_runs']}")
    print("Structural missingness imputed: NO")
    print("Listwise deletion used: NO")
    print("Within-block joint bootstrap materialised: YES")
    print("Cross-block joint distribution asserted: NO")
    print("Parametric distribution fitted: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Bootstrap mean summary: {bootstrap_summary_path}")
    print(f"Block policy: {block_policy_path}")
    print(f"Complete-case sensitivity: {sensitivity_path}")


if __name__ == "__main__":
    main()
