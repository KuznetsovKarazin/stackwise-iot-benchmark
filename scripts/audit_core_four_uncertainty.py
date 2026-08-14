from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from stackwise.uncertainty import audit_from_paths


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Stage-3 uncertainty identifiability for core-four evidence.")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("data/analysis_ready/core_four_evidence/core_four_evidence_matrix.jsonl"),
    )
    parser.add_argument(
        "--shared-parameters",
        type=Path,
        default=Path("data/analysis_ready/core_four_evidence/shared_parameters.json"),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("datasets/core_four_uncertainty_policy.yml"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("datasets/schema/uncertainty_model.schema.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/validation/core_four_uncertainty"),
    )
    args = parser.parse_args()

    summary, plan, dependence, gaps = audit_from_paths(
        args.evidence,
        args.shared_parameters,
        policy_path=args.policy,
        schema_path=args.schema,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    plan_path = args.output / "uncertainty_plan.csv"
    dep_path = args.output / "dependence_groups.csv"
    gaps_path = args.output / "calibration_gaps.csv"
    summary_path = args.output / "summary.json"
    manifest_path = args.output / "run_manifest.json"

    plan.to_csv(plan_path, index=False)
    dependence.to_csv(dep_path, index=False)
    gaps.to_csv(gaps_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "Stage-3 uncertainty contract and identifiability audit",
        "inputs": {
            str(args.evidence): sha256(args.evidence),
            str(args.shared_parameters): sha256(args.shared_parameters),
            str(args.policy): sha256(args.policy),
            str(args.schema): sha256(args.schema),
        },
        "outputs": [str(summary_path), str(plan_path), str(dep_path), str(gaps_path)],
        "scientific_safeguards": [
            "No distribution fitting or stochastic sampling is performed.",
            "No default standard deviation or coefficient of variation is introduced.",
            "Single-trace sources do not receive population confidence intervals.",
            "LoED reception rows are not treated as independent replicates.",
            "Generic study random effects are not estimated from confounded core-four study identities.",
            "Publication MCDA remains unauthorised.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Evidence records mapped: {summary['evidence_records_mapped']}")
    print(f"Dataset/metric uncertainty specs: {summary['dataset_metric_uncertainty_specs']}")
    print(f"Dependence groups: {summary['dependence_groups']}")
    print(f"Calibration gaps: {summary['calibration_gaps']}")
    print(f"Calibration statuses: {summary['calibration_status_counts']}")
    print(f"Vomhoff records without implementation context: {summary['vomhoff_records_without_implementation_context']}")
    print("Generic study random effect authorised: NO")
    print("Default SD/CV authorised: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Uncertainty plan: {plan_path}")
    print(f"Calibration gaps: {gaps_path}")


if __name__ == "__main__":
    main()
