from __future__ import annotations

import json
from pathlib import Path

from stackwise.benchmark_release_qa import audit_benchmark_release


def main() -> None:
    result = audit_benchmark_release()
    output_dir = Path('results/validation/benchmark_release_final_qa')
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / 'summary.json'
    summary_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('STACKWISE Benchmark Dataset v1.0.0 QA: OK' if result['release_integrity_passed'] else 'STACKWISE Benchmark Dataset v1.0.0 QA: FAILED')
    print(f"Integrity checks passed / failed: {result['checks_passed']} / {result['checks_failed']}")
    checks = result['checks']
    print(
        'Canonical evidence CSV/JSONL/Parquet equivalent: '
        f"{'yes' if checks['canonical_evidence_formats_semantically_equivalent'] else 'no'}"
    )
    print(
        'Complete 7x9 feasibility product / Parquet row metadata valid: '
        f"{'yes' if checks['feasibility_is_complete_scenario_stack_product'] else 'no'} / "
        f"{'yes' if checks['parquet_rows_are_materialised_not_false_zero'] else 'no'}"
    )
    print(
        'Source attribution / benchmark CC BY 4.0 licence: '
        f"{'yes' if checks.get('four_core_source_attributions_verified') else 'no'} / "
        f"{'yes' if checks.get('benchmark_release_license_is_cc_by_4_0') else 'no'}"
    )
    print(
        'Checksums complete / raw external archives absent: '
        f"{'yes' if checks['checksums_cover_all_release_files'] and checks['checksums_match'] else 'no'} / "
        f"{'yes' if checks['no_raw_external_archives'] else 'no'}"
    )
    print(
        'Zenodo finalisation ready / publication MCDA authorised: '
        f"{'yes' if result['zenodo_finalisation_ready'] else 'no'} / no"
    )
    if result['manual_finalisation_blockers']:
        print('Manual finalisation blockers: ' + ' | '.join(result['manual_finalisation_blockers']))
    print(f"QA summary: {summary_path}")


if __name__ == '__main__':
    main()
