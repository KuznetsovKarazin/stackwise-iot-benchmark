from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from stackwise.loed_uncertainty import (
    PHY_KEYS,
    build_day_coverage,
    build_daily_phy_summary,
    build_gateway_day_phy_cells,
    build_gateway_phy_from_cells,
    build_hierarchical_calibration,
    build_temporal_diagnostics,
    reconcile_with_stage2,
)
from stackwise.provenance import write_run_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bounded-memory LoED hierarchical RSSI/SNR calibration artifacts.")
    parser.add_argument("--input", type=Path, default=Path("data/processed/loed_lorawan_edge_2020/observations.parquet"))
    parser.add_argument(
        "--stage2-summary",
        type=Path,
        default=Path("results/validation/loed_stage2_materialisation/summary.json"),
    )
    parser.add_argument(
        "--stage2-phy",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/reception_phy_summary.csv"),
    )
    parser.add_argument(
        "--stage2-gateway-phy",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/gateway_phy_summary.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/loed_hierarchical_uncertainty"),
    )
    parser.add_argument("--batch-size", type=int, default=250_000)
    args = parser.parse_args()

    for path in [args.input, args.stage2_summary, args.stage2_phy, args.stage2_gateway_phy]:
        if not path.exists():
            raise FileNotFoundError(path)

    stage2 = json.loads(args.stage2_summary.read_text(encoding="utf-8"))
    if int(stage2.get("raw_reception_rows", -1)) != 11_263_001:
        raise RuntimeError("LoED Stage-3C requires the validated full-corpus Stage-2 artifact")
    if int(stage2.get("phy_strata", -1)) != 49 or int(stage2.get("gateway_phy_strata", -1)) != 398:
        raise RuntimeError("Unexpected LoED Stage-2 PHY/gateway strata checkpoint")

    cells = build_gateway_day_phy_cells(args.input, batch_size=args.batch_size)
    if cells.empty:
        raise RuntimeError("No LoED gateway-day-PHY cells were produced")
    calibration = build_hierarchical_calibration(cells)
    daily_phy = build_daily_phy_summary(cells)
    gateway_from_cells = build_gateway_phy_from_cells(cells)
    day_coverage = build_day_coverage(cells)
    temporal = build_temporal_diagnostics(daily_phy)

    stage2_phy = pd.read_csv(args.stage2_phy)
    stage2_gateway = pd.read_csv(args.stage2_gateway_phy)
    reconciliation = reconcile_with_stage2(calibration, gateway_from_cells, stage2_phy, stage2_gateway)

    source_files = int(cells["source_file"].nunique())
    source_days = int(cells["source_day"].nunique())
    gateways = int(cells["source_gateway_id"].nunique())
    phy_strata = int(calibration[list(PHY_KEYS)].drop_duplicates().shape[0])
    complete_rows = int(pd.to_numeric(cells["reception_rows"], errors="coerce").fillna(0).sum())
    if source_files != 188 or source_days != 188:
        raise RuntimeError(f"Expected 188 LoED source files/days, found files={source_files}, parsed_days={source_days}")
    if gateways != 9:
        raise RuntimeError(f"Expected 9 LoED gateways, found {gateways}")
    if phy_strata != 49:
        raise RuntimeError(f"Expected 49 LoED PHY strata, found {phy_strata}")
    if complete_rows != int(stage2["raw_reception_rows_with_complete_phy_key"]):
        raise RuntimeError(
            f"Complete-PHY reception reconciliation failed: {complete_rows} != "
            f"{stage2['raw_reception_rows_with_complete_phy_key']}"
        )

    day_basis_counts = (
        cells[["source_file", "source_day_basis"]].drop_duplicates()["source_day_basis"]
        .value_counts(dropna=False).to_dict()
    )
    paired_total = int(pd.to_numeric(cells["paired_observations"], errors="coerce").fillna(0).sum())

    def _range(column: str):
        values = pd.to_numeric(calibration[column], errors="coerce").dropna()
        return None if values.empty else {"min": float(values.min()), "max": float(values.max())}

    temporal_values = pd.to_numeric(temporal["lag1_pearson_consecutive_days"], errors="coerce")
    lag1_abs_max = None if temporal_values.dropna().empty else float(temporal_values.abs().max())
    consecutive_min = int(pd.to_numeric(temporal["consecutive_day_pairs"], errors="coerce").min())
    consecutive_max = int(pd.to_numeric(temporal["consecutive_day_pairs"], errors="coerce").max())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    cells_path = args.output_dir / "gateway_day_phy_cells.parquet"
    cells.to_parquet(cells_path, index=False)
    calibration_path = args.output_dir / "rssi_snr_hierarchical_calibration.csv"
    calibration.to_csv(calibration_path, index=False)
    daily_path = args.output_dir / "daily_phy_summary.csv"
    daily_phy.to_csv(daily_path, index=False)
    coverage_path = args.output_dir / "day_coverage.csv"
    day_coverage.to_csv(coverage_path, index=False)
    temporal_path = args.output_dir / "temporal_dependence_diagnostics.csv"
    temporal.to_csv(temporal_path, index=False)

    summary = {
        "dataset_id": "loed_lorawan_edge_2020",
        "stage": "Stage-3C LoED hierarchical grouped RSSI/SNR calibration artifact",
        "raw_reception_rows": int(stage2["raw_reception_rows"]),
        "reception_rows_with_complete_phy_key": complete_rows,
        "source_files": source_files,
        "source_days": source_days,
        "gateways": gateways,
        "phy_strata": phy_strata,
        "gateway_day_phy_cells": int(len(cells)),
        "daily_phy_cells": int(len(daily_phy)),
        "day_coverage_rows": int(len(day_coverage)),
        "temporal_diagnostic_rows": int(len(temporal)),
        "paired_rssi_snr_observations": paired_total,
        "source_day_basis_counts": {str(k): int(v) for k, v in day_basis_counts.items()},
        "rssi_between_cell_variance_fraction": _range("rssi_between_cell_variance_fraction"),
        "snr_between_cell_variance_fraction": _range("snr_between_cell_variance_fraction"),
        "consecutive_day_pairs": {"min": consecutive_min, "max": consecutive_max},
        "max_abs_lag1_pearson_consecutive_days": lag1_abs_max,
        "stage2_reconciliation": reconciliation,
        "hierarchy_policy": (
            "Primary grouped artifact is source day x gateway x exact PHY stratum. Reception rows remain nested observations; "
            "gateway-day-PHY cells are calibration blocks, not declared IID population replicates."
        ),
        "joint_rssi_snr_policy": (
            "Paired RSSI/SNR sums, sums of squares and cross-products are retained within the same recorded reception events "
            "so future joint calibration need not assume independence."
        ),
        "temporal_policy": (
            "Daily PHY summaries and consecutive-day lag-1 correlations are diagnostics only. IID day bootstrap, moving-block bootstrap "
            "and any hierarchical stochastic sampler remain unauthorised until these outputs are reviewed."
        ),
        "iid_reception_bootstrap_authorised": False,
        "iid_gateway_day_cell_bootstrap_authorised": False,
        "iid_day_bootstrap_authorised": False,
        "hierarchical_sampling_authorised": False,
        "parametric_distribution_fitted": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "gateway_day_phy_cells_artifact": str(cells_path),
        "hierarchical_calibration_artifact": str(calibration_path),
        "daily_phy_summary_artifact": str(daily_path),
        "day_coverage_artifact": str(coverage_path),
        "temporal_dependence_diagnostics_artifact": str(temporal_path),
        "next_scientific_step": (
            "Review gateway/day coverage, variance decomposition and temporal dependence; then choose a source-day/gateway-aware "
            "resampling or hierarchical model without treating receptions or cells as IID."
        ),
    }
    summary_path = args.results_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/build_loed_hierarchical_uncertainty.py",
        inputs=[args.input, args.stage2_summary, args.stage2_phy, args.stage2_gateway_phy],
        outputs=[cells_path, calibration_path, daily_path, coverage_path, temporal_path, summary_path],
        parameters={
            "grouping_unit": "source_file/source_day x gateway x spreading_factor x frequency x bandwidth",
            "paired_rssi_snr_moments": True,
            "iid_reception_bootstrap_authorised": False,
            "iid_gateway_day_cell_bootstrap_authorised": False,
            "iid_day_bootstrap_authorised": False,
            "hierarchical_sampling_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print(f"Reception rows: {summary['raw_reception_rows']:,}")
    print(f"Reception rows with complete PHY key: {complete_rows:,}")
    print(f"Source files/days: {source_files}/{source_days}")
    print(f"Gateways: {gateways}")
    print(f"PHY strata: {phy_strata}")
    print(f"Gateway-day-PHY cells: {len(cells):,}")
    print(f"Daily-PHY cells: {len(daily_phy):,}")
    print(f"Paired RSSI/SNR observations: {paired_total:,}")
    print(f"Consecutive-day pairs per diagnostic: {consecutive_min}..{consecutive_max}")
    print(f"Max |lag-1| diagnostic: {lag1_abs_max}")
    print("Stage-2 PHY/gateway reconciliation: OK")
    print("IID reception bootstrap authorised: NO")
    print("IID gateway-day-cell bootstrap authorised: NO")
    print("IID day bootstrap authorised: NO (review temporal diagnostics first)")
    print("Hierarchical stochastic sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Calibration: {calibration_path}")
    print(f"Day coverage: {coverage_path}")
    print(f"Temporal diagnostics: {temporal_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
