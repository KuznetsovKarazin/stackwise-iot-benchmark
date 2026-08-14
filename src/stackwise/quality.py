from __future__ import annotations

from typing import Any

import pandas as pd


GRADE_THRESHOLDS = [(85, "A"), (65, "B"), (45, "C"), (0, "D")]


def evidence_score(record: dict[str, Any]) -> tuple[int, str]:
    """Return a source/provenance quality score, not an inferential-strength grade."""
    score = 0
    score += 30 if record.get("raw_available") else 0
    score += 15 if record.get("code_available") else 0
    score += 15 if record.get("doi") else 5 if record.get("landing_url") else 0
    score += 15 if record.get("licence", {}).get("status") == "verified" else 5
    score += 10 if record.get("measurement_boundaries") else 0
    score += 10 if len(record.get("metrics", [])) >= 2 else 5
    score += 5 if record.get("empirical") else 0
    grade = next(label for threshold, label in GRADE_THRESHOLDS if score >= threshold)
    return score, grade


def missingness_report(frame: pd.DataFrame) -> pd.DataFrame:
    total = max(len(frame), 1)
    return pd.DataFrame({
        "column": frame.columns,
        "missing_count": [int(frame[c].isna().sum()) for c in frame.columns],
        "missing_fraction": [float(frame[c].isna().sum() / total) for c in frame.columns],
        "non_null_count": [int(frame[c].notna().sum()) for c in frame.columns],
    }).sort_values(["missing_fraction", "column"], ascending=[False, True])


def comparability_flags(frame: pd.DataFrame) -> list[str]:
    flags: list[str] = []
    if "measurement_boundary" in frame and frame["measurement_boundary"].nunique(dropna=True) > 1:
        flags.append("multiple_measurement_boundaries")
    if "source_license" in frame and frame["source_license"].astype(str).str.contains("unknown", case=False).any():
        flags.append("unverified_licence_present")
    if "energy_j" in frame and frame["energy_j"].notna().any() and frame["voltage_v"].isna().all():
        flags.append("energy_without_voltage_metadata")
    if "technology" in frame and frame["technology"].isna().any():
        flags.append("missing_technology")
    return flags
