from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.vomhoff_independence import audit_vomhoff_independence


DEFAULT_INPUT = Path(
    "data/processed/vomhoff_nbiot_ltem_energy_2023/observations.parquet"
)
DEFAULT_OUTPUT = Path(
    "results/validation/vomhoff_independence_audit"
)


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serialisable")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Vomhoff within-run segment continuity and cross-Figure source reuse "
            "before Stage-2 evidence materialisation."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    frame = pd.read_parquet(args.input)
    summary, adjacency, exact_matches, run_pairs = audit_vomhoff_independence(frame)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    adjacency.to_csv(args.output_dir / "multi_segment_adjacency.csv", index=False)
    exact_matches.to_csv(args.output_dir / "exact_cross_figure_segment_matches.csv", index=False)
    run_pairs.to_csv(args.output_dir / "cross_figure_run_pairs.csv", index=False)

    manifest = {
        "script": "scripts/audit_vomhoff_independence.py",
        "input": str(args.input),
        "output_dir": str(args.output_dir),
        "input_rows": int(len(frame)),
        "scientific_scope": (
            "Audit only. Within-Figure additive aggregation may be authorised by guards; "
            "cross-Figure deduplication remains pending review."
        ),
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Input rows: {summary['input_rows']}")
    print(
        "Multi-segment adjacency: "
        f"{summary['adjacent_within_tolerance']}/{summary['adjacency_pairs']} "
        f"within {summary['adjacency_tolerance_s']:.3f} s"
    )
    print(
        "Within-source-Figure additive aggregation authorised: "
        f"{'YES' if summary['within_source_figure_additive_aggregation_authorised'] else 'NO'}"
    )
    print(
        "Exact cross-Figure segment signatures: "
        f"{summary['exact_cross_figure_segment_signatures']}"
    )
    print(f"Cross-Figure overlapping run pairs: {summary['cross_figure_run_pairs']}")
    print(f"Strong source-reuse run pairs: {summary['strong_source_reuse_run_pairs']}")
    print("Cross-Figure deduplication authorised: NO (review required)")
    print(f"Summary: {args.output_dir / 'summary.json'}")
    print(f"Run-pair audit: {args.output_dir / 'cross_figure_run_pairs.csv'}")


if __name__ == "__main__":
    main()
