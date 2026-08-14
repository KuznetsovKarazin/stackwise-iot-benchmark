from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


DEFAULT_POLICY = Path("datasets/benchmark_release_candidate.yml")
FINAL_POLICY = Path("datasets/benchmark_release.yml")
DEFAULT_REGISTRY = Path("datasets/registry.yml")
DEFAULT_OUTPUT_DIR = Path("release/stackwise_benchmark_v1.0.0-rc1")
FINAL_OUTPUT_DIR = Path("release/stackwise_benchmark_v1.0.0")


@dataclass(frozen=True)
class ReleaseArtifact:
    source: Path
    destination: Path
    layer: str
    required: bool
    expected_rows: int | None = None
    transform: str | None = None


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_rows(path: Path) -> int | None:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return len(pd.read_csv(path))
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    if suffix == ".parquet":
        # ``pd.read_parquet(..., columns=[])`` can return an empty frame with
        # zero rows even when the Parquet file contains data. Prefer Parquet
        # metadata, which is both exact and cheap, and fall back to a full read
        # only when the optional backend does not expose metadata.
        try:
            import pyarrow.parquet as pq

            return int(pq.ParquetFile(path).metadata.num_rows)
        except Exception:
            try:
                return len(pd.read_parquet(path))
            except Exception:
                return None
    return None


def _normalise_artifacts(policy: dict[str, Any]) -> list[ReleaseArtifact]:
    artifacts: list[ReleaseArtifact] = []
    for item in policy.get("artifacts", []):
        artifacts.append(
            ReleaseArtifact(
                source=Path(item["source"]),
                destination=Path(item["destination"]),
                layer=str(item["layer"]),
                required=bool(item.get("required", True)),
                expected_rows=int(item["row_count"]) if item.get("row_count") is not None else None,
                transform=str(item["transform"]) if item.get("transform") else None,
            )
        )
    return artifacts


def _core_license_rows(registry: dict[str, Any], core_ids: list[str], verified_on: str) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in registry.get("datasets", [])}
    rows: list[dict[str, Any]] = []
    for dataset_id in core_ids:
        if dataset_id not in by_id:
            raise RuntimeError(f"Core source missing from registry: {dataset_id}")
        item = by_id[dataset_id]
        licence = item.get("licence") or {}
        row = {
            "dataset_id": dataset_id,
            "title": item.get("title"),
            "doi": item.get("doi"),
            "landing_url": item.get("landing_url"),
            "license_id": licence.get("id"),
            "license_status": licence.get("status"),
            "redistribution": bool(licence.get("redistribution", False)),
            "verified_on": verified_on,
        }
        rows.append(row)
    bad = [r for r in rows if r["license_status"] != "verified" or not r["redistribution"]]
    if bad:
        details = ", ".join(f"{r['dataset_id']}:{r['license_status']}/{r['redistribution']}" for r in bad)
        raise RuntimeError(
            "Benchmark derived-data release requires verified redistributable licences for all core sources; "
            f"blocked: {details}"
        )
    return rows


def _write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _copy_with_release_license_resolution(
    artifact: ReleaseArtifact,
    project_root: Path,
    output_dir: Path,
    license_by_dataset: dict[str, str],
) -> Path:
    source = project_root / artifact.source
    destination = output_dir / artifact.destination
    destination.parent.mkdir(parents=True, exist_ok=True)

    name = artifact.source.name
    is_core_matrix = "core_four_evidence_matrix" in name
    if not is_core_matrix:
        shutil.copy2(source, destination)
        return destination

    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
        if "source_license" in frame.columns and "dataset_id" in frame.columns:
            frame["source_license"] = frame["dataset_id"].map(license_by_dataset).fillna(frame["source_license"])
        frame.to_csv(destination, index=False)
        return destination

    if source.suffix.lower() == ".jsonl":
        with source.open("r", encoding="utf-8") as input_handle, destination.open(
            "w", encoding="utf-8", newline="\n"
        ) as output_handle:
            for line in input_handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if "source_license" in record and record.get("dataset_id") in license_by_dataset:
                    record["source_license"] = license_by_dataset[record["dataset_id"]]
                output_handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return destination

    if source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
        if "source_license" in frame.columns and "dataset_id" in frame.columns:
            frame["source_license"] = frame["dataset_id"].map(license_by_dataset).fillna(frame["source_license"])
        frame.to_parquet(destination, index=False)
        return destination

    shutil.copy2(source, destination)
    return destination




