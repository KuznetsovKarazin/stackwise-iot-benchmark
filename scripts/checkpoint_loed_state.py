from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Checkpoint the current LoED processed/validation state before replacing it.")
    parser.add_argument("--label", default="sample_pre_full")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    processed = Path("data/processed/loed_lorawan_edge_2020")
    report_path = processed / "harmonization_report.json"
    if not report_path.exists():
        print("No LoED harmonization report found; nothing to checkpoint.")
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    profile = report.get("metadata", {}).get("source_profile")
    if profile != "sample" and not args.force:
        print(f"Current LoED profile is {profile!r}, not 'sample'; checkpoint skipped.")
        return

    target = Path("results/checkpoints/loed") / args.label
    target.mkdir(parents=True, exist_ok=True)

    small_candidates = [
        processed / "harmonization_report.json",
        processed / "run_manifest.json",
        Path("results/validation/loed/loed_validation_summary.json"),
        Path("data/analysis_ready/loed_lorawan_edge_2020/analysis_ready_manifest.json"),
        Path("data/analysis_ready/loed_lorawan_edge_2020/gateway_day_summary.csv"),
    ]
    copied: list[str] = []
    for path in small_candidates:
        if path.exists():
            dest = target / path.name
            shutil.copy2(path, dest)
            copied.append(str(dest))

    artifact_candidates = [
        processed / "observations.parquet",
        Path("results/validation/loed/packet_cluster_validation.csv"),
        Path("results/validation/loed/packet_cluster_validation.parquet"),
        Path("data/analysis_ready/loed_lorawan_edge_2020/packet_reception_clusters.parquet"),
        Path("data/analysis_ready/loed_lorawan_edge_2020/packet_reception_clusters.csv"),
    ]
    artifacts = []
    for path in artifact_candidates:
        if path.exists():
            artifacts.append({
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "source_profile": profile,
        "harmonized_rows": report.get("rows"),
        "copied_small_artifacts": copied,
        "large_artifact_checksums": artifacts,
        "note": "Large derived files are reproducible and are checksum-recorded rather than duplicated.",
    }
    (target / "checkpoint_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"LoED checkpoint written to {target}")


if __name__ == "__main__":
    main()
