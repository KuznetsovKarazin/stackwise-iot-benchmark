from __future__ import annotations

import math

import pandas as pd
import pytest

from stackwise.evidence import (
    CompatibilityLevel,
    assess_compatibility,
    validate_evidence_record,
    validate_shared_parameter_record,
)
from stackwise.insectt_evidence import (
    EXPECTED_PAYLOAD_BY_PERIOD_MS,
    EXPECTED_PERIOD_MS,
    EXPECTED_TECHNOLOGIES,
    InSecTTMaterialisationError,
    SHARED_VOLTAGE_PARAMETER_ID,
    build_insectt_stage2,
)


def _synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    ref = []
    base_power_uw = {"BLE": 300.0, "Thread": 700.0, "EPhESOS": 600.0, "UWB": 900.0}
    for technology in EXPECTED_TECHNOLOGIES:
        for period_ms in EXPECTED_PERIOD_MS:
            payload = EXPECTED_PAYLOAD_BY_PERIOD_MS[period_ms]
            power_uw = base_power_uw[technology] * (100.0 / period_ms) + 20.0
            mean_current_ua = power_uw / 3.3
            sample_count = 6_000_000
            duration_s = 60.0
            charge_c = mean_current_ua * 1e-6 * duration_s
            rows.append(
                {
                    "dataset_id": "insectt_wsn_power_2023",
                    "study_id": "10.5281/zenodo.7762712",
                    "observation_id": f"syn:{technology}:{period_ms}",
                    "technology": technology,
                    "access_network": technology,
                    "transport_protocol": "UDP" if technology == "Thread" else None,
                    "application_protocol": None,
                    "device_model": "Nordic nRF52840 Development Kit" if technology != "UWB" else "nRF52832 + Qorvo DW1000 board",
                    "radio_module": "Qorvo DW1000" if technology == "UWB" else "nRF52840 radio",
                    "firmware_version": "nRF Connect SDK 2.0.2" if technology in {"BLE", "Thread"} else None,
                    "payload_bytes": payload,
                    "reporting_interval_s": period_ms / 1000.0,
                    "source_update_period_ms": period_ms,
                    "sample_count": sample_count,
                    "duration_s": duration_s,
                    "mean_current_ua": mean_current_ua,
                    "current_a": mean_current_ua * 1e-6,
                    "charge_c": charge_c,
                    "evidence_grade": "A",
                    "source_license": "CC-BY-4.0",
                    "source_doi": "10.5281/zenodo.7762712",
                }
            )
            ref.append(
                {
                    "technology": technology,
                    "reporting_interval_ms": period_ms,
                    "payload_bytes": payload,
                    "reference_mean_power_uw": power_uw,
                    "source": "synthetic Table 1",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(ref)


def test_insectt_stage2_materialises_20_configurations_and_80_records():
    frame, reference = _synthetic_inputs()
    configuration, records, parameters, validation, summary = build_insectt_stage2(frame, reference)

    assert len(configuration) == 20
    assert len(records) == 80
    assert len(parameters) == 1
    assert len(validation) == 20
    assert summary["direct_empirical_records"] == 40
    assert summary["validated_derived_records"] == 40
    assert summary["n_independent_units_per_configuration"] == 1
    assert math.isclose(summary["inferred_source_voltage_v_median"], 3.3, rel_tol=1e-12)
    assert summary["power_mape_pct_using_median_voltage"] < 1e-10

    assert all(not validate_evidence_record(record) for record in records)
    assert not validate_shared_parameter_record(parameters[0])


def test_insectt_no_sample_level_pseudoreplication_and_shared_voltage_lineage():
    frame, reference = _synthetic_inputs()
    _, records, parameters, _, _ = build_insectt_stage2(frame, reference)

    direct = [r for r in records if r["derivation_class"] == "direct_empirical"]
    derived = [r for r in records if r["derivation_class"] == "validated_derived"]
    assert len(direct) == 40
    assert len(derived) == 40
    assert all(r["n_independent_units"] == 1 for r in records)
    assert all(r["n_source_observations"] == 6_000_000 for r in records)
    assert all(r["uncertainty_basis"] == "single_independent_unit" for r in direct)
    assert all(r["uncertainty_basis"] == "shared_parameter" for r in derived)
    assert all(r["shared_parameter_ids"] == [SHARED_VOLTAGE_PARAMETER_ID] for r in derived)
    assert all(r["shared_parameter_ids"] == [] for r in direct)
    assert parameters[0]["uncertainty_model_status"] == "pending_stage3"
    assert "not 20 independent" in parameters[0]["statistical_interpretation"]


def test_insectt_derived_records_link_to_matching_direct_parent():
    frame, reference = _synthetic_inputs()
    _, records, _, _, _ = build_insectt_stage2(frame, reference)
    by_id = {r["evidence_id"]: r for r in records}
    for record in records:
        if record["metric_id"] == "derived_mean_power_w":
            assert len(record["parent_evidence_ids"]) == 1
            assert by_id[record["parent_evidence_ids"][0]]["metric_id"] == "trace_mean_current_a"
        if record["metric_id"] == "derived_capture_energy_j":
            assert len(record["parent_evidence_ids"]) == 1
            assert by_id[record["parent_evidence_ids"][0]]["metric_id"] == "trace_charge_c"


def test_insectt_preserves_implementation_context_and_blocks_naive_cross_hardware_c0():
    frame, reference = _synthetic_inputs()
    _, records, _, _, _ = build_insectt_stage2(frame, reference)
    ble = next(r for r in records if r["technology"] == "BLE" and r["metric_id"] == "trace_mean_current_a" and r["payload_bytes"] == 2)
    uwb = next(r for r in records if r["technology"] == "UWB" and r["metric_id"] == "trace_mean_current_a" and r["payload_bytes"] == 2)

    assert ble["device_model"] != uwb["device_model"]
    assert uwb["radio_module"] == "Qorvo DW1000"
    assert uwb["frequency_hz"] == 4.5e9
    assert uwb["bandwidth_hz"] == 499.2e6

    assessment = assess_compatibility(
        ble,
        uwb,
        allowed_vary={"technology", "access_network", "frequency_hz", "bandwidth_hz"},
    )
    assert assessment.level is CompatibilityLevel.CONDITIONAL
    assert "implementation_context_mismatch" in assessment.reasons


def test_insectt_same_measured_implementation_across_reporting_periods_is_direct_when_workload_varies_explicitly():
    frame, reference = _synthetic_inputs()
    _, records, _, _, _ = build_insectt_stage2(frame, reference)
    ble_100 = next(r for r in records if r["technology"] == "BLE" and r["metric_id"] == "trace_mean_current_a" and r["reporting_interval_s"] == 0.1)
    ble_200 = next(r for r in records if r["technology"] == "BLE" and r["metric_id"] == "trace_mean_current_a" and r["reporting_interval_s"] == 0.2)
    assessment = assess_compatibility(
        ble_100,
        ble_200,
        allowed_vary={"payload_bytes", "reporting_interval_s"},
    )
    assert assessment.level is CompatibilityLevel.DIRECT


def test_insectt_rejects_incomplete_design():
    frame, reference = _synthetic_inputs()
    with pytest.raises(InSecTTMaterialisationError, match="Expected 20"):
        build_insectt_stage2(frame.iloc[:-1].copy(), reference)
