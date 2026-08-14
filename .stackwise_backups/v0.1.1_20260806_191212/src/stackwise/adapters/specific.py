from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .base import AdapterResult
from .generic import GenericPowerAdapter, GenericSignalAdapter
from .utils import find_column, integrate_trace, load_aliases, numeric


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


class VomhoffCellularEnergyAdapter(GenericPowerAdapter):
    """Flexible reader for the public NB-IoT/LTE-M phase-measurement CSV files."""

    def harmonize(self) -> AdapterResult:
        aliases = load_aliases()
        rows: list[dict[str, object]] = []
        warnings: list[str] = []
        for path in self.discover((".csv",)):
            try:
                raw = pd.read_csv(path, low_memory=False)
            except Exception as exc:
                warnings.append(f"Could not read {path.name}: {exc}")
                continue
            normal_columns = {str(c).casefold(): c for c in raw.columns}
            tech_col = next((c for n, c in normal_columns.items() if "technolog" in n or n in {"rat", "network"}), None)
            protocol_col = next((c for n, c in normal_columns.items() if "protocol" in n), None)
            phase_col = next((c for n, c in normal_columns.items() if "phase" in n or "state" in n), None)
            energy_col = next((c for n, c in normal_columns.items() if "energy" in n), None)
            power_col = next((c for n, c in normal_columns.items() if "power" in n), None)
            duration_col = next((c for n, c in normal_columns.items() if "duration" in n), None)

            if energy_col:
                group_cols = [c for c in [tech_col, protocol_col, phase_col] if c]
                grouped = raw.groupby(group_cols, dropna=False) if group_cols else [((), raw)]
                for key, group in grouped:
                    if not isinstance(key, tuple):
                        key = (key,)
                    labels = dict(zip(group_cols, key))
                    technology = str(labels.get(tech_col, self.infer_technology(path.name)))
                    protocol = str(labels.get(protocol_col, "")) or None
                    phase = str(labels.get(phase_col, "")) or None
                    values = numeric(group[energy_col])
                    # The source column unit must be audited. Only convert when the name states mJ.
                    energy_j = float(values.mean() / 1000.0) if "mj" in str(energy_col).casefold() else float(values.mean())
                    row = self.base_fields(path, technology)
                    row.update({
                        "observation_id": f"{self.record['id']}:{path.stem}:{len(rows)}",
                        "application_protocol": protocol,
                        "measurement_boundary": phase.casefold().replace(" ", "_") if phase else row["measurement_boundary"],
                        "energy_j": energy_j,
                        "sample_count": int(values.notna().sum()),
                        "notes": f"Aggregated from source energy column {energy_col}; verify source unit",
                    })
                    if duration_col:
                        row["duration_s"] = float(numeric(group[duration_col]).mean())
                    if power_col:
                        row["mean_power_w"] = float(numeric(group[power_col]).mean())
                    rows.append(row)
                continue

            # Fallback to generic high-frequency trace handling.
            generic = super().harmonize()
            return AdapterResult(generic.observations, warnings + generic.warnings)

        return AdapterResult(self.finalise(pd.DataFrame(rows)), warnings)


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
