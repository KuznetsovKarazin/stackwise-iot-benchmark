from __future__ import annotations

from pathlib import Path

import math
import pandas as pd

from stackwise.adapters.specific import VomhoffCellularEnergyAdapter


RECORD = {
    "id": "vomhoff_nbiot_ltem_energy_2023",
    "doi": "10.5281/zenodo.7603641",
    "evidence_grade": "A",
    "technologies": ["NB-IoT", "LTE-M"],
    "measurement_boundaries": ["full_device_cycle"],
    "licence": {"id": "CC-BY-4.0"},
}


def _row(**overrides):
    row = {
        "epoch": 0.0,
        "diff": 0.005,
        "current": 0.1,
        "voltage": 5.0,
        "rat_type": "nb-iot",
        "application_protocol": "http",
        "id": 1,
        "timestamp": "2023-01-01T00:00:00.000Z",
        "current_As": 0.0005,
        "consumption_Ws": 0.0025,
        "event": "Connection Establishment",
        "run": 1,
        "diff_time": 1.0,
        "data": "1K.data",
    }
    row.update(overrides)
    return row


def test_fig3_idle_connected_source_normalisation(tmp_path: Path):
    rows = [
        _row(
            application_protocol="auth",
            event="Idle Connected",
            diff_time=60.0,
            consumption_Ws=1.0,
            data=None,
            epoch=0.0,
        ),
        _row(
            application_protocol="auth",
            event="Idle Connected",
            diff_time=60.0,
            consumption_Ws=1.0,
            data=None,
            epoch=5.0,
        ),
    ]
    frame = pd.DataFrame(rows).drop(columns=["data"])
    frame.to_csv(tmp_path / "energy_measurements_fig3.csv", index=False)

    result = VomhoffCellularEnergyAdapter(RECORD, tmp_path).harmonize()
    assert not result.warnings
    assert len(result.observations) == 1
    observation = result.observations.iloc[0]
    assert observation["technology"] == "NB-IoT"
    assert pd.isna(observation["application_protocol"])
    assert observation["measurement_boundary"] == "idle"
    assert math.isclose(observation["raw_energy_j"], 2.0)
    assert math.isclose(observation["energy_j"], 1.0)
    assert math.isclose(observation["raw_duration_s"], 60.0)
    assert math.isclose(observation["duration_s"], 30.0)
    assert observation["normalisation_factor"] == 0.5


def test_fig4_idle_is_normalised_to_twenty_seconds(tmp_path: Path):
    rows = [
        _row(event="Idle", diff_time=40.0, consumption_Ws=1.0, epoch=0.0),
        _row(event="Idle", diff_time=40.0, consumption_Ws=1.0, epoch=5.0),
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "energy_measurements_fig4.csv", index=False)

    result = VomhoffCellularEnergyAdapter(RECORD, tmp_path).harmonize()
    assert not result.warnings
    observation = result.observations.iloc[0]
    assert observation["application_protocol"] == "HTTP"
    assert observation["payload_bytes"] == 1024
    assert math.isclose(observation["raw_energy_j"], 2.0)
    assert math.isclose(observation["energy_j"], 1.0)
    assert math.isclose(observation["duration_s"], 20.0)
    assert math.isclose(observation["normalisation_factor"], 0.5)


def test_fig5_idle_filter_and_normalisation(tmp_path: Path):
    rows = [
        # Retained because elapsed time is below 5000 ms.
        _row(event="Idle", application_protocol="mqtt", epoch=0.0, current=0.10, consumption_Ws=0.001),
        _row(event="Idle", application_protocol="mqtt", epoch=1000.0, current=0.10, consumption_Ws=0.001),
        # Excluded: late and current above the source threshold.
        _row(event="Idle", application_protocol="mqtt", epoch=6000.0, current=0.10, consumption_Ws=0.001),
        # Retained because current is at or below 0.063 A.
        _row(event="Idle", application_protocol="mqtt", epoch=7000.0, current=0.05, consumption_Ws=0.001),
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "energy_measurements_fig5.csv", index=False)

    result = VomhoffCellularEnergyAdapter(RECORD, tmp_path).harmonize()
    assert not result.warnings
    observation = result.observations.iloc[0]
    assert observation["application_protocol"] == "MQTT"
    assert observation["sample_count"] == 3
    assert math.isclose(observation["raw_duration_s"], 3 * 0.005)
    assert math.isclose(observation["raw_energy_j"], 0.003)
    assert math.isclose(observation["duration_s"], 20.0)
    assert math.isclose(observation["energy_j"], 4.0)
    assert observation["normalisation_rule"] == "authors_fig5_filtered_idle_to_20_s"


