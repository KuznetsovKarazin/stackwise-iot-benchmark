from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stackwise.loed_robustness import build_robustness_envelope, iter_joint_centered_draw_batches
from stackwise.loed_block_bootstrap import block_bootstrap_sensitivity


def _synthetic_daily() -> tuple[pd.DataFrame, pd.DataFrame]:
    days = pd.date_range("2020-01-01", periods=20, freq="D")
    campaign = pd.DataFrame({"source_day": days.strftime("%Y-%m-%d"), "campaign_id": "campaign_1"})
    rows = []
    for i, day in enumerate(days):
        for sf, freq, base in [(7, 867100000, -110.0), (8, 867300000, -105.0)]:
            # Make one stratum structurally missing on a few days.
            if sf == 8 and i in {3, 11, 17}:
                continue
            n = 10 + (i % 4)
            rssi = base + 0.15 * i + (sf - 7) * 0.2
            snr = -8.0 + 0.08 * i + (sf - 7) * 0.4
            rows.append({
                "source_day": day.strftime("%Y-%m-%d"),
                "source_spreading_factor": sf,
                "source_frequency_hz": freq,
                "source_bandwidth_khz": 125.0,
                "rssi_observations": n,
                "rssi_mean": rssi,
                "snr_observations": n,
                "snr_mean": snr,
            })
    return pd.DataFrame(rows), campaign


def test_joint_centered_draws_reconcile_and_preserve_covariance() -> None:
    daily, campaign = _synthetic_daily()
    design = pd.DataFrame([{
        "campaign_id": "campaign_1",
        "source_days": 20,
        "block_length_days": 3,
        "bootstrap_replicates": 250,
        "seed_stream": 123456,
    }])
    batches = list(iter_joint_centered_draw_batches(daily, campaign, design))
    assert len(batches) == 1
    batch = batches[0]
    assert len(batch.draws) == 250 * 2
    assert batch.centered_summary.shape[0] == 4  # 2 strata x RSSI/SNR
    assert batch.centered_summary["centered_mean_reconciliation_error"].abs().max() < 1e-12

    # Centering is a constant shift per stratum/metric, so covariance across joint draws is unchanged.
    d = batch.draws
    wide_raw = d.pivot(index="replicate_id", columns="source_spreading_factor", values="rssi_raw_mean")
    wide_ctr = d.pivot(index="replicate_id", columns="source_spreading_factor", values="rssi_centered_mean")
    assert np.allclose(wide_raw.cov().to_numpy(), wide_ctr.cov().to_numpy(), atol=1e-12)

    # Structural day support is retained explicitly.
    s8 = batch.centered_summary[
        (batch.centered_summary["source_spreading_factor"] == 8)
        & (batch.centered_summary["metric"] == "rssi")
    ].iloc[0]
    assert int(s8["observed_source_days"]) == 17
    assert np.isclose(float(s8["source_day_support_fraction"]), 17 / 20)



def test_stage3g_reuses_stage3f_seed_stream_exactly() -> None:
    daily, campaign = _synthetic_daily()
    stage3f, design = block_bootstrap_sensitivity(
        daily, campaign, block_lengths=[3], replicates=250, seed=778899
    )
    batch = list(iter_joint_centered_draw_batches(daily, campaign, design))[0]
    cur = batch.centered_summary
    keys = [
        "campaign_id", "source_spreading_factor", "source_frequency_hz",
        "source_bandwidth_khz", "metric", "block_length_days",
    ]
    merged = stage3f.merge(cur, on=keys, validate="one_to_one")
    assert np.allclose(merged["bootstrap_mean"], merged["raw_bootstrap_mean"], atol=1e-12)
    assert np.allclose(merged["bootstrap_bias"], merged["raw_bootstrap_bias"], atol=1e-12)
    assert np.allclose(merged["bootstrap_sd"], merged["centered_bootstrap_sd"], atol=1e-12)


def test_build_robustness_envelope_keeps_model_set_nonprobabilistic() -> None:
    rows = []
    for L, sd, lo, hi, bias in [
        (3, 0.2, -1.4, -0.6, 0.01),
        (7, 0.3, -1.6, -0.4, 0.05),
        (14, 0.4, -1.8, -0.2, 0.12),
    ]:
        rows.append({
            "campaign_id": "campaign_1",
            "source_spreading_factor": 7,
            "source_frequency_hz": 867100000,
            "source_bandwidth_khz": 125.0,
            "metric": "rssi",
            "block_length_days": L,
            "campaign_reception_weighted_mean": -1.0,
            "observed_source_days": 50,
            "source_day_support_fraction": 50 / 57,
            "centered_bootstrap_sd": sd,
            "q025": lo,
            "q975": hi,
            "raw_bootstrap_bias": bias,
        })
    out = build_robustness_envelope(pd.DataFrame(rows))
    assert len(out) == 1
    r = out.iloc[0]
    assert np.isclose(r["sd_max_to_min_ratio"], 2.0)
    assert np.isclose(r["robustness_lower"], -1.8)
    assert np.isclose(r["robustness_upper"], -0.2)
    assert bool(r["single_block_length_selected"]) is False
    assert bool(r["block_length_probability_weights_assigned"]) is False
    assert bool(r["robustness_envelope_is_probability_interval"]) is False


def test_stage3g_manifest_uses_current_provenance_api(tmp_path: Path) -> None:
    script = Path("scripts/materialize_loed_uncertainty_robustness.py")
    spec = importlib.util.spec_from_file_location("stage3g_check", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    inp = tmp_path / "input.txt"
    out = tmp_path / "output.txt"
    inp.write_text("in", encoding="utf-8")
    out.write_text("out", encoding="utf-8")
    results = tmp_path / "results"
    results.mkdir()
    manifest = module.write_stage3g_manifest(
        results_dir=results,
        inputs=[inp],
        outputs=[out],
        parameters={"block_length_model_set_days": [3, 7, 14]},
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["command"] == "python scripts/materialize_loed_uncertainty_robustness.py"
