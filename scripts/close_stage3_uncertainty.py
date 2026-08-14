from __future__ import annotations

import argparse
import json
from pathlib import Path

from stackwise.provenance import write_run_manifest
from stackwise.stage3_closure import close_stage3_from_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Close STACKWISE Stage 3 with mixed uncertainty semantics and explicit non-identifiability.")
    parser.add_argument("--uncertainty-policy", type=Path, default=Path("datasets/core_four_uncertainty_policy.yml"))
    parser.add_argument("--closure-policy", type=Path, default=Path("datasets/stage3_closure_policy.yml"))
    parser.add_argument("--core-summary", type=Path, default=Path("results/validation/core_four_uncertainty/summary.json"))
    parser.add_argument("--single-trace-summary", type=Path, default=Path("results/validation/single_trace_uncertainty_review/summary.json"))
    parser.add_argument("--vomhoff-summary", type=Path, default=Path("results/validation/vomhoff_joint_bootstrap/summary.json"))
    parser.add_argument("--loed-summary", type=Path, default=Path("results/validation/loed_uncertainty_robustness/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("results/validation/stage3_closure"))
    parser.add_argument("--state-output", type=Path, default=Path("data/analysis_ready/core_four_uncertainty"))
    args = parser.parse_args()

    summary, state, gaps, handoff = close_stage3_from_paths(
        uncertainty_policy_path=args.uncertainty_policy,
        closure_policy_path=args.closure_policy,
        core_uncertainty_summary_path=args.core_summary,
        single_trace_summary_path=args.single_trace_summary,
        vomhoff_bootstrap_summary_path=args.vomhoff_summary,
        loed_robustness_summary_path=args.loed_summary,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    args.state_output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / "summary.json"
    state_csv = args.state_output / "stage3_uncertainty_state.csv"
    state_json = args.state_output / "stage3_uncertainty_state.json"
    gaps_path = args.output / "residual_gaps.csv"
    handoff_path = args.output / "stage4_handoff_rules.csv"
    manifest_path = args.output / "run_manifest.json"

    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    state.to_csv(state_csv, index=False)
    state_json.write_text(json.dumps(state.to_dict(orient="records"), indent=2) + "\n", encoding="utf-8")
    gaps.to_csv(gaps_path, index=False)
    handoff.to_csv(handoff_path, index=False)

    write_run_manifest(
        manifest_path,
        command="python scripts/close_stage3_uncertainty.py",
        inputs=[
            args.uncertainty_policy,
            args.closure_policy,
            args.core_summary,
            args.single_trace_summary,
            args.vomhoff_summary,
            args.loed_summary,
        ],
        outputs=[summary_path, state_csv, state_json, gaps_path, handoff_path],
        parameters={"stage3_status": summary["stage3_status"], "publication_mcda_authorised": False},
    )

    print(f"Stage-3 status: {summary['stage3_status']}")
    print(f"Evidence records: {summary['evidence_records']}")
    print(f"Metric families: {summary['metric_families']}")
    print(f"Resolution classes: {summary['resolution_class_counts']}")
    print(f"Residual explicit gaps: {summary['residual_gaps']}")
    print(f"Stage-3 closure-blocking gaps: {summary['stage3_closure_blocking_gaps']}")
    print("Default CV/SD introduced: NO")
    print("Probability weights assigned to LoED scenarios: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Stage-4 stack definition authorised: {'YES' if summary['stage4_stack_definition_authorised'] else 'NO'}")
    print(f"Summary: {summary_path}")
    print(f"Uncertainty state: {state_csv}")
    print(f"Residual gaps: {gaps_path}")
    print(f"Stage-4 handoff rules: {handoff_path}")


if __name__ == "__main__":
    main()
