from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from stackwise.loed_robustness import (
    build_robustness_envelope,
    iter_joint_centered_draw_batches,
)
from stackwise.provenance import write_run_manifest


def write_stage3g_manifest(*, results_dir: Path, inputs: list[Path], outputs: list[Path], parameters: dict) -> Path:
    return write_run_manifest(
        results_dir / "run_manifest.json",
        command="python scripts/materialize_loed_uncertainty_robustness.py",
        inputs=inputs,
        outputs=outputs,
        parameters=parameters,
    )


def _reconcile_raw_summary(centered: pd.DataFrame, stage3f: pd.DataFrame) -> tuple[float, float, float]:
    keys = [
        "campaign_id", "source_spreading_factor", "source_frequency_hz",
        "source_bandwidth_khz", "metric", "block_length_days",
    ]
    cols = keys + ["bootstrap_mean", "bootstrap_bias", "bootstrap_sd"]
    ref = stage3f[cols].copy()
    cur = centered[keys + ["raw_bootstrap_mean", "raw_bootstrap_bias", "centered_bootstrap_sd"]].copy()
    merged = ref.merge(cur, on=keys, how="outer", validate="one_to_one", indicator=True)
    if not (merged["_merge"] == "both").all():
        raise RuntimeError("Stage-3G raw draw reconstruction does not align with Stage-3F summary")
    mean_err = float((merged["bootstrap_mean"] - merged["raw_bootstrap_mean"]).abs().max())
    bias_err = float((merged["bootstrap_bias"] - merged["raw_bootstrap_bias"]).abs().max())
    sd_err = float((merged["bootstrap_sd"] - merged["centered_bootstrap_sd"]).abs().max())
    return mean_err, bias_err, sd_err


