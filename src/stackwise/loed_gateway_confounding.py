from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .loed_evidence import PHY_KEYS
from .loed_uncertainty import _aggregate_cells


class LoEDGatewayConfoundingError(RuntimeError):
    pass


def _campaign_map(campaign_days: pd.DataFrame) -> pd.DataFrame:
    required = {"source_day", "campaign_id"}
    missing = sorted(required - set(campaign_days.columns))
    if missing:
        raise LoEDGatewayConfoundingError(f"Missing campaign-day fields: {missing}")
    out = campaign_days[["source_day", "campaign_id"]].drop_duplicates().copy()
    if out["source_day"].duplicated().any():
        raise LoEDGatewayConfoundingError("A source day maps to more than one campaign")
    return out


def _with_campaign(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    required = {"source_day", "source_gateway_id", "reception_rows", *PHY_KEYS}
    missing = sorted(required - set(cells.columns))
    if missing:
        raise LoEDGatewayConfoundingError(f"Missing gateway-day-PHY fields: {missing}")
    work = cells.merge(_campaign_map(campaign_days), on="source_day", how="left", validate="many_to_one")
    if work["campaign_id"].isna().any():
        raise LoEDGatewayConfoundingError("Some gateway-day-PHY cells are not assigned to a campaign")
    return work


def build_campaign_gateway_set_summary(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    work = _with_campaign(cells, campaign_days)
    rows: list[dict[str, Any]] = []
    sets: dict[str, set[str]] = {}
    for campaign_id, group in work.groupby("campaign_id", sort=True):
        gateways = set(map(str, pd.unique(group["source_gateway_id"])))
        sets[str(campaign_id)] = gateways
        rows.append({
            "record_type": "campaign",
            "campaign_id": str(campaign_id),
            "gateways": len(gateways),
            "gateway_ids": "|".join(sorted(gateways)),
            "shared_gateways": None,
            "gateway_union": None,
            "gateway_intersection": None,
            "cross_campaign_gateway_jaccard": None,
            "campaign_shift_as_temporal_effect_authorised": False,
        })
    if len(sets) == 2:
        ids = sorted(sets)
        a, b = sets[ids[0]], sets[ids[1]]
        inter, union = a & b, a | b
        rows.append({
            "record_type": "cross_campaign",
            "campaign_id": f"{ids[0]}__{ids[1]}",
            "gateways": None,
            "gateway_ids": None,
            "shared_gateways": "|".join(sorted(inter)),
            "gateway_union": len(union),
            "gateway_intersection": len(inter),
            "cross_campaign_gateway_jaccard": (len(inter) / len(union)) if union else None,
            "campaign_shift_as_temporal_effect_authorised": False,
        })
    return pd.DataFrame(rows)


def get_shared_gateways(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> list[str]:
    work = _with_campaign(cells, campaign_days)
    sets = [set(map(str, pd.unique(g["source_gateway_id"]))) for _, g in work.groupby("campaign_id", sort=True)]
    if len(sets) != 2:
        raise LoEDGatewayConfoundingError("Shared-gateway audit currently requires exactly two observed campaigns")
    return sorted(sets[0] & sets[1])


def build_gateway_campaign_phy_summary(cells: pd.DataFrame, campaign_days: pd.DataFrame) -> pd.DataFrame:
    work = _with_campaign(cells, campaign_days)
    keys = ["campaign_id", "source_gateway_id", *PHY_KEYS]
    out = _aggregate_cells(work, keys)
    days = work.groupby(keys, dropna=False)["source_day"].nunique().rename("source_days")
    out = out.merge(days.reset_index(), on=keys, how="left", validate="one_to_one")
    return out.sort_values(keys).reset_index(drop=True)


def build_shared_gateway_campaign_shifts(gateway_campaign_phy: pd.DataFrame, shared_gateways: list[str]) -> pd.DataFrame:
    if not shared_gateways:
        return pd.DataFrame()
    campaigns = sorted(map(str, pd.unique(gateway_campaign_phy["campaign_id"])))
    if len(campaigns) != 2:
        raise LoEDGatewayConfoundingError("Shared-gateway shift audit requires exactly two campaigns")
    a, b = campaigns
    work = gateway_campaign_phy[gateway_campaign_phy["source_gateway_id"].astype(str).isin(shared_gateways)].copy()
    rows: list[dict[str, Any]] = []
    join_keys = ["source_gateway_id", *PHY_KEYS]
    for metric in ("rssi", "snr"):
        cols = join_keys + ["source_days", f"{metric}_observations", f"{metric}_mean", f"{metric}_std_population"]
        left = work[work["campaign_id"].astype(str) == a][cols].copy()
        right = work[work["campaign_id"].astype(str) == b][cols].copy()
        merged = left.merge(right, on=join_keys, how="inner", suffixes=("_a", "_b"), validate="one_to_one")
        for row in merged.to_dict("records"):
            mean_a = float(row[f"{metric}_mean_a"])
            mean_b = float(row[f"{metric}_mean_b"])
            rows.append({
                **{k: row[k] for k in join_keys},
                "metric": metric,
                "campaign_a": a,
                "campaign_b": b,
                "source_days_a": int(row["source_days_a"]),
                "source_days_b": int(row["source_days_b"]),
                "observations_a": int(row[f"{metric}_observations_a"]),
                "observations_b": int(row[f"{metric}_observations_b"]),
                "mean_a": mean_a,
                "mean_b": mean_b,
                "delta_b_minus_a": mean_b - mean_a,
                "abs_delta": abs(mean_b - mean_a),
                "std_population_a": row[f"{metric}_std_population_a"],
                "std_population_b": row[f"{metric}_std_population_b"],
                "same_gateway_cross_campaign_comparison": True,
                "causal_temporal_effect_authorised": False,
            })
    return pd.DataFrame(rows).sort_values(["metric", "source_gateway_id", *PHY_KEYS]).reset_index(drop=True)


def build_shared_gateway_equal_weight_shift(shared_gateway_shifts: pd.DataFrame, total_shared_gateways: int) -> pd.DataFrame:
    if shared_gateway_shifts.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for key, group in shared_gateway_shifts.groupby([*PHY_KEYS, "metric"], sort=True, dropna=False):
        phy_values = key[:-1]
        metric = key[-1]
        gateways = int(group["source_gateway_id"].astype(str).nunique())
        mean_a = float(pd.to_numeric(group["mean_a"], errors="coerce").mean())
        mean_b = float(pd.to_numeric(group["mean_b"], errors="coerce").mean())
        rows.append({
            **dict(zip(PHY_KEYS, phy_values)),
            "metric": metric,
            "shared_gateways_available": gateways,
            "total_shared_gateways": int(total_shared_gateways),
            "complete_shared_gateway_support": gateways == int(total_shared_gateways),
            "equal_gateway_mean_a": mean_a,
            "equal_gateway_mean_b": mean_b,
            "equal_gateway_delta_b_minus_a": mean_b - mean_a,
            "equal_gateway_abs_delta": abs(mean_b - mean_a),
            "weighting": "equal_weight_per_shared_gateway",
            "descriptive_sensitivity_only": True,
        })
    return pd.DataFrame(rows).sort_values(["metric", *PHY_KEYS]).reset_index(drop=True)


def build_shared_gateway_reception_weighted_shift(
    cells: pd.DataFrame,
    campaign_days: pd.DataFrame,
    shared_gateways: list[str],
) -> pd.DataFrame:
    work = _with_campaign(cells, campaign_days)
    work = work[work["source_gateway_id"].astype(str).isin(shared_gateways)].copy()
    if work.empty:
        return pd.DataFrame()
    agg = _aggregate_cells(work, ["campaign_id", *PHY_KEYS])
    campaigns = sorted(map(str, pd.unique(agg["campaign_id"])))
    if len(campaigns) != 2:
        raise LoEDGatewayConfoundingError("Shared-gateway weighted shift requires two campaigns")
    a, b = campaigns
    rows: list[dict[str, Any]] = []
    for metric in ("rssi", "snr"):
        cols = [*PHY_KEYS, f"{metric}_observations", f"{metric}_mean"]
        left = agg[agg["campaign_id"].astype(str) == a][cols]
        right = agg[agg["campaign_id"].astype(str) == b][cols]
        merged = left.merge(right, on=list(PHY_KEYS), how="inner", suffixes=("_a", "_b"), validate="one_to_one")
        for row in merged.to_dict("records"):
            mean_a = float(row[f"{metric}_mean_a"])
            mean_b = float(row[f"{metric}_mean_b"])
            rows.append({
                **{k: row[k] for k in PHY_KEYS},
                "metric": metric,
                "observations_a": int(row[f"{metric}_observations_a"]),
                "observations_b": int(row[f"{metric}_observations_b"]),
                "shared_gateway_reception_weighted_mean_a": mean_a,
                "shared_gateway_reception_weighted_mean_b": mean_b,
                "shared_gateway_reception_weighted_delta_b_minus_a": mean_b - mean_a,
                "shared_gateway_reception_weighted_abs_delta": abs(mean_b - mean_a),
                "weighting": "observed_reception_weight_within_shared_gateways",
                "descriptive_sensitivity_only": True,
            })
    return pd.DataFrame(rows).sort_values(["metric", *PHY_KEYS]).reset_index(drop=True)


def build_composition_sensitivity(
    full_campaign_shift: pd.DataFrame,
    equal_gateway_shift: pd.DataFrame,
    reception_weighted_shift: pd.DataFrame,
) -> pd.DataFrame:
    keys = [*PHY_KEYS, "metric"]
    full_cols = keys + ["delta_b_minus_a", "abs_delta", "delta_in_overall_sd_units"]
    out = full_campaign_shift[full_cols].rename(columns={
        "delta_b_minus_a": "full_campaign_delta_b_minus_a",
        "abs_delta": "full_campaign_abs_delta",
        "delta_in_overall_sd_units": "full_campaign_delta_in_overall_sd_units",
    })
    out = out.merge(equal_gateway_shift, on=keys, how="left", validate="one_to_one")
    weighted_cols = keys + [
        "shared_gateway_reception_weighted_delta_b_minus_a",
        "shared_gateway_reception_weighted_abs_delta",
    ]
    out = out.merge(reception_weighted_shift[weighted_cols], on=keys, how="left", validate="one_to_one")
    out["full_minus_equal_gateway_delta"] = out["full_campaign_delta_b_minus_a"] - out["equal_gateway_delta_b_minus_a"]
    out["full_minus_shared_reception_weighted_delta"] = (
        out["full_campaign_delta_b_minus_a"] - out["shared_gateway_reception_weighted_delta_b_minus_a"]
    )
    out["same_sign_full_vs_equal_gateway"] = np.sign(out["full_campaign_delta_b_minus_a"]) == np.sign(out["equal_gateway_delta_b_minus_a"])
    out["campaign_composition_confounding_resolved"] = False
    out["causal_attribution_authorised"] = False
    return out.sort_values(["metric", *PHY_KEYS]).reset_index(drop=True)


def build_within_campaign_gateway_heterogeneity(gateway_campaign_phy: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric in ("rssi", "snr"):
        value_col = f"{metric}_mean"
        for key, group in gateway_campaign_phy.groupby(["campaign_id", *PHY_KEYS], sort=True, dropna=False):
            vals = pd.to_numeric(group[value_col], errors="coerce").dropna()
            campaign_id, *phy_values = key
            n = int(len(vals))
            rows.append({
                "campaign_id": campaign_id,
                **dict(zip(PHY_KEYS, phy_values)),
                "metric": metric,
                "gateways_with_metric": n,
                "gateway_mean_unweighted": None if n == 0 else float(vals.mean()),
                "gateway_mean_std_sample": None if n < 2 else float(vals.std(ddof=1)),
                "gateway_mean_min": None if n == 0 else float(vals.min()),
                "gateway_mean_max": None if n == 0 else float(vals.max()),
                "gateway_mean_range": None if n == 0 else float(vals.max() - vals.min()),
                "descriptive_gateway_heterogeneity_only": True,
                "gateway_random_effect_authorised": False,
            })
    return pd.DataFrame(rows).sort_values(["campaign_id", "metric", *PHY_KEYS]).reset_index(drop=True)


def summarise_gateway_confounding(
    campaign_gateway_sets: pd.DataFrame,
    shared_shifts: pd.DataFrame,
    composition_sensitivity: pd.DataFrame,
    heterogeneity: pd.DataFrame,
) -> dict[str, Any]:
    cross = campaign_gateway_sets[campaign_gateway_sets["record_type"] == "cross_campaign"]
    if len(cross) != 1:
        raise LoEDGatewayConfoundingError("Expected exactly one cross-campaign gateway-set comparison")
    c = cross.iloc[0]
    summary: dict[str, Any] = {
        "campaign_gateway_counts": {
            str(row["campaign_id"]): int(row["gateways"])
            for _, row in campaign_gateway_sets[campaign_gateway_sets["record_type"] == "campaign"].iterrows()
        },
        "gateway_union": int(c["gateway_union"]),
        "shared_gateway_count": int(c["gateway_intersection"]),
        "shared_gateway_ids": str(c["shared_gateways"]).split("|") if str(c["shared_gateways"]) else [],
        "cross_campaign_gateway_jaccard": float(c["cross_campaign_gateway_jaccard"]),
        "shared_gateway_shift_rows": int(len(shared_shifts)),
        "composition_sensitivity_rows": int(len(composition_sensitivity)),
        "within_campaign_gateway_heterogeneity_rows": int(len(heterogeneity)),
    }
    for metric in ("rssi", "snr"):
        cs = composition_sensitivity[composition_sensitivity["metric"] == metric]
        if not cs.empty:
            summary[f"{metric}_full_abs_shift_median"] = float(pd.to_numeric(cs["full_campaign_abs_delta"], errors="coerce").median())
            summary[f"{metric}_equal_shared_gateway_abs_shift_median"] = float(pd.to_numeric(cs["equal_gateway_abs_delta"], errors="coerce").median())
            summary[f"{metric}_same_sign_full_vs_equal_shared_gateway_fraction"] = float(
                cs["same_sign_full_vs_equal_gateway"].fillna(False).mean()
            )
            summary[f"{metric}_complete_shared_gateway_support_fraction"] = float(
                cs["complete_shared_gateway_support"].fillna(False).mean()
            )
        h = heterogeneity[heterogeneity["metric"] == metric]
        if not h.empty:
            summary[f"{metric}_median_within_campaign_gateway_mean_range"] = float(
                pd.to_numeric(h["gateway_mean_range"], errors="coerce").median()
            )
    summary.update({
        "campaign_shift_as_pure_temporal_effect_authorised": False,
        "campaign_composition_confounding_resolved": False,
        "campaign_random_effect_authorised": False,
        "independent_gateway_bootstrap_authorised": False,
        "campaign_stratified_block_bootstrap_authorised": False,
        "block_length_selected": False,
        "hierarchical_sampling_authorised": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
    })
    return summary
