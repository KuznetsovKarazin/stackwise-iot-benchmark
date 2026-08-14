from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmark_release import _count_rows


DEFAULT_RELEASE_DIR = Path("release/stackwise_benchmark_v1.0.0-rc1")
FINAL_RELEASE_DIR = Path("release/stackwise_benchmark_v1.0.0")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def _canonical_evidence_signature(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["evidence_id", "dataset_id", "metric_id", "technology", "source_license"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise RuntimeError(f"Evidence representation missing canonical columns: {missing}")
    return (
        frame[required]
        .fillna("")
        .astype(str)
        .sort_values("evidence_id", kind="stable")
        .reset_index(drop=True)
    )


def _parse_checksums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        rows[relative] = digest
    return rows


def audit_benchmark_release_candidate(release_dir: str | Path = DEFAULT_RELEASE_DIR) -> dict[str, Any]:
    release_dir = Path(release_dir).resolve()
    required_metadata = [
        "README.md",
        "DATASET_CARD.md",
        "SOURCE_LICENSES.csv",
        "LICENSE_METADATA_CORRECTIONS.csv",
        "RELEASE_TABLE_MANIFEST.csv",
        "release_summary.json",
        "CHECKSUMS.sha256",
    ]
    missing_metadata = [name for name in required_metadata if not (release_dir / name).exists()]
    if missing_metadata:
        raise FileNotFoundError(f"Release metadata files missing: {missing_metadata}")

    summary = json.loads((release_dir / "release_summary.json").read_text(encoding="utf-8"))
    manifest = pd.read_csv(release_dir / "RELEASE_TABLE_MANIFEST.csv")

    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    # Manifest integrity and row counts.
    checks["manifest_artifact_count_matches_summary"] = len(manifest) == int(summary["release_artifact_files"])
    row_count_mismatches: list[dict[str, Any]] = []
    parquet_rows: dict[str, int | None] = {}
    for row in manifest.to_dict(orient="records"):
        path = release_dir / str(row["release_path"])
        if not path.exists():
            row_count_mismatches.append({"release_path": row["release_path"], "error": "missing_file"})
            continue
        actual = _count_rows(path)
        if path.suffix.lower() == ".parquet":
            parquet_rows[str(row["release_path"])] = actual
        manifest_value = row.get("rows")
        if pd.isna(manifest_value):
            expected = None
        else:
            expected = int(manifest_value)
        if actual != expected:
            row_count_mismatches.append(
                {"release_path": row["release_path"], "manifest_rows": expected, "actual_rows": actual}
            )
    checks["manifest_row_counts_match_materialised_files"] = not row_count_mismatches
    checks["parquet_rows_are_materialised_not_false_zero"] = all(
        count is not None and count > 0 for count in parquet_rows.values()
    )
    details["parquet_rows"] = parquet_rows
    details["row_count_mismatches"] = row_count_mismatches

    # Three-format equivalence for the canonical 398-record evidence table.
    evidence_base = release_dir / "tables/L1_evidence_records"
    evidence_csv = pd.read_csv(evidence_base / "core_four_evidence_matrix.csv")
    evidence_jsonl = _read_jsonl(evidence_base / "core_four_evidence_matrix.jsonl")
    evidence_parquet = pd.read_parquet(evidence_base / "core_four_evidence_matrix.parquet")
    signatures = [
        _canonical_evidence_signature(evidence_csv),
        _canonical_evidence_signature(evidence_jsonl),
        _canonical_evidence_signature(evidence_parquet),
    ]
    checks["canonical_evidence_row_counts_equal"] = len({len(frame) for frame in signatures}) == 1
    checks["canonical_evidence_formats_semantically_equivalent"] = (
        signatures[0].equals(signatures[1]) and signatures[0].equals(signatures[2])
    )
    checks["canonical_evidence_ids_unique"] = not evidence_csv["evidence_id"].duplicated().any()

    # Full 7x9 feasibility coverage, not just the aggregate counts.
    scenarios = pd.read_csv(release_dir / "tables/L3_benchmark_definitions/benchmark_scenarios.csv")
    stacks = pd.read_csv(release_dir / "tables/L3_benchmark_definitions/candidate_stack_catalog.csv")
    feasibility = pd.read_csv(
        release_dir / "tables/L4_feasibility_and_support/refined_hard_feasibility_matrix.csv"
    )
    scenario_ids = set(scenarios["scenario_id"].astype(str))
    stack_ids = set(stacks["stack_id"].astype(str))
    actual_pairs = set(zip(feasibility["scenario_id"].astype(str), feasibility["stack_id"].astype(str)))
    expected_pairs = {(scenario, stack) for scenario in scenario_ids for stack in stack_ids}
    checks["scenario_ids_unique"] = scenarios["scenario_id"].is_unique
    checks["stack_ids_unique"] = stacks["stack_id"].is_unique
    checks["feasibility_pairs_unique"] = not feasibility.duplicated(["scenario_id", "stack_id"]).any()
    checks["feasibility_is_complete_scenario_stack_product"] = actual_pairs == expected_pairs
    details["missing_feasibility_pairs"] = sorted(expected_pairs - actual_pairs)
    details["unexpected_feasibility_pairs"] = sorted(actual_pairs - expected_pairs)

    # Source licence gate remains visible in the built package.
    licences = pd.read_csv(release_dir / "SOURCE_LICENSES.csv")
    checks["four_core_source_licences_present"] = len(licences) == 4
    checks["all_core_source_licences_verified"] = set(licences["license_status"].astype(str)) == {"verified"}
    redistribution = licences["redistribution"].astype(str).str.lower().isin(["true", "1", "yes"])
    checks["all_core_sources_redistributable"] = bool(redistribution.all())

    # No mirrored external archives in the compact package.
    archive_suffixes = {".zip", ".7z", ".rar", ".tar", ".tgz", ".gz", ".bz2", ".xz"}
    external_archives = [
        path.relative_to(release_dir).as_posix()
        for path in release_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in archive_suffixes
    ]
    checks["no_raw_external_archives"] = not external_archives
    details["archive_files_found"] = external_archives

    # Dataset self-description metadata added by post2.
    schema_files = sorted((release_dir / "schemas").glob("*.json")) if (release_dir / "schemas").exists() else []
    source_cards = (
        sorted((release_dir / "source_dataset_cards").glob("*.md"))
        if (release_dir / "source_dataset_cards").exists()
        else []
    )
    checks["canonical_schemas_packaged"] = len(schema_files) >= 8
    checks["four_source_dataset_cards_packaged"] = len(source_cards) == 4
    details["schema_files"] = [path.name for path in schema_files]
    details["source_dataset_cards"] = [path.name for path in source_cards]

    # Final-release attribution/citation metadata. These checks are activated only
    # for the frozen final benchmark, so RC QA remains a separate gate.
    is_final = str(summary.get("release_status") or "") == "final" or str(summary.get("benchmark_version")) == "1.0.0"
    attribution_review_passed = False
    if is_final:
        checks["final_benchmark_version_frozen"] = str(summary.get("benchmark_version")) == "1.0.0"
        attribution_path = release_dir / "SOURCE_ATTRIBUTION.csv"
        review_path = release_dir / "ATTRIBUTION_REVIEW.json"
        citation_path = release_dir / "CITATION.cff"
        zenodo_metadata_path = release_dir / "ZENODO_METADATA.json"
        checks["source_attribution_packaged"] = attribution_path.exists()
        attribution_rows: list[dict[str, Any]] = []
        if attribution_path.exists():
            attribution = pd.read_csv(attribution_path)
            attribution_rows = attribution.to_dict(orient="records")
            checks["four_core_source_attributions_verified"] = (
                len(attribution) == 4
                and set(attribution["dataset_id"].astype(str)) == set(licences["dataset_id"].astype(str))
                and set(attribution["attribution_status"].astype(str)) == {"verified"}
                and set(attribution["upstream_license"].astype(str)) == {"CC-BY-4.0"}
            )
        else:
            checks["four_core_source_attributions_verified"] = False
        if review_path.exists():
            review = json.loads(review_path.read_text(encoding="utf-8"))
            attribution_review_passed = review.get("status") == "passed" and int(review.get("core_source_rows", 0)) == 4
        checks["scientific_attribution_review_passed"] = attribution_review_passed
        checks["benchmark_citation_metadata_packaged"] = citation_path.exists() and zenodo_metadata_path.exists()
        details["source_attribution_rows"] = attribution_rows
        details["attribution_review_passed"] = attribution_review_passed

    # Verify checksum coverage and values for every file that existed at build time.
    checksum_map = _parse_checksums(release_dir / "CHECKSUMS.sha256")
    checksum_mismatches: list[str] = []
    for relative, expected_digest in checksum_map.items():
        path = release_dir / relative
        if not path.exists() or _sha256(path) != expected_digest:
            checksum_mismatches.append(relative)
    current_files = {
        path.relative_to(release_dir).as_posix()
        for path in release_dir.rglob("*")
        if path.is_file() and path.name != "CHECKSUMS.sha256"
    }
    checks["checksums_match"] = not checksum_mismatches
    checks["checksums_cover_all_release_files"] = set(checksum_map) == current_files
    details["checksum_mismatches"] = checksum_mismatches
    details["checksum_uncovered_files"] = sorted(current_files - set(checksum_map))
    details["checksum_missing_files"] = sorted(set(checksum_map) - current_files)

    # Benchmark-data licence is independent from the Apache-2.0 software licence.
    release_license_candidates = [
        release_dir / "LICENSE",
        release_dir / "LICENSE.txt",
        release_dir / "LICENSE.md",
    ]
    benchmark_license_path = next((path for path in release_license_candidates if path.exists()), None)
    benchmark_license_declared = benchmark_license_path is not None
    checks["benchmark_release_license_declared"] = benchmark_license_declared
    if is_final:
        licence_text = benchmark_license_path.read_text(encoding="utf-8") if benchmark_license_path else ""
        checks["benchmark_release_license_is_cc_by_4_0"] = (
            benchmark_license_declared
            and "CC BY 4.0" in licence_text
            and "creativecommons.org/licenses/by/4.0" in licence_text
            and str(summary.get("benchmark_release_license_id")) == "CC-BY-4.0"
        )

    # In RC mode the licence and attribution review remain manual blockers; in
    # final mode they are ordinary integrity checks and can close the gate.
    integrity_check_names = list(checks)
    if not is_final:
        integrity_check_names = [name for name in checks if name != "benchmark_release_license_declared"]
    integrity_passed = all(checks[name] for name in integrity_check_names)
    manual_blockers: list[str] = []
    if not benchmark_license_declared:
        manual_blockers.append("benchmark_release_license_not_declared")
    if not is_final or not attribution_review_passed:
        manual_blockers.append("manual_scientific_attribution_review_not_signed_off")
    zenodo_authorised = bool(summary.get("zenodo_upload_authorised", False))
    zenodo_ready = integrity_passed and not manual_blockers and zenodo_authorised

    return {
        "stage": "Benchmark final-release QA" if is_final else "Benchmark release-candidate QA",
        "release_dir": str(release_dir),
        "benchmark_version": summary.get("benchmark_version"),
        "project_version": summary.get("project_version"),
        "release_integrity_passed": integrity_passed,
        "checks_passed": sum(bool(checks[name]) for name in integrity_check_names),
        "checks_failed": sum(not bool(checks[name]) for name in integrity_check_names),
        "checks": checks,
        "details": details,
        "benchmark_release_license_declared": benchmark_license_declared,
        "manual_finalisation_blockers": manual_blockers,
        "zenodo_finalisation_ready": zenodo_ready,
        "interpretation": (
            "Final release QA verifies internal table equivalence, Parquet row metadata, full 7x9 feasibility coverage, "
            "source licences/attribution, CC BY 4.0 benchmark licensing, checksum coverage and empirical/synthetic packaging boundaries."
            if is_final else
            "RC integrity QA verifies internal table equivalence, Parquet row metadata, full 7x9 feasibility coverage, "
            "source-licence gates, checksum coverage and empirical/synthetic packaging boundaries. A successful integrity "
            "audit does not choose the licence for STACKWISE-authored benchmark material and does not itself authorise Zenodo publication."
        ),
    }


def audit_benchmark_release(release_dir: str | Path = FINAL_RELEASE_DIR) -> dict[str, Any]:
    """Audit the frozen STACKWISE Benchmark Dataset v1.0.0 package."""
    return audit_benchmark_release_candidate(release_dir)
