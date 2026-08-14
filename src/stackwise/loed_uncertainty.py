from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .loed_evidence import PHY_KEYS

DATASET_ID = "loed_lorawan_edge_2020"
GATEWAY_DAY_PHY_KEYS = ("source_file", "source_gateway_id", *PHY_KEYS)


class LoEDUncertaintyError(RuntimeError):
    pass


def _safe_var(sum_: float, sumsq: float, n: float) -> float | None:
    if n <= 0:
        return None
    mean = sum_ / n
    return max(0.0, sumsq / n - mean * mean)


def _safe_corr(cov: float | None, var_x: float | None, var_y: float | None) -> float | None:
    if cov is None or var_x is None or var_y is None or var_x <= 0 or var_y <= 0:
        return None
    return float(max(-1.0, min(1.0, cov / math.sqrt(var_x * var_y))))


def _source_day_from_label(source_file: str, timestamps: pd.Series) -> tuple[str | None, str]:
    """Recover the source-day label without changing validated source semantics.

    LoED source files use DD_MM_YYYY names. Timestamp fallback is diagnostic only and is
    used only if a future source release changes file naming.
    """
    stem = Path(str(source_file)).stem
    match = re.search(r"(?<!\d)(\d{2})_(\d{2})_(\d{4})(?!\d)", stem)
    if match:
        day, month, year = match.groups()
        try:
            return pd.Timestamp(f"{year}-{month}-{day}").date().isoformat(), "source_file_name"
        except ValueError:
            pass
    ts = pd.to_datetime(timestamps, utc=True, errors="coerce").dropna()
    if not ts.empty:
        return ts.min().date().isoformat(), "timestamp_fallback"
    return None, "unavailable"


