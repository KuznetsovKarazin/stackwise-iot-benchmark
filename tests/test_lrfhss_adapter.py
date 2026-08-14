from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stackwise.adapters.specific import LrFhssPowerAdapter


RECORD = {
    "id": "lorawan_lrfhss_energy_2024",
    "doi": "10.5281/zenodo.13838241",
    "evidence_grade": "A",
    "technologies": ["LoRaWAN-LR-FHSS"],
    "measurement_boundaries": ["end_device_radio_cycle"],
    "licence": {"id": "CC-BY-4.0"},
}


def write_trace(path: Path, ack: bool, dr: int, currents: list[float]) -> None:
    mode = "With ACK" if ack else "Without ACK"
    dt = 2.048e-05
    lines = [
        f"PA: 14585A, ED: LR1121, {mode}, DR{dr}",
        f"Sampling Period:{dt}",
        "Date:Tue Jun 18 18:47:23 2024",
        "Time,File1 Instrument A Channel 2 Current Avg",
    ]
    for idx, current in enumerate(currents):
        lines.append(f"{idx * dt:.10g},{current:.12g}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_lrfhss_metadata_and_energy(tmp_path: Path):
    currents = [0.5e-6, 0.5e-6, 25.0e-3, 26.0e-3, 0.5e-6]
    write_trace(tmp_path / "ACKDR8.csv", True, 8, currents)
    result = LrFhssPowerAdapter(RECORD, tmp_path).harmonize()
    assert len(result.observations) == 1
    row = result.observations.iloc[0]
    assert row["technology"] == "LoRaWAN-LR-FHSS"
    assert row["confirmation_mode"] == "confirmed"
    assert row["source_dr_index"] == 8
    assert row["source_coding_rate"] == "1/3"
    assert row["source_physical_bit_rate_bps"] == 162
    assert row["payload_bytes"] == 4
    assert row["tx_power_dbm"] == 14.0
    assert row["voltage_v"] == 3.3
    assert math.isclose(row["inferred_sampling_period_s"], 2.048e-05, rel_tol=1e-9)
    expected_charge = float(np.trapezoid(np.asarray(currents), dx=2.048e-05) if hasattr(np, "trapezoid") else np.trapz(np.asarray(currents), dx=2.048e-05))
    assert math.isclose(row["trace_charge_c"], expected_charge, rel_tol=1e-9)
    assert math.isclose(row["energy_j"], expected_charge * 3.3, rel_tol=1e-9)
    assert row["tx_plateau_sample_count"] == 2
    assert math.isclose(row["tx_plateau_mean_current_a"], 25.5e-3, rel_tol=1e-9)


@pytest.mark.parametrize(
    ("filename", "mode", "dr", "cr", "bitrate"),
    [
        ("ACKDR8.csv", "confirmed", 8, "1/3", 162),
        ("ACKDR9.csv", "confirmed", 9, "2/3", 325),
        ("noACKDR10.csv", "unconfirmed", 10, "1/3", 162),
        ("noACKDR11.csv", "unconfirmed", 11, "2/3", 325),
    ],
)
def test_lrfhss_filename_mapping(tmp_path: Path, filename: str, mode: str, dr: int, cr: str, bitrate: int):
    write_trace(tmp_path / filename, mode == "confirmed", dr, [0.5e-6, 25.7e-3, 0.5e-6])
    result = LrFhssPowerAdapter(RECORD, tmp_path).harmonize()
    row = result.observations.iloc[0]
    assert row["confirmation_mode"] == mode
    assert row["source_dr_index"] == dr
    assert row["source_coding_rate"] == cr
    assert row["source_physical_bit_rate_bps"] == bitrate


def test_lrfhss_negative_instrument_noise_is_preserved(tmp_path: Path):
    currents = [-0.2e-6, 0.5e-6, 0.7e-6, 25.7e-3]
    write_trace(tmp_path / "noACKDR8.csv", False, 8, currents)
    result = LrFhssPowerAdapter(RECORD, tmp_path).harmonize()
    row = result.observations.iloc[0]
    assert row["negative_current_fraction"] == pytest.approx(0.25)
    assert row["min_current_a"] < 0
    assert row["trace_charge_c"] > 0
