from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .loed_evidence import PHY_KEYS
from .loed_uncertainty import _aggregate_cells

DEFAULT_CAMPAIGN_GAP_DAYS = 30
DEFAULT_MAX_ACF_LAG = 14


class LoEDTemporalError(RuntimeError):
    pass


@dataclass(frozen=True)
class CampaignWindow:
    campaign_id: str
    start_day: str
    end_day: str
    source_days: int
    calendar_span_days: int
    gap_from_previous_observation_days: int | None


def assign_temporal_campaigns(
    day_coverage: pd.DataFrame,
    *,
    campaign_gap_days: int = DEFAULT_CAMPAIGN_GAP_DAYS,
) -> pd.DataFrame:
    """Assign contiguous acquisition campaigns without inventing source semantics.

    A new campaign is started only when the gap between consecutive observed source days
    exceeds ``campaign_gap_days``. The threshold is an audit parameter, not a claim that
    shorter missing-day gaps would be statistically ignorable.
    """
    required = {"source_day", "source_file"}
    missing = sorted(required - set(day_coverage.columns))
    if missing:
        raise LoEDTemporalError(f"Missing day-coverage fields: {missing}")
    if campaign_gap_days < 1:
        raise ValueError("campaign_gap_days must be >= 1")

    work = day_coverage.copy()
    work["day"] = pd.to_datetime(work["source_day"], errors="coerce")
    if work["day"].isna().any():
        bad = work.loc[work["day"].isna(), "source_day"].astype(str).tolist()[:5]
        raise LoEDTemporalError(f"Unparseable source_day values: {bad}")
    if work["day"].duplicated().any():
        dup = work.loc[work["day"].duplicated(keep=False), "source_day"].astype(str).tolist()[:5]
        raise LoEDTemporalError(f"Duplicate source-day coverage rows: {dup}")

    work = work.sort_values("day").reset_index(drop=True)
    work["gap_from_previous_observation_days"] = work["day"].diff().dt.days
    starts = work["gap_from_previous_observation_days"].gt(campaign_gap_days).fillna(False)
    work["campaign_number"] = starts.cumsum().astype(int) + 1
    work["campaign_id"] = work["campaign_number"].map(lambda x: f"campaign_{x}")
    return work


def build_campaign_summary(campaign_days: pd.DataFrame) -> pd.DataFrame:
    if campaign_days.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for campaign_id, group in campaign_days.groupby("campaign_id", sort=True):
        group = group.sort_values("day")
        start = group["day"].min()
        end = group["day"].max()
        first_gap = group.iloc[0]["gap_from_previous_observation_days"]
        rows.append({
            "campaign_id": campaign_id,
            "start_day": start.date().isoformat(),
            "end_day": end.date().isoformat(),
            "source_days": int(len(group)),
            "calendar_span_days": int((end - start).days + 1),
            "gap_from_previous_observation_days": None if pd.isna(first_gap) else int(first_gap),
            "reception_rows": int(pd.to_numeric(group.get("reception_rows"), errors="coerce").fillna(0).sum()),
            "gateways_observed_min": int(pd.to_numeric(group.get("gateways_observed"), errors="coerce").min()),
            "gateways_observed_median": float(pd.to_numeric(group.get("gateways_observed"), errors="coerce").median()),
            "gateways_observed_max": int(pd.to_numeric(group.get("gateways_observed"), errors="coerce").max()),
            "phy_strata_observed_min": int(pd.to_numeric(group.get("phy_strata_observed"), errors="coerce").min()),
            "phy_strata_observed_median": float(pd.to_numeric(group.get("phy_strata_observed"), errors="coerce").median()),
            "phy_strata_observed_max": int(pd.to_numeric(group.get("phy_strata_observed"), errors="coerce").max()),
        })
    return pd.DataFrame(rows)


def _campaign_map(campaign_days: pd.DataFrame) -> pd.DataFrame:
    return campaign_days[["source_day", "campaign_id"]].drop_duplicates().copy()


