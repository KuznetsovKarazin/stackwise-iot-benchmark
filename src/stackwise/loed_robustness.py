from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd

from .loed_block_bootstrap import (
    LoEDBlockBootstrapError,
    _moving_block_indices,
    _prepare_campaign_arrays,
    _validate_campaign_days,
    _validate_daily_phy,
)
from .loed_evidence import PHY_KEYS

DATASET_ID = "loed_lorawan_edge_2020"


@dataclass(frozen=True)
class JointDrawBatch:
    campaign_id: str
    block_length_days: int
    seed_stream: int
    draws: pd.DataFrame
    centered_summary: pd.DataFrame


def _design_rows(design: pd.DataFrame) -> pd.DataFrame:
    required = {
        "campaign_id",
        "source_days",
        "block_length_days",
        "bootstrap_replicates",
        "seed_stream",
    }
    missing = sorted(required - set(design.columns))
    if missing:
        raise LoEDBlockBootstrapError(f"Missing Stage-3F design fields: {missing}")
    out = design.copy()
    for col in ("source_days", "block_length_days", "bootstrap_replicates", "seed_stream"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype(int)
    if out.duplicated(["campaign_id", "block_length_days"]).any():
        raise LoEDBlockBootstrapError("Duplicate campaign/block-length rows in Stage-3F design")
    return out.sort_values(["campaign_id", "block_length_days"]).reset_index(drop=True)


def _centering_summary(
    *,
    campaign_id: str,
    block_length: int,
    strata: pd.DataFrame,
    arrays: dict[str, np.ndarray],
    raw_draws: dict[str, np.ndarray],
    centered_draws: dict[str, np.ndarray],
) -> pd.DataFrame:
    rows: list[dict] = []
    n_days = arrays["rssi_n"].shape[0]
    for metric in ("rssi", "snr"):
        orig_n = arrays[f"{metric}_n"].sum(axis=0)
        orig_s = arrays[f"{metric}_sum"].sum(axis=0)
        orig_mean = np.divide(orig_s, orig_n, out=np.full_like(orig_s, np.nan), where=orig_n > 0)
        observed_days = (arrays[f"{metric}_n"] > 0).sum(axis=0)
        for j, stratum in strata.iterrows():
            if orig_n[j] <= 0:
                continue
            raw = raw_draws[metric][:, j]
            centered = centered_draws[metric][:, j]
            if not np.isfinite(raw).all() or not np.isfinite(centered).all():
                raise LoEDBlockBootstrapError(
                    f"Non-finite robustness draws for {campaign_id}/{block_length}/{metric}/{dict(stratum)}"
                )
            q025, q05, q25, q50, q75, q95, q975 = np.quantile(
                centered, [0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975]
            )
            raw_mean = float(np.mean(raw))
            point = float(orig_mean[j])
            centered_mean = float(np.mean(centered))
            rows.append(
                {
                    "campaign_id": campaign_id,
                    **{k: stratum[k] for k in PHY_KEYS},
                    "metric": metric,
                    "block_length_days": int(block_length),
                    "source_days_in_campaign": int(n_days),
                    "observed_source_days": int(observed_days[j]),
                    "source_day_support_fraction": float(observed_days[j] / n_days),
                    "campaign_observations": int(orig_n[j]),
                    "campaign_reception_weighted_mean": point,
                    "raw_bootstrap_mean": raw_mean,
                    "raw_bootstrap_bias": raw_mean - point,
                    "centered_bootstrap_mean": centered_mean,
                    "centered_mean_reconciliation_error": centered_mean - point,
                    "centered_bootstrap_sd": float(np.std(centered, ddof=1)),
                    "q025": float(q025),
                    "q05": float(q05),
                    "q25": float(q25),
                    "median": float(q50),
                    "q75": float(q75),
                    "q95": float(q95),
                    "q975": float(q975),
                    "centered_percentile_95_width": float(q975 - q025),
                    "centering_rule": "point_estimate_plus_raw_draw_minus_raw_draw_mean",
                    "centering_removes_edge_location_bias_only": True,
                    "centering_claims_stationarity_correction": False,
                    "publication_probability_interval": False,
                }
            )
    return pd.DataFrame(rows)


def iter_joint_centered_draw_batches(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
    design: pd.DataFrame,
) -> Iterator[JointDrawBatch]:
    """Yield joint campaign/block-length bootstrap draws, preserving cross-PHY/RSSI-SNR dependence.

    The Stage-3F seed stream is reused exactly. Raw non-circular MBB draws are recentered per
    campaign x block-length x PHY x metric to the observed campaign mean. Recentring removes
    finite-sample edge-location bias from the diagnostic MBB distribution; it does not assert
    stationarity, resolve gateway/campaign confounding or create a single publication sampling
    distribution. Replicate IDs have joint meaning only within one campaign x block-length batch.
    """
    daily_phy = _validate_daily_phy(daily_phy)
    campaign_days = _validate_campaign_days(campaign_days)
    design = _design_rows(design)

    campaign_cache: dict[str, tuple[list[str], pd.DataFrame, dict[str, np.ndarray]]] = {}
    for row in design.itertuples(index=False):
        campaign_id = str(row.campaign_id)
        block_length = int(row.block_length_days)
        replicates = int(row.bootstrap_replicates)
        seed_stream = int(row.seed_stream)
        if campaign_id not in campaign_cache:
            campaign_cache[campaign_id] = _prepare_campaign_arrays(daily_phy, campaign_days, campaign_id)
        day_labels, strata, arrays = campaign_cache[campaign_id]
        n_days = len(day_labels)
        if int(row.source_days) != n_days:
            raise LoEDBlockBootstrapError(
                f"Stage-3F design source-day mismatch for {campaign_id}: {row.source_days} != {n_days}"
            )
        if block_length < 1 or block_length > n_days:
            raise LoEDBlockBootstrapError(f"Invalid block length {block_length} for {campaign_id}")

        rng = np.random.default_rng(seed_stream)
        raw_draws = {
            "rssi": np.full((replicates, len(strata)), np.nan, dtype=float),
            "snr": np.full((replicates, len(strata)), np.nan, dtype=float),
        }
        sampled_nonmissing = {
            "rssi": np.zeros((replicates, len(strata)), dtype=np.int16),
            "snr": np.zeros((replicates, len(strata)), dtype=np.int16),
        }
        for b in range(replicates):
            idx = _moving_block_indices(n_days, block_length, rng)
            for metric in ("rssi", "snr"):
                n = arrays[f"{metric}_n"][idx, :].sum(axis=0)
                s = arrays[f"{metric}_sum"][idx, :].sum(axis=0)
                raw_draws[metric][b, :] = np.divide(
                    s, n, out=np.full_like(s, np.nan), where=n > 0
                )
                sampled_nonmissing[metric][b, :] = (arrays[f"{metric}_n"][idx, :] > 0).sum(axis=0)

        centered_draws: dict[str, np.ndarray] = {}
        for metric in ("rssi", "snr"):
            orig_n = arrays[f"{metric}_n"].sum(axis=0)
            orig_s = arrays[f"{metric}_sum"].sum(axis=0)
            point = np.divide(orig_s, orig_n, out=np.full_like(orig_s, np.nan), where=orig_n > 0)
            raw_mean = np.nanmean(raw_draws[metric], axis=0)
            centered_draws[metric] = point[np.newaxis, :] + raw_draws[metric] - raw_mean[np.newaxis, :]

        n_strata = len(strata)
        base = pd.DataFrame(
            {
                "campaign_id": np.repeat(campaign_id, replicates * n_strata),
                "block_length_days": np.repeat(block_length, replicates * n_strata),
                "replicate_id": np.repeat(np.arange(replicates, dtype=np.int32), n_strata),
                "source_spreading_factor": np.tile(strata["source_spreading_factor"].to_numpy(), replicates),
                "source_frequency_hz": np.tile(strata["source_frequency_hz"].to_numpy(), replicates),
                "source_bandwidth_khz": np.tile(strata["source_bandwidth_khz"].to_numpy(), replicates),
                "rssi_raw_mean": raw_draws["rssi"].reshape(-1),
                "snr_raw_mean": raw_draws["snr"].reshape(-1),
                "rssi_centered_mean": centered_draws["rssi"].reshape(-1),
                "snr_centered_mean": centered_draws["snr"].reshape(-1),
                "rssi_sampled_nonmissing_days": sampled_nonmissing["rssi"].reshape(-1),
                "snr_sampled_nonmissing_days": sampled_nonmissing["snr"].reshape(-1),
            }
        )
        summary = _centering_summary(
            campaign_id=campaign_id,
            block_length=block_length,
            strata=strata,
            arrays=arrays,
            raw_draws=raw_draws,
            centered_draws=centered_draws,
        )
        yield JointDrawBatch(
            campaign_id=campaign_id,
            block_length_days=block_length,
            seed_stream=seed_stream,
            draws=base,
            centered_summary=summary,
        )


def build_robustness_envelope(centered_summary: pd.DataFrame) -> pd.DataFrame:
    required = {
        "campaign_id", *PHY_KEYS, "metric", "block_length_days",
        "campaign_reception_weighted_mean", "observed_source_days", "source_day_support_fraction",
        "centered_bootstrap_sd", "q025", "q975", "raw_bootstrap_bias",
    }
    missing = sorted(required - set(centered_summary.columns))
    if missing:
        raise LoEDBlockBootstrapError(f"Missing centered-summary fields: {missing}")

    rows: list[dict] = []
    keys = ["campaign_id", *PHY_KEYS, "metric"]
    for group_key, group in centered_summary.groupby(keys, sort=True):
        block_lengths = sorted(group["block_length_days"].astype(int).tolist())
        if block_lengths != [3, 7, 14]:
            raise LoEDBlockBootstrapError(f"Robustness envelope requires block lengths 3/7/14, got {block_lengths}")
        row = {k: v for k, v in zip(keys, group_key)}
        point_values = group["campaign_reception_weighted_mean"].to_numpy(float)
        if float(np.max(point_values) - np.min(point_values)) > 1e-12:
            raise LoEDBlockBootstrapError("Point estimate differs across block-length scenarios")
        support_days = group["observed_source_days"].astype(int).unique()
        support_frac = group["source_day_support_fraction"].astype(float).unique()
        if len(support_days) != 1 or len(support_frac) != 1:
            raise LoEDBlockBootstrapError("Observed source-day support differs across block-length scenarios")

        by_l = group.set_index("block_length_days")
        sds = group["centered_bootstrap_sd"].to_numpy(float)
        lower = float(group["q025"].min())
        upper = float(group["q975"].max())
        row.update(
            {
                "campaign_reception_weighted_mean": float(point_values[0]),
                "observed_source_days": int(support_days[0]),
                "source_day_support_fraction": float(support_frac[0]),
                "sd_3d": float(by_l.loc[3, "centered_bootstrap_sd"]),
                "sd_7d": float(by_l.loc[7, "centered_bootstrap_sd"]),
                "sd_14d": float(by_l.loc[14, "centered_bootstrap_sd"]),
                "sd_min_across_block_lengths": float(np.min(sds)),
                "sd_max_across_block_lengths": float(np.max(sds)),
                "sd_max_to_min_ratio": float(np.max(sds) / np.min(sds)) if np.min(sds) > 0 else np.nan,
                "q025_3d": float(by_l.loc[3, "q025"]),
                "q025_7d": float(by_l.loc[7, "q025"]),
                "q025_14d": float(by_l.loc[14, "q025"]),
                "q975_3d": float(by_l.loc[3, "q975"]),
                "q975_7d": float(by_l.loc[7, "q975"]),
                "q975_14d": float(by_l.loc[14, "q975"]),
                "robustness_lower": lower,
                "robustness_upper": upper,
                "robustness_width": upper - lower,
                "max_abs_raw_mbb_bias": float(group["raw_bootstrap_bias"].abs().max()),
                "block_length_model_set": "3|7|14",
                "block_length_probability_weights_assigned": False,
                "single_block_length_selected": False,
                "robustness_envelope_is_probability_interval": False,
                "campaign_is_fixed_deployment_scenario": True,
                "publication_uncertainty_sampling_authorised": False,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)
