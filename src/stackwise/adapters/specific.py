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
                "transport_protocol": "UDP" if technology == "Thread" else None,
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


class LrFhssPowerAdapter(BaseAdapter):
    """Harmonise the public LR-FHSS radio-interface current traces.

    Each source CSV contains three metadata rows, followed by a two-column
    ``Time, Current`` trace sampled every 20.48 us.  File names encode ACK/noACK
    and LR-FHSS DR8--DR11.  The Zenodo record documents a 4-byte FRM payload and
    +14 dBm transmit power.  The associated Sensors paper documents that the
    LR1121 radio interface is powered from a dedicated 3.3 V supply, so joules
    can be derived without an undocumented voltage assumption.

    Canonical ``energy_j`` is the energy of the *entire captured trace*, not a
    per-message energy value.  Additional provenance columns expose the capture
    duration, low-current baseline band, TX plateau, and number of detected TX
    bursts so downstream code can decide whether a per-transaction derivation is
    justified.  No such derivation is performed silently here.
    """

    chunksize = 500_000
    expected_sample_period_s = 2.048e-05
    source_voltage_v = 3.3
    frm_payload_bytes = 4
    tx_power_dbm_value = 14.0
    tx_plateau_threshold_a = 20e-3
    tx_cluster_gap_s = 0.05
    low_current_band_abs_a = 100e-6

    dr_parameters = {
        8: {"coding_rate": "1/3", "physical_bit_rate_bps": 162},
        9: {"coding_rate": "2/3", "physical_bit_rate_bps": 325},
        10: {"coding_rate": "1/3", "physical_bit_rate_bps": 162},
        11: {"coding_rate": "2/3", "physical_bit_rate_bps": 325},
    }

    @staticmethod
    def _filename_metadata(path: Path) -> tuple[str, int]:
        upper = path.stem.upper()
        confirmation = "confirmed" if upper.startswith("ACK") else "unconfirmed"
        match = re.search(r"DR(8|9|10|11)", upper)
        if not match:
            raise ValueError(f"could not infer LR-FHSS DR from {path.name}")
        return confirmation, int(match.group(1))

    @staticmethod
    def _read_source_metadata(path: Path) -> dict[str, Any]:
        lines: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for _ in range(4):
                lines.append(stream.readline().strip())
        if len(lines) < 4 or not lines[3]:
            raise ValueError("source file does not contain the expected four-line header")

        first = [part.strip() for part in lines[0].split(",")]
        sampling_match = re.search(r"Sampling\s*Period\s*:\s*([0-9.eE+-]+)", lines[1])
        date_match = re.match(r"Date\s*:\s*(.*)", lines[2], flags=re.IGNORECASE)
        dr_match = re.search(r"DR(8|9|10|11)", lines[0], flags=re.IGNORECASE)
        ack_text = lines[0].casefold()
        source_confirmation = None
        if "without ack" in ack_text:
            source_confirmation = "unconfirmed"
        elif "with ack" in ack_text:
            source_confirmation = "confirmed"

        return {
            "power_analyzer_label": first[0].split(":", 1)[-1].strip() if first else None,
            "end_device_label": first[1].split(":", 1)[-1].strip() if len(first) > 1 else None,
            "source_confirmation_mode": source_confirmation,
            "source_dr_index": int(dr_match.group(1)) if dr_match else None,
            "source_sampling_period_s": float(sampling_match.group(1)) if sampling_match else None,
            "source_measurement_date": date_match.group(1).strip() if date_match else None,
            "source_header": lines[0],
        }

    @staticmethod
    def _trace_columns(path: Path) -> tuple[str, str]:
        header = pd.read_csv(path, skiprows=3, nrows=0)
        columns = [str(column).strip() for column in header.columns]
        if len(columns) < 2:
            raise ValueError(f"expected time/current columns, found {columns}")
        time_col = next((c for c in columns if c.casefold() == "time"), columns[0])
        current_col = next((c for c in columns if "current" in c.casefold()), columns[1])
        return time_col, current_col

    def _summarise_trace(self, path: Path) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        source_meta = self._read_source_metadata(path)
        confirmation_mode, dr_index = self._filename_metadata(path)

        if source_meta.get("source_confirmation_mode") not in {None, confirmation_mode}:
            warnings.append(
                f"{path.name}: filename confirmation mode {confirmation_mode!r} disagrees with metadata "
                f"{source_meta.get('source_confirmation_mode')!r}"
            )
        if source_meta.get("source_dr_index") not in {None, dr_index}:
            warnings.append(
                f"{path.name}: filename DR{dr_index} disagrees with metadata DR{source_meta.get('source_dr_index')}"
            )

        time_col, current_col = self._trace_columns(path)

        sample_count = 0
        sum_current = 0.0
        sumsq_current = 0.0
        min_current = np.inf
        max_current = -np.inf
        negative_count = 0
        trace_start_s: float | None = None
        trace_end_s: float | None = None
        charge_c = 0.0
        prev_time: float | None = None
        prev_current: float | None = None
        sample_period_candidates: list[float] = []

        tx_sum = 0.0
        tx_count = 0
        tx_burst_count = 0
        prev_tx_time: float | None = None

        low_sum = 0.0
        low_count = 0

        reader = pd.read_csv(
            path,
            skiprows=3,
            usecols=[time_col, current_col],
            chunksize=self.chunksize,
            low_memory=False,
        )
        for chunk in reader:
            times = numeric(chunk[time_col]).to_numpy(dtype=float)
            currents = numeric(chunk[current_col]).to_numpy(dtype=float)
            finite = np.isfinite(times) & np.isfinite(currents)
            times = times[finite]
            currents = currents[finite]
            if not len(times):
                continue

            order = np.argsort(times, kind="stable")
            if not np.all(order == np.arange(len(order))):
                times = times[order]
                currents = currents[order]
                warnings.append(f"{path.name}: non-monotonic timestamps encountered and sorted within a chunk")

            if trace_start_s is None:
                trace_start_s = float(times[0])
            trace_end_s = float(times[-1])

            if len(times) > 1:
                diffs = np.diff(times)
                positive = diffs[diffs > 0]
                if len(positive):
                    sample_period_candidates.append(float(np.median(positive)))

            if prev_time is not None and prev_current is not None and times[0] > prev_time:
                charge_c += 0.5 * (prev_current + float(currents[0])) * (float(times[0]) - prev_time)
            if len(times) > 1:
                charge_c += float(np.trapezoid(currents, times) if hasattr(np, "trapezoid") else np.trapz(currents, times))
            prev_time = float(times[-1])
            prev_current = float(currents[-1])

            sample_count += int(len(currents))
            sum_current += float(currents.sum())
            sumsq_current += float(np.square(currents).sum())
            min_current = min(min_current, float(currents.min()))
            max_current = max(max_current, float(currents.max()))
            negative_count += int(np.count_nonzero(currents < 0))

            tx_mask = currents >= self.tx_plateau_threshold_a
            if np.any(tx_mask):
                tx_values = currents[tx_mask]
                tx_times = times[tx_mask]
                tx_sum += float(tx_values.sum())
                tx_count += int(len(tx_values))
                gaps = np.diff(tx_times)
                local_starts = int(np.count_nonzero(gaps > self.tx_cluster_gap_s))
                if prev_tx_time is None or float(tx_times[0]) - prev_tx_time > self.tx_cluster_gap_s:
                    tx_burst_count += 1
                tx_burst_count += local_starts
                prev_tx_time = float(tx_times[-1])

            low_mask = np.abs(currents) <= self.low_current_band_abs_a
            if np.any(low_mask):
                low_values = currents[low_mask]
                low_sum += float(low_values.sum())
                low_count += int(len(low_values))

        if sample_count == 0 or trace_start_s is None or trace_end_s is None:
            raise ValueError("no finite current samples found")

        duration_s = float(trace_end_s - trace_start_s)
        if duration_s <= 0:
            raise ValueError(f"non-positive trace duration {duration_s}")

        sample_period_s = (
            float(np.median(sample_period_candidates))
            if sample_period_candidates
            else source_meta.get("source_sampling_period_s")
        )
        documented_period = source_meta.get("source_sampling_period_s")
        if documented_period is not None and sample_period_s is not None:
            relative = abs(sample_period_s - documented_period) / documented_period
            if relative > 0.01:
                warnings.append(
                    f"{path.name}: inferred sample period {sample_period_s:.12g} s differs from source metadata "
                    f"{documented_period:.12g} s"
                )
        if documented_period is not None:
            relative = abs(documented_period - self.expected_sample_period_s) / self.expected_sample_period_s
            if relative > 0.01:
                warnings.append(
                    f"{path.name}: source sampling period {documented_period:.12g} s differs from expected "
                    f"{self.expected_sample_period_s:.12g} s"
                )

        sample_mean_current_a = sum_current / sample_count
        variance = (sumsq_current - sample_count * sample_mean_current_a**2) / max(sample_count - 1, 1)
        std_current_a = float(np.sqrt(max(variance, 0.0))) if sample_count > 1 else None
        time_weighted_mean_current_a = charge_c / duration_s
        energy_j = charge_c * self.source_voltage_v
        mean_power_w = energy_j / duration_s

        dr_meta = self.dr_parameters[dr_index]
        base = self.base_fields(path, "LoRaWAN-LR-FHSS")
        row: dict[str, Any] = {
            **base,
            "observation_id": f"{self.record['id']}:{confirmation_mode}:dr{dr_index}",
            "access_network": "LoRaWAN-LR-FHSS",
            "device_model": "Semtech LR1121DVK1TBKS development kit",
            "radio_module": "Semtech LR1121",
            "payload_bytes": self.frm_payload_bytes,
            "upper_layer_bytes": self.frm_payload_bytes,
            "direction": "uplink",
            "session_policy": "LoRaWAN Class A measurement",
            "confirmation_mode": confirmation_mode,
            "tx_power_dbm": self.tx_power_dbm_value,
            "duration_s": duration_s,
            "sample_count": sample_count,
            "voltage_v": self.source_voltage_v,
            "current_a": time_weighted_mean_current_a,
            "peak_current_a": max_current,
            "power_w": None,
            "mean_power_w": mean_power_w,
            "energy_j": energy_j,
            "measurement_boundary": "end_device_radio_cycle",
            "notes": (
                "Radio-interface-only LR-FHSS capture. energy_j is the energy of the complete recorded trace, "
                "computed with the 3.3 V radio supply documented in the associated publication; it is not "
                "silently interpreted as per-message energy."
            ),
            "source_dr_index": dr_index,
            "source_coding_rate": dr_meta["coding_rate"],
            "source_physical_bit_rate_bps": dr_meta["physical_bit_rate_bps"],
            "source_frm_payload_bytes": self.frm_payload_bytes,
            "source_tx_power_dbm": self.tx_power_dbm_value,
            "source_sampling_period_s": documented_period,
            "inferred_sampling_period_s": sample_period_s,
            "source_measurement_date": source_meta.get("source_measurement_date"),
            "source_power_analyzer_label": source_meta.get("power_analyzer_label"),
            "source_end_device_label": source_meta.get("end_device_label"),
            "source_voltage_provenance": "associated_publication_experimental_setup",
            "trace_start_s": trace_start_s,
            "trace_end_s": trace_end_s,
            "trace_charge_c": charge_c,
            "trace_energy_j": energy_j,
            "sample_mean_current_a": sample_mean_current_a,
            "std_current_a": std_current_a,
            "min_current_a": min_current,
            "negative_current_fraction": negative_count / sample_count,
            "tx_plateau_threshold_a": self.tx_plateau_threshold_a,
            "tx_plateau_sample_count": tx_count,
            "tx_plateau_mean_current_a": (tx_sum / tx_count) if tx_count else None,
            "tx_burst_count": tx_burst_count,
            "low_current_band_abs_a": self.low_current_band_abs_a,
            "low_current_band_sample_count": low_count,
            "low_current_band_mean_a": (low_sum / low_count) if low_count else None,
        }
        return row, warnings

    def harmonize(self) -> AdapterResult:
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        files_meta: list[dict[str, Any]] = []

        paths = self.discover((".csv",))
        if not paths:
            return AdapterResult(
                self.finalise(pd.DataFrame()),
                ["No LR-FHSS CSV traces found"],
                {"adapter": self.__class__.__name__},
            )

        for path in paths:
            try:
                row, local_warnings = self._summarise_trace(path)
            except Exception as exc:
                warnings.append(f"{path.name}: {exc}")
                continue
            rows.append(row)
            warnings.extend(local_warnings)
            files_meta.append(
                {
                    "source_file": str(path.relative_to(self.raw_dir)),
                    "confirmation_mode": row["confirmation_mode"],
                    "dr_index": row["source_dr_index"],
                    "sample_count": row["sample_count"],
                    "duration_s": row["duration_s"],
                    "sampling_period_s": row["inferred_sampling_period_s"],
                    "tx_burst_count": row["tx_burst_count"],
                }
            )

        observations = self.finalise(pd.DataFrame(rows))
        expected = {(mode, dr) for mode in ("confirmed", "unconfirmed") for dr in (8, 9, 10, 11)}
        actual = set(zip(observations.get("confirmation_mode", []), observations.get("source_dr_index", [])))
        missing = sorted(expected - actual)
        if missing:
            warnings.append(f"Missing LR-FHSS configurations: {missing}")
        if "observation_id" in observations and observations["observation_id"].duplicated().any():
            warnings.append("Duplicate LR-FHSS observation IDs detected")

        metadata = {
            "adapter": self.__class__.__name__,
            "aggregation_level": "one complete source trace per ACK/noACK x DR configuration",
            "source_voltage_v": self.source_voltage_v,
            "source_voltage_provenance": "associated publication DOI 10.3390/s24175770",
            "source_frm_payload_bytes": self.frm_payload_bytes,
            "source_tx_power_dbm": self.tx_power_dbm_value,
            "files": files_meta,
            "harmonised_rows": int(len(observations)),
        }
        return AdapterResult(observations, warnings, metadata)


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