def _materialise_refined_stage4_scenarios(source_yaml: Path, destination: Path) -> Path:
    """Materialise the canonical seven-scenario Stage-4E benchmark table.

    Stage-4D defined six source scenarios. Stage-4E subsequently replaced the
    underspecified ``asset_tracking_mobility`` scenario with two explicit
    semantics-preserving variants. Release L3 must therefore be derived from
    the refined scenario definition, not copied from the stale six-row
    Stage-4D CSV.
    """
    from .hard_capability_review import build_refined_scenarios

    payload = _load_yaml(source_yaml)
    scenarios, _ = build_refined_scenarios(payload)
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        q = scenario["quantitative_context"]
        d = scenario["deployment_facts"]
        rows.append({
            "scenario_id": scenario["scenario_id"],
            "name": scenario["name"],
            "archetype": scenario["archetype"],
            "payload_bytes": q["payload_bytes"],
            "reporting_interval_s": q["reporting_interval_s"],
            "target_end_to_end_latency_ms": q["target_end_to_end_latency_ms"],
            "whole_device_energy_budget_per_report_j": q.get("whole_device_energy_budget_per_report_j"),
            "cellular_access_service_available_at_site": d["cellular_access_service_available_at_site"],
            "lorawan_access_service_available_at_site": d["lorawan_access_service_available_at_site"],
            "thread_border_router_available_at_site": d["thread_border_router_available_at_site"],
            "hard_constraint_ids": "|".join(c["constraint_id"] for c in scenario["hard_constraints"]),
            "assumption_status": scenario["assumption_status"],
        })
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(destination, index=False)
    return destination


def _materialise_artifact(
    artifact: ReleaseArtifact,
    project_root: Path,
    output_dir: Path,
    license_by_dataset: dict[str, str],
) -> Path:
    if artifact.transform is None:
        return _copy_with_release_license_resolution(artifact, project_root, output_dir, license_by_dataset)
    if artifact.transform == "stage4_refined_scenarios":
        return _materialise_refined_stage4_scenarios(
            project_root / artifact.source, output_dir / artifact.destination
        )
    raise RuntimeError(f"Unknown release artifact transform: {artifact.transform}")


def _license_metadata_corrections(project_root: Path, license_by_dataset: dict[str, str]) -> list[dict[str, Any]]:
    source = project_root / "data/analysis_ready/core_four_evidence/core_four_evidence_matrix.csv"
    frame = pd.read_csv(source, usecols=["dataset_id", "source_license"])
    rows: list[dict[str, Any]] = []
    for dataset_id, group in frame.groupby("dataset_id", dropna=False):
        original_values = sorted({str(v) for v in group["source_license"].dropna().unique()})
        original = "|".join(original_values) if original_values else ""
        resolved = license_by_dataset.get(str(dataset_id), original)
        if original != resolved:
            rows.append({
                "dataset_id": str(dataset_id),
                "source_license_at_materialisation": original,
                "resolved_release_license": resolved,
                "change_scope": "metadata_only",
                "empirical_values_changed": False,
            })
    return rows


def _validate_core_matrix(csv_path: Path, expected: dict[str, Any], core_ids: list[str]) -> dict[str, Any]:
    frame = pd.read_csv(csv_path)
    if len(frame) != int(expected["core_evidence_records"]):
        raise RuntimeError(f"Unexpected core evidence count: {len(frame)}")
    if frame["dataset_id"].nunique() != int(expected["core_datasets"]):
        raise RuntimeError("Unexpected number of core datasets in release evidence matrix")
    if set(frame["dataset_id"].unique()) != set(core_ids):
        raise RuntimeError("Release evidence matrix core dataset IDs do not match release policy")
    if frame["metric_id"].nunique() != int(expected["core_metrics"]):
        raise RuntimeError("Unexpected number of core metrics in release evidence matrix")
    if int((frame["source_grade"] == "A").sum()) != int(expected["source_grade_A_records"]):
        raise RuntimeError("Not all expected core evidence records are Grade A")
    if frame["evidence_id"].duplicated().any():
        raise RuntimeError("Duplicate evidence_id values in release matrix")
    return {
        "records": int(len(frame)),
        "datasets": int(frame["dataset_id"].nunique()),
        "metrics": int(frame["metric_id"].nunique()),
        "technologies": int(frame["technology"].nunique()),
        "grade_A_records": int((frame["source_grade"] == "A").sum()),
        "direct_empirical_records": int((frame["derivation_class"] == "direct_empirical").sum()),
        "source_reproduced_records": int((frame["derivation_class"] == "source_reproduced").sum()),
        "validated_derived_records": int((frame["derivation_class"] == "validated_derived").sum()),
    }


