from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path


REQUIRED_RELEASE_FILES = (
    "README.md",
    "DATASET_CARD.md",
    "LICENSE.md",
    "SOURCE_LICENSES.csv",
    "SOURCE_ATTRIBUTION.csv",
    "ATTRIBUTION_REVIEW.json",
    "CITATION.cff",
    "ZENODO_METADATA.json",
    "RELEASE_TABLE_MANIFEST.csv",
    "CHECKSUMS.sha256",
    "release_summary.json",
)

# Keep the archive byte-for-byte reproducible across machines/runs.
ZIP_TIMESTAMP = (2026, 8, 13, 0, 0, 0)


@dataclass(frozen=True)
class DepositPackageSummary:
    benchmark_version: str
    archive_path: str
    archive_bytes: int
    archive_sha256: str
    packaged_files: int
    benchmark_license: str
    release_integrity_passed: bool
    zenodo_finalisation_ready: bool
    raw_external_archives_absent: bool
    deterministic_archive: bool
    publication_mcda_authorised: bool


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_release_for_deposit(release_dir: Path, qa_summary_path: Path) -> tuple[dict, dict]:
    release_dir = Path(release_dir)
    qa_summary_path = Path(qa_summary_path)
    missing = [name for name in REQUIRED_RELEASE_FILES if not (release_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Final benchmark release is missing required files: {missing}")

    release_summary = _load_json(release_dir / "release_summary.json")
    qa_summary = _load_json(qa_summary_path)

    if release_summary.get("benchmark_version") != "1.0.0":
        raise RuntimeError("Deposit packaging only accepts frozen Benchmark v1.0.0")
    if not bool(release_summary.get("zenodo_upload_authorised", False)):
        raise RuntimeError("Release summary does not authorise Zenodo finalisation")
    if not bool(release_summary.get("scientific_attribution_review_passed", False)):
        raise RuntimeError("Release summary does not record a passed scientific attribution review")
    if bool(release_summary.get("raw_external_data_included", True)):
        raise RuntimeError("Raw external archives/data must not be mirrored in the benchmark deposit")
    if not bool(qa_summary.get("release_integrity_passed", False)):
        raise RuntimeError("Final benchmark release QA did not pass")
    if not bool(qa_summary.get("zenodo_finalisation_ready", False)):
        raise RuntimeError("Final benchmark release QA is not Zenodo-finalisation ready")
    if qa_summary.get("benchmark_release_license_declared") is False:
        raise RuntimeError("Benchmark release licence is not declared")
    qa_checks = qa_summary.get("checks") or {}
    if not bool(qa_checks.get("scientific_attribution_review_passed", False)):
        raise RuntimeError("Final benchmark release QA does not confirm the scientific attribution review")

    attribution = _load_json(release_dir / "ATTRIBUTION_REVIEW.json")
    if attribution.get("status") != "passed":
        raise RuntimeError("Scientific attribution review has not passed")
    if int(attribution.get("core_source_rows", 0)) != 4:
        raise RuntimeError("Scientific attribution review does not cover exactly four core sources")

    return release_summary, qa_summary


def build_deterministic_deposit_archive(
    release_dir: Path,
    qa_summary_path: Path,
    output_dir: Path,
) -> DepositPackageSummary:
    release_dir = Path(release_dir)
    output_dir = Path(output_dir)
    release_summary, qa_summary = validate_release_for_deposit(release_dir, qa_summary_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "STACKWISE_Empirical_Evidence_Benchmark_v1.0.0.zip"
    prefix = "stackwise_benchmark_v1.0.0"
    files = sorted(p for p in release_dir.rglob("*") if p.is_file())

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = path.relative_to(release_dir).as_posix()
            info = zipfile.ZipInfo(f"{prefix}/{rel}", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open("rb") as fh:
                zf.writestr(info, fh.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    digest = sha256_file(archive)
    (output_dir / f"{archive.name}.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )

    summary = DepositPackageSummary(
        benchmark_version="1.0.0",
        archive_path=str(archive),
        archive_bytes=archive.stat().st_size,
        archive_sha256=digest,
        packaged_files=len(files),
        benchmark_license="CC-BY-4.0",
        release_integrity_passed=bool(qa_summary["release_integrity_passed"]),
        zenodo_finalisation_ready=bool(qa_summary["zenodo_finalisation_ready"]),
        raw_external_archives_absent=not bool(release_summary.get("raw_external_data_included", True)),
        deterministic_archive=True,
        publication_mcda_authorised=False,
    )
    (output_dir / "deposit_package_summary.json").write_text(
        json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8"
    )
    return summary
