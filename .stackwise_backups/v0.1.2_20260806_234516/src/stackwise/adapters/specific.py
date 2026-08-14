from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .base import AdapterResult, BaseAdapter
from .generic import GenericPowerAdapter, GenericSignalAdapter
from .utils import numeric


class InSecTTPowerAdapter(GenericPowerAdapter):
    """Discover power traces recursively inside the extracted InSecTT archive."""

    def infer_technology(self, text: str) -> str:
        lowered = text.casefold()
        if "thread" in lowered or "openthread" in lowered:
            return "Thread"
        if "ble" in lowered or "bluetooth" in lowered:
            return "BLE"
        if "uwb" in lowered:
            return "UWB"
        if "ephes" in lowered:
            return "EPhESOS"
        return super().infer_technology(text)


class LrFhssPowerAdapter(GenericPowerAdapter):
    skiprows = 3

    def base_fields(self, source_file: Path, technology: str | None = None):
        base = super().base_fields(source_file, "LoRaWAN-LR-FHSS")
        upper = source_file.stem.upper()
        base["confirmation_mode"] = "confirmed" if upper.startswith("ACK") else "unconfirmed"
        match = re.search(r"DR(8|9|10|11)", upper)
        if match:
            base["notes"] = f"LR-FHSS DR{match.group(1)}"
        return base