def _validate_benchmark_tables(output_dir: Path, expected: dict[str, Any]) -> dict[str, Any]:
    scenarios = pd.read_csv(output_dir / "tables/L3_benchmark_definitions/benchmark_scenarios.csv")
    stacks = pd.read_csv(output_dir / "tables/L3_benchmark_definitions/candidate_stack_catalog.csv")
    feasibility = pd.read_csv(output_dir / "tables/L4_feasibility_and_support/refined_hard_feasibility_matrix.csv")
    if len(scenarios) != int(expected["benchmark_scenarios"]):
        raise RuntimeError("Unexpected benchmark scenario count")
    if len(stacks) != int(expected["candidate_stacks"]):
        raise RuntimeError("Unexpected candidate stack count")
    if len(feasibility) != int(expected["feasibility_rows"]):
        raise RuntimeError("Unexpected feasibility matrix row count")
    counts = feasibility["status"].value_counts().to_dict()
    for key, expected_key in [
        ("feasible", "feasible_rows"),
        ("infeasible", "infeasible_rows"),
        ("unresolved", "unresolved_rows"),
    ]:
        if int(counts.get(key, 0)) != int(expected[expected_key]):
            raise RuntimeError(f"Unexpected {key} feasibility count: {counts.get(key, 0)}")
    return {
        "scenarios": int(len(scenarios)),
        "candidate_stacks": int(len(stacks)),
        "feasibility_rows": int(len(feasibility)),
        "feasible": int(counts.get("feasible", 0)),
        "infeasible": int(counts.get("infeasible", 0)),
        "unresolved": int(counts.get("unresolved", 0)),
    }


