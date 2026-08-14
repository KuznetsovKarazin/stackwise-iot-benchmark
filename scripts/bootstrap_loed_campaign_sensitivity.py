from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from stackwise.loed_block_bootstrap import (
    DEFAULT_BLOCK_LENGTHS,
    DEFAULT_REPLICATES,
    DEFAULT_SEED,
    block_bootstrap_sensitivity,
    campaign_point_estimates,
    summarise_block_length_sensitivity,
)
from stackwise.provenance import write_run_manifest


def write_stage3f_manifest(
    *,
    results_dir: Path,
    inputs: list[Path],
    outputs: list[Path],
    parameters: dict,
) -> Path:
    return write_run_manifest(
        results_dir / "run_manifest.json",
        command="python scripts/bootstrap_loed_campaign_sensitivity.py",
        inputs=inputs,
        outputs=outputs,
        parameters=parameters,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LoED Stage-3F within-campaign moving-block bootstrap sensitivity")
    parser.add_argument(
        "--daily-phy",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/daily_phy_summary.csv"),
    )
    parser.add_argument(
        "--campaign-map",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/campaign_day_map.csv"),
    )
    parser.add_argument(
        "--stage3e-summary",
        type=Path,
        default=Path("results/validation/loed_gateway_confounding/summary.json"),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("datasets/loed_block_bootstrap_policy.yml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/block_sensitivity"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/validation/loed_block_bootstrap_sensitivity"),
    )
    args = parser.parse_args()

    for path in [args.daily_phy, args.campaign_map, args.stage3e_summary, args.policy]:
        if not path.exists():
            raise FileNotFoundError(path)

    stage3e = json.loads(args.stage3e_summary.read_text(encoding="utf-8"))
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    if stage3e.get("campaign_source_days") != {"campaign_1": 57, "campaign_2": 131}:
        raise RuntimeError("Stage-3F requires validated Stage-3E campaign day counts 57 + 131")
    if int(stage3e.get("shared_gateway_count", -1)) != 2 or int(stage3e.get("gateway_union", -1)) != 9:
        raise RuntimeError("Stage-3F requires validated Stage-3E gateway-support checkpoint")
    if stage3e.get("campaign_shift_as_pure_temporal_effect_authorised") is not False:
        raise RuntimeError("Stage-3F requires campaign shifts to remain non-causal sensitivity views")

    block_lengths = tuple(int(v) for v in policy.get("candidate_block_lengths_days", DEFAULT_BLOCK_LENGTHS))
    replicates = int(policy.get("bootstrap_replicates_per_campaign_length", DEFAULT_REPLICATES))
    seed = int(policy.get("random_seed", DEFAULT_SEED))

    daily_phy = pd.read_csv(args.daily_phy)
    campaign_map = pd.read_csv(args.campaign_map)
    point = campaign_point_estimates(daily_phy, campaign_map)
    bootstrap, design = block_bootstrap_sensitivity(
        daily_phy,
        campaign_map,
        block_lengths=block_lengths,
        replicates=replicates,
        seed=seed,
    )
    sensitivity = summarise_block_length_sensitivity(bootstrap)

    # Production reconciliation: exactly two fixed campaigns and 49 PHY strata x 2 metrics.
    if set(point["campaign_id"].unique()) != {"campaign_1", "campaign_2"}:
        raise RuntimeError("Unexpected Stage-3F campaign IDs")
    point_counts = point.groupby("campaign_id").size().to_dict()
    if point_counts != {"campaign_1": 98, "campaign_2": 98}:
        raise RuntimeError(f"Unexpected campaign point-estimate rows: {point_counts}")
    expected_rows = 2 * len(block_lengths) * 98
    if len(bootstrap) != expected_rows:
        raise RuntimeError(f"Unexpected block-bootstrap summary rows: {len(bootstrap)} != {expected_rows}")
    if set(design["block_length_days"].astype(int)) != set(block_lengths):
        raise RuntimeError("Block-length design mismatch")
    if bool(bootstrap["publication_uncertainty_sampling_authorised"].any()):
        raise RuntimeError("Stage-3F sensitivity must not authorise publication uncertainty sampling")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    point_path = args.output_dir / "campaign_phy_point_estimates.csv"
    bootstrap_path = args.output_dir / "block_bootstrap_summary.csv"
    design_path = args.output_dir / "block_bootstrap_design.csv"
    sensitivity_path = args.output_dir / "block_length_sensitivity.csv"
    point.to_csv(point_path, index=False)
    bootstrap.to_csv(bootstrap_path, index=False)
    design.to_csv(design_path, index=False)
    sensitivity.to_csv(sensitivity_path, index=False)

    summary = {
        "dataset_id": "loed_lorawan_edge_2020",
        "stage": "Stage-3F LoED within-campaign moving-block bootstrap sensitivity",
        "campaigns": 2,
        "campaign_source_days": {"campaign_1": 57, "campaign_2": 131},
        "campaigns_treated_as_fixed_deployment_scenarios": True,
        "cross_campaign_pooling_authorised": False,
        "cross_campaign_joint_distribution_asserted": False,
        "gateway_composition_confounding_resolved": False,
        "shared_gateway_count": 2,
        "gateway_union": 9,
        "candidate_block_lengths_days": list(block_lengths),
        "bootstrap_replicates_per_campaign_length": replicates,
        "random_seed": seed,
        "resampler": "noncircular_overlapping_moving_block_source_day",
        "bootstrap_estimand": "campaign-conditional reception-weighted RSSI/SNR mean within exact PHY stratum",
        "source_day_cluster_policy": "All PHY metrics and observed gateway composition attached to a sampled source day move together.",
        "structural_missingness_preserved": True,
        "independent_gateway_bootstrap_authorised": False,
        "iid_day_bootstrap_authorised": False,
        "campaign_stratified_block_bootstrap_sensitivity_materialised": True,
        "campaign_stratified_block_bootstrap_authorised_for_publication_sampling": False,
        "block_length_selected": False,
        "seven_day_reference_selected_as_final": False,
        "parametric_distribution_fitted": False,
        "hierarchical_sampling_authorised": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "campaign_phy_point_estimates": str(point_path),
        "block_bootstrap_summary": str(bootstrap_path),
        "block_bootstrap_design": str(design_path),
        "block_length_sensitivity": str(sensitivity_path),
        "interpretation": (
            "The two LoED acquisition campaigns remain fixed observed deployment scenarios because time and gateway composition are confounded. "
            "Stage-3F therefore performs only within-campaign source-day moving-block sensitivity at 3, 7 and 14 days. "
            "This audit does not select a final block length or authorise a publication sampling distribution."
        ),
        "next_scientific_step": (
            "Review block-length sensitivity by campaign and metric. Select a primary within-campaign block length only if uncertainty widths are stable enough and the choice is defensible against the campaign-specific ACF diagnostics; otherwise retain multiple block lengths as robustness scenarios."
        ),
    }
    summary_path = args.results_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest_path = write_stage3f_manifest(
        results_dir=args.results_dir,
        inputs=[args.daily_phy, args.campaign_map, args.stage3e_summary, args.policy],
        outputs=[point_path, bootstrap_path, design_path, sensitivity_path, summary_path],
        parameters={
            "candidate_block_lengths_days": list(block_lengths),
            "bootstrap_replicates_per_campaign_length": replicates,
            "random_seed": seed,
            "cross_campaign_pooling_authorised": False,
            "independent_gateway_bootstrap_authorised": False,
            "block_length_selected": False,
            "publication_uncertainty_sampling_authorised": False,
            "publication_mcda_authorised": False,
        },
    )
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Campaigns: {summary['campaigns']} ({summary['campaign_source_days']})")
    print(f"Candidate block lengths: {list(block_lengths)} days")
    print(f"Bootstrap replicates per campaign/length: {replicates}")
    print(f"Bootstrap summary rows: {len(bootstrap)}")
    print("Campaigns treated as fixed deployment scenarios: YES")
    print("Cross-campaign pooling authorised: NO")
    print("Independent gateway bootstrap authorised: NO")
    print("Block-length sensitivity materialised: YES")
    print("Final block length selected: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Block-length sensitivity: {sensitivity_path}")
    print(f"Block bootstrap summary: {bootstrap_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
