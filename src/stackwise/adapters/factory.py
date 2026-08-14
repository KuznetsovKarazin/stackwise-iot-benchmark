from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter
from .generic import GenericPowerAdapter, GenericSignalAdapter, WideBleRssiAdapter
from .specific import (
    CellularCoverageAdapter,
    InSecTTPowerAdapter,
    LoedGatewayAdapter,
    LrFhssPowerAdapter,
    VomhoffCellularEnergyAdapter,
)


ADAPTERS: dict[str, type[BaseAdapter]] = {
    "generic_power": GenericPowerAdapter,
    "generic_signal": GenericSignalAdapter,
    "insectt_power": InSecTTPowerAdapter,
    "vomhoff_cellular_energy": VomhoffCellularEnergyAdapter,
    "loed_gateway": LoedGatewayAdapter,
    "lrfhss_power": LrFhssPowerAdapter,
    "cellular_coverage": CellularCoverageAdapter,
    "wide_ble_rssi": WideBleRssiAdapter,
}


def create_adapter(record: dict, raw_dir: str | Path) -> BaseAdapter:
    name = record.get("adapter")
    try:
        adapter_cls = ADAPTERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown adapter {name!r}; available: {sorted(ADAPTERS)}") from exc
    return adapter_cls(record, raw_dir)
