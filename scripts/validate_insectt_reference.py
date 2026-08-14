from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROCESSED = Path("data/processed/insectt_wsn_power_2023/observations.parquet")
REFERENCE = Path("datasets/reference/insectt_table1_power_uw.csv")
OUTPUT = Path("results/validation/insectt")


def main() -> None:
    if not PROCESSED.exists():
        raise FileNotFoundError(f"Missing harmonised dataset: {PROCESSED}")

    observed = pd.read_parquet(PROCESSED).copy()
    reference = pd.read_csv(REFERENCE)

    required = {"technology", "source_update_period_ms", "mean_current_ua"}
    missing = sorted(required - set(observed.columns))
    if missing:
        raise ValueError(f"Processed InSecTT dataset is missing columns: {missing}")

    observed = observed.rename(columns={"source_update_period_ms": "reporting_interval_ms"})
    keep = [
        "technology",
        "reporting_interval_ms",
        "payload_bytes",
        "mean_current_ua",
        "std_current_ua",
        "sample_count",
        "duration_s",
        "charge_c",
    ]
    merged = reference.merge(observed[keep], on=["technology", "reporting_interval_ms"], how="left", suffixes=("_reference", "_observed"))

    if merged["mean_current_ua"].isna().any():
        missing_rows = merged.loc[merged["mean_current_ua"].isna(), ["technology", "reporting_interval_ms"]]
        raise ValueError("Missing harmonised configurations:\n" + missing_rows.to_string(index=False))

    merged["implied_voltage_v"] = merged["reference_mean_power_uw"] / merged["mean_current_ua"]
    inferred_voltage_v = float(merged["implied_voltage_v"].median())
    merged["predicted_power_uw_from_current"] = merged["mean_current_ua"] * inferred_voltage_v
    merged["absolute_error_uw"] = merged["predicted_power_uw_from_current"] - merged["reference_mean_power_uw"]
    merged["relative_error_pct"] = 100.0 * merged["absolute_error_uw"] / merged["reference_mean_power_uw"]

    rmse_uw = float(np.sqrt(np.mean(np.square(merged["absolute_error_uw"]))))
    mape_pct = float(np.mean(np.abs(merged["relative_error_pct"])))
    voltage_median = inferred_voltage_v
    voltage_min = float(merged["implied_voltage_v"].min())
    voltage_max = float(merged["implied_voltage_v"].max())
    voltage_cv_pct = float(100.0 * merged["implied_voltage_v"].std(ddof=1) / merged["implied_voltage_v"].mean())

    OUTPUT.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT / "table1_scale_validation.csv", index=False)

    summary = {
        "configurations": int(len(merged)),
        "inferred_source_voltage_v_median": voltage_median,
        "implied_voltage_v_min": voltage_min,
        "implied_voltage_v_max": voltage_max,
        "implied_voltage_cv_pct": voltage_cv_pct,
        "power_rmse_uw_using_median_voltage": rmse_uw,
        "power_mape_pct_using_median_voltage": mape_pct,
        "interpretation": (
            "A tightly clustered implied voltage supports the source timestamp/current units and a constant PPK II source voltage. "
            "The inferred voltage is a validation result, not raw metadata, and is not written back into the harmonised observations."
        ),
        "reference_source": "Hörmann, Karoliny, Peterseil, Table 1, DOI 10.1007/978-3-031-54049-3_14",
    }
    (OUTPUT / "table1_scale_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("InSecTT reference validation")
    print("-----------------------------")
    print(f"Configurations: {len(merged)}")
    print(f"Median implied source voltage: {voltage_median:.6f} V")
    print(f"Implied voltage range: {voltage_min:.6f} .. {voltage_max:.6f} V")
    print(f"Implied voltage CV: {voltage_cv_pct:.4f} %")
    print(f"Power RMSE using median voltage: {rmse_uw:.4f} uW")
    print(f"Power MAPE using median voltage: {mape_pct:.4f} %")
    print()
    print(merged[["technology", "reporting_interval_ms", "mean_current_ua", "reference_mean_power_uw", "implied_voltage_v", "relative_error_pct"]].to_string(index=False))
    print()
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