def summarise_gateway_day_phy(source_file: str, frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "source_file", "source_gateway_id", *PHY_KEYS, "rssi_dbm", "snr_db",
        "source_crc_valid", "source_device_address", "source_packet_fingerprint", "timestamp_utc",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise LoEDUncertaintyError(f"Missing LoED hierarchical fields: {missing}")

    work = frame.copy()
    work["source_gateway_id"] = work["source_gateway_id"].astype("string")
    for key in PHY_KEYS:
        work[key] = pd.to_numeric(work[key], errors="coerce")
    work = work.dropna(subset=["source_gateway_id", *PHY_KEYS]).copy()
    if work.empty:
        return pd.DataFrame()

    work["rssi"] = pd.to_numeric(work["rssi_dbm"], errors="coerce")
    work["snr"] = pd.to_numeric(work["snr_db"], errors="coerce")
    work["rssi_sq"] = work["rssi"] ** 2
    work["snr_sq"] = work["snr"] ** 2
    pair = work["rssi"].notna() & work["snr"].notna()
    work["pair_rssi"] = work["rssi"].where(pair)
    work["pair_snr"] = work["snr"].where(pair)
    work["pair_rssi_sq"] = work["rssi_sq"].where(pair)
    work["pair_snr_sq"] = work["snr_sq"].where(pair)
    work["pair_cross"] = (work["rssi"] * work["snr"]).where(pair)
    work["crc_known"] = work["source_crc_valid"].notna().astype(int)
    work["crc_valid_int"] = (work["source_crc_valid"] == True).astype(int)  # noqa: E712
    device = work["source_device_address"].astype("string")
    work["device_non_sentinel"] = device.where(device != "-1")
    work["timestamp_num"] = pd.to_datetime(work["timestamp_utc"], utc=True, errors="coerce")

    keys = ["source_gateway_id", *PHY_KEYS]
    grouped = work.groupby(keys, sort=True, dropna=False)
    base = grouped.agg(
        reception_rows=("source_file", "size"),
        rssi_observations=("rssi", "count"),
        rssi_sum=("rssi", "sum"),
        rssi_sumsq=("rssi_sq", "sum"),
        snr_observations=("snr", "count"),
        snr_sum=("snr", "sum"),
        snr_sumsq=("snr_sq", "sum"),
        paired_observations=("pair_cross", "count"),
        pair_rssi_sum=("pair_rssi", "sum"),
        pair_snr_sum=("pair_snr", "sum"),
        pair_rssi_sumsq=("pair_rssi_sq", "sum"),
        pair_snr_sumsq=("pair_snr_sq", "sum"),
        pair_cross_sum=("pair_cross", "sum"),
        crc_known_receptions=("crc_known", "sum"),
        crc_valid_receptions=("crc_valid_int", "sum"),
        unique_non_sentinel_devices=("device_non_sentinel", "nunique"),
        unique_packet_fingerprints=("source_packet_fingerprint", "nunique"),
        timestamp_min_utc=("timestamp_num", "min"),
        timestamp_max_utc=("timestamp_num", "max"),
    ).reset_index()

    source_day, day_basis = _source_day_from_label(source_file, work["timestamp_utc"])
    base.insert(0, "source_file", str(source_file))
    base.insert(1, "source_day", source_day)
    base.insert(2, "source_day_basis", day_basis)
    base["crc_invalid_receptions"] = base["crc_known_receptions"] - base["crc_valid_receptions"]
    base["crc_valid_fraction_of_recorded_receptions"] = np.where(
        base["crc_known_receptions"] > 0,
        base["crc_valid_receptions"] / base["crc_known_receptions"],
        np.nan,
    )

    def finish(prefix: str, count_col: str, sum_col: str, sumsq_col: str) -> None:
        n = pd.to_numeric(base[count_col], errors="coerce").fillna(0).astype(float)
        s = pd.to_numeric(base[sum_col], errors="coerce").fillna(0).astype(float)
        ss = pd.to_numeric(base[sumsq_col], errors="coerce").fillna(0).astype(float)
        mean = np.where(n > 0, s / n, np.nan)
        var = np.where(n > 0, np.maximum(0.0, ss / n - mean ** 2), np.nan)
        base[f"{prefix}_mean"] = mean
        base[f"{prefix}_std_population"] = np.sqrt(var)

    finish("rssi_dbm", "rssi_observations", "rssi_sum", "rssi_sumsq")
    finish("snr_db", "snr_observations", "snr_sum", "snr_sumsq")
    finish("paired_rssi_dbm", "paired_observations", "pair_rssi_sum", "pair_rssi_sumsq")
    finish("paired_snr_db", "paired_observations", "pair_snr_sum", "pair_snr_sumsq")

    n_pair = pd.to_numeric(base["paired_observations"], errors="coerce").fillna(0).astype(float)
    mean_x = pd.to_numeric(base["paired_rssi_dbm_mean"], errors="coerce")
    mean_y = pd.to_numeric(base["paired_snr_db_mean"], errors="coerce")
    cross = pd.to_numeric(base["pair_cross_sum"], errors="coerce").fillna(0).astype(float)
    cov = np.where(n_pair > 0, cross / n_pair - mean_x * mean_y, np.nan)
    base["paired_rssi_snr_cov_population"] = cov
    denom = pd.to_numeric(base["paired_rssi_dbm_std_population"], errors="coerce") * pd.to_numeric(
        base["paired_snr_db_std_population"], errors="coerce"
    )
    base["paired_rssi_snr_corr"] = np.where(denom > 0, cov / denom, np.nan)

    return base.sort_values(["source_day", "source_gateway_id", *PHY_KEYS]).reset_index(drop=True)


def build_gateway_day_phy_cells(input_path: str | Path, *, batch_size: int = 250_000) -> pd.DataFrame:
    from .loed_streaming import _iter_source_frames_single_pass

    input_path = Path(input_path)
    columns = [
        "source_file", "source_gateway_id", *PHY_KEYS, "rssi_dbm", "snr_db",
        "source_crc_valid", "source_device_address", "source_packet_fingerprint", "timestamp_utc",
    ]
    parts: list[pd.DataFrame] = []
    for index, (source_file, frame) in enumerate(
        _iter_source_frames_single_pass(input_path, columns, batch_size=batch_size), start=1
    ):
        print(f"[LoED uncertainty] source day {index}: {Path(source_file).name} ({len(frame):,} receptions)", flush=True)
        part = summarise_gateway_day_phy(source_file, frame)
        if not part.empty:
            parts.append(part)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    duplicate = int(out.duplicated(subset=list(GATEWAY_DAY_PHY_KEYS)).sum())
    if duplicate:
        raise LoEDUncertaintyError(f"Duplicate gateway-day-PHY cells: {duplicate}")
    return out


def _combine_metric(group: pd.DataFrame, prefix: str) -> dict[str, float | int | None]:
    n_col = f"{prefix}_observations"
    sum_col = "rssi_sum" if prefix == "rssi" else "snr_sum"
    sumsq_col = "rssi_sumsq" if prefix == "rssi" else "snr_sumsq"
    n = pd.to_numeric(group[n_col], errors="coerce").fillna(0).astype(float)
    s = pd.to_numeric(group[sum_col], errors="coerce").fillna(0).astype(float)
    ss = pd.to_numeric(group[sumsq_col], errors="coerce").fillna(0).astype(float)
    total_n = float(n.sum())
    if total_n <= 0:
        return {
            "observations": 0, "mean": None, "std_population": None,
            "within_cell_variance": None, "between_cell_variance_weighted": None,
            "between_cell_variance_fraction": None, "cell_mean_std_unweighted": None,
        }
    mean = float(s.sum() / total_n)
    total_var = max(0.0, float(ss.sum() / total_n - mean * mean))
    means = np.where(n > 0, s / n, np.nan)
    cell_var = np.where(n > 0, np.maximum(0.0, ss / n - means ** 2), np.nan)
    valid = n > 0
    within = float(np.nansum(n[valid] * cell_var[valid]) / total_n)
    between = float(np.nansum(n[valid] * (means[valid] - mean) ** 2) / total_n)
    cell_means = pd.Series(means[valid]).dropna().astype(float)
    return {
        "observations": int(total_n),
        "mean": mean,
        "std_population": math.sqrt(total_var),
        "within_cell_variance": within,
        "between_cell_variance_weighted": between,
        "between_cell_variance_fraction": (between / total_var if total_var > 0 else 0.0),
        "cell_mean_std_unweighted": (float(cell_means.std(ddof=1)) if len(cell_means) > 1 else None),
    }


def _combine_pair(group: pd.DataFrame) -> dict[str, float | int | None]:
    n = pd.to_numeric(group["paired_observations"], errors="coerce").fillna(0).astype(float)
    sx = pd.to_numeric(group["pair_rssi_sum"], errors="coerce").fillna(0).astype(float)
    sy = pd.to_numeric(group["pair_snr_sum"], errors="coerce").fillna(0).astype(float)
    sxx = pd.to_numeric(group["pair_rssi_sumsq"], errors="coerce").fillna(0).astype(float)
    syy = pd.to_numeric(group["pair_snr_sumsq"], errors="coerce").fillna(0).astype(float)
    sxy = pd.to_numeric(group["pair_cross_sum"], errors="coerce").fillna(0).astype(float)
    total_n = float(n.sum())
    if total_n <= 0:
        return {"paired_observations": 0, "paired_cov_population": None, "paired_corr": None,
                "between_cell_mean_cov_weighted": None, "between_cell_mean_corr_unweighted": None}
    mx = float(sx.sum() / total_n)
    my = float(sy.sum() / total_n)
    vx = max(0.0, float(sxx.sum() / total_n - mx * mx))
    vy = max(0.0, float(syy.sum() / total_n - my * my))
    cov = float(sxy.sum() / total_n - mx * my)
    corr = _safe_corr(cov, vx, vy)

    valid = n > 0
    cell_mx = np.where(valid, sx / n, np.nan)
    cell_my = np.where(valid, sy / n, np.nan)
    between_cov = float(np.nansum(n[valid] * (cell_mx[valid] - mx) * (cell_my[valid] - my)) / total_n)
    means = pd.DataFrame({"x": cell_mx[valid], "y": cell_my[valid]}).dropna()
    cell_corr = None
    if len(means) >= 3 and means["x"].std(ddof=1) > 0 and means["y"].std(ddof=1) > 0:
        cell_corr = float(means["x"].corr(means["y"]))
    return {
        "paired_observations": int(total_n),
        "paired_cov_population": cov,
        "paired_corr": corr,
        "between_cell_mean_cov_weighted": between_cov,
        "between_cell_mean_corr_unweighted": cell_corr,
    }


def build_hierarchical_calibration(cells: pd.DataFrame) -> pd.DataFrame:
    if cells.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for key, group in cells.groupby(list(PHY_KEYS), sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = {name: value for name, value in zip(PHY_KEYS, key_tuple)}
        row.update({
            "gateway_day_cells": int(len(group)),
            "source_days": int(group["source_file"].nunique()),
            "gateways": int(group["source_gateway_id"].nunique()),
            "reception_rows": int(pd.to_numeric(group["reception_rows"], errors="coerce").fillna(0).sum()),
            "unique_non_sentinel_devices_sum_over_cells": int(pd.to_numeric(group["unique_non_sentinel_devices"], errors="coerce").fillna(0).sum()),
            "unique_packet_fingerprints_sum_over_cells": int(pd.to_numeric(group["unique_packet_fingerprints"], errors="coerce").fillna(0).sum()),
        })
        for prefix in ("rssi", "snr"):
            stats = _combine_metric(group, prefix)
            for name, value in stats.items():
                row[f"{prefix}_{name}"] = value
        pair = _combine_pair(group)
        row.update(pair)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(list(PHY_KEYS)).reset_index(drop=True)


def _aggregate_cells(cells: pd.DataFrame, group_keys: Iterable[str]) -> pd.DataFrame:
    group_keys = list(group_keys)
    rows: list[dict[str, Any]] = []
    for key, group in cells.groupby(group_keys, sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = {name: value for name, value in zip(group_keys, key_tuple)}
        row["gateway_day_cells"] = int(len(group))
        row["reception_rows"] = int(pd.to_numeric(group["reception_rows"], errors="coerce").fillna(0).sum())
        for prefix in ("rssi", "snr"):
            stats = _combine_metric(group, prefix)
            row[f"{prefix}_observations"] = stats["observations"]
            row[f"{prefix}_mean"] = stats["mean"]
            row[f"{prefix}_std_population"] = stats["std_population"]
        row.update(_combine_pair(group))
        rows.append(row)
    return pd.DataFrame(rows)


def build_daily_phy_summary(cells: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_cells(cells, ["source_file", "source_day", *PHY_KEYS])


def build_gateway_phy_from_cells(cells: pd.DataFrame) -> pd.DataFrame:
    return _aggregate_cells(cells, ["source_gateway_id", *PHY_KEYS])


def build_day_coverage(cells: pd.DataFrame) -> pd.DataFrame:
    if cells.empty:
        return pd.DataFrame()
    rows = []
    for (source_file, source_day), group in cells.groupby(["source_file", "source_day"], sort=True, dropna=False):
        rows.append({
            "source_file": source_file,
            "source_day": source_day,
            "gateways_observed": int(group["source_gateway_id"].nunique()),
            "phy_strata_observed": int(group[list(PHY_KEYS)].drop_duplicates().shape[0]),
            "gateway_day_phy_cells": int(len(group)),
            "reception_rows": int(pd.to_numeric(group["reception_rows"], errors="coerce").fillna(0).sum()),
            "rssi_observations": int(pd.to_numeric(group["rssi_observations"], errors="coerce").fillna(0).sum()),
            "snr_observations": int(pd.to_numeric(group["snr_observations"], errors="coerce").fillna(0).sum()),
        })
    return pd.DataFrame(rows).sort_values(["source_day", "source_file"]).reset_index(drop=True)


def build_temporal_diagnostics(daily_phy: pd.DataFrame) -> pd.DataFrame:
    if daily_phy.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for key, group in daily_phy.groupby(list(PHY_KEYS), sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        base = {name: value for name, value in zip(PHY_KEYS, key_tuple)}
        work = group.copy()
        work["day"] = pd.to_datetime(work["source_day"], errors="coerce")
        work = work.dropna(subset=["day"]).sort_values("day")
        for prefix in ("rssi", "snr"):
            values = pd.to_numeric(work[f"{prefix}_mean"], errors="coerce")
            valid = work.loc[values.notna(), ["day"]].copy()
            valid["value"] = values[values.notna()].to_numpy()
            x: list[float] = []
            y: list[float] = []
            if len(valid) >= 2:
                arr = valid.reset_index(drop=True)
                for i in range(len(arr) - 1):
                    delta = (arr.loc[i + 1, "day"] - arr.loc[i, "day"]).days
                    if delta == 1:
                        x.append(float(arr.loc[i, "value"]))
                        y.append(float(arr.loc[i + 1, "value"]))
            lag1 = None
            if len(x) >= 5 and np.std(x, ddof=1) > 0 and np.std(y, ddof=1) > 0:
                lag1 = float(np.corrcoef(x, y)[0, 1])
            rows.append({
                **base,
                "metric": prefix,
                "days_observed": int(len(valid)),
                "consecutive_day_pairs": int(len(x)),
                "lag1_pearson_consecutive_days": lag1,
                "diagnostic_only": True,
                "iid_day_bootstrap_authorised": False,
            })
    return pd.DataFrame(rows)


def reconcile_with_stage2(
    calibration: pd.DataFrame,
    gateway_from_cells: pd.DataFrame,
    stage2_phy: pd.DataFrame,
    stage2_gateway_phy: pd.DataFrame,
    *,
    atol: float = 1e-9,
) -> dict[str, Any]:
    phy_keys = list(PHY_KEYS)
    merged = calibration.merge(stage2_phy, on=phy_keys, how="outer", indicator=True, suffixes=("_hier", "_stage2"))
    if not (merged["_merge"] == "both").all():
        raise LoEDUncertaintyError("Hierarchical PHY strata do not reconcile with Stage-2 reception PHY strata")
    checks = {
        "phy_rssi_mean_max_abs_error": float((merged["rssi_mean"] - merged["rssi_mean_dbm"]).abs().max()),
        "phy_snr_mean_max_abs_error": float((merged["snr_mean"] - merged["snr_mean_db"]).abs().max()),
        "phy_rssi_std_max_abs_error": float((merged["rssi_std_population"] - merged["rssi_std_population_db"]).abs().max()),
        "phy_snr_std_max_abs_error": float((merged["snr_std_population"] - merged["snr_std_population_db"]).abs().max()),
        "phy_rssi_count_max_abs_error": int((merged["rssi_observations_hier"] - merged["rssi_observations_stage2"]).abs().max()),
        "phy_snr_count_max_abs_error": int((merged["snr_observations_hier"] - merged["snr_observations_stage2"]).abs().max()),
    }
    if max(checks["phy_rssi_mean_max_abs_error"], checks["phy_snr_mean_max_abs_error"], checks["phy_rssi_std_max_abs_error"], checks["phy_snr_std_max_abs_error"]) > atol:
        raise LoEDUncertaintyError(f"Stage-2 PHY moment reconciliation failed: {checks}")
    if checks["phy_rssi_count_max_abs_error"] != 0 or checks["phy_snr_count_max_abs_error"] != 0:
        raise LoEDUncertaintyError(f"Stage-2 PHY count reconciliation failed: {checks}")

    gateway_keys = ["source_gateway_id", *PHY_KEYS]
    gm = gateway_from_cells.merge(stage2_gateway_phy, on=gateway_keys, how="outer", indicator=True, suffixes=("_hier", "_stage2"))
    if not (gm["_merge"] == "both").all():
        raise LoEDUncertaintyError("Hierarchical gateway-PHY strata do not reconcile with Stage-2 gateway PHY strata")
    checks.update({
        "gateway_rssi_mean_max_abs_error": float((gm["rssi_mean"] - gm["rssi_mean_dbm"]).abs().max()),
        "gateway_snr_mean_max_abs_error": float((gm["snr_mean"] - gm["snr_mean_db"]).abs().max()),
        "gateway_rssi_std_max_abs_error": float((gm["rssi_std_population"] - gm["rssi_std_population_db"]).abs().max()),
        "gateway_snr_std_max_abs_error": float((gm["snr_std_population"] - gm["snr_std_population_db"]).abs().max()),
        "gateway_rssi_count_max_abs_error": int((gm["rssi_observations_hier"] - gm["rssi_observations_stage2"]).abs().max()),
        "gateway_snr_count_max_abs_error": int((gm["snr_observations_hier"] - gm["snr_observations_stage2"]).abs().max()),
    })
    if max(checks["gateway_rssi_mean_max_abs_error"], checks["gateway_snr_mean_max_abs_error"], checks["gateway_rssi_std_max_abs_error"], checks["gateway_snr_std_max_abs_error"]) > atol:
        raise LoEDUncertaintyError(f"Stage-2 gateway moment reconciliation failed: {checks}")
    if checks["gateway_rssi_count_max_abs_error"] != 0 or checks["gateway_snr_count_max_abs_error"] != 0:
        raise LoEDUncertaintyError(f"Stage-2 gateway count reconciliation failed: {checks}")
    return checks
