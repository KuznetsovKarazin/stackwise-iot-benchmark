from __future__ import annotations

import argparse
import json
from pathlib import Path

from stackwise.loed_streaming import validate_loed_streaming


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate structural and reception-side properties of harmonised LoED data with bounded memory."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/loed_lorawan_edge_2020/observations.parquet"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/validation/loed"),
    )
    parser.add_argument(
        "--cluster-gap-s", type=float, default=None,
        help="Deprecated compatibility option; logical-frame clustering does not use wall-clock gaps.",
    )
    parser.add_argument(
        "--analysis-ready-clusters",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/logical_frame_reception_clusters.parquet"),
        help="Reuse this already-built logical-frame artifact for fast validation.",
    )
    parser.add_argument(
        "--rebuild-clusters",
        action="store_true",
        help="Force the expensive logical-frame reconstruction audit instead of reusing analysis-ready output.",
    )
    parser.add_argument(
        "--no-reuse-raw-summary",
        action="store_true",
        help="Force a fresh scan of all gateway-level rows even when a prior passed summary matches the local Parquet artifact.",
    )
    args = parser.parse_args()

    summary = validate_loed_streaming(
        args.input,
        args.output,
        cluster_gap_s=args.cluster_gap_s,
        analysis_ready_clusters=args.analysis_ready_clusters,
        rebuild_clusters=args.rebuild_clusters,
        reuse_raw_summary=not args.no_reuse_raw_summary,
    )
    print(json.dumps(summary, indent=2))
    print(f"summary: {args.output / 'loed_validation_summary.json'}")


if __name__ == "__main__":
    main()