def build_gateway_campaign_coverage(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    required = {"source_day", "source_gateway_id", "reception_rows", *PHY_KEYS}
    missing = sorted(required - set(cells.columns))
    if missing:
        raise LoEDTemporalError(f"Missing gateway-day-PHY fields: {missing}")
    work = cells.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    if work["campaign_id"].isna().any():
        raise LoEDTemporalError("Some gateway-day-PHY cells are not mapped to a temporal campaign")

    rows: list[dict[str, Any]] = []
    campaign_day_counts = campaign_days.groupby("campaign_id")["source_day"].nunique().to_dict()
    for (campaign_id, gateway), group in work.groupby(["campaign_id", "source_gateway_id"], sort=True):
        days = pd.to_datetime(group["source_day"].drop_duplicates(), errors="coerce").dropna().sort_values()
        n_days = int(len(days))
        rows.append({
            "campaign_id": campaign_id,
            "source_gateway_id": gateway,
            "days_observed": n_days,
            "campaign_days": int(campaign_day_counts[campaign_id]),
            "day_coverage_fraction": n_days / float(campaign_day_counts[campaign_id]),
            "first_day": days.min().date().isoformat() if n_days else None,
            "last_day": days.max().date().isoformat() if n_days else None,
            "gateway_day_phy_cells": int(len(group)),
            "reception_rows": int(pd.to_numeric(group["reception_rows"], errors="coerce").fillna(0).sum()),
            "phy_strata_observed": int(group[list(PHY_KEYS)].drop_duplicates().shape[0]),
        })
    return pd.DataFrame(rows)


def build_campaign_phy_summary(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    work = cells.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    if work["campaign_id"].isna().any():
        raise LoEDTemporalError("Some cells are not mapped to campaign")
    out = _aggregate_cells(work, ["campaign_id", *PHY_KEYS])
    if out.empty:
        return out
    day_counts = work.groupby(["campaign_id", *PHY_KEYS], dropna=False)["source_day"].nunique().rename("source_days")
    gateway_counts = work.groupby(["campaign_id", *PHY_KEYS], dropna=False)["source_gateway_id"].nunique().rename("gateways")
    out = out.merge(day_counts.reset_index(), on=["campaign_id", *PHY_KEYS], how="left")
    out = out.merge(gateway_counts.reset_index(), on=["campaign_id", *PHY_KEYS], how="left")
    return out.sort_values(["campaign_id", *PHY_KEYS]).reset_index(drop=True)


def _linear_residuals(day_numbers: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, float | None, float | None]:
    if len(values) < 3 or np.std(values, ddof=1) <= 0:
        return values - np.nanmean(values), None, None
    slope, intercept = np.polyfit(day_numbers.astype(float), values.astype(float), 1)
    fitted = intercept + slope * day_numbers
    residual = values - fitted
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    ss_res = float(np.sum(residual ** 2))
    r2 = None if ss_tot <= 0 else max(0.0, min(1.0, 1.0 - ss_res / ss_tot))
    return residual, float(slope), r2


def _lag_pairs(days: np.ndarray, values: np.ndarray, lag: int) -> tuple[np.ndarray, np.ndarray]:
    by_day = {int(d): float(v) for d, v in zip(days, values) if np.isfinite(v)}
    x: list[float] = []
    y: list[float] = []
    for d in sorted(by_day):
        if d + lag in by_day:
            x.append(by_day[d])
            y.append(by_day[d + lag])
    return np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def _corr(x: np.ndarray, y: np.ndarray, *, min_pairs: int = 5) -> float | None:
    if len(x) < min_pairs or len(y) < min_pairs:
        return None
    if np.std(x, ddof=1) <= 0 or np.std(y, ddof=1) <= 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def build_campaign_series_diagnostics(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
) -> pd.DataFrame:
    work = daily_phy.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    if work["campaign_id"].isna().any():
        raise LoEDTemporalError("Some daily-PHY rows are not mapped to campaign")
    rows: list[dict[str, Any]] = []
    for key, group in work.groupby(["campaign_id", *PHY_KEYS], sort=True, dropna=False):
        campaign_id, *phy_values = key if isinstance(key, tuple) else (key,)
        base = {"campaign_id": campaign_id, **dict(zip(PHY_KEYS, phy_values))}
        group = group.copy()
        group["day"] = pd.to_datetime(group["source_day"], errors="coerce")
        group = group.dropna(subset=["day"]).sort_values("day")
        campaign_start = group["day"].min()
        for metric in ("rssi", "snr"):
            value_col = f"{metric}_mean"
            valid = group.loc[pd.to_numeric(group[value_col], errors="coerce").notna(), ["day", value_col]].copy()
            if valid.empty:
                continue
            values = pd.to_numeric(valid[value_col], errors="coerce").to_numpy(dtype=float)
            day_numbers = (valid["day"] - campaign_start).dt.days.to_numpy(dtype=int)
            residuals, slope, trend_r2 = _linear_residuals(day_numbers, values)
            x1, y1 = _lag_pairs(day_numbers, values, 1)
            rx1, ry1 = _lag_pairs(day_numbers, residuals, 1)

            diff_corr = None
            if len(values) >= 4:
                # First differences only across genuinely consecutive calendar days.
                diffs: list[tuple[int, float]] = []
                by_day = {int(d): float(v) for d, v in zip(day_numbers, values)}
                for d in sorted(by_day):
                    if d + 1 in by_day:
                        diffs.append((d + 1, by_day[d + 1] - by_day[d]))
                if len(diffs) >= 6:
                    dd = np.asarray([d for d, _ in diffs], dtype=int)
                    dv = np.asarray([v for _, v in diffs], dtype=float)
                    dx, dy = _lag_pairs(dd, dv, 1)
                    diff_corr = _corr(dx, dy)

            rows.append({
                **base,
                "metric": metric,
                "days_observed": int(len(valid)),
                "mean_daily_phy_value": float(np.mean(values)),
                "std_daily_phy_value": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                "linear_trend_per_calendar_day": slope,
                "linear_trend_r2": trend_r2,
                "lag1_raw": _corr(x1, y1),
                "lag1_linear_detrended": _corr(rx1, ry1),
                "lag1_first_difference": diff_corr,
                "diagnostic_only": True,
            })
    return pd.DataFrame(rows)


def build_campaign_acf_diagnostics(
    daily_phy: pd.DataFrame,
    campaign_days: pd.DataFrame,
    *,
    max_lag: int = DEFAULT_MAX_ACF_LAG,
) -> pd.DataFrame:
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")
    work = daily_phy.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    if work["campaign_id"].isna().any():
        raise LoEDTemporalError("Some daily-PHY rows are not mapped to campaign")
    rows: list[dict[str, Any]] = []
    for key, group in work.groupby(["campaign_id", *PHY_KEYS], sort=True, dropna=False):
        campaign_id, *phy_values = key if isinstance(key, tuple) else (key,)
        base = {"campaign_id": campaign_id, **dict(zip(PHY_KEYS, phy_values))}
        group = group.copy()
        group["day"] = pd.to_datetime(group["source_day"], errors="coerce")
        group = group.dropna(subset=["day"]).sort_values("day")
        campaign_start = group["day"].min()
        for metric in ("rssi", "snr"):
            value_col = f"{metric}_mean"
            valid = group.loc[pd.to_numeric(group[value_col], errors="coerce").notna(), ["day", value_col]].copy()
            if valid.empty:
                continue
            values = pd.to_numeric(valid[value_col], errors="coerce").to_numpy(dtype=float)
            day_numbers = (valid["day"] - campaign_start).dt.days.to_numpy(dtype=int)
            residuals, _, _ = _linear_residuals(day_numbers, values)
            for lag in range(1, max_lag + 1):
                x, y = _lag_pairs(day_numbers, values, lag)
                rx, ry = _lag_pairs(day_numbers, residuals, lag)
                rows.append({
                    **base,
                    "metric": metric,
                    "lag_days": lag,
                    "raw_pairs": int(len(x)),
                    "raw_acf": _corr(x, y),
                    "detrended_pairs": int(len(rx)),
                    "linear_detrended_acf": _corr(rx, ry),
                    "diagnostic_only": True,
                })
    return pd.DataFrame(rows)


def build_acf_lag_summary(acf: pd.DataFrame) -> pd.DataFrame:
    if acf.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (campaign_id, metric, lag), group in acf.groupby(["campaign_id", "metric", "lag_days"], sort=True):
        for variant in ("raw_acf", "linear_detrended_acf"):
            vals = pd.to_numeric(group[variant], errors="coerce").dropna()
            rows.append({
                "campaign_id": campaign_id,
                "metric": metric,
                "lag_days": int(lag),
                "series_variant": variant,
                "strata_with_correlation": int(len(vals)),
                "acf_min": None if vals.empty else float(vals.min()),
                "acf_q25": None if vals.empty else float(vals.quantile(0.25)),
                "acf_median": None if vals.empty else float(vals.median()),
                "acf_q75": None if vals.empty else float(vals.quantile(0.75)),
                "acf_max": None if vals.empty else float(vals.max()),
            })
    return pd.DataFrame(rows)


def build_gateway_set_transitions(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    work = cells.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    day_sets = (
        work.groupby(["campaign_id", "source_day"], sort=True)["source_gateway_id"]
        .agg(lambda x: frozenset(map(str, pd.unique(x))))
        .reset_index(name="gateway_set")
    )
    rows: list[dict[str, Any]] = []
    for campaign_id, group in day_sets.groupby("campaign_id", sort=True):
        group = group.copy()
        group["day"] = pd.to_datetime(group["source_day"], errors="coerce")
        group = group.sort_values("day").reset_index(drop=True)
        for i in range(len(group) - 1):
            d0, d1 = group.loc[i, "day"], group.loc[i + 1, "day"]
            if (d1 - d0).days != 1:
                continue
            a = group.loc[i, "gateway_set"]
            b = group.loc[i + 1, "gateway_set"]
            union = a | b
            inter = a & b
            rows.append({
                "campaign_id": campaign_id,
                "day_from": d0.date().isoformat(),
                "day_to": d1.date().isoformat(),
                "gateways_from": len(a),
                "gateways_to": len(b),
                "gateway_union": len(union),
                "gateway_intersection": len(inter),
                "gateway_set_jaccard": (len(inter) / len(union)) if union else None,
                "gateways_added": len(b - a),
                "gateways_removed": len(a - b),
                "gateway_set_unchanged": a == b,
            })
    return pd.DataFrame(rows)


def build_campaign_shift_diagnostics(
    campaign_phy: pd.DataFrame,
    overall_calibration: pd.DataFrame,
) -> pd.DataFrame:
    campaigns = sorted(campaign_phy["campaign_id"].dropna().astype(str).unique())
    if len(campaigns) != 2:
        raise LoEDTemporalError(
            f"Campaign-shift diagnostics currently require exactly two observed campaigns; found {len(campaigns)}"
        )
    a_id, b_id = campaigns
    keys = list(PHY_KEYS)
    rows: list[dict[str, Any]] = []
    for metric in ("rssi", "snr"):
        cols = keys + ["campaign_id", f"{metric}_observations", f"{metric}_mean", f"{metric}_std_population"]
        cur = campaign_phy[cols].copy()
        a = cur[cur["campaign_id"] == a_id].drop(columns=["campaign_id"]).rename(columns={
            f"{metric}_observations": "observations_a",
            f"{metric}_mean": "mean_a",
            f"{metric}_std_population": "std_a",
        })
        b = cur[cur["campaign_id"] == b_id].drop(columns=["campaign_id"]).rename(columns={
            f"{metric}_observations": "observations_b",
            f"{metric}_mean": "mean_b",
            f"{metric}_std_population": "std_b",
        })
        merged = a.merge(b, on=keys, how="outer")
        overall = overall_calibration[keys + [f"{metric}_std_population"]].rename(
            columns={f"{metric}_std_population": "overall_std_population"}
        )
        merged = merged.merge(overall, on=keys, how="left")
        for _, row in merged.iterrows():
            mean_a = row.get("mean_a")
            mean_b = row.get("mean_b")
            delta = None if pd.isna(mean_a) or pd.isna(mean_b) else float(mean_b - mean_a)
            overall_std = row.get("overall_std_population")
            rows.append({
                **{k: row[k] for k in keys},
                "metric": metric,
                "campaign_a": a_id,
                "campaign_b": b_id,
                "observations_a": None if pd.isna(row.get("observations_a")) else int(row["observations_a"]),
                "observations_b": None if pd.isna(row.get("observations_b")) else int(row["observations_b"]),
                "mean_a": None if pd.isna(mean_a) else float(mean_a),
                "mean_b": None if pd.isna(mean_b) else float(mean_b),
                "delta_b_minus_a": delta,
                "abs_delta": None if delta is None else abs(delta),
                "overall_std_population": None if pd.isna(overall_std) else float(overall_std),
                "delta_in_overall_sd_units": (
                    None if delta is None or pd.isna(overall_std) or float(overall_std) <= 0
                    else float(delta / float(overall_std))
                ),
                "descriptive_domain_shift_only": True,
                "campaign_random_effect_authorised": False,
            })
    return pd.DataFrame(rows)


def summarise_temporal_audit(
    campaigns: pd.DataFrame,
    series_diag: pd.DataFrame,
    acf_summary: pd.DataFrame,
    transitions: pd.DataFrame,
    shifts: pd.DataFrame,
) -> dict[str, Any]:
    raw_lag1 = acf_summary[(acf_summary["lag_days"] == 1) & (acf_summary["series_variant"] == "raw_acf")]
    detr_lag1 = acf_summary[(acf_summary["lag_days"] == 1) & (acf_summary["series_variant"] == "linear_detrended_acf")]
    shift_units = pd.to_numeric(shifts["delta_in_overall_sd_units"], errors="coerce").dropna().abs()
    jaccard = pd.to_numeric(transitions.get("gateway_set_jaccard"), errors="coerce").dropna()
    trend_r2 = pd.to_numeric(series_diag.get("linear_trend_r2"), errors="coerce").dropna()
    return {
        "campaigns": int(len(campaigns)),
        "campaign_source_days": {str(r.campaign_id): int(r.source_days) for r in campaigns.itertuples()},
        "campaign_windows": {
            str(r.campaign_id): {"start": str(r.start_day), "end": str(r.end_day)} for r in campaigns.itertuples()
        },
        "max_gap_from_previous_observation_days": int(
            pd.to_numeric(campaigns["gap_from_previous_observation_days"], errors="coerce").dropna().max()
        ) if len(campaigns) > 1 else None,
        "raw_lag1_median_range_across_campaign_metric_groups": {
            "min": None if raw_lag1.empty else float(pd.to_numeric(raw_lag1["acf_median"], errors="coerce").min()),
            "max": None if raw_lag1.empty else float(pd.to_numeric(raw_lag1["acf_median"], errors="coerce").max()),
        },
        "detrended_lag1_median_range_across_campaign_metric_groups": {
            "min": None if detr_lag1.empty else float(pd.to_numeric(detr_lag1["acf_median"], errors="coerce").min()),
            "max": None if detr_lag1.empty else float(pd.to_numeric(detr_lag1["acf_median"], errors="coerce").max()),
        },
        "linear_trend_r2": {
            "median": None if trend_r2.empty else float(trend_r2.median()),
            "max": None if trend_r2.empty else float(trend_r2.max()),
        },
        "gateway_set_transition_jaccard": {
            "min": None if jaccard.empty else float(jaccard.min()),
            "median": None if jaccard.empty else float(jaccard.median()),
            "max": None if jaccard.empty else float(jaccard.max()),
            "unchanged_fraction": None if transitions.empty else float(transitions["gateway_set_unchanged"].mean()),
        },
        "absolute_campaign_shift_in_overall_sd_units": {
            "median": None if shift_units.empty else float(shift_units.median()),
            "max": None if shift_units.empty else float(shift_units.max()),
        },
    }
