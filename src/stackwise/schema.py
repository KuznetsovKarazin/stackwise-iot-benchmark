from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd

from .constants import CANONICAL_COLUMNS


DEFAULT_SCHEMA = Path("datasets/schema/canonical_observation.schema.json")


def canonicalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in CANONICAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    ordered = CANONICAL_COLUMNS + [c for c in result.columns if c not in CANONICAL_COLUMNS]
    return result[ordered]


def validate_frame(frame: pd.DataFrame, schema_path: str | Path = DEFAULT_SCHEMA) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    canonical = canonicalise_columns(frame)
    for index, row in canonical.iterrows():
        record = {}
        for key, value in row.items():
            if pd.isna(value):
                record[key] = None
            elif isinstance(value, np.generic):
                record[key] = value.item()
            elif isinstance(value, pd.Timestamp):
                record[key] = value.isoformat()
            else:
                record[key] = value
        for error in validator.iter_errors(record):
            errors.append(f"row={index} field={'.'.join(map(str, error.path))}: {error.message}")
    return errors