def _copy_release_metadata_assets(project_root: Path, output_dir: Path, policy: dict[str, Any]) -> list[Path]:
    """Copy compact self-description assets for RC or final benchmark releases."""

    dataset_card_source = Path(policy.get("dataset_card_source") or "docs/BENCHMARK_DATASET_RELEASE_CANDIDATE.md")
    assets: list[tuple[Path, Path]] = [
        (dataset_card_source, Path("DATASET_CARD.md")),
        (Path("datasets/schema/evidence_record.schema.json"), Path("schemas/evidence_record.schema.json")),
        (Path("datasets/schema/canonical_observation.schema.json"), Path("schemas/canonical_observation.schema.json")),
        (Path("datasets/schema/shared_parameter.schema.json"), Path("schemas/shared_parameter.schema.json")),
        (Path("datasets/schema/benchmark_scenario.schema.json"), Path("schemas/benchmark_scenario.schema.json")),
        (Path("datasets/schema/stack_candidate.schema.json"), Path("schemas/stack_candidate.schema.json")),
        (Path("datasets/schema/stack_component.schema.json"), Path("schemas/stack_component.schema.json")),
        (Path("datasets/schema/uncertainty_model.schema.json"), Path("schemas/uncertainty_model.schema.json")),
        (Path("datasets/schema/hard_constraint.schema.json"), Path("schemas/hard_constraint.schema.json")),
        (Path("docs/DATASET_CARDS/insectt_wsn_power_2023.md"), Path("source_dataset_cards/insectt_wsn_power_2023.md")),
        (Path("docs/DATASET_CARDS/vomhoff_nbiot_ltem_energy_2023.md"), Path("source_dataset_cards/vomhoff_nbiot_ltem_energy_2023.md")),
        (Path("docs/DATASET_CARDS/loed_lorawan_edge_2020.md"), Path("source_dataset_cards/loed_lorawan_edge_2020.md")),
        (Path("docs/DATASET_CARDS/lorawan_lrfhss_energy_2024.md"), Path("source_dataset_cards/lorawan_lrfhss_energy_2024.md")),
    ]
    for item in policy.get("metadata_assets", []) or []:
        assets.append((Path(item["source"]), Path(item["destination"])))

    copied: list[Path] = []
    for source_rel, destination_rel in assets:
        source = project_root / source_rel
        if not source.exists():
            raise FileNotFoundError(f"Required release metadata asset missing: {source_rel}")
        destination = output_dir / destination_rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def _source_attribution_rows(project_root: Path, policy: dict[str, Any], core_ids: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    review = policy.get("attribution_review") or {}
    source_rel = review.get("source")
    if not source_rel:
        return [], None
    payload = _load_yaml(project_root / Path(source_rel))
    rows: list[dict[str, Any]] = []
    for source in payload.get("sources", []) or []:
        rows.append({
            "dataset_id": source.get("dataset_id"),
            "dataset_title": source.get("dataset_title"),
            "creators": " | ".join(source.get("creators") or []),
            "dataset_doi": source.get("dataset_doi"),
            "related_publication_title": source.get("related_publication_title"),
            "related_publication_doi": source.get("related_publication_doi"),
            "upstream_license": source.get("upstream_license"),
            "stackwise_role": source.get("stackwise_role"),
            "attribution_status": source.get("attribution_status"),
            "verification_basis": source.get("verification_basis"),
        })
    if set(row["dataset_id"] for row in rows) != set(core_ids):
        raise RuntimeError("Source attribution manifest does not match the four core source IDs")
    if any(row["attribution_status"] != "verified" for row in rows):
        raise RuntimeError("Source attribution manifest contains unverified core source rows")
    review_record = {
        "status": str(review.get("status") or payload.get("review_status") or "unknown"),
        "reviewed_on": str(review.get("reviewed_on") or payload.get("reviewed_on") or ""),
        "review_scope": str(payload.get("review_scope") or "scientific_attribution"),
        "source_manifest": str(source_rel),
        "core_source_rows": len(rows),
    }
    return rows, review_record


def _materialise_benchmark_license(project_root: Path, output_dir: Path, policy: dict[str, Any]) -> tuple[Path | None, str | None]:
    license_policy = policy.get("benchmark_license") or {}
    source_rel = license_policy.get("source")
    if not source_rel:
        return None, None
    destination_rel = Path(license_policy.get("destination") or "LICENSE.md")
    source = project_root / Path(source_rel)
    if not source.exists():
        raise FileNotFoundError(f"Benchmark licence source missing: {source_rel}")
    destination = output_dir / destination_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination, str(license_policy.get("id") or "")


def _release_readme(policy: dict[str, Any], stats: dict[str, Any], licenses: list[dict[str, Any]]) -> str:
    evidence = stats["evidence"]
    benchmark = stats["benchmark"]
    source_lines = "\n".join(
        f"- `{row['dataset_id']}` — {row['doi']} — {row['license_id']}" for row in licenses
    )
    is_final = str(policy.get("release_status") or "release_candidate") == "final"
    status_line = "Final research dataset release." if is_final else "Release-candidate research dataset."
    ranking_line = (
        "No real candidate ranking or publication MCDA result is included in this benchmark release."
        if is_final
        else "No real candidate ranking or publication MCDA result is included in this release candidate."
    )
    if is_final:
        release_status = (
            f"This is the frozen **v{policy['benchmark_version']}** benchmark release. "
            f"STACKWISE-authored benchmark material is licensed under **{policy['benchmark_license']['id']}**. "
            "The package is technically ready for archival deposit; publication MCDA remains a separate research step."
        )
    else:
        release_status = (
            f"This is **v{policy['benchmark_version']}**. It is ready for manual scientific/licence review, "
            "but archival upload remains blocked until final release decisions are completed."
        )
    return f"""# STACKWISE Empirical Evidence Benchmark {policy['benchmark_version']}

{status_line} Generated by STACKWISE project v{policy['project_version']}.

## What this release is

A harmonised, provenance-preserving benchmark derived from four independently published real IoT measurement datasets. It is **not** a new physical measurement campaign and it contains no mirrored raw external archives.

The release separates six layers: analysis-ready source-specific derivatives, canonical evidence records, uncertainty contracts, benchmark definitions, feasibility/evidence-support results, and explicitly synthetic/model-derived sensitivity artifacts. A dataset card, canonical JSON schemas and the four upstream dataset cards are packaged alongside the tables for standalone interpretation.

## Frozen release statistics

- canonical evidence records: **{evidence['records']}**
- empirical source datasets: **{evidence['datasets']}**
- metric IDs: **{evidence['metrics']}**
- technologies represented in the evidence matrix: **{evidence['technologies']}**
- direct empirical / source-reproduced / validated-derived records: **{evidence['direct_empirical_records']} / {evidence['source_reproduced_records']} / {evidence['validated_derived_records']}**
- benchmark scenarios / candidate stacks: **{benchmark['scenarios']} / {benchmark['candidate_stacks']}**
- hard-feasibility outcomes: **{benchmark['feasible']} feasible / {benchmark['infeasible']} infeasible / {benchmark['unresolved']} unresolved**

## Core empirical sources

{source_lines}

Each upstream dataset must still be cited independently. Source creators, related-publication metadata and STACKWISE derivation roles are listed in `SOURCE_ATTRIBUTION.csv`.

## Scientific boundaries

The benchmark does not force heterogeneous energy, link-quality, reliability, latency or cost observations onto a common score. Measurement boundaries, statistical units, independence assumptions, applicability domains and non-identifiable uncertainty are retained.

Synthetic protocol/session/cost sensitivity tables are clearly separated under `L5_synthetic_sensitivity` and must not be described as measurements. {ranking_line}

## Release status

{release_status}
"""


def build_benchmark_release_candidate(
    project_root: str | Path = ".",
    *,
    policy_path: str | Path = DEFAULT_POLICY,
    registry_path: str | Path = DEFAULT_REGISTRY,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    clean: bool = True,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    policy = _load_yaml(project_root / Path(policy_path))
    registry = _load_yaml(project_root / Path(registry_path))
    output_dir = project_root / Path(output_dir)

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    core_ids = list(policy.get("core_source_ids") or [])
    verified_on = str(policy.get("prepared_on"))
    license_rows = _core_license_rows(registry, core_ids, verified_on)
    license_by_dataset = {row["dataset_id"]: row["license_id"] for row in license_rows}

    artifacts = _normalise_artifacts(policy)
    missing = [str(a.source) for a in artifacts if a.required and not (project_root / a.source).exists()]
    if missing:
        raise FileNotFoundError(
            "Benchmark release inputs are missing. Rebuild the existing analysis-ready/validation artifacts first:\n- "
            + "\n- ".join(missing)
        )

    manifest_rows: list[dict[str, Any]] = []
    copied_paths: list[Path] = []
    for artifact in artifacts:
        source_path = project_root / artifact.source
        if not source_path.exists():
            continue
        if artifact.expected_rows is not None and artifact.transform is None:
            actual = _count_rows(source_path)
            if actual is not None and actual != artifact.expected_rows:
                raise RuntimeError(
                    f"Unexpected row count for {artifact.source}: {actual} != {artifact.expected_rows}"
                )
        destination = _materialise_artifact(
            artifact, project_root, output_dir, license_by_dataset
        )
        if artifact.expected_rows is not None:
            actual = _count_rows(destination)
            if actual is not None and actual != artifact.expected_rows:
                raise RuntimeError(
                    f"Unexpected row count after materialising {artifact.destination}: "
                    f"{actual} != {artifact.expected_rows}"
                )
        copied_paths.append(destination)
        manifest_rows.append(
            {
                "layer": artifact.layer,
                "source_path": artifact.source.as_posix(),
                "release_path": artifact.destination.as_posix(),
                "bytes": destination.stat().st_size,
                "rows": _count_rows(destination),
                "sha256": _sha256(destination),
                "raw_external_data": False,
            }
        )

    licenses_path = _write_csv(license_rows, output_dir / "SOURCE_LICENSES.csv")
    copied_paths.append(licenses_path)
    correction_rows = _license_metadata_corrections(project_root, license_by_dataset)
    corrections_path = _write_csv(correction_rows, output_dir / "LICENSE_METADATA_CORRECTIONS.csv")
    copied_paths.append(corrections_path)

    metadata_paths = _copy_release_metadata_assets(project_root, output_dir, policy)
    copied_paths.extend(metadata_paths)

    benchmark_license_path, benchmark_license_id = _materialise_benchmark_license(project_root, output_dir, policy)
    if benchmark_license_path is not None:
        copied_paths.append(benchmark_license_path)

    attribution_rows, attribution_review = _source_attribution_rows(project_root, policy, core_ids)
    attribution_path = None
    attribution_review_path = None
    if attribution_rows:
        attribution_path = _write_csv(attribution_rows, output_dir / "SOURCE_ATTRIBUTION.csv")
        copied_paths.append(attribution_path)
    if attribution_review is not None:
        attribution_review_path = output_dir / "ATTRIBUTION_REVIEW.json"
        attribution_review_path.write_text(json.dumps(attribution_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        copied_paths.append(attribution_review_path)

    evidence_stats = _validate_core_matrix(
        output_dir / "tables/L1_evidence_records/core_four_evidence_matrix.csv",
        policy["expected"],
        core_ids,
    )
    benchmark_stats = _validate_benchmark_tables(output_dir, policy["expected"])

    stats = {"evidence": evidence_stats, "benchmark": benchmark_stats}
    readme_path = output_dir / "README.md"
    readme_path.write_text(_release_readme(policy, stats, license_rows), encoding="utf-8")
    copied_paths.append(readme_path)

    manifest_path = _write_csv(manifest_rows, output_dir / "RELEASE_TABLE_MANIFEST.csv")
    copied_paths.append(manifest_path)

    is_final = str(policy.get("release_status") or "release_candidate") == "final"
    attribution_passed = bool(attribution_review and attribution_review.get("status") == "passed")
    summary = {
        "stage": "Benchmark Dataset Final Release" if is_final else "Benchmark Dataset Release Candidate",
        "project_version": str(policy["project_version"]),
        "benchmark_id": str(policy["benchmark_id"]),
        "benchmark_version": str(policy["benchmark_version"]),
        "release_status": str(policy.get("release_status") or "release_candidate"),
        "release_profile": str(policy["release_profile"]),
        "core_source_licenses_verified_redistributable": len(license_rows),
        "raw_external_data_included": False,
        "license_metadata_corrections": len(correction_rows),
        "core_evidence_records": evidence_stats["records"],
        "core_datasets": evidence_stats["datasets"],
        "core_metrics": evidence_stats["metrics"],
        "benchmark_scenarios": benchmark_stats["scenarios"],
        "candidate_stacks": benchmark_stats["candidate_stacks"],
        "feasibility": {
            "feasible": benchmark_stats["feasible"],
            "infeasible": benchmark_stats["infeasible"],
            "unresolved": benchmark_stats["unresolved"],
        },
        "release_artifact_files": len(manifest_rows),
        "release_metadata_files": len(metadata_paths) + int(benchmark_license_path is not None) + int(attribution_path is not None) + int(attribution_review_path is not None),
        "benchmark_release_license_declared": benchmark_license_path is not None,
        "benchmark_release_license_id": benchmark_license_id,
        "scientific_attribution_review_passed": attribution_passed,
        "release_candidate_ready_for_manual_review": not is_final,
        "zenodo_upload_authorised": bool(policy.get("zenodo_upload_authorised", False)) and is_final and attribution_passed and benchmark_license_path is not None,
        "real_candidate_ranking_included": False,
        "publication_mcda_authorised": bool(policy.get("publication_mcda_authorised", False)),
        "interpretation": (
            f"STACKWISE v{policy['benchmark_version']} is a harmonised derived benchmark built from four real published IoT measurement datasets. "
            "The release preserves provenance, measurement boundaries and uncertainty semantics, contains no mirrored raw external archives, "
            "and separates empirical-derived content from synthetic/model-derived sensitivity artifacts."
        ),
    }
    summary_path = output_dir / "release_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    copied_paths.append(summary_path)

    checksum_lines = []
    for path in sorted([p for p in output_dir.rglob("*") if p.is_file()]):
        if path.name == "CHECKSUMS.sha256":
            continue
        checksum_lines.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}")
    checksum_path = output_dir / "CHECKSUMS.sha256"
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    return {
        "output_dir": str(output_dir),
        "summary": summary,
        "release_table_manifest": str(manifest_path),
        "source_licenses": str(licenses_path),
        "license_metadata_corrections": str(corrections_path),
        "source_attribution": str(attribution_path) if attribution_path else None,
        "attribution_review": str(attribution_review_path) if attribution_review_path else None,
        "benchmark_license": str(benchmark_license_path) if benchmark_license_path else None,
        "checksums": str(checksum_path),
    }


def build_benchmark_release(
    project_root: str | Path = ".",
    *,
    policy_path: str | Path = FINAL_POLICY,
    registry_path: str | Path = DEFAULT_REGISTRY,
    output_dir: str | Path = FINAL_OUTPUT_DIR,
    clean: bool = True,
) -> dict[str, Any]:
    """Build the frozen STACKWISE Benchmark Dataset v1.0.0 package."""
    return build_benchmark_release_candidate(
        project_root,
        policy_path=policy_path,
        registry_path=registry_path,
        output_dir=output_dir,
        clean=clean,
    )
