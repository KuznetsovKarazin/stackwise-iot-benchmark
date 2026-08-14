from __future__ import annotations

import pandas as pd
import pytest

from stackwise.loed_evidence import GATEWAY_PHY_KEYS, PHY_KEYS, summarise_reception_frame
from stackwise.loed_uncertainty import (
    build_daily_phy_summary,
    build_gateway_phy_from_cells,
    build_hierarchical_calibration,
    build_temporal_diagnostics,
    reconcile_with_stage2,
    summarise_gateway_day_phy,
)


def _source(day: int, shift: float = 0.0) -> pd.DataFrame:
    rows = []
    label = f"{day:02d}_01_2020.csv"
    for gateway in ["g1", "g2"]:
        for i, (rssi, snr) in enumerate([(-100.0, -5.0), (-90.0, 0.0), (-80.0, 5.0)]):
            rows.append({
                "source_file": label,
                "source_gateway_id": gateway,
                "source_spreading_factor": 7,
                "source_frequency_hz": 868100000,
                "source_bandwidth_khz": 125.0,
                "rssi_dbm": rssi + shift,
                "snr_db": snr,
                "source_crc_valid": i != 0,
                "source_device_address": str(i),
                "source_packet_fingerprint": f"p{i}",
                "timestamp_utc": f"2020-01-{day:02d}T12:00:00Z",
            })
    return pd.DataFrame(rows)


def test_gateway_day_phy_preserves_joint_moments_and_source_day():
    part = summarise_gateway_day_phy("01_01_2020.csv", _source(1))
    assert len(part) == 2
    assert set(part["source_day"]) == {"2020-01-01"}
    assert set(part["source_day_basis"]) == {"source_file_name"}
    assert set(part["reception_rows"]) == {3}
    assert set(part["paired_observations"]) == {3}
    assert all(part["paired_rssi_snr_corr"].round(12) == 1.0)
    assert set(part["unique_non_sentinel_devices"]) == {3}


def test_hierarchical_calibration_reconstructs_stage2_means_and_counts():
    raw = pd.concat([_source(1, 0.0), _source(2, 1.0)], ignore_index=True)
    cells = pd.concat([
        summarise_gateway_day_phy("01_01_2020.csv", raw[raw["source_file"] == "01_01_2020.csv"]),
        summarise_gateway_day_phy("02_01_2020.csv", raw[raw["source_file"] == "02_01_2020.csv"]),
    ], ignore_index=True)
    calibration = build_hierarchical_calibration(cells)
    gateway = build_gateway_phy_from_cells(cells)
    stage2_phy = summarise_reception_frame(raw, group_keys=PHY_KEYS)
    stage2_gateway = summarise_reception_frame(raw, group_keys=GATEWAY_PHY_KEYS)
    checks = reconcile_with_stage2(calibration, gateway, stage2_phy, stage2_gateway)
    assert checks["phy_rssi_count_max_abs_error"] == 0
    assert checks["phy_snr_count_max_abs_error"] == 0
    assert checks["phy_rssi_mean_max_abs_error"] < 1e-12
    assert checks["phy_snr_mean_max_abs_error"] < 1e-12
    row = calibration.iloc[0]
    assert row["source_days"] == 2
    assert row["gateways"] == 2
    assert row["gateway_day_cells"] == 4
    assert row["rssi_between_cell_variance_fraction"] > 0


def test_temporal_diagnostics_do_not_authorise_iid_day_bootstrap():
    parts = []
    for day in range(1, 8):
        frame = _source(day, shift=float(day))
        parts.append(summarise_gateway_day_phy(frame["source_file"].iloc[0], frame))
    cells = pd.concat(parts, ignore_index=True)
    daily = build_daily_phy_summary(cells)
    diagnostics = build_temporal_diagnostics(daily)
    assert len(diagnostics) == 2
    assert set(diagnostics["metric"]) == {"rssi", "snr"}
    assert diagnostics["iid_day_bootstrap_authorised"].eq(False).all()  # noqa: E712
    rssi = diagnostics.loc[diagnostics["metric"] == "rssi"].iloc[0]
    assert rssi["consecutive_day_pairs"] == 6
    assert rssi["lag1_pearson_consecutive_days"] == pytest.approx(1.0)
