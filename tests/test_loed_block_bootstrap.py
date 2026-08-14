from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stackwise.loed_block_bootstrap import (
    _moving_block_indices,
    block_bootstrap_sensitivity,
    campaign_point_estimates,
    summarise_block_length_sensitivity,
)


def _synthetic_daily() -> tuple[pd.DataFrame, pd.DataFrame]:
    days = pd.date_range("2020-01-01", periods=12, freq="D")
    campaign = pd.DataFrame({
        "source_day": [d.date().isoformat() for d in days],
        "campaign_id": ["campaign_1"] * 6 + ["campaign_2"] * 6,
    })
    rows = []
    for i, day in enumerate(days):
        for sf in (7, 8):
            n = 10 + sf
            rows.append({
                "source_day": day.date().isoformat(),
                "source_spreading_factor": sf,
                "source_frequency_hz": 868100000,
                "source_bandwidth_khz": 125.0,
                "rssi_observations": n,
                "rssi_mean": -100 + i + 0.1 * sf,
                "snr_observations": n,
                "snr_mean": -10 + 0.5 * i + 0.05 * sf,
            })
    return pd.DataFrame(rows), campaign


def test_moving_blocks_never_wrap_campaign_endpoint() -> None:
    rng = np.random.default_rng(123)
    for _ in range(100):
        idx = _moving_block_indices(10, 4, rng)
        assert len(idx) == 10
        assert idx.min() >= 0 and idx.max() < 10
        # Inside every untrimmed four-position chunk, indices are consecutive and never 9 -> 0.
        for start in range(0, 8, 4):
            chunk = idx[start:start + 4]
            if len(chunk) == 4:
                assert np.all(np.diff(chunk) == 1)


def test_campaign_point_estimates_are_reception_weighted() -> None:
    daily, campaign = _synthetic_daily()
    out = campaign_point_estimates(daily, campaign)
    row = out[(out.campaign_id == "campaign_1") & (out.metric == "rssi") & (out.source_spreading_factor == 7)].iloc[0]
    src = daily[(daily.source_day <= "2020-01-06") & (daily.source_spreading_factor == 7)]
    expected = np.average(src.rssi_mean, weights=src.rssi_observations)
    assert np.isclose(row.campaign_reception_weighted_mean, expected)


def test_block_bootstrap_sensitivity_preserves_joint_day_design() -> None:
    daily, campaign = _synthetic_daily()
    out, design = block_bootstrap_sensitivity(
        daily, campaign, block_lengths=[2, 3], replicates=200, seed=7
    )
    assert len(out) == 2 * 2 * 2 * 2  # campaigns x lengths x strata x metrics
    assert set(out.block_length_days) == {2, 3}
    assert not out.publication_uncertainty_sampling_authorised.any()
    assert out.structural_missingness_preserved.all()
    assert len(design) == 4
    assert not design.final_block_length_selected.any()
    assert set(design.resampler) == {"noncircular_overlapping_moving_block_source_day"}


def test_block_length_summary_has_seven_day_reference_without_selecting_it() -> None:
    daily, campaign = _synthetic_daily()
    # Use a 14-day synthetic campaign by making one campaign only.
    campaign = campaign.copy()
    campaign["campaign_id"] = "campaign_1"
    # Extend daily/campaign by two days to permit 7-day blocks robustly.
    extra_days = pd.date_range("2020-01-13", periods=2, freq="D")
    extra = []
    for i, day in enumerate(extra_days, start=12):
        campaign.loc[len(campaign)] = [day.date().isoformat(), "campaign_1"]
        for sf in (7, 8):
            n = 10 + sf
            extra.append({
                "source_day": day.date().isoformat(), "source_spreading_factor": sf,
                "source_frequency_hz": 868100000, "source_bandwidth_khz": 125.0,
                "rssi_observations": n, "rssi_mean": -100 + i + 0.1 * sf,
                "snr_observations": n, "snr_mean": -10 + 0.5 * i + 0.05 * sf,
            })
    daily = pd.concat([daily, pd.DataFrame(extra)], ignore_index=True)
    out, _ = block_bootstrap_sensitivity(daily, campaign, block_lengths=[3, 7], replicates=150, seed=9)
    summary = summarise_block_length_sensitivity(out)
    assert set(summary.block_length_days) == {3, 7}
    ref = summary[summary.block_length_days == 7]
    assert np.allclose(ref.bootstrap_sd_ratio_to_7day, 1.0)
    assert not summary.seven_day_reference_selected_as_final.any()


def test_stage3f_manifest_helper_uses_real_provenance_api(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "bootstrap_loed_campaign_sensitivity.py"
    spec = importlib.util.spec_from_file_location("stage3f_script", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    inp = tmp_path / "input.txt"
    out = tmp_path / "output.txt"
    inp.write_text("in", encoding="utf-8")
    out.write_text("out", encoding="utf-8")
    results = tmp_path / "results"
    results.mkdir()
    manifest = module.write_stage3f_manifest(
        results_dir=results,
        inputs=[inp],
        outputs=[out],
        parameters={"block_lengths": [3, 7, 14]},
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest.name == "run_manifest.json"
    assert payload["command"] == "python scripts/bootstrap_loed_campaign_sensitivity.py"
