from __future__ import annotations

import argparse
import json
from pathlib import Path

from stackwise.provenance import write_run_manifest
from stackwise.single_trace_uncertainty import audit_single_trace_uncertainty


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit targeted primary-source uncertainty evidence for core single-trace datasets.")
    parser.add_argument("--evidence", type=Path, default=Path("data/analysis_ready/core_four_evidence/core_four_evidence_matrix.csv"))
    parser.add_argument("--policy", type=Path, default=Path("datasets/single_trace_uncertainty_evidence.yml"))
    parser.add_argument("--output", type=Path, default=Path("results/validation/single_trace_uncertainty_review"))
    args = parser.parse_args()

    summary, review, instrumentation = audit_single_trace_uncertainty(args.evidence, policy_path=args.policy)
    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / "summary.json"
    review_path = args.output / "evidence_review.csv"
    instrumentation_path = args.output / "instrumentation_reconciliation.csv"
    manifest_path = args.output / "run_manifest.json"

    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    review.to_csv(review_path, index=False)
    instrumentation.to_csv(instrumentation_path, index=False)
    write_run_manifest(
        manifest_path,
        command="python scripts/audit_single_trace_uncertainty_evidence.py",
        inputs=[args.evidence, args.policy],
        outputs=[summary_path, review_path, instrumentation_path],
        parameters={"review_scope": "InSecTT and LR-FHSS single-trace uncertainty evidence"},
    )

    print(f"Datasets reviewed: {summary['datasets_reviewed']}")
    print(f"Metric families reviewed: {summary['metric_families_reviewed']}")
    print(f"Numeric population priors identified: {summary['numeric_population_priors_identified']}")
    print(f"LR-FHSS instrumentation reconciled: {'YES' if summary['lrfhss_instrumentation_reconciled'] else 'NO'}")
    print("Infer CV from qualitative 'negligible': NO")
    print("Convert instrument accuracy to population SD: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
