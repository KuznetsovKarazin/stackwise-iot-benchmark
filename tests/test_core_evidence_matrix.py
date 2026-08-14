from __future__ import annotations

from copy import deepcopy

import pytest

from stackwise.evidence_matrix import (
    CORE_FOUR_DATASET_IDS,
    EvidenceMatrixError,
    build_boundary_profile,
    build_target_gap_matrix,
    records_to_frame,
    validate_core_four_matrix,
)


def _valid_record(dataset_id: str, evidence_id: str, **overrides):
    record = {
        "evidence_id": evidence_id,
        "dataset_id": dataset_id,
        "study_id": "synthetic-study",
        "source_doi": "10.0000/synthetic",
        "source_license": "CC-BY-4.0",
        "source_artifact": "synthetic.jsonl",
        "technology": "Synthetic-Radio",
        "access_network": "Synthetic-Radio",
        "transport_protocol": None,
        "application_protocol": None,
        "security_mode": None,
        "management_protocol": None,
        "metric_id": "radio_incremental_transaction_energy_j",
        "metric_family": "energy",
        "unit": "J",
        "value_semantics": "Synthetic transaction energy.",
        "estimate": 0.1,
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
        "dependence_structure": "One synthetic unit.",
        "source_grade": "A",
        "validation_status": "validated_with_limitations",
        "derivation_class": "direct_empirical",
        "parent_evidence_ids": [],
        "shared_parameter_ids": [],
        "uncertainty_basis": "single_independent_unit",
        "uncertainty_notes": "Synthetic test.",
        "applicability_domain": "Synthetic test only.",
        "intended_use": "bridge_input",
        "bridge_requirements": "Synthetic.",
        "limitations": "Synthetic.",
        "notes": None,
    }
    record.update(overrides)
    return record


def test_core_matrix_validation_resolves_four_datasets_without_assuming_record_counts():
    records = [
        _valid_record(dataset_id, f"evidence-{index}")
        for index, dataset_id in enumerate(CORE_FOUR_DATASET_IDS)
    ]
    summary = validate_core_four_matrix(records, [], expected_counts=None)
    assert summary["records"] == 4
    assert summary["datasets"] == 4
    assert summary["duplicate_evidence_ids"] == 0
    assert summary["target_only_empirical_records"] == 0


def test_core_matrix_validation_rejects_unresolved_parent_reference():
    records = [
        _valid_record(dataset_id, f"evidence-{index}")
        for index, dataset_id in enumerate(CORE_FOUR_DATASET_IDS)
    ]
    records[0]["parent_evidence_ids"] = ["missing-parent"]
    with pytest.raises(EvidenceMatrixError, match="unresolved parent"):
        validate_core_four_matrix(records, [], expected_counts=None)



def test_core_matrix_validation_rejects_target_metric_even_if_mislabelled_as_bridge_input():
    records = [
        _valid_record(dataset_id, f"evidence-{index}")
        for index, dataset_id in enumerate(CORE_FOUR_DATASET_IDS)
    ]
    records[0].update(
        {
            "metric_id": "expected_device_energy_per_application_report_j",
            "metric_family": "energy",
            "unit": "J",
            "intended_use": "bridge_input",
            "system_scope": "whole_device",
            "temporal_scope": "reporting_cycle",
            "accounting_basis": "per_report",
            "payload_basis": "application_payload",
            "path_start": "device_application",
            "path_end": "radio_antenna",
            "reporting_interval_s": 60.0,
        }
    )
    with pytest.raises(EvidenceMatrixError, match="target-only decision metrics"):
        validate_core_four_matrix(records, [], expected_counts=None)

def test_legacy_vomhoff_records_expand_to_extended_optional_schema_columns():
    record = _valid_record(CORE_FOUR_DATASET_IDS[0], "legacy")
    for field in [
        "implementation_context_id",
        "device_model",
        "radio_module",
        "firmware_version",
        "measurement_instrument",
        "implementation_notes",
    ]:
        record.pop(field, None)
    frame = records_to_frame([record])
    assert "implementation_context_id" in frame.columns
    assert frame.loc[0, "implementation_context_id"] is None


def _gap_support_records():
    metrics = {
        "vomhoff_nbiot_ltem_energy_2023": ["device_phase_energy_j", "device_phase_duration_s"],
        "insectt_wsn_power_2023": ["derived_capture_energy_j", "trace_charge_c"],
        "lorawan_lrfhss_energy_2024": [
            "radio_incremental_transaction_energy_j",
            "radio_full_capture_energy_j",
        ],
        "loed_lorawan_edge_2020": [
            "gateway_rssi_dbm",
            "gateway_snr_db",
            "gateway_crc_valid_fraction_of_receptions",
            "logical_frame_multi_gateway_fraction",
        ],
    }
    return [
        {"dataset_id": dataset_id, "metric_id": metric_id}
        for dataset_id, metric_ids in metrics.items()
        for metric_id in metric_ids
    ]


def test_target_gap_policy_is_complete_and_keeps_loed_pdr_proxy_prohibition():
    gaps = build_target_gap_matrix(_gap_support_records())
    assert len(gaps) == 20
    assert gaps["target_metric_id"].nunique() == 5
    assert set(gaps["dataset_id"]) == set(CORE_FOUR_DATASET_IDS)

    loed_delivery = gaps[
        (gaps["dataset_id"] == "loed_lorawan_edge_2020")
        & (gaps["target_metric_id"] == "delivery_probability")
    ].iloc[0]
    assert loed_delivery["relation_class"] == "C2_CONDITIONAL"
    assert "gateway_crc_valid_fraction_of_receptions" in loed_delivery["prohibited_proxy_metric_ids"]

    loed_energy = gaps[
        (gaps["dataset_id"] == "loed_lorawan_edge_2020")
        & (gaps["target_metric_id"] == "expected_device_energy_per_application_report_j")
    ].iloc[0]
    assert loed_energy["relation_class"] == "E0_MISSING"
    assert loed_energy["supporting_metric_ids"] == ""


def test_boundary_profile_keeps_whole_device_and_radio_rail_energy_separate():
    whole = _valid_record(
        "vomhoff_nbiot_ltem_energy_2023",
        "whole",
        metric_id="device_phase_energy_j",
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
    )
    radio = _valid_record("lorawan_lrfhss_energy_2024", "radio")
    profile = build_boundary_profile([whole, radio])
    assert len(profile) == 2
    assert set(profile["system_scope"]) == {"whole_device", "radio_rail"}
