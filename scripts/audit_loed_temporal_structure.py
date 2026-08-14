from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.loed_temporal import (
    DEFAULT_CAMPAIGN_GAP_DAYS,
    DEFAULT_MAX_ACF_LAG,
    assign_temporal_campaigns,
    build_acf_lag_summary,
    build_campaign_acf_diagnostics,
    build_campaign_phy_summary,
    build_campaign_series_diagnostics,
    build_campaign_shift_diagnostics,
    build_campaign_summary,
    build_gateway_campaign_coverage,
    build_gateway_set_transitions,
    summarise_temporal_audit,
)
from stackwise.provenance import write_run_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit LoED temporal campaigns and gateway-aware dependence before resampling.")
    parser.add_argument(
        "--cells",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/gateway_day_phy_cells.parquet"),
    )
    parser.add_argument(
        "--daily-phy",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/daily_phy_summary.csv"),
    )
    parser.add_argument(
        "--day-coverage",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/day_coverage.csv"),
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/rssi_snr_hierarchical_calibration.csv"),
    )
    parser.add_argument(
        "--stage3c-summary",
        type=Path,
        default=Path("results/validation/loed_hierarchical_uncertainty/summary.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/loed_temporal_structure"),
    )
    parser.add_argument("--campaign-gap-days", type=int, default=DEFAULT_CAMPAIGN_GAP_DAYS)
    parser.add_argument("--max-acf-lag", type=int, default=DEFAULT_MAX_ACF_LAG)
    args = parser.parse_args()

    for path in [args.cells, args.daily_phy, args.day_coverage, args.calibration, args.stage3c_summary]:
        if not path.exists():
            raise FileNotFoundError(path)

    stage3c = json.loads(args.stage3c_summary.read_text(encoding="utf-8"))
    if int(stage3c.get("source_days", -1)) != 188 or int(stage3c.get("gateways", -1)) != 9:
        raise RuntimeError("LoED Stage-3D requires validated Stage-3C full-corpus artifacts")
    if int(stage3c.get("phy_strata", -1)) != 49:
        raise RuntimeError("Unexpected LoED Stage-3C PHY-stratum checkpoint")

    cells = pd.read_parquet(args.cells)
    daily_phy = pd.read_csv(args.daily_phy)
    day_coverage = pd.read_csv(args.day_coverage)
    calibration = pd.read_csv(args.calibration)

    campaign_days = assign_temporal_campaigns(day_coverage, campaign_gap_days=args.campaign_gap_days)
    campaigns = build_campaign_summary(campaign_days)
    gateway_campaign = build_gateway_campaign_coverage(cells, campaign_days)
    campaign_phy = build_campaign_phy_summary(cells, campaign_days)
    series_diag = build_campaign_series_diagnostics(daily_phy, campaign_days)
    acf = build_campaign_acf_diagnostics(daily_phy, campaign_days, max_lag=args.max_acf_lag)
    acf_summary = build_acf_lag_summary(acf)
    transitions = build_gateway_set_transitions(cells, campaign_days)
    shifts = build_campaign_shift_diagnostics(campaign_phy, calibration)
    diagnostics = summarise_temporal_audit(campaigns, series_diag, acf_summary, transitions, shifts)

    if len(campaigns) != 2:
        raise RuntimeError(f"Expected two LoED acquisition campaigns after temporal audit, found {len(campaigns)}")
    day_counts = sorted(int(v) for v in campaigns["source_days"].tolist())
    if day_counts != [57, 131]:
        raise RuntimeError(f"Unexpected LoED campaign day counts: {day_counts}")
    if int(campaigns["source_days"].sum()) != 188:
        raise RuntimeError("LoED campaign day counts do not reconcile to 188 source days")
    gaps = pd.to_numeric(campaign_days["gap_from_previous_observation_days"], errors="coerce").dropna()
    if int(gaps.max()) != 386:
        raise RuntimeError(f"Unexpected maximum LoED source-day gap: {gaps.max()}")
    if int(campaign_phy[["source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz"]].drop_duplicates().shape[0]) != 49:
        raise RuntimeError("Campaign-PHY audit lost validated PHY strata")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    campaign_days_path = args.output_dir / "campaign_day_map.csv"
    campaigns_path = args.output_dir / "campaign_summary.csv"
    gateway_campaign_path = args.output_dir / "gateway_campaign_coverage.csv"
    campaign_phy_path = args.output_dir / "campaign_phy_summary.csv"
    series_path = args.output_dir / "campaign_series_diagnostics.csv"
    acf_path = args.output_dir / "campaign_acf_diagnostics.csv"
    acf_summary_path = args.output_dir / "acf_lag_summary.csv"
    transitions_path = args.output_dir / "gateway_set_transitions.csv"
    shifts_path = args.output_dir / "campaign_shift_diagnostics.csv"

    campaign_days.to_csv(campaign_days_path, index=False)
    campaigns.to_csv(campaigns_path, index=False)
    gateway_campaign.to_csv(gateway_campaign_path, index=False)
    campaign_phy.to_csv(campaign_phy_path, index=False)
    series_diag.to_csv(series_path, index=False)
    acf.to_csv(acf_path, index=False)
    acf_summary.to_csv(acf_summary_path, index=False)
    transitions.to_csv(transitions_path, index=False)
    shifts.to_csv(shifts_path, index=False)

    summary = {
        "dataset_id": "loed_lorawan_edge_2020",
        "stage": "Stage-3D LoED campaign/nonstationarity audit",
        "source_days": int(stage3c["source_days"]),
        "gateways": int(stage3c["gateways"]),
        "phy_strata": int(stage3c["phy_strata"]),
        "campaign_gap_threshold_days": int(args.campaign_gap_days),
        "max_acf_lag_days": int(args.max_acf_lag),
        **diagnostics,
        "campaign_pooling_policy": (
            "The 2019 and 2020 acquisition windows are retained as separate observed campaigns. With only two campaigns, "
            "campaign identity is not treated as an exchangeable random effect and days are not pooled across the 386-day gap."
        ),
        "gateway_policy": (
            "Gateways are recurring deployment infrastructure, not an IID population sample. Gateway-set composition is carried "
            "inside source-day clusters; gateways are not independently resampled at this stage."
        ),
        "temporal_policy": (
            "Raw and linearly detrended ACF diagnostics are calculated separately within each acquisition campaign. Any future "
            "block resampler must be campaign-stratified and must preserve all gateway/P HY cells attached to a sampled source day."
        ).replace("P HY", "PHY"),
        "iid_reception_bootstrap_authorised": False,
        "iid_gateway_day_cell_bootstrap_authorised": False,
        "iid_day_bootstrap_authorised": False,
        "cross_campaign_day_pooling_authorised": False,
        "campaign_random_effect_authorised": False,
        "independent_gateway_bootstrap_authorised": False,
        "campaign_stratified_block_bootstrap_authorised": False,
        "block_length_selected": False,
        "hierarchical_sampling_authorised": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "campaign_summary_artifact": str(campaigns_path),
        "gateway_campaign_coverage_artifact": str(gateway_campaign_path),
        "campaign_phy_summary_artifact": str(campaign_phy_path),
        "campaign_series_diagnostics_artifact": str(series_path),
        "campaign_acf_diagnostics_artifact": str(acf_path),
        "acf_lag_summary_artifact": str(acf_summary_path),
        "gateway_set_transitions_artifact": str(transitions_path),
        "campaign_shift_diagnostics_artifact": str(shifts_path),
        "next_scientific_step": (
            "Review campaign-specific raw/detrended ACF, gateway-set stability and 2019-vs-2020 domain shift; then select a "
            "campaign-stratified source-day block length or retain campaign trajectories as sensitivity scenarios if stationarity is not defensible."
        ),
    }
    summary_path = args.results_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest_path = write_run_manifest(
        args.results_dir / "run_manifest.json",
        command="python scripts/audit_loed_temporal_structure.py",
        inputs=[args.cells, args.daily_phy, args.day_coverage, args.calibration, args.stage3c_summary],
        outputs=[
            campaign_days_path, campaigns_path, gateway_campaign_path, campaign_phy_path, series_path,
            acf_path, acf_summary_path, transitions_path, shifts_path, summary_path,
        ],
        parameters={
            "campaign_gap_threshold_days": int(args.campaign_gap_days),
            "max_acf_lag_days": int(args.max_acf_lag),
            "campaign_pooling_authorised": False,
            "campaign_random_effect_authorised": False,
            "independent_gateway_bootstrap_authorised": False,
            "campaign_stratified_block_bootstrap_authorised": False,
            "hierarchical_sampling_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print(f"Source days: {summary['source_days']}")
    print(f"Temporal campaigns: {summary['campaigns']}")
    for row in campaigns.itertuples():
        print(f"  {row.campaign_id}: {row.start_day} .. {row.end_day} ({row.source_days} days, {row.reception_rows:,} receptions)")
    print(f"Maximum inter-observation gap: {summary['max_gap_from_previous_observation_days']} days")
    print(f"Gateway-set transitions: {len(transitions)}")
    print(f"ACF diagnostics through lag: {args.max_acf_lag} days")
    print("Cross-campaign day pooling authorised: NO")
    print("Campaign random effect authorised: NO (two observed campaigns only)")
    print("Independent gateway bootstrap authorised: NO")
    print("Campaign-stratified block bootstrap authorised: NO (block length review pending)")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Campaign summary: {campaigns_path}")
    print(f"ACF lag summary: {acf_summary_path}")
    print(f"Campaign shift diagnostics: {shifts_path}")
    print(f"Gateway transitions: {transitions_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
