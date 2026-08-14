from __future__ import annotations

from pathlib import Path
import math
import zipfile

import pandas as pd
import pytest

from stackwise.adapters.specific import InSecTTPowerAdapter


RECORD = {
    "id": "insectt_wsn_power_2023",
    "doi": "10.5281/zenodo.7762712",
    "evidence_grade": "A",
    "technologies": ["BLE", "Thread", "UWB", "EPhESOS"],
    "measurement_boundaries": ["full_device_cycle"],
    "licence": {"id": "CC-BY-4.0"},
}


def _write_trace(tmp_path: Path, archive_name: str, member_name: str | None = None) -> Path:
    frame = pd.DataFrame(
        {
            "timestamp": [0.00, 0.01, 0.02, 0.03],
            "current_100ms": [10.0, 20.0, 30.0, 40.0],
            "current_200ms": [5.0, 5.0, 5.0, 5.0],
            "current_400ms": [4.0, 4.0, 4.0, 4.0],
            "current_800ms": [3.0, 3.0, 3.0, 3.0],
            "current_1600ms": [2.0, 2.0, 2.0, 2.0],
        }
    )
    csv = frame.to_csv(index=False).encode("utf-8")
    path = tmp_path / archive_name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name or Path(archive_name).stem, csv)
    return path


def test_insectt_nested_zip_current_and_charge(tmp_path: Path):
    _write_trace(tmp_path, "BLE.zip", "BLE")
    result = InSecTTPowerAdapter(RECORD, tmp_path).harmonize()

    assert not result.warnings
    assert len(result.observations) == 5
    assert result.observations["observation_id"].is_unique

    row = result.observations.loc[result.observations["source_update_period_ms"] == 100].iloc[0]
    assert row["technology"] == "BLE"
    assert row["payload_bytes"] == 2
    assert math.isclose(row["reporting_interval_s"], 0.1)
    assert math.isclose(row["sample_period_s"], 10e-6, rel_tol=1e-9)
    assert row["sample_count"] == 4
    assert math.isclose(row["duration_s"], 40e-6, rel_tol=1e-9)
    assert math.isclose(row["mean_current_ua"], 25.0)
    assert math.isclose(row["current_a"], 25e-6)
    assert math.isclose(row["peak_current_a"], 40e-6)
    assert math.isclose(row["charge_c"], (10 + 20 + 30 + 40) * 1e-6 * 10e-6)
    assert pd.isna(row["energy_j"])
    assert pd.isna(row["mean_power_w"])


def test_insectt_period_to_payload_mapping(tmp_path: Path):
    _write_trace(tmp_path, "OpenThread.zip", "OpenThread")
    result = InSecTTPowerAdapter(RECORD, tmp_path).harmonize()
    mapping = dict(zip(result.observations["source_update_period_ms"], result.observations["payload_bytes"]))
    assert mapping == {100: 2, 200: 4, 400: 8, 800: 16, 1600: 32}
    assert set(result.observations["technology"]) == {"Thread"}
    assert set(result.observations["transport_protocol"]) == {"UDP"}
    assert result.observations["application_protocol"].isna().all()


@pytest.mark.parametrize(
    ("archive_name", "expected"),
    [("BLE.zip", "BLE"), ("OpenThread.zip", "Thread"), ("Ephesos.zip", "EPhESOS"), ("UWB.zip", "UWB")],
)
def test_insectt_technology_mapping(tmp_path: Path, archive_name: str, expected: str):
    _write_trace(tmp_path, archive_name)
    result = InSecTTPowerAdapter(RECORD, tmp_path).harmonize()
    assert not result.warnings
    assert set(result.observations["technology"]) == {expected}


def test_insectt_rejects_incomplete_trace(tmp_path: Path):
    frame = pd.DataFrame({"timestamp": [0.0, 0.01], "current_100ms": [1.0, 2.0]})
    with zipfile.ZipFile(tmp_path / "BLE.zip", "w") as archive:
        archive.writestr("BLE", frame.to_csv(index=False))
    result = InSecTTPowerAdapter(RECORD, tmp_path).harmonize()
    assert result.observations.empty
    assert any("missing current columns" in warning for warning in result.warnings)
