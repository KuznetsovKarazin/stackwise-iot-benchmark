from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml


def normalise_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().casefold()).strip("_")


def load_aliases(path: str | Path = "datasets/mappings/column_aliases.yml") -> dict[str, list[str]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return {key: [normalise_name(v) for v in values] for key, values in raw.items()}


def find_column(columns: Iterable[str], canonical: str, aliases: dict[str, list[str]]) -> str | None:
    normal_to_original = {normalise_name(c): c for c in columns}
    candidates = [normalise_name(canonical)] + aliases.get(canonical, [])
    for candidate in candidates:
        if candidate in normal_to_original:
            return normal_to_original[candidate]
    return None


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def integrate_trace(
    time_s: pd.Series,
    *,
    current_a: pd.Series | None = None,
    power_w: pd.Series | None = None,
    voltage_v: pd.Series | float | None = None,
) -> dict[str, float | int | None]:
    t = numeric(time_s).to_numpy(dtype=float)
    order = np.argsort(t)
    t = t[order]
    valid_t = np.isfinite(t)
    t = t[valid_t]
    if len(t) < 2:
        return {"duration_s": None, "sample_count": len(t), "energy_j": None}

    result: dict[str, float | int | None] = {
        "duration_s": float(t[-1] - t[0]),
        "sample_count": int(len(t)),
        "energy_j": None,
        "mean_power_w": None,
        "peak_current_a": None,
    }
    if power_w is not None:
        p_all = numeric(power_w).to_numpy(dtype=float)[order][valid_t]
        mask = np.isfinite(t) & np.isfinite(p_all)
        if mask.sum() >= 2:
            result["energy_j"] = float(np.trapezoid(p_all[mask], t[mask]))
            result["mean_power_w"] = float(np.nanmean(p_all[mask]))
        return result

    if current_a is None:
        return result
    i_all = numeric(current_a).to_numpy(dtype=float)[order][valid_t]
    result["peak_current_a"] = float(np.nanmax(i_all)) if np.isfinite(i_all).any() else None
    if voltage_v is None:
        return result
    if np.isscalar(voltage_v):
        v_all = np.full_like(i_all, float(voltage_v))
    else:
        v_all = numeric(voltage_v).to_numpy(dtype=float)[order][valid_t]
    power = i_all * v_all
    mask = np.isfinite(t) & np.isfinite(power)
    if mask.sum() >= 2:
        result["energy_j"] = float(np.trapezoid(power[mask], t[mask]))
        result["mean_power_w"] = float(np.nanmean(power[mask]))
    return result
