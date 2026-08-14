"""Prototype/smoke modelling helpers. Not authorised for publication analysis before Stage-2/3 evidence validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .io import dump_json


@dataclass
class FittedEnergyModel:
    result: Any
    formula: str
    model_type: str
    rows_used: int

    def summary_text(self) -> str:
        return self.result.summary().as_text()


def prepare_energy_frame(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["energy_j"] = pd.to_numeric(data.get("energy_j"), errors="coerce")
    data = data[data["energy_j"] > 0].copy()
    data["log_energy"] = np.log(data["energy_j"])
    payload = pd.to_numeric(data.get("payload_bytes"), errors="coerce")
    data["log_payload"] = np.log(payload.clip(lower=1).fillna(payload.median() if payload.notna().any() else 1))
    data["fresh"] = data.get("session_policy", pd.Series(index=data.index, dtype=object)).eq("fresh").astype(int)
    data["confirmed"] = data.get("confirmation_mode", pd.Series(index=data.index, dtype=object)).isin(["confirmed", "application_ack"]).astype(int)
    coverage = None
    for candidate in ["sinr_db", "snr_db", "rsrp_dbm", "rssi_dbm"]:
        if candidate in data and data[candidate].notna().sum() >= 5:
            coverage = pd.to_numeric(data[candidate], errors="coerce")
            break
    data["coverage_indicator"] = coverage if coverage is not None else 0.0
    if coverage is not None:
        data["coverage_indicator"] = data["coverage_indicator"].fillna(data["coverage_indicator"].median())
    data["technology"] = data["technology"].astype(str)
    data["study_id"] = data.get("study_id", data.get("dataset_id", "unknown")).astype(str)
    return data


def fit_energy_model(frame: pd.DataFrame) -> FittedEnergyModel:
    data = prepare_energy_frame(frame)
    if len(data) < 8:
        raise ValueError("At least 8 positive energy observations are required")
    formula = "log_energy ~ log_payload + fresh + confirmed + coverage_indicator + C(technology)"
    if data["study_id"].nunique() >= 2 and len(data) >= 20:
        try:
            model = smf.mixedlm(formula, data, groups=data["study_id"])
            result = model.fit(reml=False, method="lbfgs", maxiter=500)
            return FittedEnergyModel(result, formula, "mixedlm", len(data))
        except Exception:
            pass
    result = smf.ols(formula, data).fit(cov_type="HC3")
    return FittedEnergyModel(result, formula, "ols_hc3", len(data))


def save_energy_model(model: FittedEnergyModel, output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "energy_model_summary.txt"
    summary_path.write_text(model.summary_text(), encoding="utf-8")
    coefficients = pd.DataFrame({
        "term": model.result.params.index,
        "estimate": model.result.params.values,
        "std_error": model.result.bse.values,
        "p_value": model.result.pvalues.values,
    })
    coefficients_path = output / "energy_model_coefficients.csv"
    coefficients.to_csv(coefficients_path, index=False)
    metadata_path = dump_json({
        "formula": model.formula,
        "model_type": model.model_type,
        "rows_used": model.rows_used,
    }, output / "energy_model_metadata.json")
    return {"summary": summary_path, "coefficients": coefficients_path, "metadata": metadata_path}
