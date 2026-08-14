from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .loed_evidence import PHY_KEYS

DATASET_ID = "loed_lorawan_edge_2020"
DEFAULT_BLOCK_LENGTHS = (3, 7, 14)
DEFAULT_REPLICATES = 5000
DEFAULT_SEED = 20260811


class LoEDBlockBootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class CampaignBootstrapDesign:
    campaign_id: str
    source_days: int
    block_length_days: int
    overlapping_blocks: int
    blocks_sampled_per_replicate: int


def _validate_campaign_days(campaign_days: pd.DataFrame) -> pd.DataFrame:
    required = {"source_day", "campaign_id"}
    missing = sorted(required - set(campaign_days.columns))
    if missing:
        raise LoEDBlockBootstrapError(f"Missing campaign-day fields: {missing}")
    work = campaign_days[["source_day", "campaign_id"]].drop_duplicates().copy()
    work["day"] = pd.to_datetime(work["source_day"], errors="coerce")
    if work["day"].isna().any():
        raise LoEDBlockBootstrapError("Unparseable source_day in campaign map")
    if work["source_day"].duplicated().any():
        raise LoEDBlockBootstrapError("A source day maps to multiple campaigns")
    return work.sort_values(["campaign_id", "day"]).reset_index(drop=True)


def _validate_daily_phy(daily_phy: pd.DataFrame) -> pd.DataFrame:
    required = {
        "source_day", *PHY_KEYS,
        "rssi_observations", "rssi_mean",
        "snr_observations", "snr_mean",
    }
    missing = sorted(required - set(daily_phy.columns))
    if missing:
        raise LoEDBlockBootstrapError(f"Missing daily-PHY fields: {missing}")
    work = daily_phy.copy()
    for col in ("rssi_observations", "snr_observations", "rssi_mean", "snr_mean"):
        work[col] = pd.to_numeric(work[col], errors="coerce")
    return work


def _moving_block_indices(n_days: int, block_length: int, rng: np.random.Generator) -> np.ndarray:
    """Sample a non-circular overlapping moving-block bootstrap sequence.

    Blocks never wrap from campaign end to campaign start. Concatenated blocks may meet at
    synthetic boundaries, as in the standard moving-block bootstrap. The returned sequence
    has exactly ``n_days`` positions.
    """
    if block_length < 1 or block_length > n_days:
        raise ValueError("block_length must be between 1 and n_days")
    possible_starts = n_days - block_length + 1
    n_blocks = int(math.ceil(n_days / block_length))
    starts = rng.integers(0, possible_starts, size=n_blocks)
    chunks = [np.arange(start, start + block_length, dtype=int) for start in starts]
    return np.concatenate(chunks)[:n_days]


def _prepare_campaign_arrays(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
    campaign_id: str,
) -> tuple[list[str], pd.DataFrame, dict[str, np.ndarray]]:
    days = campaign_days.loc[campaign_days["campaign_id"] == campaign_id].sort_values("day")
    day_labels = days["source_day"].astype(str).tolist()
    if not day_labels:
        raise LoEDBlockBootstrapError(f"No days for {campaign_id}")

    # Within an identified acquisition campaign the source-day sequence is expected to be
    # calendar-contiguous. This is a production audit guard, not a stationarity claim.
    day_numbers = days["day"].to_numpy(dtype="datetime64[D]").astype("int64")
    if len(day_numbers) > 1 and not np.all(np.diff(day_numbers) == 1):
        raise LoEDBlockBootstrapError(f"{campaign_id} contains non-consecutive source days")

    part = daily_phy[daily_phy["source_day"].astype(str).isin(day_labels)].copy()
    strata = part[list(PHY_KEYS)].drop_duplicates().sort_values(list(PHY_KEYS)).reset_index(drop=True)
    if strata.empty:
        raise LoEDBlockBootstrapError(f"No PHY strata for {campaign_id}")
    strata["stratum_index"] = np.arange(len(strata), dtype=int)
    day_index = {day: i for i, day in enumerate(day_labels)}
    stratum_index = {
        tuple(getattr(row, k) for k in PHY_KEYS): int(row.stratum_index)
        for row in strata.itertuples(index=False)
    }

    arrays: dict[str, np.ndarray] = {}
    n_days = len(day_labels)
    n_strata = len(strata)
    for metric in ("rssi", "snr"):
        n_arr = np.zeros((n_days, n_strata), dtype=float)
        sum_arr = np.zeros((n_days, n_strata), dtype=float)
        for row in part.itertuples(index=False):
            d = day_index[str(row.source_day)]
            key = tuple(getattr(row, k) for k in PHY_KEYS)
            s = stratum_index[key]
            n = getattr(row, f"{metric}_observations")
            mean = getattr(row, f"{metric}_mean")
            if pd.notna(n) and float(n) > 0 and pd.notna(mean):
                n_arr[d, s] = float(n)
                sum_arr[d, s] = float(n) * float(mean)
        arrays[f"{metric}_n"] = n_arr
        arrays[f"{metric}_sum"] = sum_arr
    return day_labels, strata.drop(columns=["stratum_index"]), arrays