class VomhoffCellularEnergyAdapter(BaseAdapter):
    """Harmonise the public NB-IoT/LTE-M phase-level power traces.

    The source CSV files contain 5 ms samples. ``current_As`` is the charge
    contribution of one sample and ``consumption_Ws`` is its energy contribution
    in joules. The adapter aggregates one canonical observation per experimental
    run and phase and reproduces the normalisation rules in the authors' R scripts:

    * Figure 3: ``Idle Connected`` energy and duration are divided by two.
    * Figure 4: ``Idle`` is normalised to 20 seconds.
    * Figure 5: HTTP/MQTT idle samples are filtered exactly as in ``fig5.R`` and
      then normalised to 20 seconds.

    Raw energy and duration are retained in additional provenance columns.
    """

    chunksize = 500_000
    sample_period_s = 0.005

    required_columns = {
        "epoch",
        "diff",
        "current",
        "voltage",
        "rat_type",
        "application_protocol",
        "timestamp",
        "current_As",
        "consumption_Ws",
        "event",
        "run",
        "diff_time",
    }

    event_boundaries = {
        "changing rat type": "authentication",
        "connecting": "connection",
        "idle connected": "idle",
        "idle not connected": "idle",
        "connection establishment": "connection",
        "data request": "transfer",
        "data download": "transfer",
        "postprocessing": "transfer",
        "standby": "standby",
        "idle": "idle",
    }

    direction_by_event = {
        "data request": "uplink",
        "data download": "downlink",
    }

    @staticmethod
    def _normalise_technology(value: object) -> str:
        text = str(value).strip().casefold().replace("_", "-")
        mapping = {
            "nb-iot": "NB-IoT",
            "nbiot": "NB-IoT",
            "lte-m": "LTE-M",
            "ltem": "LTE-M",
            "cat-m1": "LTE-M",
        }
        return mapping.get(text, str(value).strip())

    @staticmethod
    def _normalise_protocol(value: object, figure: int) -> str | None:
        text = str(value).strip().casefold()
        if figure == 3 or text in {"", "nan", "none", "auth"}:
            return None
        return text.upper()

    @staticmethod
    def _payload_bytes(value: object) -> int | None:
        text = str(value).strip().casefold()
        if text in {"", "nan", "none"}:
            return None
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([kmg]?)b?(?:\.data)?", text)
        if not match:
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmg]?)", text)
        if not match:
            return None
        number = float(match.group(1))
        factor = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[match.group(2)]
        return int(round(number * factor))

    @staticmethod
    def _slug(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(value).strip().casefold()).strip("-") or "none"

    @staticmethod
    def _figure_number(path: Path) -> int | None:
        match = re.search(r"fig([345])", path.stem.casefold())
        return int(match.group(1)) if match else None

    @staticmethod
    def _empty_accumulator() -> dict[str, Any]:
        return {
            "sample_count": 0,
            "sum_current": 0.0,
            "sum_voltage": 0.0,
            "peak_current": -np.inf,
            "sum_charge_as": 0.0,
            "sum_energy_j": 0.0,
            "source_duration_values": set(),
            "timestamp_min": None,
        }

    @staticmethod
    def _merge_timestamp(current: str | None, values: pd.Series) -> str | None:
        non_null = values.dropna().astype(str)
        if non_null.empty:
            return current
        candidate = non_null.min()
        return candidate if current is None or candidate < current else current

    def _validate_columns(self, path: Path) -> tuple[list[str], list[str]]:
        columns = list(pd.read_csv(path, nrows=0).columns)
        missing = sorted(self.required_columns - set(columns))
        return columns, missing

    def _find_fig5_min_epoch(self, path: Path) -> dict[tuple[object, object], float]:
        minima: dict[tuple[object, object], float] = {}
        usecols = ["epoch", "run", "event"]
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=self.chunksize, low_memory=False):
            chunk["epoch"] = numeric(chunk["epoch"])
            grouped = chunk.groupby(["run", "event"], dropna=False)["epoch"].min()
            for key, value in grouped.items():
                if pd.isna(value):
                    continue
                key_tuple = key if isinstance(key, tuple) else (key, None)
                previous = minima.get(key_tuple)
                numeric_value = float(value)
                minima[key_tuple] = numeric_value if previous is None else min(previous, numeric_value)
        return minima

    def _aggregate_file(self, path: Path, figure: int) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
        columns, missing = self._validate_columns(path)
        warnings: list[str] = []
        if missing:
            return [], [f"{path.name}: missing required columns {missing}"], {}

        has_data = "data" in columns
        usecols = sorted(self.required_columns | ({"data"} if has_data else set()))
        minima = self._find_fig5_min_epoch(path) if figure == 5 else {}

        accumulators: dict[tuple[Any, ...], dict[str, Any]] = defaultdict(self._empty_accumulator)
        fig5_idle_match_counts: dict[tuple[Any, ...], int] = defaultdict(int)
        source_rows = 0
        retained_rows = 0

        for chunk in pd.read_csv(path, usecols=usecols, chunksize=self.chunksize, low_memory=False):
            source_rows += len(chunk)
            for column in ["epoch", "current", "voltage", "current_As", "consumption_Ws", "diff_time"]:
                chunk[column] = numeric(chunk[column])

            chunk["data"] = chunk["data"] if has_data else pd.NA

            if figure == 5:
                min_epoch = pd.Series(
                    [minima.get((run, event), np.nan) for run, event in zip(chunk["run"], chunk["event"])],
                    index=chunk.index,
                    dtype=float,
                )
                elapsed_ms = chunk["epoch"] - min_epoch
                protocol = chunk["application_protocol"].astype(str).str.casefold()
                idle = chunk["event"].astype(str).str.casefold().eq("idle")
                targeted = idle & protocol.isin(["http", "mqtt"])
                keep_targeted = chunk["current"].le(0.063).fillna(False) | elapsed_ms.lt(5000).fillna(False)

                match_rows = chunk.loc[targeted & keep_targeted, ["run", "event", "application_protocol"]]
                if not match_rows.empty:
                    counts = match_rows.groupby(["run", "event", "application_protocol"], dropna=False).size()
                    for key, count in counts.items():
                        fig5_idle_match_counts[key] += int(count)

                chunk = chunk.loc[~targeted | keep_targeted].copy()

            chunk = chunk.loc[chunk["current"].notna()].copy()
            retained_rows += len(chunk)
            if chunk.empty:
                continue

            group_columns = ["run", "event", "rat_type", "application_protocol", "data"]
            grouped = chunk.groupby(group_columns, dropna=False, sort=False)
            for key, group in grouped:
                accumulator = accumulators[key]
                sample_count = int(len(group))
                accumulator["sample_count"] += sample_count
                accumulator["sum_current"] += float(group["current"].sum(skipna=True))
                accumulator["sum_voltage"] += float(group["voltage"].sum(skipna=True))
                local_peak = float(group["current"].max(skipna=True))
                if np.isfinite(local_peak):
                    accumulator["peak_current"] = max(accumulator["peak_current"], local_peak)
                accumulator["sum_charge_as"] += float(group["current_As"].sum(skipna=True))
                accumulator["sum_energy_j"] += float(group["consumption_Ws"].sum(skipna=True))
                accumulator["source_duration_values"].update(
                    float(value) for value in group["diff_time"].dropna().unique()
                )
                accumulator["timestamp_min"] = self._merge_timestamp(
                    accumulator["timestamp_min"], group["timestamp"]
                )

        rows: list[dict[str, Any]] = []
        for key, accumulator in accumulators.items():
            run, event, rat_type, source_protocol, data_value = key
            event_text = str(event).strip()
            event_normal = event_text.casefold()
            technology = self._normalise_technology(rat_type)
            protocol = self._normalise_protocol(source_protocol, figure)
            payload_bytes = self._payload_bytes(data_value)
            durations = sorted(accumulator["source_duration_values"])
            if len(durations) > 1:
                warnings.append(
                    f"{path.name}: run={run!r}, event={event_text!r} has multiple diff_time values {durations[:5]}"
                )
            raw_duration = float(np.mean(durations)) if durations else None
            raw_energy = float(accumulator["sum_energy_j"])
            normalised_duration = raw_duration
            normalised_energy = raw_energy
            normalisation = "none"
            normalisation_factor = 1.0

            if figure == 3 and event_normal == "idle connected":
                normalised_energy = raw_energy / 2.0
                normalised_duration = raw_duration / 2.0 if raw_duration is not None else None
                normalisation = "authors_fig3_idle_connected_divide_by_2"
                normalisation_factor = 0.5
            elif figure == 4 and event_normal == "idle" and raw_duration and raw_duration > 0:
                normalisation_factor = 20.0 / raw_duration
                normalised_energy = raw_energy * normalisation_factor
                normalised_duration = 20.0
                normalisation = "authors_fig4_idle_to_20_s"
            elif figure == 5 and event_normal == "idle":
                count_key = (run, event, source_protocol)
                filtered_duration = fig5_idle_match_counts.get(count_key, 0) * self.sample_period_s
                if filtered_duration <= 0:
                    warnings.append(
                        f"{path.name}: no Figure 5 idle duration reconstructed for run={run!r}, protocol={source_protocol!r}"
                    )
                    normalised_duration = raw_duration
                else:
                    raw_duration = filtered_duration
                    normalisation_factor = 20.0 / filtered_duration
                    normalised_energy = raw_energy * normalisation_factor
                    normalised_duration = 20.0
                    normalisation = "authors_fig5_filtered_idle_to_20_s"

            sample_count = int(accumulator["sample_count"])
            mean_current = accumulator["sum_current"] / sample_count if sample_count else None
            mean_voltage = accumulator["sum_voltage"] / sample_count if sample_count else None
            mean_power = (
                normalised_energy / normalised_duration
                if normalised_duration is not None and normalised_duration > 0
                else None
            )
            boundary = self.event_boundaries.get(event_normal, "full_device_cycle")
            base = self.base_fields(path, technology)
            observation_id = ":".join(
                [
                    self.record["id"],
                    f"fig{figure}",
                    f"run-{self._slug(run)}",
                    self._slug(technology),
                    self._slug(protocol),
                    self._slug(event_text),
                    self._slug(data_value),
                ]
            )
            notes_parts = [
                f"Source Figure {figure}",
                f"phase={event_text}",
                f"normalisation={normalisation}",
            ]
            if figure == 3:
                notes_parts.append("source application_protocol='auth' is not treated as an application protocol")

            row: dict[str, Any] = dict(base)
            row.update(
                {
                    "observation_id": observation_id,
                    "technology": technology,
                    "access_network": technology,
                    "application_protocol": protocol,
                    "payload_bytes": payload_bytes,
                    "direction": self.direction_by_event.get(event_normal),
                    "timestamp_utc": accumulator["timestamp_min"],
                    "duration_s": normalised_duration,
                    "sample_count": sample_count,
                    "voltage_v": mean_voltage,
                    "current_a": mean_current,
                    "peak_current_a": (
                        float(accumulator["peak_current"])
                        if np.isfinite(accumulator["peak_current"])
                        else None
                    ),
                    "mean_power_w": mean_power,
                    "energy_j": normalised_energy,
                    "measurement_boundary": boundary,
                    "notes": "; ".join(notes_parts),
                    # Provenance fields retained beyond the canonical minimum.
                    "source_figure": figure,
                    "source_run": run,
                    "source_event": event_text,
                    "source_application_protocol": (
                        None if pd.isna(source_protocol) else str(source_protocol)
                    ),
                    "source_data_object": None if pd.isna(data_value) else str(data_value),
                    "raw_duration_s": raw_duration,
                    "raw_energy_j": raw_energy,
                    "normalisation_factor": normalisation_factor,
                    "normalisation_rule": normalisation,
                    "charge_as": float(accumulator["sum_charge_as"]),
                }
            )
            rows.append(row)

        metadata = {
            "source_file": path.name,
            "source_figure": figure,
            "source_rows": source_rows,
            "retained_current_samples": retained_rows,
            "harmonised_run_phase_rows": len(rows),
            "sample_period_s": self.sample_period_s,
            "source_units": {
                "current": "A",
                "voltage": "V",
                "current_As": "A*s per sample",
                "consumption_Ws": "W*s = J per sample",
                "epoch": "ms since Unix epoch",
            },
        }
        return rows, warnings, metadata

    def harmonize(self) -> AdapterResult:
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        metadata: dict[str, Any] = {
            "adapter": "VomhoffCellularEnergyAdapter",
            "aggregation_level": "experimental run x phase",
            "source_normalisation": "authors' R scripts fig3.R, fig4.R, and fig5.R",
            "files": [],
        }

        csv_paths = [
            path
            for path in self.discover((".csv",))
            if re.search(r"energy_measurements_fig[345]", path.name.casefold())
        ]
        if not csv_paths:
            return AdapterResult(
                self.finalise(pd.DataFrame()),
                ["No energy_measurements_fig3/fig4/fig5 CSV files found"],
                metadata,
            )

        for path in csv_paths:
            figure = self._figure_number(path)
            if figure is None:
                warnings.append(f"Could not infer source figure from {path.name}")
                continue
            file_rows, file_warnings, file_metadata = self._aggregate_file(path, figure)
            rows.extend(file_rows)
            warnings.extend(file_warnings)
            metadata["files"].append(file_metadata)

        observations = self.finalise(pd.DataFrame(rows))
        if observations.empty:
            warnings.append("No run-phase observations were produced")
        else:
            duplicates = observations["observation_id"].duplicated(keep=False)
            if duplicates.any():
                warnings.append(
                    f"Duplicate observation IDs detected: {observations.loc[duplicates, 'observation_id'].nunique()}"
                )
        metadata["harmonised_rows"] = len(observations)
        metadata["technologies"] = sorted(observations["technology"].dropna().unique().tolist()) if not observations.empty else []
        metadata["application_protocols"] = sorted(
            observations["application_protocol"].dropna().unique().tolist()
        ) if not observations.empty else []
        return AdapterResult(observations, warnings, metadata)


class LoedGatewayAdapter(GenericSignalAdapter):
    """Parse flat LoED exports and common ChirpStack-style JSON columns."""

    def harmonize(self) -> AdapterResult:
        result = super().harmonize()
        frame = result.observations
        if not frame.empty:
            frame["technology"] = "LoRaWAN"
            frame["measurement_boundary"] = "gateway_observation"
        return AdapterResult(frame, result.warnings, result.metadata)


class CellularCoverageAdapter(GenericSignalAdapter):
    def harmonize(self) -> AdapterResult:
        result = super().harmonize()
        if not result.observations.empty:
            result.observations["measurement_boundary"] = result.observations["measurement_boundary"].fillna("network_coverage")
        return result
