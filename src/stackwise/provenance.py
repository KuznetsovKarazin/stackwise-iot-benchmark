from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .io import dump_json


def file_checksum(path: str | Path, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_manifest(files: Iterable[str | Path]) -> list[dict[str, object]]:
    result = []
    for item in files:
        path = Path(item)
        result.append({
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": file_checksum(path),
        })
    return result


def write_run_manifest(
    output: str | Path,
    *,
    command: str,
    inputs: Iterable[str | Path] = (),
    outputs: Iterable[str | Path] = (),
    parameters: dict[str, object] | None = None,
) -> Path:
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "python": sys.version,
        "platform": platform.platform(),
        "parameters": parameters or {},
        "inputs": build_file_manifest([p for p in inputs if Path(p).exists()]),
        "outputs": build_file_manifest([p for p in outputs if Path(p).exists()]),
    }
    return dump_json(payload, output)