def main() -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    parser = argparse.ArgumentParser(description="LoED Stage-3G scenario-indexed uncertainty robustness family")
    parser.add_argument(
        "--daily-phy", type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/daily_phy_summary.csv"),
    )
    parser.add_argument(
        "--campaign-map", type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/campaign_day_map.csv"),
    )
    parser.add_argument(
        "--stage3f-summary", type=Path,
        default=Path("results/validation/loed_block_bootstrap_sensitivity/summary.json"),
    )
    parser.add_argument(
        "--stage3f-design", type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/block_sensitivity/block_bootstrap_design.csv"),
    )
    parser.add_argument(
        "--stage3f-bootstrap-summary", type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/block_sensitivity/block_bootstrap_summary.csv"),
    )
    parser.add_argument(
        "--policy", type=Path,
        default=Path("datasets/loed_uncertainty_robustness_policy.yml"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/analysis_ready/loed_lorawan_edge_2020/uncertainty/temporal_audit/robustness_family"),
    )
    parser.add_argument(
        "--results-dir", type=Path,
        default=Path("results/validation/loed_uncertainty_robustness"),
    )
    args = parser.parse_args()

    inputs = [
        args.daily_phy, args.campaign_map, args.stage3f_summary,
        args.stage3f_design, args.stage3f_bootstrap_summary, args.policy,
    ]
    for path in inputs:
        if not path.exists():
            raise FileNotFoundError(path)

    stage3f_meta = json.loads(args.stage3f_summary.read_text(encoding="utf-8"))
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    if stage3f_meta.get("candidate_block_lengths_days") != [3, 7, 14]:
        raise RuntimeError("Stage-3G requires validated Stage-3F 3/7/14-day sensitivity")
    if stage3f_meta.get("block_length_selected") is not False:
        raise RuntimeError("Stage-3G requires no single Stage-3F block length to be selected")
    if stage3f_meta.get("campaigns_treated_as_fixed_deployment_scenarios") is not True:
        raise RuntimeError("Stage-3G requires fixed deployment-scenario campaign semantics")

    daily_phy = pd.read_csv(args.daily_phy)
    campaign_map = pd.read_csv(args.campaign_map)
    design = pd.read_csv(args.stage3f_design)
    stage3f_bootstrap = pd.read_csv(args.stage3f_bootstrap_summary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    draws_path = args.output_dir / "joint_centered_block_draws.parquet"
    centered_summary_path = args.output_dir / "centered_block_summary.csv"
    envelope_path = args.output_dir / "block_length_robustness_envelope.csv"
    support_path = args.output_dir / "phy_source_day_support.csv"

    writer: pq.ParquetWriter | None = None
    centered_parts: list[pd.DataFrame] = []
    draw_rows = 0
    batch_count = 0
    try:
        for batch in iter_joint_centered_draw_batches(daily_phy, campaign_map, design):
            table = pa.Table.from_pandas(batch.draws, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(draws_path, table.schema, compression="zstd")
            writer.write_table(table)
            draw_rows += len(batch.draws)
            batch_count += 1
            centered_parts.append(batch.centered_summary)
    finally:
        if writer is not None:
            writer.close()

    centered = pd.concat(centered_parts, ignore_index=True)
    envelope = build_robustness_envelope(centered)
    centered.to_csv(centered_summary_path, index=False)
    envelope.to_csv(envelope_path, index=False)

    support_cols = [
        "campaign_id", "source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz",
        "metric", "source_days_in_campaign", "observed_source_days", "source_day_support_fraction",
        "campaign_observations",
    ]
    support = centered[support_cols].drop_duplicates().sort_values(support_cols[:5]).reset_index(drop=True)
    support.to_csv(support_path, index=False)

    mean_err, bias_err, sd_err = _reconcile_raw_summary(centered, stage3f_bootstrap)
    expected_draw_rows = 2 * 3 * 5000 * 49
    if draw_rows != expected_draw_rows:
        raise RuntimeError(f"Unexpected joint draw rows: {draw_rows} != {expected_draw_rows}")
    if len(centered) != 588:
        raise RuntimeError(f"Unexpected centered summary rows: {len(centered)} != 588")
    if len(envelope) != 196:
        raise RuntimeError(f"Unexpected robustness-envelope rows: {len(envelope)} != 196")
    if len(support) != 196:
        raise RuntimeError(f"Unexpected source-day-support rows: {len(support)} != 196")
    if max(mean_err, bias_err, sd_err) > 1e-10:
        raise RuntimeError(
            f"Stage-3F reconstruction mismatch: mean={mean_err}, bias={bias_err}, sd={sd_err}"
        )
    centered_recon = float(centered["centered_mean_reconciliation_error"].abs().max())
    if centered_recon > 1e-10:
        raise RuntimeError(f"Centered draw means do not reconcile to campaign point estimates: {centered_recon}")

    sparse = support.sort_values("source_day_support_fraction").iloc[0]
    sensitivity = envelope.groupby(["campaign_id", "metric"], sort=True).agg(
        sd_max_to_min_ratio_median=("sd_max_to_min_ratio", "median"),
        sd_max_to_min_ratio_q75=("sd_max_to_min_ratio", lambda s: s.quantile(0.75)),
        robustness_width_median=("robustness_width", "median"),
        max_abs_raw_mbb_bias=("max_abs_raw_mbb_bias", "max"),
    ).reset_index()
    sensitivity_path = args.results_dir / "robustness_family_summary.csv"
    sensitivity.to_csv(sensitivity_path, index=False)

    summary = {
        "dataset_id": "loed_lorawan_edge_2020",
        "stage": "Stage-3G LoED scenario-indexed block-length robustness family",
        "campaigns": 2,
        "campaigns_treated_as_fixed_deployment_scenarios": True,
        "block_length_model_set_days": [3, 7, 14],
        "single_block_length_selected": False,
        "block_length_probability_weights_assigned": False,
        "bootstrap_replicates_per_campaign_length": 5000,
        "joint_draw_scope": "campaign_id x block_length_days only",
        "joint_draw_batches": batch_count,
        "joint_draw_rows": draw_rows,
        "centered_summary_rows": int(len(centered)),
        "robustness_envelope_rows": int(len(envelope)),
        "source_day_support_rows": int(len(support)),
        "raw_stage3f_reconciliation_max_abs_error": {
            "bootstrap_mean": mean_err,
            "bootstrap_bias": bias_err,
            "bootstrap_sd": sd_err,
        },
        "centered_mean_reconciliation_max_abs_error": centered_recon,
        "centering_rule": "point_estimate + raw_draw - mean(raw_draws) within campaign x block-length x PHY x metric",
        "centering_interpretation": "Removes finite-sample edge-location bias of the non-circular MBB while preserving within-scenario covariance and distributional shape. It does not correct nonstationarity or gateway/campaign confounding.",
        "minimum_source_day_support": {
            "campaign_id": str(sparse["campaign_id"]),
            "metric": str(sparse["metric"]),
            "source_spreading_factor": float(sparse["source_spreading_factor"]),
            "source_frequency_hz": float(sparse["source_frequency_hz"]),
            "source_bandwidth_khz": float(sparse["source_bandwidth_khz"]),
            "observed_source_days": int(sparse["observed_source_days"]),
            "source_days_in_campaign": int(sparse["source_days_in_campaign"]),
            "source_day_support_fraction": float(sparse["source_day_support_fraction"]),
            "campaign_observations": int(sparse["campaign_observations"]),
        },
        "robustness_family_materialised": True,
        "robustness_envelope_is_probability_interval": False,
        "cross_campaign_pooling_authorised": False,
        "cross_campaign_joint_distribution_asserted": False,
        "independent_gateway_bootstrap_authorised": False,
        "campaign_random_effect_authorised": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "joint_centered_draws_artifact": str(draws_path),
        "centered_block_summary_artifact": str(centered_summary_path),
        "robustness_envelope_artifact": str(envelope_path),
        "source_day_support_artifact": str(support_path),
        "robustness_family_summary_artifact": str(sensitivity_path),
        "interpretation": (
            "LoED does not support one defensible block length or one cross-campaign probability distribution. "
            "Stage-3G therefore retains two fixed deployment campaigns and three temporal block assumptions as a scenario-indexed robustness family. "
            "Joint centered draws preserve RSSI/SNR and cross-PHY dependence only within one campaign x block-length model."
        ),
        "next_scientific_step": (
            "Treat the LoED campaign x block-length family as model/deployment robustness scenarios when building the later link-feasibility bridge. "
            "Do not assign probabilities to campaigns or block lengths. Before publication-wide stochastic sampling, resolve the remaining single-trace InSecTT/LR-FHSS uncertainty gaps with targeted external evidence or explicit conservative priors."
        ),
    }
    summary_path = args.results_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest_path = write_stage3g_manifest(
        results_dir=args.results_dir,
        inputs=inputs,
        outputs=[draws_path, centered_summary_path, envelope_path, support_path, sensitivity_path, summary_path],
        parameters={
            "block_length_model_set_days": [3, 7, 14],
            "single_block_length_selected": False,
            "block_length_probability_weights_assigned": False,
            "centering_rule": summary["centering_rule"],
            "publication_uncertainty_sampling_authorised": False,
            "publication_mcda_authorised": False,
        },
    )
    summary["run_manifest"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Campaigns: {summary['campaigns']} (fixed deployment scenarios)")
    print(f"Block-length robustness family: {summary['block_length_model_set_days']} days")
    print(f"Joint draw rows: {draw_rows}")
    print(f"Centered summary rows: {len(centered)}")
    print(f"Robustness envelope rows: {len(envelope)}")
    print(f"Stage-3F raw reconstruction max error: {max(mean_err, bias_err, sd_err):.3e}")
    print(f"Centered mean reconciliation max error: {centered_recon:.3e}")
    print("Single final block length selected: NO")
    print("Block-length probabilities assigned: NO")
    print("Robustness envelope interpreted as probability interval: NO")
    print("Publication uncertainty sampling authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")
    print(f"Robustness envelope: {envelope_path}")
    print(f"Source-day support: {support_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
