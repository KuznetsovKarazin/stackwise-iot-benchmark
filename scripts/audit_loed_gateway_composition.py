from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stackwise.loed_gateway_confounding import (
    build_campaign_gateway_set_summary,
    build_composition_sensitivity,
    build_gateway_campaign_phy_summary,
    build_shared_gateway_campaign_shifts,
    build_shared_gateway_equal_weight_shift,
    build_shared_gateway_reception_weighted_shift,
    build_within_campaign_gateway_heterogeneity,
    get_shared_gateways,
    summarise_gateway_confounding,
)
from stackwise.loed_temporal import assign_temporal_campaigns
from stackwise.provenance import write_run_manifest


def write_stage3e_manifest(
    *,
    results_dir: Path,
    inputs: list[Path],
    outputs: list[Path],
    stage3d: dict[str, object],
) -> Path:
    """Write the Stage-3E provenance manifest using the repository provenance API."""
    return write_run_manifest(
        results_dir / "run_manifest.json",
        command="python scripts/audit_loed_gateway_composition.py",
        inputs=inputs,
        outputs=outputs,
        parameters={
            "campaigns": 2,
            "campaign_source_days": stage3d["campaign_source_days"],
            "campaign_gap_days": int(stage3d["campaign_gap_threshold_days"]),
            "causal_campaign_effect_authorised": False,
            "campaign_stratified_block_bootstrap_authorised": False,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit LoED campaign-shift confounding by changing gateway composition.")
    parser.add_argument(
        "--cells",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/gateway_day_phy_cells.parquet"),
    )
    parser.add_argument(
        "--day-coverage",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/day_coverage.csv"),
    )
    parser.add_argument(
        "--stage3d-summary",
        type=Path,
        default=Path("results/validation/loed_temporal_structure/summary.json"),
    )
    parser.add_argument(
        "--full-shift",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/campaign_shift_diagnostics.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/gateway_confounding"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/loed_gateway_confounding"),
    )
    args = parser.parse_args()

    for path in (args.cells, args.day_coverage, args.stage3d_summary, args.full_shift):
        if not path.exists():
            raise FileNotFoundError(path)

    stage3d = json.loads(args.stage3d_summary.read_text(encoding="utf-8"))
    if stage3d.get("campaigns") != 2 or stage3d.get("campaign_source_days") != {"campaign_1": 57, "campaign_2": 131}:
        raise RuntimeError("LoED Stage-3E requires the validated two-campaign Stage-3D audit")
    if int(stage3d.get("max_gap_from_previous_observation_days", -1)) != 386:
        raise RuntimeError("Unexpected LoED campaign-gap checkpoint")

    cells = pd.read_parquet(args.cells)
    coverage = pd.read_csv(args.day_coverage)
    full_shift = pd.read_csv(args.full_shift)
    campaign_days = assign_temporal_campaigns(coverage, campaign_gap_days=int(stage3d["campaign_gap_threshold_days"]))

    campaign_gateway_sets = build_campaign_gateway_set_summary(cells, campaign_days)
    shared_gateways = get_shared_gateways(cells, campaign_days)
    gateway_campaign_phy = build_gateway_campaign_phy_summary(cells, campaign_days)
    shared_shifts = build_shared_gateway_campaign_shifts(gateway_campaign_phy, shared_gateways)
    equal_shift = build_shared_gateway_equal_weight_shift(shared_shifts, len(shared_gateways))
    weighted_shift = build_shared_gateway_reception_weighted_shift(cells, campaign_days, shared_gateways)
    sensitivity = build_composition_sensitivity(full_shift, equal_shift, weighted_shift)
    heterogeneity = build_within_campaign_gateway_heterogeneity(gateway_campaign_phy)

    summary = summarise_gateway_confounding(campaign_gateway_sets, shared_shifts, sensitivity, heterogeneity)
    summary.update({
        "dataset_id": "loed_lorawan_edge_2020",
        "stage": "Stage-3E LoED gateway-composition/campaign confounding audit",
        "source_days": int(stage3d["source_days"]),
        "campaigns": 2,
        "campaign_source_days": stage3d["campaign_source_days"],
        "campaign_windows": stage3d["campaign_windows"],
        "max_gap_from_previous_observation_days": int(stage3d["max_gap_from_previous_observation_days"]),
        "interpretation": (
            "The two acquisition campaigns use substantially different gateway sets. Full-campaign RSSI/SNR shifts are therefore "
            "not identified as pure temporal effects. Same-gateway and equal-shared-gateway comparisons are descriptive sensitivity "
            "analyses only; they do not causally decompose time, gateway placement/hardware, traffic mix, or device-population changes."
        ),
        "next_scientific_step": (
            "Review same-gateway and equal-shared-gateway campaign shifts. If substantial shifts persist on common infrastructure, "
            "retain campaigns as fixed deployment sensitivity scenarios and only consider within-campaign block resampling for conditional "
            "mean uncertainty. If shifts collapse, gateway composition is a dominant confounder and campaign pooling remains prohibited."
        ),
    })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "campaign_gateway_set_summary": args.output_dir / "campaign_gateway_set_summary.csv",
        "gateway_campaign_phy_summary": args.output_dir / "gateway_campaign_phy_summary.csv",
        "shared_gateway_campaign_shifts": args.output_dir / "shared_gateway_campaign_shifts.csv",
        "shared_gateway_equal_weight_shift": args.output_dir / "shared_gateway_equal_weight_shift.csv",
        "shared_gateway_reception_weighted_shift": args.output_dir / "shared_gateway_reception_weighted_shift.csv",
        "composition_sensitivity": args.output_dir / "composition_sensitivity.csv",
        "within_campaign_gateway_heterogeneity": args.output_dir / "within_campaign_gateway_heterogeneity.csv",
    }
    dataframes = {
        "campaign_gateway_set_summary": campaign_gateway_sets,
        "gateway_campaign_phy_summary": gateway_campaign_phy,
        "shared_gateway_campaign_shifts": shared_shifts,
        "shared_gateway_equal_weight_shift": equal_shift,
        "shared_gateway_reception_weighted_shift": weighted_shift,
        "composition_sensitivity": sensitivity,
        "within_campaign_gateway_heterogeneity": heterogeneity,
    }
    for key, path in artifacts.items():
        dataframes[key].to_csv(path, index=False)
        summary[f"{key}_artifact"] = str(path)

    summary_path = args.results_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path = write_stage3e_manifest(
        results_dir=args.results_dir,
        inputs=[args.cells, args.day_coverage, args.stage3d_summary, args.full_shift],
        outputs=[summary_path, *artifacts.values()],
        stage3d=stage3d,
    )
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Campaign gateway counts: {summary['campaign_gateway_counts']}")
    print(f"Shared gateways: {summary['shared_gateway_count']} / union {summary['gateway_union']}")
    print(f"Cross-campaign gateway Jaccard: {summary['cross_campaign_gateway_jaccard']:.6f}")
    print(f"Shared-gateway shift rows: {summary['shared_gateway_shift_rows']}")
    print(f"Composition sensitivity rows: {summary['composition_sensitivity_rows']}")
    print("Campaign shift as pure temporal effect authorised: NO")
    print("Campaign-stratified block bootstrap authorised: NO (gateway-confounding review pending)")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
