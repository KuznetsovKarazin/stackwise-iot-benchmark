from __future__ import annotations

from copy import deepcopy

from stackwise.evidence import (
    CompatibilityLevel,
    assess_compatibility,
    load_boundary_taxonomy,
    load_metric_catalog,
    validate_evidence_record,
    validate_shared_parameter_record,
)


def _record(**overrides):
    record = {
        "evidence_id": "lrfhss:dr8:noack:transaction_energy",
        "dataset_id": "lorawan_lrfhss_energy_2024",
        "study_id": "10.5281/zenodo.13838241",
        "source_doi": "10.5281/zenodo.13838241",
        "source_license": "CC-BY-4.0",
        "source_artifact": "data/analysis_ready/lorawan_lrfhss_energy_2024/transaction_energy.csv",
        "technology": "LoRaWAN-LR-FHSS",
        "access_network": "LoRaWAN-LR-FHSS",
        "transport_protocol": None,
        "application_protocol": None,
        "security_mode": None,
        "management_protocol": None,
        "metric_id": "radio_incremental_transaction_energy_j",
        "metric_family": "energy",
        "unit": "J",
        "value_semantics": "Incremental energy above the trace-specific radio sleep baseline.",
        "estimate": 0.150,
        "summary_statistic": "raw_measurement",
        "system_scope": "radio_rail",
        "temporal_scope": "transaction",
        "accounting_basis": "per_transaction",
        "conditioning": "unconditional",
        "payload_basis": "lorawan_frm_payload",
        "baseline_accounting": "excluded",
        "ack_rx_accounting": "excluded",
        "retry_accounting": "excluded",
        "path_start": "device_radio",
        "path_end": "radio_antenna",
        "payload_bytes": 4,
        "reporting_interval_s": None,
        "direction": "uplink",
        "confirmation_mode": "unconfirmed",
        "tx_power_dbm": 14.0,
        "environment": "laboratory",
        "phase_name": None,
        "data_rate_mode": "DR8",
        "frequency_hz": None,
        "bandwidth_hz": None,
        "spreading_factor": None,
        "coding_rate": "1/3",
        "bit_rate_bps": 162,
        "operator": None,
        "empirical_unit": "trace_configuration",
        "independence_unit": "trace_configuration",
        "n_source_observations": 1,
        "n_independent_units": 1,
        "dependence_structure": "One source trace for this DR/confirmation configuration.",
        "source_grade": "A",
        "validation_status": "validated_with_limitations",
        "derivation_class": "validated_derived",
        "parent_evidence_ids": ["lrfhss:dr8:noack:full_capture_energy"],
        "shared_parameter_ids": ["lrfhss:radio_supply_voltage_v"],
        "uncertainty_basis": "single_independent_unit",
        "uncertainty_notes": "Population variance is not identifiable from one trace.",
        "applicability_domain": "LR1121, DR8, 4-byte FRMPayload, +14 dBm, no ACK.",
        "intended_use": "bridge_input",
        "bridge_requirements": "Whole-device reporting-cycle energy requires an explicit device-component model.",
        "limitations": "Capture-specific estimate; not a population mean.",
        "notes": None,
    }
    record.update(overrides)
    return record


def test_evidence_record_validates_against_schema_and_catalog():
    assert validate_evidence_record(_record()) == []


def test_evidence_record_rejects_wrong_metric_family_and_unit():
    errors = validate_evidence_record(_record(metric_family="power", unit="W"))
    assert any("does not match catalogue family" in error for error in errors)
    assert any("does not match canonical unit" in error for error in errors)


def test_contract_catalog_and_taxonomy_load():
    catalog = load_metric_catalog()
    taxonomy = load_boundary_taxonomy()
    assert "radio_incremental_transaction_energy_j" in catalog["metrics"]
    assert "C0_DIRECT" in taxonomy["comparison_classes"]
    assert "system_scope" in taxonomy["critical_boundary_fields"]


def test_direct_comparison_requires_explicitly_allowed_technology_factor():
    left = _record()
    right = deepcopy(left)
    right["evidence_id"] = "other:transaction_energy"
    right["technology"] = "OTHER-RADIO"
    right["access_network"] = "OTHER-RADIO"

    strict = assess_compatibility(left, right)
    assert strict.level is CompatibilityLevel.CONDITIONAL

    comparison = assess_compatibility(
        left,
        right,
        allowed_vary={"technology", "access_network"},
    )
    assert comparison.level is CompatibilityLevel.DIRECT


