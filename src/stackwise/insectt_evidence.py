from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd

DATASET_ID = "insectt_wsn_power_2023"
RELATED_PUBLICATION_DOI = "10.1007/978-3-031-54049-3_14"
SHARED_VOLTAGE_PARAMETER_ID = "insectt_ppk2_source_voltage_v"
EXPECTED_TECHNOLOGIES = ("BLE", "Thread", "EPhESOS", "UWB")
EXPECTED_PERIOD_MS = (100, 200, 400, 800, 1600)
EXPECTED_PAYLOAD_BY_PERIOD_MS = {100: 2, 200: 4, 400: 8, 800: 16, 1600: 32}
MEASUREMENT_INSTRUMENT = "Nordic Power Profiler Kit II (source mode)"


class InSecTTMaterialisationError(ValueError):
    pass


def _stable_id(prefix: str, *values: Any) -> str:
    serialised = "|".join("<NA>" if pd.isna(v) else str(v) for v in values)
    return f"{prefix}-{hashlib.sha1(serialised.encode('utf-8')).hexdigest()[:16]}"


def _none_if_na(value: Any) -> Any:
    return None if pd.isna(value) else value


def _implementation_context(technology: str, row: pd.Series) -> dict[str, Any]:
    if technology == "BLE":
        return {
            "implementation_context_id": "insectt_nrf52840_ble_ncs2.0.2",
            "device_model": _none_if_na(row.get("device_model")) or "Nordic nRF52840 Development Kit",
            "radio_module": _none_if_na(row.get("radio_module")) or "nRF52840 LE 1M PHY",
            "firmware_version": _none_if_na(row.get("firmware_version")) or "nRF Connect SDK 2.0.2",
            "implementation_notes": "BLE Peripheral; 45 ms connection interval; up to 40 skipped connection events; LE 1M PHY.",
            "frequency_hz": None,
            "bandwidth_hz": None,
        }
    if technology == "Thread":
        return {
            "implementation_context_id": "insectt_nrf52840_openthread_ncs2.0.2",
            "device_model": _none_if_na(row.get("device_model")) or "Nordic nRF52840 Development Kit",
            "radio_module": _none_if_na(row.get("radio_module")) or "nRF52840 IEEE 802.15.4 PHY",
            "firmware_version": _none_if_na(row.get("firmware_version")) or "nRF Connect SDK 2.0.2",
            "implementation_notes": "OpenThread Sleepy End Device; UDP messages; parent poll interval 1 s.",
            "frequency_hz": None,
            "bandwidth_hz": None,
        }
    if technology == "EPhESOS":
        return {
            "implementation_context_id": "insectt_nrf52840_ephesos_ble1m",
            "device_model": _none_if_na(row.get("device_model")) or "Nordic nRF52840 Development Kit",
            "radio_module": _none_if_na(row.get("radio_module")) or "nRF52840 LE 1M PHY",
            "firmware_version": _none_if_na(row.get("firmware_version")),
            "implementation_notes": "EPhESOS implementation using the BLE 1M PHY; exact firmware revision not stated in the dataset README.",
            "frequency_hz": None,
            "bandwidth_hz": None,
        }
    if technology == "UWB":
        return {
            "implementation_context_id": "insectt_nrf52832_dw1000_uwb",
            "device_model": _none_if_na(row.get("device_model")) or "nRF52832 + Qorvo DW1000 board",
            "radio_module": _none_if_na(row.get("radio_module")) or "Qorvo DW1000",
            "firmware_version": _none_if_na(row.get("firmware_version")),
            "implementation_notes": "Periodic UWB beacons; centre frequency 4.5 GHz; bandwidth 499.2 MHz; PRF 64 MHz; 64 preamble symbols.",
            "frequency_hz": 4.5e9,
            "bandwidth_hz": 499.2e6,
        }
    raise InSecTTMaterialisationError(f"Unexpected technology: {technology!r}")