def campaign_point_estimates(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
) -> pd.DataFrame:
    daily_phy = _validate_daily_phy(daily_phy)
    campaign_days = _validate_campaign_days(campaign_days)
    rows: list[dict] = []
    for campaign_id in sorted(campaign_days["campaign_id"].unique()):
        day_labels, strata, arrays = _prepare_campaign_arrays(daily_phy, campaign_days, campaign_id)
        for metric in ("rssi", "snr"):
            n = arrays[f"{metric}_n"].sum(axis=0)
            s = arrays[f"{metric}_sum"].sum(axis=0)
            means = np.divide(s, n, out=np.full_like(s, np.nan), where=n > 0)
            for j, stratum in strata.iterrows():
                if n[j] <= 0:
                    continue
                rows.append({
                    "campaign_id": campaign_id,
                    **{k: stratum[k] for k in PHY_KEYS},
                    "metric": metric,
                    "source_days_in_campaign": len(day_labels),
                    "observations": int(n[j]),
                    "campaign_reception_weighted_mean": float(means[j]),
                })
    return pd.DataFrame(rows)


def block_bootstrap_sensitivity(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
    *,
    block_lengths: Iterable[int] = DEFAULT_BLOCK_LENGTHS,
    replicates: int = DEFAULT_REPLICATES,
    seed: int = DEFAULT_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return record-level bootstrap summaries and campaign/block design rows.

    This is a sensitivity audit, not authorisation of a final sampling distribution. Source
    days are resampled jointly across every PHY stratum and RSSI/SNR metric in a campaign.
    Gateways remain embedded in each source-day aggregate and are never sampled independently.
    """
    if replicates < 100:
        raise ValueError("replicates must be >= 100")
    daily_phy = _validate_daily_phy(daily_phy)
    campaign_days = _validate_campaign_days(campaign_days)
    block_lengths = tuple(sorted({int(v) for v in block_lengths}))
    if not block_lengths:
        raise ValueError("At least one block length is required")

    summary_rows: list[dict] = []
    design_rows: list[dict] = []
    root_rng = np.random.default_rng(seed)

    for campaign_id in sorted(campaign_days["campaign_id"].unique()):
        day_labels, strata, arrays = _prepare_campaign_arrays(daily_phy, campaign_days, campaign_id)
        n_days = len(day_labels)
        for block_length in block_lengths:
            if block_length > n_days:
                raise LoEDBlockBootstrapError(
                    f"Block length {block_length} exceeds {campaign_id} length {n_days}"
                )
            # Independent RNG stream per campaign/block-length; replicate indices are not
            # interpreted across campaigns or lengths.
            child_seed = int(root_rng.integers(0, np.iinfo(np.uint32).max))
            rng = np.random.default_rng(child_seed)
            n_blocks = int(math.ceil(n_days / block_length))
            design_rows.append({
                "campaign_id": campaign_id,
                "source_days": n_days,
                "block_length_days": block_length,
                "overlapping_candidate_blocks": n_days - block_length + 1,
                "blocks_sampled_per_replicate": n_blocks,
                "nominal_campaign_lengths_per_block": n_days / float(block_length),
                "bootstrap_replicates": int(replicates),
                "seed_stream": child_seed,
                "resampler": "noncircular_overlapping_moving_block_source_day",
                "cross_campaign_joint_meaning": False,
                "final_block_length_selected": False,
            })

            # Store draws only while this campaign/length is being summarised.
            draws = {
                "rssi": np.full((replicates, len(strata)), np.nan, dtype=float),
                "snr": np.full((replicates, len(strata)), np.nan, dtype=float),
            }
            sampled_nonmissing = {
                "rssi": np.zeros((replicates, len(strata)), dtype=int),
                "snr": np.zeros((replicates, len(strata)), dtype=int),
            }
            for b in range(replicates):
                idx = _moving_block_indices(n_days, block_length, rng)
                for metric in ("rssi", "snr"):
                    n = arrays[f"{metric}_n"][idx, :].sum(axis=0)
                    s = arrays[f"{metric}_sum"][idx, :].sum(axis=0)
                    draws[metric][b, :] = np.divide(
                        s, n, out=np.full_like(s, np.nan), where=n > 0
                    )
                    sampled_nonmissing[metric][b, :] = (arrays[f"{metric}_n"][idx, :] > 0).sum(axis=0)

            for metric in ("rssi", "snr"):
                orig_n = arrays[f"{metric}_n"].sum(axis=0)
                orig_s = arrays[f"{metric}_sum"].sum(axis=0)
                orig_mean = np.divide(
                    orig_s, orig_n, out=np.full_like(orig_s, np.nan), where=orig_n > 0
                )
                for j, stratum in strata.iterrows():
                    if orig_n[j] <= 0:
                        continue
                    x = draws[metric][:, j]
                    valid = x[np.isfinite(x)]
                    if len(valid) != replicates:
                        raise LoEDBlockBootstrapError(
                            f"Bootstrap produced empty {metric} stratum in {campaign_id}: "
                            f"{dict(stratum)}"
                        )
                    q025, q05, q25, q50, q75, q95, q975 = np.quantile(
                        valid, [0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975]
                    )
                    mean_boot = float(np.mean(valid))
                    summary_rows.append({
                        "campaign_id": campaign_id,
                        **{k: stratum[k] for k in PHY_KEYS},
                        "metric": metric,
                        "block_length_days": block_length,
                        "source_days_in_campaign": n_days,
                        "bootstrap_replicates": int(replicates),
                        "campaign_observations": int(orig_n[j]),
                        "campaign_reception_weighted_mean": float(orig_mean[j]),
                        "bootstrap_mean": mean_boot,
                        "bootstrap_bias": mean_boot - float(orig_mean[j]),
                        "bootstrap_sd": float(np.std(valid, ddof=1)),
                        "q025": float(q025),
                        "q05": float(q05),
                        "q25": float(q25),
                        "median": float(q50),
                        "q75": float(q75),
                        "q95": float(q95),
                        "q975": float(q975),
                        "percentile_95_width": float(q975 - q025),
                        "min_sampled_nonmissing_days": int(sampled_nonmissing[metric][:, j].min()),
                        "median_sampled_nonmissing_days": float(np.median(sampled_nonmissing[metric][:, j])),
                        "structural_missingness_preserved": True,
                        "diagnostic_sensitivity_only": True,
                        "publication_uncertainty_sampling_authorised": False,
                    })
    return pd.DataFrame(summary_rows), pd.DataFrame(design_rows)


def summarise_block_length_sensitivity(bootstrap_summary: pd.DataFrame) -> pd.DataFrame:
    required = {"campaign_id", "metric", "block_length_days", "bootstrap_sd", "percentile_95_width"}
    missing = sorted(required - set(bootstrap_summary.columns))
    if missing:
        raise LoEDBlockBootstrapError(f"Missing bootstrap-summary fields: {missing}")
    rows: list[dict] = []
    for (campaign_id, metric, block_length), group in bootstrap_summary.groupby(
        ["campaign_id", "metric", "block_length_days"], sort=True
    ):
        rows.append({
            "campaign_id": campaign_id,
            "metric": metric,
            "block_length_days": int(block_length),
            "phy_strata": int(len(group)),
            "bootstrap_sd_median": float(group["bootstrap_sd"].median()),
            "bootstrap_sd_q25": float(group["bootstrap_sd"].quantile(0.25)),
            "bootstrap_sd_q75": float(group["bootstrap_sd"].quantile(0.75)),
            "percentile_95_width_median": float(group["percentile_95_width"].median()),
            "percentile_95_width_q25": float(group["percentile_95_width"].quantile(0.25)),
            "percentile_95_width_q75": float(group["percentile_95_width"].quantile(0.75)),
            "max_abs_bootstrap_bias": float(group["bootstrap_bias"].abs().max()),
            "diagnostic_sensitivity_only": True,
        })
    out = pd.DataFrame(rows)
    # Ratios to the 7-day diagnostic reference are descriptive only; 7 days is not selected.
    ref = out[out["block_length_days"] == 7][
        ["campaign_id", "metric", "bootstrap_sd_median", "percentile_95_width_median"]
    ].rename(columns={
        "bootstrap_sd_median": "ref7_bootstrap_sd_median",
        "percentile_95_width_median": "ref7_percentile_95_width_median",
    })
    out = out.merge(ref, on=["campaign_id", "metric"], how="left")
    out["bootstrap_sd_ratio_to_7day"] = out["bootstrap_sd_median"] / out["ref7_bootstrap_sd_median"]
    out["percentile_width_ratio_to_7day"] = (
        out["percentile_95_width_median"] / out["ref7_percentile_95_width_median"]
    )
    out["seven_day_reference_selected_as_final"] = False
    return out