def test_energy_scope_mismatch_is_bridgeable_not_direct():
    left = _record()
    right = deepcopy(left)
    right.update(
        {
            "evidence_id": "whole-device:transaction-energy",
            "system_scope": "whole_device",
            "path_start": "device_application",
        }
    )
    assessment = assess_compatibility(left, right)
    assert assessment.level is CompatibilityLevel.BRIDGEABLE
    assert "measurement_boundary_mismatch" in assessment.reasons


def test_unknown_critical_boundary_prevents_direct_classification():
    left = _record(retry_accounting="unknown")
    right = deepcopy(left)
    assessment = assess_compatibility(left, right)
    assert assessment.level is CompatibilityLevel.CONDITIONAL
    assert "unknown_critical_boundary" in assessment.reasons


def test_loed_crc_fraction_cannot_be_promoted_to_delivery_probability():
    left = _record(
        evidence_id="loed:crc",
        dataset_id="loed_lorawan_edge_2020",
        technology="LoRaWAN",
        access_network="LoRaWAN",
        metric_id="gateway_crc_valid_indicator",
        metric_family="reception_status",
        unit="boolean",
        system_scope="gateway_receiver",
        temporal_scope="reception_event",
        accounting_basis="per_reception",
        conditioning="observed_reception",
        payload_basis="phy_payload",
        baseline_accounting="not_applicable",
        ack_rx_accounting="not_applicable",
        retry_accounting="unknown",
        path_start="radio_antenna",
        path_end="gateway_receiver",
        estimate=None,
        summary_statistic="distribution",
        payload_bytes=None,
        confirmation_mode=None,
        tx_power_dbm=None,
        empirical_unit="gateway_reception",
        independence_unit="logical_frame",
        n_source_observations=11263001,
        n_independent_units=None,
        derivation_class="direct_empirical",
        uncertainty_basis="hierarchical_observational",
        intended_use="descriptive",
    )
    right = _record(
        evidence_id="target:delivery",
        dataset_id="decision_target",
        technology="LoRaWAN",
        access_network="LoRaWAN",
        metric_id="delivery_probability",
        metric_family="delivery_reliability",
        unit="probability",
        system_scope="network_path",
        temporal_scope="transaction",
        accounting_basis="per_attempt",
        conditioning="unconditional",
        payload_basis="application_payload",
        baseline_accounting="not_applicable",
        ack_rx_accounting="conditional",
        retry_accounting="conditional",
        path_start="device_application",
        path_end="application_endpoint",
        estimate=None,
        summary_statistic="not_materialised",
        empirical_unit="transmission_attempt",
        independence_unit="transmission_attempt",
        n_source_observations=None,
        n_independent_units=None,
        source_grade="D",
        validation_status="pending",
        derivation_class="assumption",
        parent_evidence_ids=[],
        shared_parameter_ids=[],
        uncertainty_basis="external_prior_required",
        intended_use="target_only",
    )
    assessment = assess_compatibility(left, right)
    assert assessment.level is CompatibilityLevel.INCOMPATIBLE
    assert "hard_incompatible_metric_pair" in assessment.reasons


def test_loed_snr_is_bridgeable_to_feasible_link_only_via_link_model():
    snr = _record(
        evidence_id="loed:snr",
        dataset_id="loed_lorawan_edge_2020",
        technology="LoRaWAN",
        access_network="LoRaWAN",
        metric_id="gateway_snr_db",
        metric_family="link_quality",
        unit="dB",
    )
    target = _record(
        evidence_id="target:feasible-link",
        dataset_id="decision_target",
        technology="LoRaWAN",
        access_network="LoRaWAN",
        metric_id="feasible_link_probability",
        metric_family="coverage",
        unit="probability",
    )
    assessment = assess_compatibility(snr, target)
    assert assessment.level is CompatibilityLevel.BRIDGEABLE
    assert "explicit_metric_bridge_required" in assessment.reasons


def test_missing_metric_specific_condition_prevents_direct_classification():
    left = _record(data_rate_mode=None)
    right = deepcopy(left)
    assessment = assess_compatibility(left, right)
    assert assessment.level is CompatibilityLevel.CONDITIONAL
    assert "unknown_required_direct_condition" in assessment.reasons


