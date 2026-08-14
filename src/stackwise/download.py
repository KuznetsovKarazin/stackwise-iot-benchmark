from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .io import dump_json
from .registry import DatasetRecord


ZENODO_API = "https://zenodo.org/api/records/{record_id}"


@dataclass
class DownloadedFile:
    path: Path
    source_url: str
    source_checksum: str | None
    checksum_verified: bool | None


def _stream_download(url: str, target: Path, timeout: int = 120) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def _verify_source_checksum(path: Path, checksum: str | None) -> bool | None:
    if not checksum or ":" not in checksum:
        return None
    algorithm, expected = checksum.split(":", 1)
    algorithm = algorithm.lower()
    if algorithm not in hashlib.algorithms_available:
        return None
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.lower()


def _matches(name: str, patterns: list[str]) -> bool:
    return not patterns or any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def download_zenodo(
    record: DatasetRecord,
    target_dir: Path,
    patterns_override: list[str] | None = None,
) -> list[DownloadedFile]:
    record_id = record.data["record_id"]
    response = requests.get(ZENODO_API.format(record_id=record_id), timeout=60)
    response.raise_for_status()
    metadata = response.json()
    dump_json(metadata, target_dir / "zenodo_record.json")

    patterns = list(patterns_override) if patterns_override is not None else list(record.data.get("file_globs", []))
    downloaded: list[DownloadedFile] = []
    for file_info in metadata.get("files", []):
        name = file_info.get("key") or file_info.get("filename")
        if not name or not _matches(name, patterns):
            continue
        links = file_info.get("links", {})
        url = links.get("self") or links.get("download") or file_info.get("links", {}).get("content")
        if not url:
            continue
        path = target_dir / name
        _stream_download(url, path)
        source_checksum = file_info.get("checksum")
        verified = _verify_source_checksum(path, source_checksum)
        if verified is False:
            path.unlink(missing_ok=True)
            raise ValueError(f"Checksum mismatch for {name}")
        downloaded.append(DownloadedFile(path, url, source_checksum, verified))
    if not downloaded:
        raise RuntimeError(
            f"No files matched registry patterns for {record.id}. "
            "Inspect zenodo_record.json and update file_globs."
        )
    return downloaded


def download_kaggle(record: DatasetRecord, target_dir: Path) -> list[DownloadedFile]:
    if shutil.which("kaggle") is None:
        raise RuntimeError("Kaggle CLI is not installed. Run: pip install kaggle")
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = record.data["slug"]
    command = ["kaggle", "datasets", "download", "-d", slug, "-p", str(target_dir), "--unzip"]
    subprocess.run(command, check=True)
    files = [path for path in target_dir.rglob("*") if path.is_file()]
    return [DownloadedFile(path, f"kaggle:{slug}", None, None) for path in files]


def download_dataset(
    record: DatasetRecord,
    *,
    root: str | Path = "data/raw",
    accept_license: bool,
    accept_unverified_license: bool = False,
    file_globs_override: list[str] | None = None,
) -> list[DownloadedFile]:
    if not accept_license:
        raise PermissionError("Explicit --accept-license is required")
    if record.licence_status != "verified" and not accept_unverified_license:
        raise PermissionError(
            f"Licence status for {record.id} is {record.licence_status!r}. "
            "Review the live record and pass --accept-unverified-license if appropriate."
        )

    target_dir = Path(root) / record.raw_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    if record.provider == "zenodo":
        downloaded = download_zenodo(record, target_dir, patterns_override=file_globs_override)
    elif record.provider == "kaggle":
        downloaded = download_kaggle(record, target_dir)
    else:
        raise NotImplementedError(f"Provider not implemented: {record.provider}")

    manifest = {
        "dataset_id": record.id,
        "landing_url": record.data.get("landing_url"),
        "doi": record.data.get("doi"),
        "licence_registry_value": record.data.get("licence"),
        "requested_file_globs": file_globs_override,
        "files": [
            {
                "path": str(item.path),
                "source_url": item.source_url,
                "source_checksum": item.source_checksum,
                "checksum_verified": item.checksum_verified,
            }
            for item in downloaded
        ],
    }
    dump_json(manifest, target_dir / "download_manifest.json")
    return downloaded
