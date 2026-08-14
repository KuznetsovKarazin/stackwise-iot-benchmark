from __future__ import annotations

import numpy as np
import pandas as pd


def summarise_observations(frame: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "energy_j", "latency_ms", "delivery_success", "rssi_dbm", "snr_db",
        "rsrp_dbm", "sinr_db", "retries", "upper_layer_bytes",
    ]
    available = [metric for metric in metrics if metric in frame and frame[metric].notna().any()]
    groups = [column for column in ["technology", "measurement_boundary", "application_protocol", "session_policy", "confirmation_mode"] if column in frame]
    rows = []
    for keys, group in frame.groupby(groups, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(groups, keys))
        row["n"] = len(group)
        for metric in available:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            if values.empty:
                continue
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_median"] = float(values.median())
            row[f"{metric}_p05"] = float(values.quantile(0.05))
            row[f"{metric}_p95"] = float(values.quantile(0.95))
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_mean(values: pd.Series, samples: int = 2000, seed: int = 26) -> dict[str, float]:
    array = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(array) == 0:
        return {"mean": np.nan, "lower": np.nan, "upper": np.nan, "n": 0}
    rng = np.random.default_rng(seed)
    estimates = np.mean(rng.choice(array, size=(samples, len(array)), replace=True), axis=1)
    return {
        "mean": float(array.mean()),
        "lower": float(np.quantile(estimates, 0.025)),
        "upper": float(np.quantile(estimates, 0.975)),
        "n": int(len(array)),
    }


def battery_life_years(
    *,
    capacity_wh: float,
    report_energy_j: float,
    reports_per_day: float,
    baseline_power_w: float = 0.0,
    annual_self_discharge_fraction: float = 0.0,
    planning_cap_years: float | None = None,
) -> tuple[float, float]:
    capacity_j = capacity_wh * 3600.0
    daily_j = report_energy_j * reports_per_day + baseline_power_w * 86400.0
    if annual_self_discharge_fraction > 0:
        daily_j += capacity_j * annual_self_discharge_fraction / 365.0
    ideal = capacity_j / daily_j / 365.0 if daily_j > 0 else np.inf
    planning = min(ideal, planning_cap_years) if planning_cap_years is not None else ideal
    return float(ideal), float(planning)
