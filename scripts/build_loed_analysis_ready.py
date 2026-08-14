from __future__ import annotations

import argparse
from pathlib import Path

from stackwise.loed_streaming import build_loed_analysis_ready_streaming


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build LoED CRC-valid logical-frame and gateway-day analysis-ready tables with bounded memory."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/loed_lorawan_edge_2020/observations.parquet"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020"),
    )
    parser.add_argument(
        "--cluster-gap-s", type=float, default=None,
        help="Deprecated compatibility option; logical-frame clustering does not use wall-clock gaps.",
    )
    args = parser.parse_args()

    paths = build_loed_analysis_ready_streaming(
        args.input,
        args.output,
        cluster_gap_s=args.cluster_gap_s,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
