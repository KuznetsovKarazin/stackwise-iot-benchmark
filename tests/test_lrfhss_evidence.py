from __future__ import annotations

import math

import pandas as pd
import pytest

from stackwise.evidence import CompatibilityLevel, assess_compatibility, validate_evidence_record
from stackwise.lrfhss_evidence import (
    EXPECTED_CONFIRMATION,
    EXPECTED_DRS,
    LRFHSSMaterialisationError,
    build_lrfhss_stage2,
)


def _synthetic_frame() -> pd.DataFrame:
    rows = []
    for mode in EXPECTED_CONFIRMATION:
        for dr in EXPECTED_DRS:
            bit_rate = 162 if dr in {8, 10} else 325
            coding_rate = "1/3" if dr in {8, 10} else "2/3"
            duration = 60.0
            baseline = 0.45e-6
            active_energy = (0.15 if bit_rate == 162 else 0.09) * (2.0 if mode == "confirmed" else 1.0)
            baseline_energy = baseline * 3.3 * duration
            energy = active_energy + baseline_energy
            rows.append(
                {
                    "dataset_id": "lorawan_lrfhss_energy_2024",
                    "study_id": "10.5281/zenodo.13838241",
                    "observation_id": f"syn:{mode}:dr{dr}",
                    "confirmation_mode": mode,
                    "source_dr_index": dr,
                    "source_coding_rate": coding_rate,
                    "source_physical_bit_rate_bps": bit_rate,
                    "payload_bytes": 4,
                    "direction": "uplink",
                    "tx_power_dbm": 14.0,
                    "duration_s": duration,
                    "sample_count": 2_929_688,
                    "voltage_v": 3.3,
                    "energy_j": energy,
                    "trace_charge_c": energy / 3.3,
                    "tx_burst_count": 1,
                    "low_current_band_abs_a": 100e-6,
                    "low_current_band_sample_count": 2_800_000,
                    "low_current_band_mean_a": baseline,
                    "device_model": "Semtech LR1121DVK1TBKS development kit",
                    "radio_module": "Semtech LR1121",
                    "firmware_version": None,
                    "evidence_grade": "A",
                    "source_license": "CC-BY-4.0",
                    "source_doi": "10.5281/zenodo.13838241",
                }
            )
    return pd.DataFrame(rows)


def test_lrfhss_stage2_materialises_8_configs_and_20_records():
    configuration, records, derivation, contrasts, summary = build_lrfhss_stage2(_synthetic_frame())
    assert len(configuration) == 8
    assert len(records) == 20
    assert len(derivation) == 8
    assert len(contrasts) == 4
    assert summary["full_capture_evidence_records"] == 8
    assert summary["incremental_transaction_evidence_records"] == 8
    assert summary["ack_rx_contrast_evidence_records"] == 4
    assert summary["n_independent_units_per_configuration"] == 1
    assert summary["tx_burst_count_values"] == [1]
    assert summary["measurement_hardware"] == "Keysight N6705A DC Power Analyzer"
    assert summary["acquisition_software"] == "Keysight 14585A Control and Analysis Software"
    assert set(configuration["measurement_instrument"]) == {"Keysight N6705A DC Power Analyzer"}
    assert set(configuration["acquisition_software"]) == {"Keysight 14585A Control and Analysis Software"}
    assert all(record["measurement_instrument"] == "Keysight N6705A DC Power Analyzer" for record in records)
    assert all(record["acquisition_software"] == "Keysight 14585A Control and Analysis Software" for record in records)
    assert all(not validate_evidence_record(record) for record in records)


def test_lrfhss_transaction_subtracts_trace_baseline_not_an_independent_replication():
    _, records, derivation, _, _ = build_lrfhss_stage2(_synthetic_frame())
    tx = [r for r in records if r["metric_id"] == "radio_incremental_transaction_energy_j"]
    assert len(tx) == 8
    assert all(r["n_independent_units"] == 1 for r in tx)
    assert all(r["uncertainty_basis"] == "single_independent_unit" for r in tx)
    assert all(len(r["parent_evidence_ids"]) == 1 for r in tx)
    assert all("low-current baseline" in r["value_semantics"] for r in tx)
    assert derivation["baseline_fraction_pct_of_full_capture"].between(0, 0.2).all()


def test_lrfhss_ack_contrasts_are_descriptive_single_contrasts():
    _, records, _, contrasts, _ = build_lrfhss_stage2(_synthetic_frame())
    overhead = [r for r in records if r["metric_id"] == "radio_ack_rx_overhead_energy_j"]
    assert len(overhead) == 4
    assert all(r["intended_use"] == "descriptive" for r in overhead)
    assert all(r["n_independent_units"] == 1 for r in overhead)
    assert all(len(r["parent_evidence_ids"]) == 2 for r in overhead)
    assert not contrasts["population_ack_overhead_estimate_authorised"].any()
    assert all(math.isclose(v, 100.0, rel_tol=1e-12) for v in contrasts["overhead_pct_vs_unconfirmed"])


def test_lrfhss_full_capture_and_transaction_are_bridgeable_not_direct():
    _, records, _, _, _ = build_lrfhss_stage2(_synthetic_frame())
    full = next(r for r in records if r["metric_id"] == "radio_full_capture_energy_j" and r["confirmation_mode"] == "unconfirmed" and r["data_rate_mode"] == "DR8")
    tx = next(r for r in records if r["metric_id"] == "radio_incremental_transaction_energy_j" and r["confirmation_mode"] == "unconfirmed" and r["data_rate_mode"] == "DR8")
    assessment = assess_compatibility(full, tx)
    assert assessment.level is CompatibilityLevel.BRIDGEABLE


def test_lrfhss_confirmation_modes_are_directly_comparable_only_when_confirmation_is_explicit_factor():
    _, records, _, _, _ = build_lrfhss_stage2(_synthetic_frame())
    noack = next(r for r in records if r["metric_id"] == "radio_incremental_transaction_energy_j" and r["confirmation_mode"] == "unconfirmed" and r["data_rate_mode"] == "DR8")
    ack = next(r for r in records if r["metric_id"] == "radio_incremental_transaction_energy_j" and r["confirmation_mode"] == "confirmed" and r["data_rate_mode"] == "DR8")
    conditional = assess_compatibility(noack, ack)
    assert conditional.level is CompatibilityLevel.CONDITIONAL
    direct = assess_compatibility(noack, ack, allowed_vary={"confirmation_mode", "ack_rx_accounting"})
    # ack_rx_accounting is a boundary field and is intentionally not relaxed by allowed_vary.
    assert direct.level is not CompatibilityLevel.DIRECT


def test_lrfhss_rejects_more_than_one_tx_burst_for_transaction_derivation():
    frame = _synthetic_frame()
    frame.loc[0, "tx_burst_count"] = 2
    with pytest.raises(LRFHSSMaterialisationError, match="exactly one TX burst"):
        build_lrfhss_stage2(frame)
