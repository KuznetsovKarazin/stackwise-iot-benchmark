from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from .io import load_yaml


DEFAULT_REGISTRY = Path("datasets/registry.yml")
DEFAULT_SCHEMA = Path("datasets/schema/dataset_registry.schema.json")


@dataclass(frozen=True)
class DatasetRecord:
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def provider(self) -> str:
        return str(self.data["provider"])

    @property
    def licence_status(self) -> str:
        return str(self.data.get("licence", {}).get("status", "unknown"))

    @property
    def raw_dir_name(self) -> str:
        return self.id


class DatasetRegistry:
    def __init__(self, path: str | Path = DEFAULT_REGISTRY):
        self.path = Path(path)
        self.document = load_yaml(self.path)
        self.records = [DatasetRecord(item) for item in self.document.get("datasets", [])]
        self._by_id = {record.id: record for record in self.records}
        if len(self._by_id) != len(self.records):
            raise ValueError("Duplicate dataset IDs in registry")

    def validate(self, schema_path: str | Path = DEFAULT_SCHEMA) -> None:
        import json

        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        jsonschema.validate(self.document, schema)
        for record in self.records:
            if record.provider == "zenodo" and "record_id" not in record.data:
                raise ValueError(f"Zenodo record {record.id} has no record_id")
            if record.provider == "kaggle" and "slug" not in record.data:
                raise ValueError(f"Kaggle record {record.id} has no slug")
            if not record.data.get("empirical", False):
                raise ValueError(f"Non-empirical dataset in active registry: {record.id}")

    def get(self, dataset_id: str) -> DatasetRecord:
        try:
            return self._by_id[dataset_id]
        except KeyError as exc:
            raise KeyError(f"Unknown dataset ID: {dataset_id}") from exc

    def select(
        self,
        *,
        status: str | None = None,
        technology: str | None = None,
        provider: str | None = None,
    ) -> list[DatasetRecord]:
        records: Iterable[DatasetRecord] = self.records
        if status:
            records = [r for r in records if r.data.get("status") == status]
        if provider:
            records = [r for r in records if r.provider == provider]
        if technology:
            wanted = technology.casefold()
            records = [
                r for r in records
                if any(str(t).casefold() == wanted for t in r.data.get("technologies", []))
            ]
        return list(records)
