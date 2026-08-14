from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

DATASET_ID = "lorawan_lrfhss_energy_2024"
OBSERVATIONS = Path(f"data/processed/{DATASET_ID}/observations.parquet")
REFERENCE = Path("datasets/reference/lrfhss_measurement_reference.yml")
OUTPUT = Path("results/validation/lrfhss")


def pct_error(value: float | None, reference: float) -> float | None:
    if value is None or not np.isfinite(value):
        return None
    return 100.0 * (float(value) - reference) / reference


def main() -> None:
    if not OBSERVATIONS.exists():
        raise FileNotFoundError(f"Missing harmonised observations: {OBSERVATIONS}")
    ref = yaml.safe_load(REFERENCE.read_text(encoding="utf-8"))
    df = pd.read_parquet(OBSERVATIONS).copy()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    expected = {(m, dr) for m in ("confirmed", "unconfirmed") for dr in (8, 9, 10, 11)}
    actual = set(zip(df["confirmation_mode"], df["source_dr_index"].astype(int)))
    structural_errors: list[str] = []
    if len(df) != int(ref["expected_configurations"]):
        structural_errors.append(f"expected 8 configurations, found {len(df)}")
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        structural_errors.append(f"missing configurations: {missing}")
    if extra:
        structural_errors.append(f"unexpected configurations: {extra}")
    if df["observation_id"].duplicated().any():
        structural_errors.append("duplicate observation IDs")

    expected_sample = float(ref["sampling_period_s"])
    expected_voltage = float(ref["radio_supply_voltage_v"])
    expected_payload = int(ref["frm_payload_bytes"])
    expected_tx_power = float(ref["tx_power_dbm"])

    checks = df[[
        "observation_id", "confirmation_mode", "source_dr_index", "duration_s",
        "sample_count", "voltage_v", "payload_bytes", "tx_power_dbm",
        "inferred_sampling_period_s", "current_a", "mean_power_w", "energy_j",
        "peak_current_a", "negative_current_fraction", "tx_burst_count",
        "tx_plateau_sample_count", "tx_plateau_mean_current_a",
        "low_current_band_sample_count", "low_current_band_mean_a",
    ]].copy()
    checks["sampling_period_error_pct"] = 100.0 * (
        checks["inferred_sampling_period_s"] - expected_sample
    ) / expected_sample
    tx_ref = float(ref["reference_state_currents"]["unconfirmed_dr8_tx_a"])
    checks["tx_plateau_error_vs_25p7mA_pct"] = checks["tx_plateau_mean_current_a"].apply(
        lambda value: pct_error(value, tx_ref)
    )
    checks.to_csv(OUTPUT / "trace_validation.csv", index=False)

    for column, expected_value, label in [
        ("voltage_v", expected_voltage, "voltage"),
        ("payload_bytes", expected_payload, "payload"),
        ("tx_power_dbm", expected_tx_power, "TX power"),
    ]:
        values = pd.to_numeric(df[column], errors="coerce")
        if not np.allclose(values, expected_value, rtol=0, atol=1e-12, equal_nan=False):
            structural_errors.append(f"{label} does not match expected source metadata value {expected_value}")

    sampling_abs = checks["sampling_period_error_pct"].abs()
    if sampling_abs.max() > 1.0:
        structural_errors.append(
            f"sampling-period error exceeds 1% (max={sampling_abs.max():.6g}%)"
        )

    dr8 = checks[
        (checks["confirmation_mode"] == "unconfirmed")
        & (checks["source_dr_index"].astype(int) == 8)
    ]
    dr8_tx = None
    dr8_sleep = None
    if len(dr8) == 1:
        dr8_tx = float(dr8.iloc[0]["tx_plateau_mean_current_a"]) if pd.notna(dr8.iloc[0]["tx_plateau_mean_current_a"]) else None
        dr8_sleep = float(dr8.iloc[0]["low_current_band_mean_a"]) if pd.notna(dr8.iloc[0]["low_current_band_mean_a"]) else None
    else:
        structural_errors.append("could not isolate exactly one unconfirmed DR8 trace")

    valid_tx = pd.to_numeric(checks["tx_plateau_mean_current_a"], errors="coerce").dropna()
    tx_mape = float((100.0 * (valid_tx - tx_ref).abs() / tx_ref).mean()) if len(valid_tx) else None

    summary = {
        "configurations": int(len(df)),
        "structural_checks_passed": not structural_errors,
        "structural_errors": structural_errors,
        "sampling_period_s_min": float(checks["inferred_sampling_period_s"].min()),
        "sampling_period_s_max": float(checks["inferred_sampling_period_s"].max()),
        "trace_duration_s_min": float(checks["duration_s"].min()),
        "trace_duration_s_max": float(checks["duration_s"].max()),
        "radio_supply_voltage_v": expected_voltage,
        "full_trace_energy_j_min": float(checks["energy_j"].min()),
        "full_trace_energy_j_max": float(checks["energy_j"].max()),
        "tx_burst_count_values": sorted({int(x) for x in checks["tx_burst_count"].dropna()}),
        "tx_plateau_current_a_mean_all_traces": float(valid_tx.mean()) if len(valid_tx) else None,
        "tx_plateau_current_mape_pct_vs_publication_25p7mA": tx_mape,
        "unconfirmed_dr8_tx_plateau_current_a": dr8_tx,
        "unconfirmed_dr8_tx_error_pct_vs_publication_25p7mA": pct_error(dr8_tx, tx_ref),
        "unconfirmed_dr8_low_current_band_mean_a": dr8_sleep,
        "unconfirmed_dr8_low_current_error_pct_vs_publication_0p5uA": pct_error(
            dr8_sleep, float(ref["reference_state_currents"]["sleep_a"])
        ),
        "interpretation": (
            "Structural checks validate source parsing and measurement scale. TX-plateau and low-current-band "
            "comparisons are diagnostics against publication state-current values; they do not redefine raw data. "
            "energy_j is full-capture energy, not automatically per-message energy."
        ),
        "reference_source": "Sanchez-Vital et al., Sensors 2024, DOI 10.3390/s24175770",
    }
    (OUTPUT / "trace_validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2))
    if structural_errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
