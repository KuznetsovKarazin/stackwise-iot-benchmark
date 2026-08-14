from __future__ import annotations

import math

import pandas as pd

from stackwise.evidence import CompatibilityLevel, assess_compatibility, validate_evidence_record
from stackwise.loed_evidence import (
    build_evidence_records,
    build_overall_descriptive_records,
    build_summary,
    summarise_logical_frame_frame,
    summarise_reception_frame,
)


def _receptions() -> pd.DataFrame:
    return pd.DataFrame([
        {"source_gateway_id": "g1", "source_spreading_factor": 7, "source_frequency_hz": 868100000,
         "source_bandwidth_khz": 125.0, "rssi_dbm": -100.0, "snr_db": -5.0, "source_crc_valid": True},
        {"source_gateway_id": "g2", "source_spreading_factor": 7, "source_frequency_hz": 868100000,
         "source_bandwidth_khz": 125.0, "rssi_dbm": -90.0, "snr_db": -3.0, "source_crc_valid": True},
        {"source_gateway_id": "g1", "source_spreading_factor": 7, "source_frequency_hz": 868100000,
         "source_bandwidth_khz": 125.0, "rssi_dbm": -110.0, "snr_db": None, "source_crc_valid": False},
        {"source_gateway_id": "g1", "source_spreading_factor": 8, "source_frequency_hz": 867500000,
         "source_bandwidth_khz": 125.0, "rssi_dbm": -105.0, "snr_db": -8.0, "source_crc_valid": True},
        {"source_gateway_id": "g2", "source_spreading_factor": 8, "source_frequency_hz": 867500000,
         "source_bandwidth_khz": 125.0, "rssi_dbm": -95.0, "snr_db": -6.0, "source_crc_valid": False},
    ])


def _logical_frames() -> pd.DataFrame:
    return pd.DataFrame([
        {"source_spreading_factor": 7, "source_frequency_hz": 868100000, "source_bandwidth_khz": 125.0,
         "gateway_count": 1, "repeat_reception_rows": 0, "gateway_time_span_s": 0.01},
        {"source_spreading_factor": 7, "source_frequency_hz": 868100000, "source_bandwidth_khz": 125.0,
         "gateway_count": 2, "repeat_reception_rows": 1, "gateway_time_span_s": 0.02},
        {"source_spreading_factor": 8, "source_frequency_hz": 867500000, "source_bandwidth_khz": 125.0,
         "gateway_count": 1, "repeat_reception_rows": 0, "gateway_time_span_s": 2.0},
        {"source_spreading_factor": 8, "source_frequency_hz": 867500000, "source_bandwidth_khz": 125.0,
         "gateway_count": 3, "repeat_reception_rows": 2, "gateway_time_span_s": 0.5},
    ])


def test_loed_reception_summary_is_reception_conditional_and_keeps_snr_missingness():
    summary = summarise_reception_frame(_receptions())
    assert len(summary) == 2
    sf7 = summary.loc[summary["source_spreading_factor"] == 7].iloc[0]
    assert sf7["reception_rows"] == 3
    assert sf7["rssi_observations"] == 3
    assert sf7["snr_observations"] == 2
    assert math.isclose(sf7["rssi_mean_dbm"], -100.0)
    assert math.isclose(sf7["snr_mean_db"], -4.0)
    assert math.isclose(sf7["crc_valid_fraction_of_recorded_receptions"], 2 / 3)


def test_loed_logical_frame_summary_is_observation_diversity_not_pdr():
    summary = summarise_logical_frame_frame(_logical_frames())
    assert len(summary) == 2
    sf7 = summary.loc[summary["source_spreading_factor"] == 7].iloc[0]
    assert sf7["logical_frame_count"] == 2
    assert math.isclose(sf7["mean_distinct_gateway_count"], 1.5)
    assert math.isclose(sf7["multi_gateway_fraction"], 0.5)
    assert math.isclose(sf7["repeat_reception_frame_fraction"], 0.5)


