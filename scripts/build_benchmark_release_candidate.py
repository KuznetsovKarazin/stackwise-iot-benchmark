from __future__ import annotations

import argparse
from pathlib import Path

from stackwise.benchmark_release import build_benchmark_release_candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the STACKWISE v1.0.0-rc1 harmonised empirical evidence benchmark release candidate."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("release/stackwise_benchmark_v1.0.0-rc1"),
    )
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    result = build_benchmark_release_candidate(
        args.project_root,
        output_dir=args.output_dir,
        clean=not args.no_clean,
    )
    summary = result["summary"]
    feasibility = summary["feasibility"]
    print("STACKWISE Benchmark Dataset v1.0.0-rc1 build: OK")
    print(
        "Core evidence records / datasets / metrics: "
        f"{summary['core_evidence_records']} / {summary['core_datasets']} / {summary['core_metrics']}"
    )
    print(
        "Benchmark scenarios / candidate stacks: "
        f"{summary['benchmark_scenarios']} / {summary['candidate_stacks']}"
    )
    print(
        "Hard feasibility feasible / infeasible / unresolved: "
        f"{feasibility['feasible']} / {feasibility['infeasible']} / {feasibility['unresolved']}"
    )
    print(
        "Verified redistributable core-source licences / raw external archives included: "
        f"{summary['core_source_licenses_verified_redistributable']} / no"
    )
    print(f"Release table/data artifacts / metadata assets: {summary['release_artifact_files']} / {summary['release_metadata_files']}")
    print("Release candidate ready for manual review: yes")
    print("Zenodo upload / publication MCDA authorised: no / no")
    print(f"Release directory: {result['output_dir']}")


if __name__ == "__main__":
    main()
