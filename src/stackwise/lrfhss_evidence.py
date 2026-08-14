from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd

DATASET_ID = "lorawan_lrfhss_energy_2024"
PUBLICATION_DOI = "10.3390/s24175770"
DATASET_DOI = "10.5281/zenodo.13838241"
EXPECTED_DRS = (8, 9, 10, 11)
EXPECTED_CONFIRMATION = ("confirmed", "unconfirmed")
EXPECTED_PAYLOAD_BYTES = 4
EXPECTED_TX_POWER_DBM = 14.0
EXPECTED_VOLTAGE_V = 3.3
EXPECTED_TRACE_DURATION_S = 59.99998976
BASELINE_BAND_ABS_A = 100e-6
IMPLEMENTATION_CONTEXT_ID = "lrfhss_lr1121dvk1tbks_lr1121_n6705a_2024"
MEASUREMENT_INSTRUMENT = "Keysight N6705A DC Power Analyzer"
ACQUISITION_SOFTWARE = "Keysight 14585A Control and Analysis Software"


class LRFHSSMaterialisationError(ValueError):
    pass


def _stable_id(prefix: str, *values: Any) -> str:
    serialised = "|".join("<NA>" if pd.isna(v) else str(v) for v in values)
    return f"{prefix}-{hashlib.sha1(serialised.encode('utf-8')).hexdigest()[:16]}"


def _none_if_na(value: Any) -> Any:
    return None if pd.isna(value) else value