def test_loed_builds_typed_records_without_independent_unit_counts_or_pdr():
    phy = summarise_reception_frame(_receptions())
    logical = summarise_logical_frame_frame(_logical_frames())
    records = build_evidence_records(phy, logical)
    diagnostics = {
        "crc_known_receptions": 5,
        "crc_valid_receptions": 3,
        "crc_invalid_receptions": 2,
        "raw_reception_rows": 5,
        "raw_reception_rows_with_complete_phy_key": 5,
        "canonical_snr_observations": 4,
        "logical_frame_rows": 4,
        "logical_frame_rows_with_complete_phy_key": 4,
        "phy_strata": 2,
        "gateway_phy_strata": 4,
        "logical_frame_phy_strata": 2,
    }
    records.extend(build_overall_descriptive_records(diagnostics, logical))
    # 2 strata x (RSSI + SNR + CRC + gateway-count + multi-gateway) + 3 corpus-level descriptive records.
    assert len(records) == 13
    assert len({r["evidence_id"] for r in records}) == 13
    assert all(r["n_independent_units"] is None for r in records)
    assert all(r["uncertainty_basis"] == "hierarchical_observational" for r in records)
    assert not any(r["metric_id"] == "delivery_probability" for r in records)
    assert all(not validate_evidence_record(r) for r in records)


def test_loed_crc_fraction_and_gateway_diversity_are_hard_incompatible_with_delivery_probability():
    phy = summarise_reception_frame(_receptions())
    logical = summarise_logical_frame_frame(_logical_frames())
    records = build_evidence_records(phy, logical)
    crc = next(r for r in records if r["metric_id"] == "gateway_crc_valid_fraction_of_receptions")
    diversity = next(r for r in records if r["metric_id"] == "logical_frame_multi_gateway_fraction")
    target = dict(crc)
    target.update({
        "evidence_id": "target-delivery",
        "metric_id": "delivery_probability",
        "metric_family": "delivery_reliability",
        "unit": "probability",
        "value_semantics": "target",
        "summary_statistic": "not_materialised",
        "estimate": None,
        "conditioning": "unconditional",
        "accounting_basis": "per_attempt",
        "payload_basis": "application_payload",
        "path_start": "device_application",
        "path_end": "application_endpoint",
        "intended_use": "target_only",
        "derivation_class": "assumption",
        "source_grade": "D",
        "validation_status": "pending",
        "uncertainty_basis": "external_prior_required",
        "payload_bytes": 1.0,
        "direction": "uplink",
    })
    assert assess_compatibility(crc, target).level is CompatibilityLevel.INCOMPATIBLE
    assert assess_compatibility(diversity, target).level is CompatibilityLevel.INCOMPATIBLE


def test_loed_summary_preserves_frozen_semantic_counts_without_inference():
    phy = summarise_reception_frame(_receptions())
    gateway_phy = summarise_reception_frame(_receptions(), group_keys=("source_gateway_id", "source_spreading_factor", "source_frequency_hz", "source_bandwidth_khz"))
    logical = summarise_logical_frame_frame(_logical_frames())
    diagnostics = {
        "raw_reception_rows": 5,
        "raw_reception_rows_with_complete_phy_key": 5,
        "canonical_snr_observations": 4,
        "crc_known_receptions": 5,
        "crc_valid_receptions": 3,
        "crc_invalid_receptions": 2,
        "logical_frame_rows": 4,
        "logical_frame_rows_with_complete_phy_key": 4,
        "phy_strata": len(phy),
        "gateway_phy_strata": len(gateway_phy),
        "logical_frame_phy_strata": len(logical),
    }
    records = build_evidence_records(phy, logical) + build_overall_descriptive_records(diagnostics, logical)
    summary = build_summary(phy, gateway_phy, logical, diagnostics, records)
    assert summary["logical_frame_clusters"] == 4
    assert summary["multi_gateway_logical_frames"] == 2
    assert math.isclose(summary["multi_gateway_logical_frame_fraction"], 0.5)
    assert summary["gateway_count_max_per_logical_frame"] == 3
    assert "No independent-unit count" in summary["independent_unit_policy"]
    assert "No absolute PDR" in summary["reliability_policy"]