def test_repeated_event_with_distinct_diff_time_is_preserved_as_separate_segments(tmp_path: Path):
    rows = [
        _row(
            event="Data Request",
            run=2,
            diff_time=0.294158203125,
            consumption_Ws=0.10,
            epoch=0.0,
        ),
        _row(
            event="Data Request",
            run=2,
            diff_time=0.294158203125,
            consumption_Ws=0.20,
            epoch=5.0,
        ),
        _row(
            event="Data Request",
            run=2,
            diff_time=1.83612084960938,
            consumption_Ws=0.30,
            epoch=10.0,
        ),
        _row(
            event="Data Request",
            run=2,
            diff_time=1.83612084960938,
            consumption_Ws=0.40,
            epoch=15.0,
        ),
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "energy_measurements_fig4.csv", index=False)

    result = VomhoffCellularEnergyAdapter(RECORD, tmp_path).harmonize()

    assert not result.warnings
    assert len(result.observations) == 2
    assert result.observations["observation_id"].is_unique
    durations = sorted(result.observations["raw_duration_s"].tolist())
    energies = sorted(result.observations["raw_energy_j"].tolist())
    assert durations == [0.294158203125, 1.83612084960938]
    assert energies == [0.30000000000000004, 0.7]
    assert set(result.observations["source_diff_time_s"]) == set(durations)


def test_observation_ids_retain_raw_protocol_key(tmp_path: Path):
    rows = [
        _row(
            event="Data Request",
            run=1,
            application_protocol="mqtt",
            diff_time=1.0,
            consumption_Ws=0.1,
        ),
        _row(
            event="Data Request",
            run=1,
            application_protocol="MQTT ",
            diff_time=1.0,
            consumption_Ws=0.2,
            epoch=5.0,
        ),
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "energy_measurements_fig4.csv", index=False)

    result = VomhoffCellularEnergyAdapter(RECORD, tmp_path).harmonize()

    # The source groups are preserved even when their normalised protocol labels
    # are the same. IDs must remain unique and provenance must not be lost.
    assert len(result.observations) == 2
    assert result.observations["observation_id"].is_unique
    assert set(result.observations["application_protocol"]) == {"MQTT"}


def test_missing_group_values_merge_across_csv_chunks(tmp_path: Path):
    rows = [
        _row(
            application_protocol="auth",
            event="Idle Connected",
            run=26,
            diff_time=59.9890461425781,
            consumption_Ws=1.0,
            current_As=0.1,
            data=None,
            epoch=0.0,
            timestamp="2023-01-31T14:29:44.580Z",
        ),
        _row(
            application_protocol="auth",
            event="Idle Connected",
            run=26,
            diff_time=59.9890461425781,
            consumption_Ws=2.0,
            current_As=0.2,
            data=None,
            epoch=5.0,
            timestamp="2023-01-31T14:30:23.170Z",
        ),
    ]
    frame = pd.DataFrame(rows).drop(columns=["data"])
    frame.to_csv(tmp_path / "energy_measurements_fig3.csv", index=False)

    adapter = VomhoffCellularEnergyAdapter(RECORD, tmp_path)
    adapter.chunksize = 1
    result = adapter.harmonize()

    assert not result.warnings
    assert len(result.observations) == 1
    assert result.observations["observation_id"].is_unique
    observation = result.observations.iloc[0]
    assert observation["sample_count"] == 2
    assert math.isclose(observation["raw_energy_j"], 3.0)
    assert math.isclose(observation["energy_j"], 1.5)
    assert observation["timestamp_utc"] == "2023-01-31T14:29:44.580Z"