def _validate_design(frame: pd.DataFrame) -> None:
    required = {
        "dataset_id", "observation_id", "confirmation_mode", "source_dr_index", "source_coding_rate",
        "source_physical_bit_rate_bps", "payload_bytes", "direction", "tx_power_dbm", "duration_s",
        "sample_count", "voltage_v", "energy_j", "trace_charge_c", "tx_burst_count",
        "low_current_band_abs_a", "low_current_band_sample_count", "low_current_band_mean_a",
        "device_model", "radio_module", "evidence_grade", "source_license", "source_doi",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise LRFHSSMaterialisationError(f"Missing harmonised LR-FHSS fields: {missing}")
    if len(frame) != 8:
        raise LRFHSSMaterialisationError(f"Expected 8 LR-FHSS configurations, found {len(frame)}")
    if set(frame["dataset_id"].dropna().astype(str)) != {DATASET_ID}:
        raise LRFHSSMaterialisationError("Input contains a dataset_id other than LR-FHSS")
    if frame["observation_id"].duplicated().any():
        raise LRFHSSMaterialisationError("Duplicate LR-FHSS observation_id values detected")

    observed = {
        (str(row.confirmation_mode), int(row.source_dr_index))
        for row in frame[["confirmation_mode", "source_dr_index"]].itertuples(index=False)
    }
    expected = {(mode, dr) for mode in EXPECTED_CONFIRMATION for dr in EXPECTED_DRS}
    if observed != expected:
        raise LRFHSSMaterialisationError(
            f"Incomplete/extra LR-FHSS design: missing={sorted(expected-observed)}, extra={sorted(observed-expected)}"
        )

    for row in frame.itertuples(index=False):
        if int(row.payload_bytes) != EXPECTED_PAYLOAD_BYTES:
            raise LRFHSSMaterialisationError(f"Unexpected payload for {row.confirmation_mode}/DR{row.source_dr_index}")
        if str(row.direction) != "uplink":
            raise LRFHSSMaterialisationError(f"Unexpected direction for {row.confirmation_mode}/DR{row.source_dr_index}")
        if not np.isclose(float(row.tx_power_dbm), EXPECTED_TX_POWER_DBM, rtol=0, atol=1e-12):
            raise LRFHSSMaterialisationError(f"Unexpected TX power for {row.confirmation_mode}/DR{row.source_dr_index}")
        if not np.isclose(float(row.voltage_v), EXPECTED_VOLTAGE_V, rtol=0, atol=1e-12):
            raise LRFHSSMaterialisationError(f"Unexpected voltage for {row.confirmation_mode}/DR{row.source_dr_index}")
        if int(row.tx_burst_count) != 1:
            raise LRFHSSMaterialisationError(
                f"Transaction derivation requires exactly one TX burst; found {row.tx_burst_count} for "
                f"{row.confirmation_mode}/DR{row.source_dr_index}"
            )
        if int(row.sample_count) <= 0 or float(row.duration_s) <= 0 or float(row.energy_j) <= 0:
            raise LRFHSSMaterialisationError(f"Non-positive trace statistic for {row.confirmation_mode}/DR{row.source_dr_index}")
        baseline = float(row.low_current_band_mean_a)
        if not np.isfinite(baseline) or baseline <= 0:
            raise LRFHSSMaterialisationError(
                f"Non-positive/invalid trace baseline for {row.confirmation_mode}/DR{row.source_dr_index}: {baseline}"
            )
        band = float(row.low_current_band_abs_a)
        if not np.isclose(band, BASELINE_BAND_ABS_A, rtol=0, atol=1e-15):
            raise LRFHSSMaterialisationError(
                f"Unexpected low-current baseline band for {row.confirmation_mode}/DR{row.source_dr_index}: {band}"
            )


def _base_record(row: pd.Series, *, metric_id: str, estimate: float, value_semantics: str,
                 temporal_scope: str, accounting_basis: str, baseline_accounting: str,
                 derivation_class: str, validation_status: str, parent_ids: list[str],
                 intended_use: str, limitations: str, dependence_structure: str,
                 uncertainty_notes: str) -> dict[str, Any]:
    dr = int(row["source_dr_index"])
    mode = str(row["confirmation_mode"])
    evidence_id = _stable_id("lrfhss-evidence", metric_id, mode, dr)
    metric_family = "energy"
    ack_accounting = "included" if mode == "confirmed" else "excluded"
    return {
        "evidence_id": evidence_id,
        "dataset_id": DATASET_ID,
        "study_id": "lrfhss_energy_measurement_campaign_2024",
        "source_doi": str(row.get("source_doi") or DATASET_DOI),
        "source_license": str(row.get("source_license")),
        "source_artifact": "data/analysis_ready/lorawan_lrfhss_energy_2024/configuration_observations.parquet",
        "technology": "LoRaWAN-LR-FHSS",
        "access_network": "LoRaWAN-LR-FHSS",
        "transport_protocol": None,
        "application_protocol": None,
        "security_mode": None,
        "management_protocol": None,
        "implementation_context_id": IMPLEMENTATION_CONTEXT_ID,
        "device_model": _none_if_na(row.get("device_model")) or "Semtech LR1121DVK1TBKS development kit",
        "radio_module": _none_if_na(row.get("radio_module")) or "Semtech LR1121",
        "firmware_version": _none_if_na(row.get("firmware_version")),
        "measurement_instrument": MEASUREMENT_INSTRUMENT,
        "acquisition_software": ACQUISITION_SOFTWARE,
        "implementation_notes": (
            "Measured in a complete LR-FHSS network with Kerlink iBTS Compact gateway and ChirpStack network server; "
            "current measurement accounts exclusively for the end-device radio interface. The associated paper identifies the hardware as Keysight N6705A; the Zenodo dataset labels 14585A as the power analyzer, but Keysight documents 14585A as control/analysis software for N6705-series instruments."
        ),
        "metric_id": metric_id,
        "metric_family": metric_family,
        "unit": "J",
        "value_semantics": value_semantics,
        "estimate": float(estimate),
        "summary_statistic": "raw_measurement",
        "system_scope": "radio_rail",
        "temporal_scope": temporal_scope,
        "accounting_basis": accounting_basis,
        "conditioning": "unconditional",
        "payload_basis": "lorawan_frm_payload",
        "baseline_accounting": baseline_accounting,
        "ack_rx_accounting": ack_accounting,
        "retry_accounting": "excluded",
        "path_start": "device_radio",
        "path_end": "radio_antenna",
        "payload_bytes": float(row["payload_bytes"]),
        "reporting_interval_s": None,
        "direction": "uplink",
        "confirmation_mode": mode,
        "tx_power_dbm": float(row["tx_power_dbm"]),
        "environment": "laboratory_operational_network",
        "phase_name": None,
        "data_rate_mode": f"DR{dr}",
        "frequency_hz": None,
        "bandwidth_hz": None,
        "spreading_factor": None,
        "coding_rate": str(row["source_coding_rate"]),
        "bit_rate_bps": float(row["source_physical_bit_rate_bps"]),
        "operator": None,
        "empirical_unit": "one_approximately_60s_radio_trace_with_one_lr_fhss_uplink_transaction",
        "independence_unit": "one_source_configuration_trace",
        "n_source_observations": int(row["sample_count"]),
        "n_independent_units": 1,
        "dependence_structure": dependence_structure,
        "source_grade": str(row["evidence_grade"]),
        "validation_status": validation_status,
        "derivation_class": derivation_class,
        "parent_evidence_ids": parent_ids,
        "shared_parameter_ids": [],
        "uncertainty_basis": "single_independent_unit",
        "uncertainty_notes": uncertainty_notes,
        "applicability_domain": (
            f"LR1121 radio-interface measurement: {mode}, DR{dr}, 4-byte FRM payload, +14 dBm, "
            "one observed TX burst in the approximately 60 s capture."
        ),
        "intended_use": intended_use,
        "bridge_requirements": (
            "Radio-interface-only energy. A whole-device/reporting-cycle bridge is required before comparison with "
            "whole-device energy evidence or use in expected_device_energy_per_application_report_j."
        ),
        "limitations": limitations,
        "notes": (
            f"Source trace observation_id={row['observation_id']}; 3.3 V rail is source-backed by the associated publication."
        ),
    }


def _overhead_record(dr: int, confirmed: dict[str, Any], unconfirmed: dict[str, Any],
                     confirmed_value: float, unconfirmed_value: float) -> dict[str, Any]:
    estimate = float(confirmed_value - unconfirmed_value)
    return {
        "evidence_id": _stable_id("lrfhss-evidence", "radio_ack_rx_overhead_energy_j", dr),
        "dataset_id": DATASET_ID,
        "study_id": "lrfhss_energy_measurement_campaign_2024",
        "source_doi": DATASET_DOI,
        "source_license": confirmed["source_license"],
        "source_artifact": "data/analysis_ready/lorawan_lrfhss_energy_2024/ack_rx_contrasts.csv",
        "technology": "LoRaWAN-LR-FHSS",
        "access_network": "LoRaWAN-LR-FHSS",
        "transport_protocol": None,
        "application_protocol": None,
        "security_mode": None,
        "management_protocol": None,
        "implementation_context_id": IMPLEMENTATION_CONTEXT_ID,
        "device_model": confirmed["device_model"],
        "radio_module": confirmed["radio_module"],
        "firmware_version": confirmed["firmware_version"],
        "measurement_instrument": MEASUREMENT_INSTRUMENT,
        "acquisition_software": ACQUISITION_SOFTWARE,
        "implementation_notes": confirmed["implementation_notes"],
        "metric_id": "radio_ack_rx_overhead_energy_j",
        "metric_family": "energy",
        "unit": "J",
        "value_semantics": (
            "Capture-specific matched-DR difference: confirmed incremental transaction radio energy minus "
            "unconfirmed incremental transaction radio energy."
        ),
        "estimate": estimate,
        "summary_statistic": "difference",
        "system_scope": "radio_rail",
        "temporal_scope": "transaction",
        "accounting_basis": "per_transaction",
        "conditioning": "not_applicable",
        "payload_basis": "lorawan_frm_payload",
        "baseline_accounting": "excluded",
        "ack_rx_accounting": "conditional",
        "retry_accounting": "excluded",
        "path_start": "device_radio",
        "path_end": "radio_antenna",
        "payload_bytes": 4.0,
        "reporting_interval_s": None,
        "direction": "uplink",
        "confirmation_mode": "confirmed_minus_unconfirmed",
        "tx_power_dbm": 14.0,
        "environment": "laboratory_operational_network",
        "phase_name": None,
        "data_rate_mode": f"DR{dr}",
        "frequency_hz": None,
        "bandwidth_hz": None,
        "spreading_factor": None,
        "coding_rate": confirmed["coding_rate"],
        "bit_rate_bps": confirmed["bit_rate_bps"],
        "operator": None,
        "empirical_unit": "one_matched_dr_confirmed_minus_unconfirmed_capture_contrast",
        "independence_unit": "one_matched_dr_capture_contrast",
        "n_source_observations": int(confirmed["n_source_observations"] + unconfirmed["n_source_observations"]),
        "n_independent_units": 1,
        "dependence_structure": (
            "The contrast is derived from two single configuration traces at the same DR. It is one matched "
            "configuration contrast, not a replicated paired experiment."
        ),
        "source_grade": confirmed["source_grade"],
        "validation_status": "validated_with_limitations",
        "derivation_class": "validated_derived",
        "parent_evidence_ids": [confirmed["evidence_id"], unconfirmed["evidence_id"]],
        "shared_parameter_ids": [],
        "uncertainty_basis": "single_independent_unit",
        "uncertainty_notes": (
            "No between-capture distribution of ACK/RX overhead is identifiable: only one confirmed and one "
            "unconfirmed trace exist at this DR. No confidence interval is authorised from electrical samples."
        ),
        "applicability_domain": (
            f"Capture-specific LR1121 DR{dr} comparison, 4-byte FRM payload, +14 dBm, confirmed versus unconfirmed."
        ),
        "intended_use": "descriptive",
        "bridge_requirements": (
            "Do not interpret this single capture contrast as a population mean ACK overhead. A replicated or "
            "externally calibrated ACK/RX state model is required for stochastic decision use."
        ),
        "limitations": (
            "Confirmed and unconfirmed configurations are each represented by one trace. The difference may include "
            "capture-specific receive-window/ACK state behaviour and is not a population-level causal ACK effect."
        ),
        "notes": "Derived only after one-TX-burst validation and trace-specific sleep-baseline removal.",
    }


def build_lrfhss_stage2(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Materialise LR-FHSS Stage-2 energy evidence while preserving n=1/configuration."""
    _validate_design(frame)
    work = frame.copy()
    work["baseline_current_a"] = pd.to_numeric(work["low_current_band_mean_a"], errors="raise")
    work["baseline_energy_j"] = work["baseline_current_a"] * pd.to_numeric(work["voltage_v"], errors="raise") * pd.to_numeric(work["duration_s"], errors="raise")
    work["incremental_transaction_energy_j"] = pd.to_numeric(work["energy_j"], errors="raise") - work["baseline_energy_j"]
    if (work["incremental_transaction_energy_j"] <= 0).any():
        raise LRFHSSMaterialisationError("Baseline subtraction produced non-positive transaction energy")
    work["baseline_fraction_pct_of_full_capture"] = 100.0 * work["baseline_energy_j"] / work["energy_j"]
    work["independent_unit_count"] = 1
    work["implementation_context_id"] = IMPLEMENTATION_CONTEXT_ID
    work["measurement_instrument"] = MEASUREMENT_INSTRUMENT
    work["acquisition_software"] = ACQUISITION_SOFTWARE
    work["baseline_method"] = (
        "Trace-specific mean of samples with |current| <= 100 uA; scale checked against the publication sleep-current reference."
    )

    records: list[dict[str, Any]] = []
    transaction_by_dr_mode: dict[tuple[int, str], dict[str, Any]] = {}
    for _, row in work.sort_values(["source_dr_index", "confirmation_mode"], kind="stable").iterrows():
        dr = int(row["source_dr_index"])
        mode = str(row["confirmation_mode"])
        full = _base_record(
            row,
            metric_id="radio_full_capture_energy_j",
            estimate=float(row["energy_j"]),
            value_semantics="Energy on the measured LR1121 radio rail over the complete approximately 60 s source capture.",
            temporal_scope="trace_window",
            accounting_basis="per_capture",
            baseline_accounting="included",
            derivation_class="direct_empirical",
            validation_status="validated",
            parent_ids=[],
            intended_use="descriptive",
            limitations=(
                "Full-capture energy includes approximately 60 s of baseline sleep and therefore is not energy per message. "
                "Only one trace exists for this confirmation-mode/DR configuration."
            ),
            dependence_structure=(
                "One approximately 60 s trace per confirmation-mode x DR configuration. High-frequency current samples "
                "estimate the trace integral but are not independent experimental replicates."
            ),
            uncertainty_notes=(
                "No between-run variance is identifiable. Within-trace electrical sample dispersion must not be used "
                "as a technology-level standard error."
            ),
        )
        transaction = _base_record(
            row,
            metric_id="radio_incremental_transaction_energy_j",
            estimate=float(row["incremental_transaction_energy_j"]),
            value_semantics=(
                "Incremental radio-rail energy associated with the single observed Class-A transaction, obtained by "
                "subtracting the trace-specific low-current baseline over the full capture duration."
            ),
            temporal_scope="transaction",
            accounting_basis="per_transaction",
            baseline_accounting="excluded",
            derivation_class="validated_derived",
            validation_status="validated_with_limitations",
            parent_ids=[full["evidence_id"]],
            intended_use="bridge_input",
            limitations=(
                "The transaction boundary is inferred from exactly one detected TX burst plus baseline subtraction; "
                "the baseline is an empirical low-current-band proxy rather than a separately replicated sleep trace. "
                "Only one trace exists for this configuration."
            ),
            dependence_structure=(
                "Derived from the same single trace as its full-capture parent. Baseline samples and active-state samples "
                "are within-trace repeated measurements, not independent experimental replicates."
            ),
            uncertainty_notes=(
                "No between-run variance is identifiable from the released traces. Capture-to-capture variation remains an "
                "explicit Stage-3 epistemic gap unless new repeatability data or a clearly labelled sensitivity model is supplied; "
                "no confidence interval is authorised from electrical samples."
            ),
        )
        records.extend([full, transaction])
        transaction_by_dr_mode[(dr, mode)] = transaction

    contrasts: list[dict[str, Any]] = []
    contrast_records: list[dict[str, Any]] = []
    for dr in EXPECTED_DRS:
        confirmed = transaction_by_dr_mode[(dr, "confirmed")]
        unconfirmed = transaction_by_dr_mode[(dr, "unconfirmed")]
        contrast = _overhead_record(
            dr,
            confirmed,
            unconfirmed,
            confirmed_value=float(confirmed["estimate"]),
            unconfirmed_value=float(unconfirmed["estimate"]),
        )
        contrast_records.append(contrast)
        overhead = float(contrast["estimate"])
        contrasts.append(
            {
                "source_dr_index": dr,
                "data_rate_mode": f"DR{dr}",
                "coding_rate": confirmed["coding_rate"],
                "bit_rate_bps": confirmed["bit_rate_bps"],
                "confirmed_incremental_energy_j": float(confirmed["estimate"]),
                "unconfirmed_incremental_energy_j": float(unconfirmed["estimate"]),
                "confirmed_minus_unconfirmed_energy_j": overhead,
                "overhead_pct_vs_unconfirmed": 100.0 * overhead / float(unconfirmed["estimate"]),
                "n_confirmed_independent_units": 1,
                "n_unconfirmed_independent_units": 1,
                "n_contrast_replications": 1,
                "population_ack_overhead_estimate_authorised": False,
            }
        )
    records.extend(contrast_records)

    transaction_validation = work[
        [
            "observation_id", "confirmation_mode", "source_dr_index", "sample_count", "duration_s", "tx_burst_count",
            "energy_j", "baseline_current_a", "baseline_energy_j", "incremental_transaction_energy_j",
            "baseline_fraction_pct_of_full_capture", "low_current_band_sample_count", "low_current_band_abs_a",
        ]
    ].sort_values(["source_dr_index", "confirmation_mode"], kind="stable").reset_index(drop=True)
    contrast_frame = pd.DataFrame(contrasts).sort_values("source_dr_index").reset_index(drop=True)
    configuration = work.sort_values(["source_dr_index", "confirmation_mode"], kind="stable").reset_index(drop=True)

    summary = {
        "dataset_id": DATASET_ID,
        "stage": "Stage-2 LR-FHSS materialisation",
        "configurations": int(len(configuration)),
        "data_rates": [f"DR{dr}" for dr in EXPECTED_DRS],
        "confirmation_modes": list(EXPECTED_CONFIRMATION),
        "full_capture_evidence_records": 8,
        "incremental_transaction_evidence_records": 8,
        "ack_rx_contrast_evidence_records": 4,
        "evidence_records": int(len(records)),
        "n_independent_units_per_configuration": 1,
        "tx_burst_count_values": sorted(int(v) for v in configuration["tx_burst_count"].unique()),
        "baseline_current_a_min": float(configuration["baseline_current_a"].min()),
        "baseline_current_a_max": float(configuration["baseline_current_a"].max()),
        "baseline_energy_fraction_pct_min": float(configuration["baseline_fraction_pct_of_full_capture"].min()),
        "baseline_energy_fraction_pct_max": float(configuration["baseline_fraction_pct_of_full_capture"].max()),
        "incremental_transaction_energy_j_min": float(configuration["incremental_transaction_energy_j"].min()),
        "incremental_transaction_energy_j_max": float(configuration["incremental_transaction_energy_j"].max()),
        "ack_rx_overhead_pct_by_dr": {
            f"DR{int(row.source_dr_index)}": float(row.overhead_pct_vs_unconfirmed)
            for row in contrast_frame.itertuples(index=False)
        },
        "measurement_boundary_policy": (
            "All LR-FHSS evidence is radio-interface-only. Full-capture and baseline-subtracted transaction energy are "
            "different estimands and are retained as separate metrics."
        ),
        "baseline_policy": (
            "Transaction energy subtracts a trace-specific low-current-band baseline after validation of exactly one TX "
            "burst per capture. The low-current mean is a within-trace baseline proxy, not an independent sleep replicate."
        ),
        "uncertainty_policy": (
            "Each confirmation-mode x DR configuration has one independent trace. ACK/RX differences are single "
            "capture-specific matched-DR contrasts; no population confidence interval is produced."
        ),
        "measurement_hardware": MEASUREMENT_INSTRUMENT,
        "acquisition_software": ACQUISITION_SOFTWARE,
        "instrumentation_provenance_note": (
            "The associated publication identifies Keysight N6705A as measurement hardware. The Zenodo record labels "
            "'Power Analyzer: Keysight 14585A'; Keysight documentation identifies 14585A as Control and Analysis Software."
        ),
    }
    return configuration, records, transaction_validation, contrast_frame, summary