def _validate_complete_design(frame: pd.DataFrame) -> None:
    required = {
        "dataset_id", "observation_id", "technology", "payload_bytes", "reporting_interval_s",
        "source_update_period_ms", "sample_count", "duration_s", "current_a", "mean_current_ua",
        "charge_c", "evidence_grade", "source_license", "source_doi",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise InSecTTMaterialisationError(f"Missing harmonised fields: {missing}")
    if len(frame) != 20:
        raise InSecTTMaterialisationError(f"Expected 20 InSecTT configurations, found {len(frame)}")
    if set(frame["dataset_id"].dropna().astype(str)) != {DATASET_ID}:
        raise InSecTTMaterialisationError("Input contains a dataset_id other than InSecTT")
    if frame["observation_id"].duplicated().any():
        raise InSecTTMaterialisationError("Duplicate InSecTT observation_id values detected")

    observed_design = {
        (str(row.technology), int(row.source_update_period_ms))
        for row in frame[["technology", "source_update_period_ms"]].itertuples(index=False)
    }
    expected_design = {(t, p) for t in EXPECTED_TECHNOLOGIES for p in EXPECTED_PERIOD_MS}
    if observed_design != expected_design:
        missing_design = sorted(expected_design - observed_design)
        extra_design = sorted(observed_design - expected_design)
        raise InSecTTMaterialisationError(
            f"Incomplete/extra technology-period design: missing={missing_design}, extra={extra_design}"
        )

    for row in frame.itertuples(index=False):
        period_ms = int(row.source_update_period_ms)
        expected_payload = EXPECTED_PAYLOAD_BY_PERIOD_MS[period_ms]
        if int(row.payload_bytes) != expected_payload:
            raise InSecTTMaterialisationError(
                f"Payload mismatch for {row.technology}/{period_ms}ms: {row.payload_bytes} != {expected_payload}"
            )
        if not np.isclose(float(row.reporting_interval_s), period_ms / 1000.0, rtol=0, atol=1e-12):
            raise InSecTTMaterialisationError(f"Reporting interval mismatch for {row.technology}/{period_ms}ms")
        if int(row.sample_count) <= 0 or float(row.duration_s) <= 0:
            raise InSecTTMaterialisationError(f"Non-positive trace size/duration for {row.technology}/{period_ms}ms")
        if not np.isclose(float(row.current_a), float(row.mean_current_ua) * 1e-6, rtol=1e-10, atol=1e-15):
            raise InSecTTMaterialisationError(f"Current-unit inconsistency for {row.technology}/{period_ms}ms")


def _calibrate_voltage(frame: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required_ref = {"technology", "reporting_interval_ms", "reference_mean_power_uw"}
    missing = sorted(required_ref - set(reference.columns))
    if missing:
        raise InSecTTMaterialisationError(f"Reference Table 1 is missing columns: {missing}")

    if "payload_bytes" in reference.columns:
        for ref_row in reference[["reporting_interval_ms", "payload_bytes"]].itertuples(index=False):
            period_ms = int(ref_row.reporting_interval_ms)
            if period_ms in EXPECTED_PAYLOAD_BY_PERIOD_MS and int(ref_row.payload_bytes) != EXPECTED_PAYLOAD_BY_PERIOD_MS[period_ms]:
                raise InSecTTMaterialisationError(
                    f"Reference payload mismatch for {period_ms}ms: {ref_row.payload_bytes}"
                )

    left = frame.copy()
    left["reporting_interval_ms"] = pd.to_numeric(left["source_update_period_ms"], errors="raise").astype(int)
    reference_for_merge = reference.drop(columns=["payload_bytes"], errors="ignore")
    merged = reference_for_merge.merge(
        left,
        on=["technology", "reporting_interval_ms"],
        how="left",
        validate="one_to_one",
    )
    if len(merged) != 20 or merged["mean_current_ua"].isna().any():
        raise InSecTTMaterialisationError("Reference validation did not match all 20 configurations one-to-one")

    merged["implied_voltage_v"] = (
        pd.to_numeric(merged["reference_mean_power_uw"], errors="raise")
        / pd.to_numeric(merged["mean_current_ua"], errors="raise")
    )
    voltage_v = float(merged["implied_voltage_v"].median())
    merged["derived_mean_power_w"] = pd.to_numeric(merged["current_a"], errors="raise") * voltage_v
    merged["derived_capture_energy_j"] = pd.to_numeric(merged["charge_c"], errors="raise") * voltage_v
    merged["predicted_power_uw_from_current"] = merged["derived_mean_power_w"] * 1e6
    merged["absolute_error_uw"] = merged["predicted_power_uw_from_current"] - merged["reference_mean_power_uw"]
    merged["relative_error_pct"] = 100.0 * merged["absolute_error_uw"] / merged["reference_mean_power_uw"]

    rmse_uw = float(np.sqrt(np.mean(np.square(merged["absolute_error_uw"]))))
    mape_pct = float(np.mean(np.abs(merged["relative_error_pct"])))
    voltage_cv_pct = float(100.0 * merged["implied_voltage_v"].std(ddof=1) / merged["implied_voltage_v"].mean())
    diagnostics = {
        "configurations": 20,
        "inferred_source_voltage_v_median": voltage_v,
        "implied_voltage_v_min": float(merged["implied_voltage_v"].min()),
        "implied_voltage_v_max": float(merged["implied_voltage_v"].max()),
        "implied_voltage_cv_pct": voltage_cv_pct,
        "power_rmse_uw_using_median_voltage": rmse_uw,
        "power_mape_pct_using_median_voltage": mape_pct,
    }
    return merged, diagnostics


def _shared_voltage_parameter(diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "parameter_id": SHARED_VOLTAGE_PARAMETER_ID,
        "parameter_kind": "calibration",
        "name": "InSecTT PPK II source voltage used for Stage-2 derived power/energy",
        "unit": "V",
        "estimate": float(diagnostics["inferred_source_voltage_v_median"]),
        "derivation_class": "validated_derived",
        "validation_status": "validated_with_limitations",
        "source_dois": ["10.5281/zenodo.7762712", RELATED_PUBLICATION_DOI],
        "supporting_artifacts": [
            "datasets/reference/insectt_table1_power_uw.csv",
            "results/validation/insectt_stage2_materialisation/power_scale_validation.csv",
        ],
        "shared_across_dataset_ids": [DATASET_ID],
        "n_supporting_configurations": 20,
        "uncertainty_basis": "validation_scale_check_not_replication",
        "uncertainty_model_status": "pending_stage3",
        "statistical_interpretation": (
            "The 20 implied voltages are configuration-wise scale checks against a rounded publication table, "
            "not 20 independent measurements of supply voltage. Their spread must not be converted into a "
            "standard error or confidence interval."
        ),
        "diagnostics": {
            "implied_voltage_v_min": float(diagnostics["implied_voltage_v_min"]),
            "implied_voltage_v_max": float(diagnostics["implied_voltage_v_max"]),
            "implied_voltage_cv_pct": float(diagnostics["implied_voltage_cv_pct"]),
            "power_rmse_uw_using_median_voltage": float(diagnostics["power_rmse_uw_using_median_voltage"]),
            "power_mape_pct_using_median_voltage": float(diagnostics["power_mape_pct_using_median_voltage"]),
        },
        "applicability_domain": "All 20 InSecTT technology x reporting-period traces in the validated dataset release.",
        "limitations": (
            "Voltage is inferred from published mean-power values for the same measurement campaign because the "
            "dataset README does not state the PPK II source voltage."
        ),
    }


def _metric_record(
    row: pd.Series,
    *,
    metric_id: str,
    metric_family: str,
    unit: str,
    estimate: float,
    value_semantics: str,
    temporal_scope: str,
    accounting_basis: str,
    derivation_class: str,
    parent_ids: list[str],
    shared_parameter_ids: list[str],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    technology = str(row["technology"])
    period_ms = int(row["reporting_interval_ms"])
    payload = float(row["payload_bytes"])
    derived = derivation_class == "validated_derived"
    implementation_limitation = (
        "The measured implementation is part of the estimand. UWB uses nRF52832 + DW1000, whereas BLE, Thread "
        "and EPhESOS use nRF52840; cross-technology differences are not identifiable as protocol-only effects."
    )
    voltage_limitation = (
        " Derived power/energy uses one shared voltage calibration inferred from the associated publication Table 1; "
        "its uncertainty is correlated across all derived records."
        if derived
        else ""
    )
    evidence_id = _stable_id("insectt-evidence", metric_id, technology, period_ms)
    return {
        "evidence_id": evidence_id,
        "dataset_id": DATASET_ID,
        "study_id": "insectt_wsn_power_2023_campaign",
        "source_doi": str(row["source_doi"]),
        "source_license": str(row["source_license"]),
        "source_artifact": "data/analysis_ready/insectt_wsn_power_2023/configuration_observations.parquet",
        "technology": technology,
        "access_network": technology,
        "transport_protocol": None if pd.isna(row.get("transport_protocol")) else str(row.get("transport_protocol")),
        "application_protocol": None if pd.isna(row.get("application_protocol")) else str(row.get("application_protocol")),
        "security_mode": None,
        "management_protocol": None,
        "implementation_context_id": implementation["implementation_context_id"],
        "device_model": implementation["device_model"],
        "radio_module": implementation["radio_module"],
        "firmware_version": implementation["firmware_version"],
        "measurement_instrument": MEASUREMENT_INSTRUMENT,
        "implementation_notes": implementation["implementation_notes"],
        "metric_id": metric_id,
        "metric_family": metric_family,
        "unit": unit,
        "value_semantics": value_semantics,
        "estimate": float(estimate),
        "summary_statistic": "mean" if metric_id in {"trace_mean_current_a", "derived_mean_power_w"} else "raw_measurement",
        "system_scope": "whole_device",
        "temporal_scope": temporal_scope,
        "accounting_basis": accounting_basis,
        "conditioning": "unconditional",
        "payload_basis": "source_message_size",
        "baseline_accounting": "included",
        "ack_rx_accounting": "excluded",
        "retry_accounting": "excluded",
        "path_start": "not_applicable",
        "path_end": "not_applicable",
        "payload_bytes": payload,
        "reporting_interval_s": float(row["reporting_interval_s"]),
        "direction": "uplink",
        "confirmation_mode": "unconfirmed",
        "tx_power_dbm": None,
        "environment": "laboratory",
        "phase_name": None,
        "data_rate_mode": None,
        "frequency_hz": implementation["frequency_hz"],
        "bandwidth_hz": implementation["bandwidth_hz"],
        "spreading_factor": None,
        "coding_rate": None,
        "bit_rate_bps": None,
        "operator": None,
        "empirical_unit": "one_approximately_60s_technology_reporting_period_trace",
        "independence_unit": "one_source_configuration_trace",
        "n_source_observations": int(row["sample_count"]),
        "n_independent_units": 1,
        "dependence_structure": (
            "One approximately 60 s trace per technology x reporting-period configuration. High-frequency samples "
            "within the trace are repeated measurements of the same trace, not independent experimental replicates."
            + (" All derived records share the same voltage calibration parameter." if derived else "")
        ),
        "source_grade": str(row["evidence_grade"]),
        "validation_status": "validated_with_limitations" if derived else "validated",
        "derivation_class": derivation_class,
        "parent_evidence_ids": parent_ids,
        "shared_parameter_ids": shared_parameter_ids,
        "uncertainty_basis": "shared_parameter" if derived else "single_independent_unit",
        "uncertainty_notes": (
            "No between-run variance is identifiable from this dataset. Within-trace sample dispersion must not be "
            "used as a technology-level standard error."
            + (" Stage 3 must additionally propagate the shared voltage parameter jointly." if derived else "")
        ),
        "applicability_domain": (
            f"InSecTT laboratory configuration: technology={technology}, reporting_interval={period_ms} ms, "
            f"source data size={int(payload)} bytes, no acknowledgements/retransmissions."
        ),
        "intended_use": "direct_comparison",
        "bridge_requirements": (
            "This is a complete ~60 s capture statistic, not energy/current per application report. A reporting-cycle "
            "or workload bridge is required before populating expected_device_energy_per_application_report_j."
        ),
        "limitations": implementation_limitation + voltage_limitation,
        "notes": (
            f"Source trace observation_id={row['observation_id']}; publication-scale validation uses {RELATED_PUBLICATION_DOI}."
        ),
    }


def build_insectt_stage2(
    frame: pd.DataFrame,
    reference: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    """Materialise InSecTT configuration-level Stage-2 evidence without pseudo-replication."""
    _validate_complete_design(frame)
    merged, diagnostics = _calibrate_voltage(frame, reference)

    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for _, row in merged.sort_values(["technology", "reporting_interval_ms"], kind="stable").iterrows():
        implementation = _implementation_context(str(row["technology"]), row)
        current_id = _stable_id("insectt-evidence", "trace_mean_current_a", row["technology"], int(row["reporting_interval_ms"]))
        charge_id = _stable_id("insectt-evidence", "trace_charge_c", row["technology"], int(row["reporting_interval_ms"]))

        materialised = row.to_dict()
        materialised.update(implementation)
        materialised["measurement_instrument"] = MEASUREMENT_INSTRUMENT
        materialised["analysis_voltage_v"] = float(diagnostics["inferred_source_voltage_v_median"])
        materialised["analysis_voltage_provenance"] = (
            f"validated-derived median implied voltage from publication Table 1 ({RELATED_PUBLICATION_DOI}); not raw metadata"
        )
        materialised["shared_voltage_parameter_id"] = SHARED_VOLTAGE_PARAMETER_ID
        materialised["independent_unit_count"] = 1
        materialised["independence_note"] = "One source trace per configuration; within-trace samples are not independent replicates."
        rows.append(materialised)

        records.extend(
            [
                _metric_record(
                    row,
                    metric_id="trace_mean_current_a",
                    metric_family="current",
                    unit="A",
                    estimate=float(row["current_a"]),
                    value_semantics="Time-average whole-device current over the complete approximately 60 s source capture.",
                    temporal_scope="trace_window",
                    accounting_basis="time_average",
                    derivation_class="direct_empirical",
                    parent_ids=[],
                    shared_parameter_ids=[],
                    implementation=implementation,
                ),
                _metric_record(
                    row,
                    metric_id="trace_charge_c",
                    metric_family="charge",
                    unit="C",
                    estimate=float(row["charge_c"]),
                    value_semantics="Integrated whole-device charge over the complete approximately 60 s source capture.",
                    temporal_scope="trace_window",
                    accounting_basis="per_capture",
                    derivation_class="direct_empirical",
                    parent_ids=[],
                    shared_parameter_ids=[],
                    implementation=implementation,
                ),
                _metric_record(
                    row,
                    metric_id="derived_mean_power_w",
                    metric_family="power",
                    unit="W",
                    estimate=float(row["derived_mean_power_w"]),
                    value_semantics="Mean whole-device power derived from trace mean current using the shared validated InSecTT voltage calibration.",
                    temporal_scope="trace_window",
                    accounting_basis="time_average",
                    derivation_class="validated_derived",
                    parent_ids=[current_id],
                    shared_parameter_ids=[SHARED_VOLTAGE_PARAMETER_ID],
                    implementation=implementation,
                ),
                _metric_record(
                    row,
                    metric_id="derived_capture_energy_j",
                    metric_family="energy",
                    unit="J",
                    estimate=float(row["derived_capture_energy_j"]),
                    value_semantics="Whole-device energy over the complete source capture derived from integrated charge using the shared validated InSecTT voltage calibration.",
                    temporal_scope="trace_window",
                    accounting_basis="per_capture",
                    derivation_class="validated_derived",
                    parent_ids=[charge_id],
                    shared_parameter_ids=[SHARED_VOLTAGE_PARAMETER_ID],
                    implementation=implementation,
                ),
            ]
        )

    configuration = pd.DataFrame(rows).sort_values(["technology", "reporting_interval_ms"], kind="stable").reset_index(drop=True)
    shared_parameters = [_shared_voltage_parameter(diagnostics)]
    validation = configuration[
        [
            "technology", "reporting_interval_ms", "payload_bytes", "sample_count", "duration_s",
            "mean_current_ua", "reference_mean_power_uw", "implied_voltage_v",
            "predicted_power_uw_from_current", "absolute_error_uw", "relative_error_pct",
        ]
    ].copy()

    summary = {
        "dataset_id": DATASET_ID,
        "stage": "Stage-2 InSecTT materialisation",
        "configurations": int(len(configuration)),
        "technologies": sorted(configuration["technology"].astype(str).unique().tolist()),
        "reporting_intervals_ms": sorted(int(v) for v in configuration["reporting_interval_ms"].unique()),
        "evidence_records": int(len(records)),
        "evidence_records_by_metric": {
            metric: int(sum(r["metric_id"] == metric for r in records))
            for metric in sorted({r["metric_id"] for r in records})
        },
        "direct_empirical_records": int(sum(r["derivation_class"] == "direct_empirical" for r in records)),
        "validated_derived_records": int(sum(r["derivation_class"] == "validated_derived" for r in records)),
        "shared_parameters": 1,
        "shared_voltage_parameter_id": SHARED_VOLTAGE_PARAMETER_ID,
        "n_independent_units_per_configuration": 1,
        "independence_policy": (
            "Each technology x reporting-period configuration contributes one independent approximately 60 s trace. "
            "High-frequency samples estimate that trace but do not create replicate runs."
        ),
        "implementation_context_policy": (
            "Measured hardware/firmware context is preserved. Cross-technology differences, especially UWB versus "
            "nRF52840-based configurations, are configuration-level effects rather than identified protocol-only effects."
        ),
        "voltage_policy": (
            "Canonical processed voltage/power/energy remain untouched. Stage-2 derived power/energy use one shared "
            "validated voltage parameter inferred from publication Table 1 and linked through shared_parameter_ids."
        ),
        **diagnostics,
    }
    return configuration, records, shared_parameters, validation, summary
