from __future__ import annotations

import pandas as pd
import pytest

from stackwise.loed_temporal import (
    assign_temporal_campaigns,
    build_acf_lag_summary,
    build_campaign_acf_diagnostics,
    build_campaign_phy_summary,
    build_campaign_series_diagnostics,
    build_campaign_shift_diagnostics,
    build_campaign_summary,
    build_gateway_campaign_coverage,
    build_gateway_set_transitions,
)
from stackwise.loed_uncertainty import build_hierarchical_calibration


def _coverage() -> pd.DataFrame:
    days = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-03-15", "2020-03-16", "2020-03-17"]
    return pd.DataFrame({
        "source_file": [d.replace("-", "_") + ".csv" for d in days],
        "source_day": days,
        "gateways_observed": [2, 2, 1, 2, 2, 2],
        "phy_strata_observed": [1] * 6,
        "gateway_day_phy_cells": [2, 2, 1, 2, 2, 2],
        "reception_rows": [20, 20, 10, 20, 20, 20],
        "rssi_observations": [20, 20, 10, 20, 20, 20],
        "snr_observations": [20, 20, 10, 20, 20, 20],
    })


def _cells() -> pd.DataFrame:
    rows = []
    days = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-03-15", "2020-03-16", "2020-03-17"]
    for di, day in enumerate(days):
        gateways = ["g1", "g2"] if di != 2 else ["g1"]
        for gi, gateway in enumerate(gateways):
            n = 10
            rssi_mean = -100.0 + di + gi
            snr_mean = -5.0 + 0.5 * di + gi
            rows.append({
                "source_file": day.replace("-", "_") + ".csv",
                "source_day": day,
                "source_gateway_id": gateway,
                "source_spreading_factor": 7,
                "source_frequency_hz": 868100000,
                "source_bandwidth_khz": 125.0,
                "reception_rows": n,
                "rssi_observations": n,
                "rssi_sum": n * rssi_mean,
                "rssi_sumsq": n * (rssi_mean**2 + 4.0),
                "snr_observations": n,
                "snr_sum": n * snr_mean,
                "snr_sumsq": n * (snr_mean**2 + 1.0),
                "paired_observations": n,
                "pair_rssi_sum": n * rssi_mean,
                "pair_snr_sum": n * snr_mean,
                "pair_rssi_sumsq": n * (rssi_mean**2 + 4.0),
                "pair_snr_sumsq": n * (snr_mean**2 + 1.0),
                "pair_cross_sum": n * (rssi_mean * snr_mean + 1.0),
                "unique_non_sentinel_devices": 3,
                "unique_packet_fingerprints": 4,
            })
    return pd.DataFrame(rows)


def _daily_phy(cells: pd.DataFrame) -> pd.DataFrame:
    # Minimal daily-PHY artifact required by the temporal audit.
    rows = []
    for day, group in cells.groupby("source_day", sort=True):
        rn = group["rssi_observations"].sum()
        sn = group["snr_observations"].sum()
        rows.append({
            "source_file": group.iloc[0]["source_file"],
            "source_day": day,
            "source_spreading_factor": 7,
            "source_frequency_hz": 868100000,
            "source_bandwidth_khz": 125.0,
            "rssi_observations": rn,
            "rssi_mean": group["rssi_sum"].sum() / rn,
            "snr_observations": sn,
            "snr_mean": group["snr_sum"].sum() / sn,
        })
    return pd.DataFrame(rows)


def test_campaign_assignment_preserves_large_gap():
    assigned = assign_temporal_campaigns(_coverage(), campaign_gap_days=30)
    assert assigned["campaign_id"].tolist() == ["campaign_1"] * 3 + ["campaign_2"] * 3
    summary = build_campaign_summary(assigned)
    assert summary["source_days"].tolist() == [3, 3]
    assert int(summary.iloc[1]["gap_from_previous_observation_days"]) == 72


def test_gateway_coverage_and_transitions_preserve_day_clusters():
    assigned = assign_temporal_campaigns(_coverage(), campaign_gap_days=30)
    gateway = build_gateway_campaign_coverage(_cells(), assigned)
    g1 = gateway[(gateway.campaign_id == "campaign_1") & (gateway.source_gateway_id == "g1")].iloc[0]
    g2 = gateway[(gateway.campaign_id == "campaign_1") & (gateway.source_gateway_id == "g2")].iloc[0]
    assert g1.days_observed == 3
    assert g2.days_observed == 2
    transitions = build_gateway_set_transitions(_cells(), assigned)
    assert len(transitions) == 4
    assert transitions["gateway_set_jaccard"].min() == pytest.approx(0.5)
    assert not transitions["gateway_set_unchanged"].all()


def test_campaign_acf_does_not_bridge_campaign_gap():
    assigned = assign_temporal_campaigns(_coverage(), campaign_gap_days=30)
    daily = _daily_phy(_cells())
    acf = build_campaign_acf_diagnostics(daily, assigned, max_lag=2)
    lag1 = acf[acf.lag_days == 1]
    # Three days per campaign produce two lag-1 pairs, never a pair across the 72-day gap.
    assert set(lag1["raw_pairs"]) == {2}
    summary = build_acf_lag_summary(acf)
    assert set(summary["campaign_id"]) == {"campaign_1", "campaign_2"}


def test_campaign_series_diagnostics_are_campaign_local():
    assigned = assign_temporal_campaigns(_coverage(), campaign_gap_days=30)
    diag = build_campaign_series_diagnostics(_daily_phy(_cells()), assigned)
    assert len(diag) == 4  # two campaigns x RSSI/SNR
    assert set(diag.days_observed) == {3}
    assert diag["diagnostic_only"].all()


def test_campaign_phy_and_shift_are_descriptive_not_random_effect():
    cells = _cells()
    assigned = assign_temporal_campaigns(_coverage(), campaign_gap_days=30)
    campaign_phy = build_campaign_phy_summary(cells, assigned)
    overall = build_hierarchical_calibration(cells)
    shifts = build_campaign_shift_diagnostics(campaign_phy, overall)
    assert len(shifts) == 2
    assert set(shifts.metric) == {"rssi", "snr"}
    assert shifts["descriptive_domain_shift_only"].all()
    assert not shifts["campaign_random_effect_authorised"].any()
    assert shifts["delta_b_minus_a"].notna().all()
