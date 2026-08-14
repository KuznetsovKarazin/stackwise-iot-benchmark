from __future__ import annotations

import hashlib
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .base import AdapterResult, BaseAdapter
from .generic import GenericPowerAdapter, GenericSignalAdapter
from .utils import numeric


class InSecTTPowerAdapter(BaseAdapter):
    """Harmonise the public InSecTT WSN high-resolution current traces.

    The dataset contains four ZIP-compressed CSV traces (BLE, OpenThread,
    Ephesos, and UWB). Each CSV has one timestamp column in milliseconds and
    five current columns in microamperes for communication periods of
    100/200/400/800/1600 ms. The sampling interval is 0.01 ms = 10 us and each
    configuration is measured for approximately 60 seconds.

    The dataset README does not state the PPK II source voltage. Therefore this
    adapter deliberately does *not* infer watts or joules from current. It
    reports current statistics and integrated charge. Power/energy calibration
    against the related publication is handled as a separate validation step.
    """

    chunksize = 500_000
    timestamp_scale_s = 1e-3  # source timestamp is in milliseconds
    expected_sample_period_s = 10e-6
    expected_periods_ms = (100, 200, 400, 800, 1600)
    payload_by_period_ms = {100: 2, 200: 4, 400: 8, 800: 16, 1600: 32}

    technology_by_stem = {
        "ble": "BLE",
        "openthread": "Thread",
        "thread": "Thread",
        "ephesos": "EPhESOS",
        "ephesos": "EPhESOS",
        "uwb": "UWB",
    }

    device_by_technology = {
        "BLE": "Nordic nRF52840 Development Kit",
        "Thread": "Nordic nRF52840 Development Kit",
        "EPhESOS": "Nordic nRF52840 Development Kit",
        "UWB": "nRF52832 + Qorvo DW1000 board",
    }

    radio_by_technology = {
        "BLE": "nRF52840 LE 1M PHY",
        "Thread": "nRF52840 IEEE 802.15.4 PHY",
        "EPhESOS": "nRF52840 LE 1M PHY",
        "UWB": "Qorvo DW1000",
    }

    def infer_technology(self, text: str) -> str:
        stem = Path(text).stem.casefold()
        for token, technology in self.technology_by_stem.items():
            if token in stem:
                return technology
        return super().infer_technology(text)

    @staticmethod
    def _source_member(archive: zipfile.ZipFile) -> str:
        members = [info.filename for info in archive.infolist() if not info.is_dir()]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {len(members)}: {members[:10]}")
        return members[0]

    @staticmethod
    def _current_columns(columns: list[str]) -> dict[int, str]:
        found: dict[int, str] = {}
        for column in columns:
            match = re.fullmatch(r"current_(100|200|400|800|1600)ms", str(column).strip())
            if match:
                found[int(match.group(1))] = column
        return found

    @staticmethod
    def _empty_stats() -> dict[str, float | int]:
        return {
            "count": 0,
            "sum_ua": 0.0,
            "sumsq_ua": 0.0,
            "min_ua": np.inf,
            "max_ua": -np.inf,
        }

    def _read_archive(self, path: Path) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
        warnings: list[str] = []
        technology = self.infer_technology(path.name)
        if technology == "UNKNOWN":
            return [], [f"{path.name}: could not infer technology"], {}

        with zipfile.ZipFile(path) as archive:
            try:
                member = self._source_member(archive)
            except ValueError as exc:
                return [], [f"{path.name}: {exc}"], {}

            with archive.open(member) as stream:
                header = pd.read_csv(stream, nrows=0)
            columns = [str(column).strip() for column in header.columns]
            if "timestamp" not in columns:
                return [], [f"{path.name}: missing timestamp column"], {}
            current_columns = self._current_columns(columns)
            missing_periods = sorted(set(self.expected_periods_ms) - set(current_columns))
            if missing_periods:
                return [], [f"{path.name}: missing current columns for periods {missing_periods}"], {}

            stats = {period: self._empty_stats() for period in self.expected_periods_ms}
            sample_periods: list[float] = []
            timestamp_min_ms: float | None = None
            timestamp_max_ms: float | None = None
            source_rows = 0

            usecols = ["timestamp"] + [current_columns[p] for p in self.expected_periods_ms]
            with archive.open(member) as stream:
                reader = pd.read_csv(
                    stream,
                    usecols=usecols,
                    chunksize=self.chunksize,
                    low_memory=False,
                )
                for chunk in reader:
                    source_rows += len(chunk)
                    timestamps_ms = numeric(chunk["timestamp"])
                    finite_t = timestamps_ms[np.isfinite(timestamps_ms)]
                    if not finite_t.empty:
                        local_min = float(finite_t.min())
                        local_max = float(finite_t.max())
                        timestamp_min_ms = local_min if timestamp_min_ms is None else min(timestamp_min_ms, local_min)
                        timestamp_max_ms = local_max if timestamp_max_ms is None else max(timestamp_max_ms, local_max)
                        diffs_ms = finite_t.diff().dropna()
                        positive = diffs_ms[diffs_ms > 0]
                        if not positive.empty:
                            sample_periods.append(float(positive.median()) * self.timestamp_scale_s)

                    for period_ms, column in current_columns.items():
                        values = numeric(chunk[column])
                        values = values[np.isfinite(values)]
                        if values.empty:
                            continue
                        accumulator = stats[period_ms]
                        accumulator["count"] += int(len(values))
                        accumulator["sum_ua"] += float(values.sum())
                        accumulator["sumsq_ua"] += float(np.square(values.to_numpy(dtype=float)).sum())
                        accumulator["min_ua"] = min(float(accumulator["min_ua"]), float(values.min()))
                        accumulator["max_ua"] = max(float(accumulator["max_ua"]), float(values.max()))

        if not sample_periods:
            sample_period_s = self.expected_sample_period_s
            warnings.append(f"{path.name}: sample period could not be inferred; using documented 10 us")
        else:
            sample_period_s = float(np.median(sample_periods))
            relative_error = abs(sample_period_s - self.expected_sample_period_s) / self.expected_sample_period_s
            if relative_error > 0.01:
                warnings.append(
                    f"{path.name}: inferred sample period {sample_period_s:.12g} s differs from documented 10 us"
                )

        rows: list[dict[str, Any]] = []
        for period_ms in self.expected_periods_ms:
            accumulator = stats[period_ms]
            count = int(accumulator["count"])
            if count == 0:
                warnings.append(f"{path.name}: no finite current samples for {period_ms} ms")
                continue

            mean_ua = float(accumulator["sum_ua"]) / count
            if count > 1:
                variance_ua2 = (
                    float(accumulator["sumsq_ua"]) - count * mean_ua**2
                ) / (count - 1)
                std_ua = float(np.sqrt(max(variance_ua2, 0.0)))
            else:
                std_ua = None

            duration_s = count * sample_period_s
            mean_current_a = mean_ua * 1e-6
            charge_c = float(accumulator["sum_ua"]) * 1e-6 * sample_period_s
            payload_bytes = self.payload_by_period_ms[period_ms]

            base = self.base_fields(path, technology)
            row: dict[str, Any] = {
                **base,
                "observation_id": f"{self.record['id']}:{technology.casefold()}:{period_ms}ms",
                "access_network": technology,
                "application_protocol": "UDP" if technology == "Thread" else None,
                "device_model": self.device_by_technology.get(technology),
                "radio_module": self.radio_by_technology.get(technology),
                "firmware_version": "nRF Connect SDK 2.0.2" if technology in {"BLE", "Thread"} else None,
                "payload_bytes": payload_bytes,
                "upper_layer_bytes": payload_bytes,
                "direction": "uplink",
                "reporting_interval_s": period_ms / 1000.0,
                "session_policy": "periodic",
                "confirmation_mode": "unconfirmed",
                "duration_s": duration_s,
                "sample_count": count,
                "current_a": mean_current_a,
                "peak_current_a": float(accumulator["max_ua"]) * 1e-6,
                "voltage_v": None,
                "power_w": None,
                "mean_power_w": None,
                "energy_j": None,
                "notes": (
                    "InSecTT 60 s full-device current trace; no acknowledgements/retransmissions. "
                    "Power and energy are not computed because the dataset README does not state "
                    "the PPK II source voltage."
                ),
                "source_archive": str(path.relative_to(self.raw_dir)),
                "source_member": member,
                "source_current_column": current_columns[period_ms],
                "source_timestamp_unit": "ms",
                "source_current_unit": "uA",
                "source_update_period_ms": period_ms,
                "source_payload_bytes": payload_bytes,
                "sample_period_s": sample_period_s,
                "mean_current_ua": mean_ua,
                "std_current_ua": std_ua,
                "min_current_ua": float(accumulator["min_ua"]),
                "max_current_ua": float(accumulator["max_ua"]),
                "charge_c": charge_c,
                "trace_start_ms": timestamp_min_ms,
                "trace_end_ms": timestamp_max_ms,
            }
            rows.append(row)

        metadata = {
            "source_archive": str(path.relative_to(self.raw_dir)),
            "source_member": member,
            "technology": technology,
            "source_rows": source_rows,
            "sample_period_s": sample_period_s,
            "timestamp_unit": "ms",
            "current_unit": "uA",
            "measurement_duration_s": max((int(stats[p]["count"]) for p in self.expected_periods_ms), default=0)
            * sample_period_s,
        }
        return rows, warnings, metadata

    def harmonize(self) -> AdapterResult:
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        files_meta: list[dict[str, Any]] = []

        archives = sorted(self.raw_dir.rglob("*.zip"))
        if not archives:
            return AdapterResult(
                self.finalise(pd.DataFrame()),
                ["No InSecTT inner ZIP archives found after extraction"],
                {"adapter": self.__class__.__name__},
            )

        for path in archives:
            technology = self.infer_technology(path.name)
            if technology == "UNKNOWN":
                # Ignore unrelated archives rather than treating the outer container as a trace.
                continue
            try:
                file_rows, file_warnings, metadata = self._read_archive(path)
            except Exception as exc:
                warnings.append(f"{path.name}: failed to read InSecTT trace: {exc}")
                continue
            rows.extend(file_rows)
            warnings.extend(file_warnings)
            if metadata:
                files_meta.append(metadata)

        frame = self.finalise(pd.DataFrame(rows))
        if not frame.empty:
            duplicated = int(frame["observation_id"].duplicated().sum())
            if duplicated:
                warnings.append(f"Duplicate observation IDs detected: {duplicated}")

        metadata = {
            "adapter": self.__class__.__name__,
            "aggregation_level": "technology x communication period (one 60 s trace each)",
            "source_measurement": "PPK II current trace at 100 kS/s",
            "energy_policy": "not computed: source voltage is absent from dataset README",
            "independent_replication": "one trace per technology/configuration; no replicate runs",
            "files": files_meta,
            "harmonised_rows": int(len(frame)),
            "technologies": sorted(frame["technology"].dropna().unique().tolist()) if not frame.empty else [],
            "communication_periods_ms": sorted(frame["source_update_period_ms"].dropna().unique().tolist())
            if "source_update_period_ms" in frame
            else [],
        }
        return AdapterResult(frame, warnings, metadata)


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
    fig5_idle_segment_key = "__filtered_idle__"
    missing_group_key = "__stackwise_missing__"

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
    def _key_digest(*values: object) -> str:
        payload = "|".join(repr(value) for value in values).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()[:12]

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

            # The authors' R scripts treat distinct ``diff_time`` values as
            # distinct run-phase segments.  Preserve that key instead of
            # collapsing repeated event labels within a run.  Figure 5 idle
            # duration is reconstructed after filtering, so all retained idle
            # samples for a run/protocol use one sentinel segment.
            chunk["_segment_duration_s"] = chunk["diff_time"].astype(object)
            if figure == 5:
                protocol = chunk["application_protocol"].astype(str).str.casefold()
                idle = chunk["event"].astype(str).str.casefold().eq("idle")
                chunk.loc[
                    idle & protocol.isin(["http", "mqtt"]),
                    "_segment_duration_s",
                ] = self.fig5_idle_segment_key

            group_columns = [
                "run",
                "event",
                "rat_type",
                "application_protocol",
                "data",
                "_segment_duration_s",
            ]
            grouped = chunk.groupby(group_columns, dropna=False, sort=False)
            for key, group in grouped:
                # pandas represents missing group values with NaN. NaN is not
                # equal to itself, so raw group tuples can split one logical
                # source group when it crosses CSV chunk boundaries.
                canonical_key = tuple(
                    self.missing_group_key if pd.isna(value) else value
                    for value in key
                )
                accumulator = accumulators[canonical_key]
                sample_count = int(len(group))
                accumulator["sample_count"] += sample_count
                accumulator["sum_current"] += float(group["current"].sum(skipna=True))
                accumulator["sum_voltage"] += float(group["voltage"].sum(skipna=True))
                local_peak = float(group["current"].max(skipna=True))
                if np.isfinite(local_peak):
                    accumulator["peak_current"] = max(accumulator["peak_current"], local_peak)
                accumulator["sum_charge_as"] += float(group["current_As"].sum(skipna=True))
                accumulator["sum_energy_j"] += float(group["consumption_Ws"].sum(skipna=True))
                accumulator["timestamp_min"] = self._merge_timestamp(
                    accumulator["timestamp_min"], group["timestamp"]
                )

        rows: list[dict[str, Any]] = []
        for key, accumulator in accumulators.items():
            run, event, rat_type, source_protocol, data_value, source_duration_key = key
            source_protocol = (
                np.nan if source_protocol == self.missing_group_key else source_protocol
            )
            data_value = np.nan if data_value == self.missing_group_key else data_value
            source_duration_key = (
                np.nan
                if source_duration_key == self.missing_group_key
                else source_duration_key
            )
            event_text = str(event).strip()
            event_normal = event_text.casefold()
            technology = self._normalise_technology(rat_type)
            protocol = self._normalise_protocol(source_protocol, figure)
            payload_bytes = self._payload_bytes(data_value)
            raw_duration = (
                None
                if source_duration_key == self.fig5_idle_segment_key
                or pd.isna(source_duration_key)
                else float(source_duration_key)
            )
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
                    self._slug(rat_type),
                    self._slug(source_protocol),
                    self._slug(event_text),
                    self._slug(data_value),
                    f"duration-{self._slug(source_duration_key)}",
                    f"key-{self._key_digest(run, event, rat_type, source_protocol, data_value, source_duration_key)}",
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
                    "source_diff_time_s": (
                        None
                        if source_duration_key == self.fig5_idle_segment_key
                        or pd.isna(source_duration_key)
                        else float(source_duration_key)
                    ),
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
