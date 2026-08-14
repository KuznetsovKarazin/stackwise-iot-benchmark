from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from .adapters import create_adapter
from .io import dump_json, write_table
from .provenance import write_run_manifest
from .registry import DatasetRegistry
from .schema import validate_frame


def extract_archives(raw_dir: Path, interim_dir: Path) -> list[Path]:
    interim_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    for archive in raw_dir.rglob("*.zip"):
        destination = interim_dir / archive.stem
        if not destination.exists():
            shutil.unpack_archive(str(archive), str(destination))
        extracted.append(destination)
    return extracted


def harmonize_dataset(
    dataset_id: str,
    *,
    registry_path: str | Path = "datasets/registry.yml",
    raw_root: str | Path = "data/raw",
    interim_root: str | Path = "data/interim",
    processed_root: str | Path = "data/processed",
    strict: bool = False,
) -> tuple[Path, list[str]]:
    registry = DatasetRegistry(registry_path)
    record = registry.get(dataset_id)
    raw_dir = Path(raw_root) / dataset_id
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw dataset directory does not exist: {raw_dir}")

    output = Path(processed_root) / dataset_id / "observations.parquet"

    # LoED full-scale processing is streamed directly from the source ZIP to
    # Parquet.  This avoids extracting the ~400 MB archive and, more importantly,
    # avoids accumulating a multi-million-row wide DataFrame in RAM.
    if record.data.get("adapter") == "loed_gateway":
        from .loed_streaming import harmonize_loed_streaming

        report = harmonize_loed_streaming(
            record.data,
            raw_dir=raw_dir,
            output=output,
            strict=strict,
        )
        dump_json(report, output.parent / "harmonization_report.json")
        result_warnings = list(report.get("warnings", []))
        errors = list(report.get("validation_errors", []))
    else:
        interim_dir = Path(interim_root) / dataset_id
        extracted = extract_archives(raw_dir, interim_dir)
        source_dir = interim_dir if extracted else raw_dir
        adapter = create_adapter(record.data, source_dir)
        result = adapter.harmonize()
        errors = validate_frame(result.observations)
        if strict and errors:
            raise ValueError("Canonical validation failed:\n" + "\n".join(errors[:20]))

        write_table(result.observations, output)
        report = {
            "dataset_id": dataset_id,
            "rows": len(result.observations),
            "columns": list(result.observations.columns),
            "warnings": result.warnings,
            "validation_errors": errors,
            "metadata": result.metadata,
        }
        dump_json(report, output.parent / "harmonization_report.json")
        result_warnings = result.warnings
    write_run_manifest(
        output.parent / "run_manifest.json",
        command=f"stackwise harmonize {dataset_id}",
        inputs=[path for path in raw_dir.rglob("*") if path.is_file()],
        outputs=[output, output.parent / "harmonization_report.json"],
        parameters={"adapter": record.data.get("adapter"), "strict": strict},
    )
    return output, result_warnings + errors


def combine_processed(
    processed_root: str | Path = "data/processed",
    output: str | Path = "data/processed/canonical_observations.parquet",
) -> Path:
    files = [
        path for path in Path(processed_root).glob("*/observations.parquet")
        if path.resolve() != Path(output).resolve()
    ]
    if not files:
        raise FileNotFoundError("No harmonised observation files found")
    frames = [pd.read_parquet(path) for path in files]
    combined = pd.concat(frames, ignore_index=True, sort=False)
    return write_table(combined, output)
