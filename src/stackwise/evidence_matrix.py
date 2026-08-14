from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .evidence import (
    DEFAULT_EVIDENCE_SCHEMA,
    validate_evidence_record,
    validate_shared_parameter_record,
)

CORE_FOUR_DATASET_IDS = (
    "vomhoff_nbiot_ltem_energy_2023",
    "insectt_wsn_power_2023",
    "lorawan_lrfhss_energy_2024",
    "loed_lorawan_edge_2020",
)

EXPECTED_CORE_FOUR_RECORD_COUNTS = {
    "vomhoff_nbiot_ltem_energy_2023": 52,
    "insectt_wsn_power_2023": 80,
    "lorawan_lrfhss_energy_2024": 20,
    "loed_lorawan_edge_2020": 246,
}

DEFAULT_GAP_POLICY = Path("datasets/core_four_evidence_gap_policy.yml")
DEFAULT_METRIC_CATALOG = Path("datasets/evidence_metric_catalog.yml")


class EvidenceMatrixError(RuntimeError):
    pass


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceMatrixError(f"Invalid JSONL in {path} line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise EvidenceMatrixError(f"Expected object in {path} line {line_number}")
            records.append(value)
    return records


def load_shared_parameters(path: str | Path) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise EvidenceMatrixError(f"Shared-parameter artifact must contain a list: {path}")
    if not all(isinstance(item, dict) for item in value):
        raise EvidenceMatrixError(f"Shared-parameter artifact contains a non-object: {path}")
    return value


def schema_columns(schema_path: str | Path = DEFAULT_EVIDENCE_SCHEMA) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise EvidenceMatrixError("Evidence schema has no properties mapping")
    return list(properties)


def records_to_frame(
    records: Iterable[dict[str, Any]],
    *,
    schema_path: str | Path = DEFAULT_EVIDENCE_SCHEMA,
) -> pd.DataFrame:
    columns = schema_columns(schema_path)
    rows = []
    for record in records:
        rows.append({column: record.get(column) for column in columns})
    return pd.DataFrame(rows, columns=columns)


def records_to_csv_frame(
    records: Iterable[dict[str, Any]],
    *,
    schema_path: str | Path = DEFAULT_EVIDENCE_SCHEMA,
) -> pd.DataFrame:
    frame = records_to_frame(records, schema_path=schema_path)
    for field in ("parent_evidence_ids", "shared_parameter_ids"):
        if field in frame:
            frame[field] = frame[field].map(
                lambda value: "|".join(value) if isinstance(value, list) else ("" if value is None else str(value))
            )
    return frame


def validate_core_four_matrix(
    records: list[dict[str, Any]],
    shared_parameters: list[dict[str, Any]],
    *,
    expected_counts: dict[str, int] | None = EXPECTED_CORE_FOUR_RECORD_COUNTS,
) -> dict[str, Any]:
    errors: list[str] = []

    ids = [str(record.get("evidence_id")) for record in records]
    duplicate_ids = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate evidence_id values: {duplicate_ids[:5]}")

    for record in records:
        validation_errors = validate_evidence_record(record)
        if validation_errors:
            errors.append(f"{record.get('evidence_id')}: {validation_errors}")

    dataset_counts = Counter(str(record.get("dataset_id")) for record in records)
    unexpected_datasets = sorted(set(dataset_counts) - set(CORE_FOUR_DATASET_IDS))
    missing_datasets = sorted(set(CORE_FOUR_DATASET_IDS) - set(dataset_counts))
    if unexpected_datasets:
        errors.append(f"unexpected datasets in core-four matrix: {unexpected_datasets}")
    if missing_datasets:
        errors.append(f"missing core datasets: {missing_datasets}")

    if expected_counts is not None:
        for dataset_id, expected in expected_counts.items():
            actual = int(dataset_counts.get(dataset_id, 0))
            if actual != int(expected):
                errors.append(f"record-count checkpoint failed for {dataset_id}: {actual} != {expected}")

    metric_catalog = load_metric_catalog().get("metrics", {})
    target_records = [
        record["evidence_id"]
        for record in records
        if record.get("intended_use") == "target_only"
        or metric_catalog.get(record.get("metric_id"), {}).get("source_status") == "target_only"
    ]
    if target_records:
        errors.append(f"target-only decision metrics were materialised as empirical evidence: {target_records[:5]}")

    id_set = set(ids)
    unresolved_parents: list[tuple[str, str]] = []
    for record in records:
        for parent_id in record.get("parent_evidence_ids") or []:
            if parent_id not in id_set:
                unresolved_parents.append((str(record.get("evidence_id")), str(parent_id)))
    if unresolved_parents:
        errors.append(f"unresolved parent evidence references: {unresolved_parents[:5]}")

    parameter_ids: list[str] = []
    for parameter in shared_parameters:
        validation_errors = validate_shared_parameter_record(parameter)
        if validation_errors:
            errors.append(f"shared parameter {parameter.get('parameter_id')}: {validation_errors}")
        parameter_ids.append(str(parameter.get("parameter_id")))
    duplicate_parameter_ids = sorted(item for item, count in Counter(parameter_ids).items() if count > 1)
    if duplicate_parameter_ids:
        errors.append(f"duplicate shared parameter IDs: {duplicate_parameter_ids}")

    parameter_id_set = set(parameter_ids)
    unresolved_parameters: list[tuple[str, str]] = []
    for record in records:
        for parameter_id in record.get("shared_parameter_ids") or []:
            if parameter_id not in parameter_id_set:
                unresolved_parameters.append((str(record.get("evidence_id")), str(parameter_id)))
    if unresolved_parameters:
        errors.append(f"unresolved shared parameter references: {unresolved_parameters[:5]}")

    if errors:
        raise EvidenceMatrixError("; ".join(errors[:12]))

    metric_counts = Counter(str(record.get("metric_id")) for record in records)
    uncertainty_counts = Counter(str(record.get("uncertainty_basis")) for record in records)
    derivation_counts = Counter(str(record.get("derivation_class")) for record in records)
    source_grade_counts = Counter(str(record.get("source_grade")) for record in records)

    return {
        "records": len(records),
        "datasets": len(dataset_counts),
        "records_by_dataset": dict(sorted(dataset_counts.items())),
        "metrics": len(metric_counts),
        "records_by_metric": dict(sorted(metric_counts.items())),
        "shared_parameters": len(shared_parameters),
        "duplicate_evidence_ids": 0,
        "unresolved_parent_references": 0,
        "unresolved_shared_parameter_references": 0,
        "target_only_empirical_records": 0,
        "uncertainty_basis_counts": dict(sorted(uncertainty_counts.items())),
        "derivation_class_counts": dict(sorted(derivation_counts.items())),
        "source_grade_counts": dict(sorted(source_grade_counts.items())),
    }


def _joined_unique(series: pd.Series) -> str:
    values = sorted({str(value) for value in series.dropna() if str(value) not in {"", "nan", "None"}})
    return "|".join(values)


def build_metric_coverage(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = records_to_frame(records)
    group_fields = ["dataset_id", "technology", "metric_id", "metric_family", "unit"]
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(group_fields, dropna=False, sort=True):
        row = dict(zip(group_fields, key))
        n_ind = pd.to_numeric(group["n_independent_units"], errors="coerce")
        payload = pd.to_numeric(group["payload_bytes"], errors="coerce")
        interval = pd.to_numeric(group["reporting_interval_s"], errors="coerce")
        row.update(
            {
                "record_count": int(len(group)),
                "source_grades": _joined_unique(group["source_grade"]),
                "validation_statuses": _joined_unique(group["validation_status"]),
                "derivation_classes": _joined_unique(group["derivation_class"]),
                "uncertainty_bases": _joined_unique(group["uncertainty_basis"]),
                "intended_uses": _joined_unique(group["intended_use"]),
                "system_scopes": _joined_unique(group["system_scope"]),
                "temporal_scopes": _joined_unique(group["temporal_scope"]),
                "accounting_bases": _joined_unique(group["accounting_basis"]),
                "implementation_contexts": _joined_unique(group["implementation_context_id"]),
                "n_independent_units_min": int(n_ind.min()) if n_ind.notna().any() else None,
                "n_independent_units_max": int(n_ind.max()) if n_ind.notna().any() else None,
                "records_without_independent_n": int(n_ind.isna().sum()),
                "payload_bytes_min": int(payload.min()) if payload.notna().any() else None,
                "payload_bytes_max": int(payload.max()) if payload.notna().any() else None,
                "reporting_interval_s_min": float(interval.min()) if interval.notna().any() else None,
                "reporting_interval_s_max": float(interval.max()) if interval.notna().any() else None,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_boundary_profile(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = records_to_frame(records)
    boundary_fields = [
        "dataset_id",
        "metric_id",
        "system_scope",
        "temporal_scope",
        "accounting_basis",
        "conditioning",
        "payload_basis",
        "baseline_accounting",
        "ack_rx_accounting",
        "retry_accounting",
        "path_start",
        "path_end",
    ]
    grouped = (
        frame.groupby(boundary_fields, dropna=False, sort=True)
        .size()
        .reset_index(name="record_count")
    )
    return grouped


def load_gap_policy(path: str | Path = DEFAULT_GAP_POLICY) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceMatrixError(f"Gap policy must be a mapping: {path}")
    return value


def load_metric_catalog(path: str | Path = DEFAULT_METRIC_CATALOG) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceMatrixError(f"Metric catalogue must be a mapping: {path}")
    return value


def build_target_gap_matrix(
    records: list[dict[str, Any]],
    *,
    policy_path: str | Path = DEFAULT_GAP_POLICY,
    metric_catalog_path: str | Path = DEFAULT_METRIC_CATALOG,
) -> pd.DataFrame:
    policy = load_gap_policy(policy_path)
    catalog = load_metric_catalog(metric_catalog_path).get("metrics", {})
    actual_metrics_by_dataset: dict[str, set[str]] = {}
    for record in records:
        actual_metrics_by_dataset.setdefault(str(record["dataset_id"]), set()).add(str(record["metric_id"]))

    allowed_relations = {"C1_BRIDGEABLE", "C2_CONDITIONAL", "C3_INCOMPATIBLE", "E0_MISSING"}
    rows = policy.get("target_relations", [])
    if not isinstance(rows, list):
        raise EvidenceMatrixError("target_relations must be a list")

    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise EvidenceMatrixError("Each target relation must be a mapping")
        target = str(item.get("target_metric_id"))
        dataset_id = str(item.get("dataset_id"))
        relation = str(item.get("relation_class"))
        key = (target, dataset_id)
        if key in seen:
            raise EvidenceMatrixError(f"Duplicate target/dataset relation: {key}")
        seen.add(key)
        if dataset_id not in CORE_FOUR_DATASET_IDS:
            raise EvidenceMatrixError(f"Unknown core dataset in gap policy: {dataset_id}")
        metric = catalog.get(target)
        if not metric or metric.get("source_status") != "target_only":
            raise EvidenceMatrixError(f"Gap target is not a target_only metric: {target}")
        if relation not in allowed_relations:
            raise EvidenceMatrixError(f"Invalid relation_class {relation} for {key}")
        supporting = list(item.get("supporting_metric_ids") or [])
        prohibited = list(item.get("prohibited_proxy_metric_ids") or [])
        available = actual_metrics_by_dataset.get(dataset_id, set())
        missing_support = sorted(set(supporting) - available)
        missing_prohibited = sorted(set(prohibited) - available)
        if missing_support:
            raise EvidenceMatrixError(f"Gap policy support metrics absent for {key}: {missing_support}")
        if missing_prohibited:
            raise EvidenceMatrixError(f"Gap policy prohibited proxy metrics absent for {key}: {missing_prohibited}")
        if relation == "E0_MISSING" and supporting:
            raise EvidenceMatrixError(f"E0_MISSING cannot declare supporting metrics for {key}")
        output.append(
            {
                "target_metric_id": target,
                "target_family": metric.get("family"),
                "target_unit": metric.get("unit"),
                "dataset_id": dataset_id,
                "relation_class": relation,
                "supporting_metric_ids": "|".join(supporting),
                "prohibited_proxy_metric_ids": "|".join(prohibited),
                "required_bridge_or_missing_evidence": str(item.get("required_bridge_or_missing_evidence", "")),
                "interpretation": str(item.get("interpretation", "")),
            }
        )

    expected_targets = set(policy.get("target_metrics", []))
    expected_pairs = {(target, dataset_id) for target in expected_targets for dataset_id in CORE_FOUR_DATASET_IDS}
    if seen != expected_pairs:
        missing = sorted(expected_pairs - seen)
        extra = sorted(seen - expected_pairs)
        raise EvidenceMatrixError(f"Gap policy target/dataset coverage mismatch; missing={missing}, extra={extra}")
    return pd.DataFrame(output).sort_values(["target_metric_id", "dataset_id"]).reset_index(drop=True)


def build_nonmetric_gap_table(*, policy_path: str | Path = DEFAULT_GAP_POLICY) -> pd.DataFrame:
    policy = load_gap_policy(policy_path)
    rows = policy.get("non_metric_gaps", [])
    if not isinstance(rows, list):
        raise EvidenceMatrixError("non_metric_gaps must be a list")
    return pd.DataFrame(rows)


def build_matrix_summary(
    records: list[dict[str, Any]],
    shared_parameters: list[dict[str, Any]],
    target_gap_matrix: pd.DataFrame,
    boundary_profile: pd.DataFrame,
    validation: dict[str, Any],
) -> dict[str, Any]:
    unresolved_targets = sorted(target_gap_matrix["target_metric_id"].unique().tolist())
    loed = [r for r in records if r.get("dataset_id") == "loed_lorawan_edge_2020"]
    loed_without_n = sum(r.get("n_independent_units") is None for r in loed)
    return {
        "stage": "Stage-2 unified core-four empirical evidence matrix",
        **validation,
        "boundary_signatures": int(len(boundary_profile)),
        "target_metrics_assessed": int(target_gap_matrix["target_metric_id"].nunique()),
        "target_metrics_still_requiring_external_evidence_or_bridge": unresolved_targets,
        "loed_records_without_independent_n": int(loed_without_n),
        "publication_mcda_authorised": False,
        "stage2_core_four_materialisation_complete": True,
        "next_scientific_stage": "Stage 3 uncertainty model specification and calibration; do not rank stacks yet.",
    }
