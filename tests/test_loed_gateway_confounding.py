from __future__ import annotations

import pandas as pd
import pytest

from stackwise.loed_gateway_confounding import (
    build_campaign_gateway_set_summary,
    build_composition_sensitivity,
    build_gateway_campaign_phy_summary,
    build_shared_gateway_campaign_shifts,
    build_shared_gateway_equal_weight_shift,
    build_shared_gateway_reception_weighted_shift,
    build_within_campaign_gateway_heterogeneity,
    get_shared_gateways,
    summarise_gateway_confounding,
)


def _campaign_days() -> pd.DataFrame:
    return pd.DataFrame({
        "source_day": ["2020-01-01", "2020-01-02", "2021-01-01", "2021-01-02"],
        "campaign_id": ["campaign_1", "campaign_1", "campaign_2", "campaign_2"],
    })


def _cells() -> pd.DataFrame:
    rows = []
    setup = {
        "2020-01-01": {"g1": -100.0, "g2": -90.0},
        "2020-01-02": {"g1": -98.0, "g2": -88.0},
        "2021-01-01": {"g1": -95.0, "g3": -70.0},
        "2021-01-02": {"g1": -93.0, "g3": -68.0},
    }
    for day, gateways in setup.items():
        for gateway, rssi in gateways.items():
            n = 10
            snr = (rssi + 100.0) / 5.0
            rows.append({
                "source_file": day + ".csv",
                "source_day": day,
                "source_gateway_id": gateway,
                "source_spreading_factor": 7,
                "source_frequency_hz": 868100000,
                "source_bandwidth_khz": 125.0,
                "reception_rows": n,
                "rssi_observations": n,
                "rssi_sum": n * rssi,
                "rssi_sumsq": n * (rssi**2 + 4.0),
                "snr_observations": n,
                "snr_sum": n * snr,
                "snr_sumsq": n * (snr**2 + 1.0),
                "paired_observations": n,
                "pair_rssi_sum": n * rssi,
                "pair_snr_sum": n * snr,
                "pair_rssi_sumsq": n * (rssi**2 + 4.0),
                "pair_snr_sumsq": n * (snr**2 + 1.0),
                "pair_cross_sum": n * (rssi * snr),
                "unique_non_sentinel_devices": 3,
                "unique_packet_fingerprints": 4,
            })
    return pd.DataFrame(rows)


def _full_shift() -> pd.DataFrame:
    # Overall campaigns have a large composition-driven RSSI shift because g2 is replaced by g3.
    return pd.DataFrame([
        {
            "source_spreading_factor": 7,
            "source_frequency_hz": 868100000,
            "source_bandwidth_khz": 125.0,
            "metric": "rssi",
            "delta_b_minus_a": 15.0,
            "abs_delta": 15.0,
            "delta_in_overall_sd_units": 1.5,
        },
        {
            "source_spreading_factor": 7,
            "source_frequency_hz": 868100000,
            "source_bandwidth_khz": 125.0,
            "metric": "snr",
            "delta_b_minus_a": 3.0,
            "abs_delta": 3.0,
            "delta_in_overall_sd_units": 1.0,
        },
    ])


def test_gateway_set_overlap_is_explicit_and_not_temporal_effect():
    sets = build_campaign_gateway_set_summary(_cells(), _campaign_days())
    cross = sets[sets.record_type == "cross_campaign"].iloc[0]
    assert int(cross.gateway_union) == 3
    assert int(cross.gateway_intersection) == 1
    assert float(cross.cross_campaign_gateway_jaccard) == pytest.approx(1 / 3)
    assert cross.shared_gateways == "g1"
    assert not bool(cross.campaign_shift_as_temporal_effect_authorised)
    assert get_shared_gateways(_cells(), _campaign_days()) == ["g1"]


def test_same_gateway_shift_is_separate_from_composition_shift():
    gateway_phy = build_gateway_campaign_phy_summary(_cells(), _campaign_days())
    shared = build_shared_gateway_campaign_shifts(gateway_phy, ["g1"])
    rssi = shared[shared.metric == "rssi"].iloc[0]
    assert rssi.mean_a == pytest.approx(-99.0)
    assert rssi.mean_b == pytest.approx(-94.0)
    assert rssi.delta_b_minus_a == pytest.approx(5.0)
    assert not bool(rssi.causal_temporal_effect_authorised)

    equal = build_shared_gateway_equal_weight_shift(shared, 1)
    weighted = build_shared_gateway_reception_weighted_shift(_cells(), _campaign_days(), ["g1"])
    sensitivity = build_composition_sensitivity(_full_shift(), equal, weighted)
    sr = sensitivity[sensitivity.metric == "rssi"].iloc[0]
    assert sr.full_campaign_delta_b_minus_a == pytest.approx(15.0)
    assert sr.equal_gateway_delta_b_minus_a == pytest.approx(5.0)
    assert sr.full_minus_equal_gateway_delta == pytest.approx(10.0)
    assert not bool(sr.causal_attribution_authorised)


def test_gateway_heterogeneity_is_descriptive_and_summary_keeps_bootstrap_blocked():
    gateway_phy = build_gateway_campaign_phy_summary(_cells(), _campaign_days())
    hetero = build_within_campaign_gateway_heterogeneity(gateway_phy)
    assert len(hetero) == 4  # two campaigns x RSSI/SNR
    assert hetero["descriptive_gateway_heterogeneity_only"].all()
    assert not hetero["gateway_random_effect_authorised"].any()

    sets = build_campaign_gateway_set_summary(_cells(), _campaign_days())
    shared = build_shared_gateway_campaign_shifts(gateway_phy, ["g1"])
    equal = build_shared_gateway_equal_weight_shift(shared, 1)
    weighted = build_shared_gateway_reception_weighted_shift(_cells(), _campaign_days(), ["g1"])
    sensitivity = build_composition_sensitivity(_full_shift(), equal, weighted)
    summary = summarise_gateway_confounding(sets, shared, sensitivity, hetero)
    assert summary["shared_gateway_count"] == 1
    assert summary["gateway_union"] == 3
    assert summary["cross_campaign_gateway_jaccard"] == pytest.approx(1 / 3)
    assert not summary["campaign_shift_as_pure_temporal_effect_authorised"]
    assert not summary["campaign_stratified_block_bootstrap_authorised"]
    assert not summary["publication_mcda_authorised"]


def test_stage3e_script_imports_run_manifest_from_provenance():
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "audit_loed_gateway_composition.py"
    spec = importlib.util.spec_from_file_location("audit_loed_gateway_composition_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.write_run_manifest.__module__ == "stackwise.provenance"


def test_stage3e_manifest_helper_matches_provenance_api(tmp_path):
    import importlib.util
    import json
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "audit_loed_gateway_composition.py"
    spec = importlib.util.spec_from_file_location("audit_loed_gateway_composition_manifest_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("input", encoding="utf-8")
    output_path.write_text("output", encoding="utf-8")
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    manifest_path = module.write_stage3e_manifest(
        results_dir=results_dir,
        inputs=[input_path],
        outputs=[output_path],
        stage3d={
            "campaign_source_days": {"campaign_1": 57, "campaign_2": 131},
            "campaign_gap_threshold_days": 30,
        },
    )
    assert manifest_path == results_dir / "run_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["command"] == "python scripts/audit_loed_gateway_composition.py"
    assert payload["parameters"]["campaigns"] == 2
    assert payload["parameters"]["campaign_source_days"] == {"campaign_1": 57, "campaign_2": 131}