def test_implementation_context_mismatch_is_conditional_by_default():
    left = _record(device_model="nRF52840 DK", radio_module="nRF52840")
    right = deepcopy(left)
    right.update(
        {
            "evidence_id": "uwb:trace-energy",
            "device_model": "nRF52832 + DW1000 board",
            "radio_module": "Qorvo DW1000",
        }
    )
    assessment = assess_compatibility(left, right)
    assert assessment.level is CompatibilityLevel.CONDITIONAL
    assert "implementation_context_mismatch" in assessment.reasons
    assert "different:device_model" in assessment.reasons


def test_implementation_variation_must_be_explicitly_allowed():
    left = _record(device_model="nRF52840 DK", radio_module="nRF52840")
    right = deepcopy(left)
    right.update(
        {
            "evidence_id": "candidate-b:transaction-energy",
            "technology": "OTHER-RADIO",
            "access_network": "OTHER-RADIO",
            "device_model": "other development board",
            "radio_module": "other radio",
        }
    )
    assessment = assess_compatibility(
        left,
        right,
        allowed_vary={"technology", "access_network", "device_model", "radio_module"},
    )
    assert assessment.level is CompatibilityLevel.DIRECT


def test_schema_accepts_structured_implementation_context():
    record = _record(
        implementation_context_id="lrfhss-lr1121-eval-board",
        device_model="LR1121 evaluation platform",
        radio_module="Semtech LR1121",
        firmware_version=None,
        measurement_instrument="source current-capture setup",
        implementation_notes="Implementation fields describe the measured hardware, not a technology-wide invariant.",
    )
    assert validate_evidence_record(record) == []


def test_shared_parameter_schema_accepts_correlated_calibration_record():
    parameter = {
        "parameter_id": "insectt_ppk2_source_voltage_v",
        "parameter_kind": "calibration",
        "name": "validated source voltage",
        "unit": "V",
        "estimate": 3.3000554,
        "derivation_class": "validated_derived",
        "validation_status": "validated_with_limitations",
        "source_dois": ["10.5281/zenodo.7762712", "10.1007/978-3-031-54049-3_14"],
        "supporting_artifacts": ["datasets/reference/insectt_table1_power_uw.csv"],
        "shared_across_dataset_ids": ["insectt_wsn_power_2023"],
        "n_supporting_configurations": 20,
        "uncertainty_basis": "validation_scale_check_not_replication",
        "uncertainty_model_status": "pending_stage3",
        "statistical_interpretation": "Configuration-wise implied values are not independent voltage replicates.",
        "diagnostics": {"mape_pct": 0.03475},
        "applicability_domain": "validated InSecTT release",
        "limitations": "Voltage is inferred from publication mean powers.",
    }
    assert validate_shared_parameter_record(parameter) == []


def test_vomhoff_phase_duration_is_bridgeable_to_end_to_end_latency_target():
    phase = _record(
        evidence_id="vomhoff:phase-duration",
        dataset_id="vomhoff_nbiot_ltem_energy_2023",
        technology="NB-IoT",
        access_network="NB-IoT",
        metric_id="device_phase_duration_s",
        metric_family="duration",
        unit="s",
        system_scope="whole_device",
        temporal_scope="phase",
        accounting_basis="per_phase",
        conditioning="unconditional",
        payload_basis="source_message_size",
        baseline_accounting="included",
        ack_rx_accounting="included",
        retry_accounting="included",
        path_start="not_applicable",
        path_end="not_applicable",
        phase_name="Data Request",
        data_rate_mode=None,
    )
    target = _record(
        evidence_id="target:e2e-latency",
        dataset_id="decision_target",
        technology="NB-IoT",
        access_network="NB-IoT",
        metric_id="end_to_end_application_latency_ms",
        metric_family="latency",
        unit="ms",
        system_scope="application_path",
        temporal_scope="transaction",
        accounting_basis="per_transaction",
        conditioning="unconditional",
        payload_basis="application_payload",
        baseline_accounting="not_applicable",
        ack_rx_accounting="conditional",
        retry_accounting="conditional",
        path_start="device_application",
        path_end="application_endpoint",
        phase_name=None,
        data_rate_mode=None,
        intended_use="target_only",
    )
    assessment = assess_compatibility(phase, target)
    assert assessment.level is CompatibilityLevel.BRIDGEABLE
    assert "explicit_metric_bridge_required" in assessment.reasons
