from __future__ import annotations

import pandas as pd
import pytest

from stackwise.vomhoff_audit import DATASET_ID, VomhoffAuditError, audit_vomhoff_logical_units


def _observation(**overrides):
    row = {
        "dataset_id": DATASET_ID,
        "observation_id": "obs-1",
        "source_file": "energy_measurements_fig4.csv",
        "source_figure": 4,
        "source_run": 2,
        "source_event": "Data Request",
        "source_application_protocol": "http",
        "source_data_object": "1K.data",
        "source_diff_time_s": 0.3,
        "technology": "NB-IoT",
        "access_network": "NB-IoT",
        "application_protocol": "HTTP",
        "payload_bytes": 1024,
        "direction": "uplink",
        "measurement_boundary": "transfer",
        "evidence_grade": "A",
        "source_license": "CC-BY-4.0",
        "source_doi": "10.5281/zenodo.7603641",
        "energy_j": 0.5,
        "duration_s": 0.3,
        "raw_energy_j": 0.5,
        "raw_duration_s": 0.3,
        "normalisation_rule": "none",
        "timestamp_utc": "2023-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def test_audit_keeps_source_target_phases_separate_from_auxiliary_events():
    frame = pd.DataFrame(
        [
            _observation(observation_id="a"),
            _observation(
                observation_id="b",
                source_event="Before reading data",
                source_diff_time_s=0.1,
                energy_j=0.1,
                duration_s=0.1,
                raw_energy_j=0.1,
                raw_duration_s=0.1,
            ),
        ]
    )

    summary, groups, multi, non_target, standby = audit_vomhoff_logical_units(frame)

    assert summary["target_phase_rows"] == 1
    assert summary["non_target_event_rows"] == 1
    assert summary["candidate_logical_phase_groups"] == 1
    assert summary["aggregation_authorised"] is False
    assert multi.empty
    assert non_target.loc[0, "source_event"] == "Before reading data"
    assert standby.empty
    assert len(groups) == 1


def test_repeated_diff_time_segments_are_flagged_not_silently_aggregated():
    frame = pd.DataFrame(
        [
            _observation(observation_id="a", source_diff_time_s=0.3, energy_j=0.5, duration_s=0.3),
            _observation(
                observation_id="b",
                source_diff_time_s=1.8,
                energy_j=0.7,
                duration_s=1.8,
                raw_energy_j=0.7,
                raw_duration_s=1.8,
                timestamp_utc="2023-01-01T00:00:01Z",
            ),
        ]
    )

    summary, groups, multi, _, _ = audit_vomhoff_logical_units(frame)

    assert summary["candidate_logical_phase_groups"] == 1
    assert summary["multi_segment_target_groups"] == 1
    assert summary["max_segments_per_candidate_group"] == 2
    assert summary["segment_count_distribution"] == {"2": 1}
    assert len(multi) == 2
    assert groups.loc[0, "segment_count"] == 2
    assert groups.loc[0, "candidate_energy_sum_j"] == pytest.approx(1.2)
    assert groups.loc[0, "candidate_energy_mean_j"] == pytest.approx(0.6)
    assert groups.loc[0, "candidate_duration_sum_s"] == pytest.approx(2.1)
    # The audit reports candidate summaries but deliberately does not select one.
    assert summary["aggregation_authorised"] is False


def test_candidate_group_does_not_merge_protocols_or_payload_objects():
    frame = pd.DataFrame(
        [
            _observation(observation_id="http-1"),
            _observation(
                observation_id="mqtt-1",
                source_application_protocol="mqtt",
                application_protocol="MQTT",
            ),
            _observation(
                observation_id="http-10k",
                source_data_object="10K.data",
                payload_bytes=10240,
            ),
        ]
    )

    summary, groups, _, _, _ = audit_vomhoff_logical_units(frame)

    assert summary["candidate_logical_phase_groups"] == 3
    assert set(groups["segment_count"]) == {1}


def test_metadata_inconsistency_inside_candidate_group_is_reported():
    frame = pd.DataFrame(
        [
            _observation(observation_id="a"),
            _observation(
                observation_id="b",
                source_diff_time_s=1.0,
                measurement_boundary="full_device_cycle",
                timestamp_utc="2023-01-01T00:00:01Z",
            ),
        ]
    )

    summary, groups, _, _, _ = audit_vomhoff_logical_units(frame)

    assert summary["metadata_inconsistent_candidate_groups"] == 1
    assert not bool(groups.loc[0, "metadata_conditions_consistent"])
    assert "measurement_boundary" in groups.loc[0, "inconsistent_condition_fields"]


def test_figure5_standby_discrepancy_is_reported_without_rewriting_duration():
    frame = pd.DataFrame(
        [
            _observation(
                observation_id="s1",
                source_file="energy_measurements_fig5.csv",
                source_figure=5,
                source_event="Standby",
                source_application_protocol="mqtt",
                application_protocol="MQTT",
                source_diff_time_s=9.3,
                duration_s=9.3,
                raw_duration_s=9.3,
                energy_j=0.2,
                raw_energy_j=0.2,
                direction=None,
                measurement_boundary="standby",
            )
        ]
    )

    summary, _, _, _, standby = audit_vomhoff_logical_units(frame)

    audit = summary["figure5_standby_source_discrepancy_audit"]
    assert audit["readme_target_duration_s"] == 10.0
    assert audit["source_r_script_explicit_standby_normalisation"] is False
    assert audit["duration_s"]["median"] == pytest.approx(9.3)
    assert standby.loc[0, "duration_s"] == pytest.approx(9.3)


def test_wrong_dataset_is_rejected():
    frame = pd.DataFrame([_observation(dataset_id="other")])
    with pytest.raises(VomhoffAuditError):
        audit_vomhoff_logical_units(frame)
