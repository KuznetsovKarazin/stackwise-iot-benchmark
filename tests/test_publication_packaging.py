from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from stackwise.publication_packaging import (
    build_deterministic_deposit_archive,
    sha256_file,
    validate_release_for_deposit,
)


def _fake_release(root: Path) -> tuple[Path, Path]:
    release = root / "release"
    release.mkdir()
    required = [
        "README.md", "DATASET_CARD.md", "LICENSE.md", "SOURCE_LICENSES.csv",
        "SOURCE_ATTRIBUTION.csv", "CITATION.cff", "ZENODO_METADATA.json",
        "RELEASE_TABLE_MANIFEST.csv", "CHECKSUMS.sha256",
    ]
    for name in required:
        (release / name).write_text(f"fixture {name}\n", encoding="utf-8")
    (release / "ATTRIBUTION_REVIEW.json").write_text(
        json.dumps({"status": "passed", "core_source_rows": 4}) + "\n", encoding="utf-8"
    )
    (release / "release_summary.json").write_text(
        json.dumps({
            "benchmark_version": "1.0.0",
            "zenodo_upload_authorised": True,
            "scientific_attribution_review_passed": True,
            "raw_external_data_included": False,
        }) + "\n", encoding="utf-8"
    )
    (release / "tables").mkdir()
    (release / "tables/example.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    qa = root / "qa.json"
    qa.write_text(json.dumps({
        "release_integrity_passed": True,
        "zenodo_finalisation_ready": True,
        "benchmark_release_license_declared": True,
        "checks": {"scientific_attribution_review_passed": True},
    }) + "\n", encoding="utf-8")
    return release, qa


def test_validate_release_for_deposit_accepts_final_release(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    r, q = validate_release_for_deposit(release, qa)
    assert r["benchmark_version"] == "1.0.0"
    assert q["zenodo_finalisation_ready"] is True


def test_archive_is_deterministic_and_contains_top_level_folder(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    a = build_deterministic_deposit_archive(release, qa, out1)
    b = build_deterministic_deposit_archive(release, qa, out2)
    assert a.archive_sha256 == b.archive_sha256
    assert sha256_file(Path(a.archive_path)) == a.archive_sha256
    with zipfile.ZipFile(a.archive_path) as zf:
        names = zf.namelist()
    assert names
    assert all(name.startswith("stackwise_benchmark_v1.0.0/") for name in names)
    assert "stackwise_benchmark_v1.0.0/tables/example.csv" in names


def test_archive_summary_keeps_scope_limits(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    result = build_deterministic_deposit_archive(release, qa, tmp_path / "out")
    assert result.benchmark_license == "CC-BY-4.0"
    assert result.raw_external_archives_absent is True
    assert result.publication_mcda_authorised is False
    assert result.deterministic_archive is True


def test_packaging_fails_closed_if_zenodo_gate_is_false(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    data = json.loads(qa.read_text(encoding="utf-8"))
    data["zenodo_finalisation_ready"] = False
    qa.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Zenodo-finalisation ready"):
        validate_release_for_deposit(release, qa)


def test_packaging_accepts_canonical_final_attribution_record(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    attribution = json.loads((release / "ATTRIBUTION_REVIEW.json").read_text(encoding="utf-8"))
    assert attribution == {"status": "passed", "core_source_rows": 4}
    validate_release_for_deposit(release, qa)


def test_packaging_rejects_legacy_review_status_key(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    (release / "ATTRIBUTION_REVIEW.json").write_text(
        json.dumps({"review_status": "passed", "core_source_rows": 4}) + "\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="Scientific attribution review has not passed"):
        validate_release_for_deposit(release, qa)


def test_packaging_requires_four_reviewed_core_sources(tmp_path: Path) -> None:
    release, qa = _fake_release(tmp_path)
    (release / "ATTRIBUTION_REVIEW.json").write_text(
        json.dumps({"status": "passed", "core_source_rows": 3}) + "\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="exactly four core sources"):
        validate_release_for_deposit(release, qa)