class LoedGatewayAdapter(BaseAdapter):
    """Harmonise LoED gateway reception records.

    LoED is a reception-side dataset.  Each CSV row is one packet observation
    at one gateway and contains the PHY/gateway metadata reported by that
    gateway.  The adapter therefore preserves one canonical observation per
    source row and deliberately leaves ``delivery_success`` unset: the dataset
    does not contain a complete denominator of attempted transmissions.

    The same physical LoRaWAN transmission may be recorded by multiple
    gateways.  A SHA-256 fingerprint of the public ``physical_payload`` field
    is retained for downstream packet-reception clustering, while the payload
    itself is not copied into the processed table.
    """

    chunksize = 250_000
    required_columns = {
        "time",
        "device_address",
        "physical_payload",
        "gateway",
        "crc_status",
        "frequency",
        "spreading_factor",
        "bandwidth",
        "code_rate",
        "rssi",
        "snr",
        "size",
        "mtype",
        "fcnt",
        "fport",
    }

    gateway_metadata = {
        "00000f0c210281c4": {
            "latitude": 51.506900,
            "longitude": -0.1160894,
            "altitude_m": 25,
            "model": "Cisco Wireless Gateway for LoRaWAN",
            "location": "Dense outdoor area, on top of a building",
        },
        "00000f0c22433141": {
            "latitude": 51.49120,
            "longitude": -0.12774,
            "altitude_m": 20,
            "model": "Cisco Wireless Gateway for LoRaWAN",
            "location": "Roof of a low building in a non-dense area",
        },
        "00000f0c210721f2": {
            "latitude": 51.50766,
            "longitude": -0.0989,
            "altitude_m": 40,
            "model": "Cisco Wireless Gateway for LoRaWAN",
            "location": "Top of a building in a very dense area and large open spaces",
        },
        "00000f0c224331c4": {
            "latitude": 51.5046,
            "longitude": -0.11119,
            "altitude_m": 2,
            "model": "Cisco Wireless Gateway for LoRaWAN",
            "location": "Indoor on the ground floor, surrounded by buildings",
        },
        "00800000a0001914": {
            "latitude": 51.49896,
            "longitude": -0.17801,
            "altitude_m": 5,
            "model": "Multitech MTCDT-H5-246A-868-EU-GB",
            "location": "Inside a university building",
        },
        "00800000a0001793": {
            "latitude": 51.49843,
            "longitude": -0.17823,
            "altitude_m": 5,
            "model": "Multitech MTCDT-H5-246A-868-EU-GB",
            "location": "Inside a university building",
        },
        "00800000a0001794": {
            "latitude": 51.49896,
            "longitude": -0.17801,
            "altitude_m": 5,
            "model": "Multitech MTCDT-H5-246A-868-EU-GB",
            "location": "Inside a university building",
        },
        "7276ff002e062804": {
            "latitude": 51.49904,
            "longitude": -0.1764,
            "altitude_m": 65,
            "model": "Kerlink Wirnet Station V2",
            "location": "Top of a tall university building, with large open spaces",
        },
        "0000024b0b031c97": {
            "latitude": 51.52183,
            "longitude": -0.135,
            "altitude_m": 66,
            "model": "Kerlink Wirnet Station V2",
            "location": "Urban area, top of building, dense deployment",
        },
    }

    mtype_names = {
        "000": "Join Request",
        "001": "Join Accept",
        "010": "Unconfirmed Data Up",
        "011": "Unconfirmed Data Down",
        "100": "Confirmed Data Up",
        "101": "Confirmed Data Down",
        "110": "Rejoin Request",
        "111": "Proprietary",
    }

    @staticmethod
    def _payload_fingerprint(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _payload_length(value: Any) -> int | None:
        if value is None or pd.isna(value):
            return None
        import base64

        text = str(value).strip()
        if not text:
            return None
        try:
            return len(base64.b64decode(text, validate=False))
        except Exception:
            return None

    @classmethod
    def _mtype_bits(cls, value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None
        if number < 0:
            return None
        text = str(number)
        if len(text) > 3 or any(ch not in "01" for ch in text):
            return None
        return text.zfill(3)

    @classmethod
    def _direction_from_mtype(cls, bits: str | None) -> str | None:
        if bits in {"000", "010", "100", "110"}:
            return "uplink"
        if bits in {"001", "011", "101"}:
            return "downlink"
        return None

    @staticmethod
    def _profile(paths: list[Path]) -> str:
        lowered = [str(path).casefold() for path in paths]
        has_full = any(
            "loed_lorawan_at_edge_dataset" in text and "sample" not in text
            for text in lowered
        )
        return "full" if has_full else "sample"

    @staticmethod
    def _is_real_daily_csv(path: Path) -> bool:
        """Return True for source daily CSVs and ignore archive metadata artefacts.

        Some LoED ZIPs contain macOS AppleDouble entries such as ``._02_05_2020.csv``
        (and may contain ``__MACOSX`` directories). These are binary resource-fork
        metadata, not dataset records, and must never enter header parsing or
        scientific warning counts.
        """
        return (
            path.suffix.casefold() == ".csv"
            and not path.name.startswith("._")
            and "__MACOSX" not in path.parts
        )

    def _selected_csvs(self) -> tuple[list[Path], str]:
        paths = sorted(
            path for path in self.raw_dir.rglob("*.csv")
            if self._is_real_daily_csv(path)
        )
        if not paths:
            return [], "unknown"
        profile = self._profile(paths)
        if profile == "full":
            full_paths = [path for path in paths if "sample" not in str(path).casefold()]
            if full_paths:
                return full_paths, "full"
        return paths, "sample"

    def harmonize(self) -> AdapterResult:
        paths, profile = self._selected_csvs()
        if not paths:
            return AdapterResult(
                self.finalise(pd.DataFrame()),
                ["No LoED daily CSV files found after archive extraction"],
                {"adapter": self.__class__.__name__, "source_profile": "unknown"},
            )

        frames: list[pd.DataFrame] = []
        warnings: list[str] = []
        files_meta: list[dict[str, Any]] = []
        global_rows = 0
        snr_out_of_range_count = 0

        for path in paths:
            try:
                header = pd.read_csv(path, nrows=0)
            except Exception as exc:
                warnings.append(f"{path.name}: could not read header: {exc}")
                continue
            missing = sorted(self.required_columns - set(header.columns))
            if missing:
                warnings.append(f"{path.name}: missing required columns {missing}")
                continue

            file_rows = 0
            file_gateways: set[str] = set()
            crc_values: set[int] = set()
            file_start: pd.Timestamp | None = None
            file_end: pd.Timestamp | None = None

            try:
                reader = pd.read_csv(path, chunksize=self.chunksize, low_memory=False)
                for chunk in reader:
                    n = len(chunk)
                    if n == 0:
                        continue
                    row_indices = np.arange(file_rows, file_rows + n, dtype=np.int64)
                    file_rows += n
                    global_rows += n

                    timestamps = pd.to_datetime(chunk["time"], utc=True, errors="coerce")
                    if timestamps.notna().any():
                        local_start = timestamps.min()
                        local_end = timestamps.max()
                        file_start = local_start if file_start is None else min(file_start, local_start)
                        file_end = local_end if file_end is None else max(file_end, local_end)

                    gateway = chunk["gateway"].astype("string")
                    file_gateways.update(gateway.dropna().astype(str).unique().tolist())

                    crc_status = pd.to_numeric(chunk["crc_status"], errors="coerce")
                    crc_values.update(int(v) for v in crc_status.dropna().unique())

                    mtype_bits = chunk["mtype"].map(self._mtype_bits)
                    direction = mtype_bits.map(self._direction_from_mtype)
                    mtype_name = mtype_bits.map(self.mtype_names)

                    payload_hash = chunk["physical_payload"].map(self._payload_fingerprint)
                    payload_len = chunk["physical_payload"].map(self._payload_length)

                    out = pd.DataFrame(index=chunk.index)
                    relative = str(path.relative_to(self.raw_dir))
                    out["dataset_id"] = self.record["id"]
                    out["study_id"] = self.record.get("doi") or self.record["id"]
                    out["source_file"] = relative
                    out["observation_id"] = [
                        f"{self.record['id']}:{path.stem}:{int(i)}" for i in row_indices
                    ]
                    out["technology"] = "LoRaWAN"
                    out["access_network"] = "LoRaWAN"
                    out["direction"] = direction
                    out["measurement_boundary"] = "gateway_observation"
                    out["evidence_grade"] = self.record.get("evidence_grade", "A")
                    out["source_license"] = self.record.get("licence", {}).get("id", "unknown")
                    out["source_doi"] = self.record.get("doi")
                    out["timestamp_utc"] = timestamps
                    out["rssi_dbm"] = pd.to_numeric(chunk["rssi"], errors="coerce")
                    source_snr = pd.to_numeric(chunk["snr"], errors="coerce")
                    snr_out_of_range_count += int(((source_snr < -50.0) | (source_snr > 50.0)).sum())
                    out["source_snr_db_raw"] = source_snr
                    # Preserve the source value, but keep the canonical physical SNR field
                    # free of obviously non-physical/out-of-range source sentinels.  The
                    # LoED sample contains rare -128 dB values; they are retained above
                    # for provenance and mapped to missing for link-quality statistics.
                    out["snr_db"] = source_snr.where(source_snr.between(-50.0, 50.0))
                    out["delivery_success"] = pd.NA
                    out["retries"] = pd.NA

                    out["source_gateway_id"] = gateway
                    out["source_crc_status"] = crc_status
                    out["source_crc_valid"] = crc_status.map({1.0: True, -1.0: False})
                    out["source_frequency_hz"] = pd.to_numeric(chunk["frequency"], errors="coerce")
                    out["source_spreading_factor"] = pd.to_numeric(chunk["spreading_factor"], errors="coerce")
                    out["source_bandwidth_khz"] = pd.to_numeric(chunk["bandwidth"], errors="coerce")
                    out["source_code_rate"] = chunk["code_rate"].astype("string")
                    out["source_device_address"] = chunk["device_address"].astype("string")
                    out["source_frame_counter"] = pd.to_numeric(chunk["fcnt"], errors="coerce")
                    out["source_fport"] = pd.to_numeric(chunk["fport"], errors="coerce")
                    out["source_mtype_raw"] = pd.to_numeric(chunk["mtype"], errors="coerce")
                    out["source_mtype_bits"] = mtype_bits
                    out["source_mtype_name"] = mtype_name
                    out["source_size_field"] = pd.to_numeric(chunk["size"], errors="coerce")
                    out["source_physical_payload_bytes"] = pd.to_numeric(payload_len, errors="coerce")
                    out["source_packet_fingerprint"] = payload_hash
                    out["source_profile"] = profile
                    out["source_row_index"] = row_indices

                    # Gateway deployment metadata comes from the public LoED README.
                    out["latitude"] = gateway.map(
                        lambda x: self.gateway_metadata.get(str(x), {}).get("latitude") if pd.notna(x) else None
                    )
                    out["longitude"] = gateway.map(
                        lambda x: self.gateway_metadata.get(str(x), {}).get("longitude") if pd.notna(x) else None
                    )
                    out["source_gateway_altitude_m"] = gateway.map(
                        lambda x: self.gateway_metadata.get(str(x), {}).get("altitude_m") if pd.notna(x) else None
                    )
                    out["source_gateway_model"] = gateway.map(
                        lambda x: self.gateway_metadata.get(str(x), {}).get("model") if pd.notna(x) else None
                    )
                    out["environment"] = gateway.map(
                        lambda x: self.gateway_metadata.get(str(x), {}).get("location") if pd.notna(x) else None
                    )
                    out["notes"] = (
                        "LoED reception-side gateway observation. Presence of a row is not an absolute "
                        "packet-delivery-success denominator; delivery_success intentionally remains null."
                    )
                    frames.append(out)
            except Exception as exc:
                warnings.append(f"{path.name}: failed during chunked import: {exc}")
                continue

            files_meta.append(
                {
                    "source_file": str(path.relative_to(self.raw_dir)),
                    "rows": file_rows,
                    "gateways": sorted(file_gateways),
                    "crc_status_values": sorted(crc_values),
                    "time_start_utc": file_start.isoformat() if file_start is not None else None,
                    "time_end_utc": file_end.isoformat() if file_end is not None else None,
                }
            )

        frame = self.finalise(pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame())
        if not frame.empty:
            duplicate_ids = int(frame["observation_id"].duplicated().sum())
            if duplicate_ids:
                warnings.append(f"Duplicate observation IDs detected: {duplicate_ids}")
            unknown_gateways = sorted(
                set(frame["source_gateway_id"].dropna().astype(str)) - set(self.gateway_metadata)
            )
            if unknown_gateways:
                warnings.append(f"Gateway metadata missing for IDs: {unknown_gateways}")

        metadata = {
            "adapter": self.__class__.__name__,
            "aggregation_level": "one source row = one gateway reception observation",
            "source_profile": profile,
            "source_files": len(files_meta),
            "source_rows": global_rows,
            "files": files_meta,
            "gateway_count": int(frame["source_gateway_id"].nunique(dropna=True)) if not frame.empty else 0,
            "source_snr_out_of_range_count": int(snr_out_of_range_count),
            "snr_cleaning_rule": "source_snr_db_raw outside [-50, 50] dB mapped to canonical snr_db = null",
            "crc_status_values": sorted(
                int(v) for v in pd.to_numeric(frame.get("source_crc_status"), errors="coerce").dropna().unique()
            ) if not frame.empty else [],
            "spreading_factors": sorted(
                int(v) for v in pd.to_numeric(frame.get("source_spreading_factor"), errors="coerce").dropna().unique()
            ) if not frame.empty else [],
            "frequency_hz_values": sorted(
                int(v) for v in pd.to_numeric(frame.get("source_frequency_hz"), errors="coerce").dropna().unique()
            ) if not frame.empty else [],
            "delivery_success_policy": "not populated: reception logs do not provide attempted-transmission denominator",
            "packet_identity_policy": "SHA-256 physical-payload fingerprint retained for separate temporal clustering",
        }
        return AdapterResult(frame, warnings, metadata)


class CellularCoverageAdapter(GenericSignalAdapter):
    def harmonize(self) -> AdapterResult:
        result = super().harmonize()
        if not result.observations.empty:
            result.observations["measurement_boundary"] = result.observations["measurement_boundary"].fillna("network_coverage")
        return result
