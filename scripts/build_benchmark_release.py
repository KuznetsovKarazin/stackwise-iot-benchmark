from __future__ import annotations

from pathlib import Path

from stackwise.benchmark_release import build_benchmark_release


def main() -> None:
    result = build_benchmark_release(Path('.'))
    summary = result['summary']
    print('STACKWISE Benchmark Dataset v1.0.0 build: OK')
    print(
        'Core evidence records / datasets / metrics: '
        f"{summary['core_evidence_records']} / {summary['core_datasets']} / {summary['core_metrics']}"
    )
    print(
        'Benchmark scenarios / candidate stacks: '
        f"{summary['benchmark_scenarios']} / {summary['candidate_stacks']}"
    )
    f = summary['feasibility']
    print(
        'Hard feasibility feasible / infeasible / unresolved: '
        f"{f['feasible']} / {f['infeasible']} / {f['unresolved']}"
    )
    print(
        'Verified redistributable core-source licences / raw external archives included: '
        f"{summary['core_source_licenses_verified_redistributable']} / "
        f"{'yes' if summary['raw_external_data_included'] else 'no'}"
    )
    print(
        'Benchmark licence / attribution review: '
        f"{summary['benchmark_release_license_id']} / "
        f"{'passed' if summary['scientific_attribution_review_passed'] else 'not passed'}"
    )
    print(f"Release artifact files: {summary['release_artifact_files']}")
    print(
        'Zenodo finalisation / publication MCDA authorised: '
        f"{'yes' if summary['zenodo_upload_authorised'] else 'no'} / "
        f"{'yes' if summary['publication_mcda_authorised'] else 'no'}"
    )
    print(f"Release directory: {result['output_dir']}")


if __name__ == '__main__':
    main()
