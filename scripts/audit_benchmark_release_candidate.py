from __future__ import annotations

import argparse
import json
from pathlib import Path

from stackwise.benchmark_release_qa import DEFAULT_RELEASE_DIR, audit_benchmark_release_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a built STACKWISE benchmark release candidate.")
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/validation/benchmark_release_candidate_qa/summary.json"),
    )
    args = parser.parse_args()

    result = audit_benchmark_release_candidate(args.release_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("STACKWISE Benchmark Dataset v1.0.0-rc1 QA: OK" if result["release_integrity_passed"] else "STACKWISE Benchmark Dataset v1.0.0-rc1 QA: FAILED")
    print(f"Integrity checks passed / failed: {result['checks_passed']} / {result['checks_failed']}")
    print(
        "Canonical evidence CSV/JSONL/Parquet equivalent: "
        f"{'yes' if result['checks']['canonical_evidence_formats_semantically_equivalent'] else 'no'}"
    )
    print(
        "Complete 7x9 feasibility product / Parquet row metadata valid: "
        f"{'yes' if result['checks']['feasibility_is_complete_scenario_stack_product'] else 'no'} / "
        f"{'yes' if result['checks']['parquet_rows_are_materialised_not_false_zero'] else 'no'}"
    )
    print(
        "Schemas / source dataset cards packaged: "
        f"{'yes' if result['checks']['canonical_schemas_packaged'] else 'no'} / "
        f"{'yes' if result['checks']['four_source_dataset_cards_packaged'] else 'no'}"
    )
    print(
        "Checksums complete / raw external archives absent: "
        f"{'yes' if result['checks']['checksums_cover_all_release_files'] else 'no'} / "
        f"{'yes' if result['checks']['no_raw_external_archives'] else 'no'}"
    )
    print(
        "Benchmark release licence declared / Zenodo finalisation ready: "
        f"{'yes' if result['benchmark_release_license_declared'] else 'no'} / "
        f"{'yes' if result['zenodo_finalisation_ready'] else 'no'}"
    )
    if result["manual_finalisation_blockers"]:
        print("Manual finalisation blockers: " + " | ".join(result["manual_finalisation_blockers"]))
    print(f"QA summary: {args.output}")

    if not result["release_integrity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
