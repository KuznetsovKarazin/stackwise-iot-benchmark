from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from stackwise.schema import canonicalise_columns


@dataclass
class AdapterResult:
    observations: pd.DataFrame
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    def __init__(self, record: dict[str, Any], raw_dir: str | Path):
        self.record = record
        self.raw_dir = Path(raw_dir)

    def discover(self, suffixes: Iterable[str] = (".csv", ".txt", ".json", ".parquet")) -> list[Path]:
        wanted = {s.lower() for s in suffixes}
        return sorted(path for path in self.raw_dir.rglob("*") if path.is_file() and path.suffix.lower() in wanted)

    def base_fields(self, source_file: Path, technology: str | None = None) -> dict[str, Any]:
        licence = self.record.get("licence", {}).get("id", "unknown")
        return {
            "dataset_id": self.record["id"],
            "study_id": self.record.get("doi") or self.record["id"],
            "source_file": str(source_file.relative_to(self.raw_dir)),
            "technology": technology or self.infer_technology(source_file.name),
            "measurement_boundary": self.record.get("measurement_boundaries", ["unknown"])[0],
            "evidence_grade": self.record.get("evidence_grade", "D"),
            "source_license": licence,
            "source_doi": self.record.get("doi"),
        }

    def infer_technology(self, text: str) -> str:
        normal = re.sub(r"[_\-]+", " ", text).casefold()
        candidates = sorted(self.record.get("technologies", []), key=len, reverse=True)
        for candidate in candidates:
            if candidate.casefold().replace("-", " ") in normal:
                return candidate
        return candidates[0] if len(candidates) == 1 else "UNKNOWN"

    def finalise(self, frame: pd.DataFrame) -> pd.DataFrame:
        frame = canonicalise_columns(frame)
        if "observation_id" in frame:
            missing = frame["observation_id"].isna()
            frame.loc[missing, "observation_id"] = [
                f"{self.record['id']}:{i}" for i in frame.index[missing]
            ]
        return frame

    @abstractmethod
    def harmonize(self) -> AdapterResult:
        raise NotImplementedError
