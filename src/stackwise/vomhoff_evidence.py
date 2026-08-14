
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from stackwise.vomhoff_audit import CANDIDATE_GROUP_FIELDS, DATASET_ID
from stackwise.vomhoff_independence import audit_vomhoff_independence

ADDITIVE_FIELDS = (
    "energy_j",
    "duration_s",
    "raw_energy_j",
    "raw_duration_s",
    "charge_as",
    "sample_count",
)

CONST_FIELDS = (
    "dataset_id",
    "study_id",
    "technology",
    "access_network",
    "transport_protocol",
    "application_protocol",
    "security_mode",
    "payload_bytes",
    "direction",
    "measurement_boundary",
    "evidence_grade",
    "source_license",
    "source_doi",
    "environment",
)

FIGURE5_MQTT_IDLE_EXCLUSION = "excluded_source_declared_invalid"
FIGURE5_HTTP_IDLE_ALTERNATE = "alternate_source_filtered_view"
CANONICAL_ROLE = "canonical"


class VomhoffMaterialisationError(ValueError):
    pass


def _stable_id(prefix: str, *values: Any) -> str:
    serialised = "|".join("<NA>" if pd.isna(v) else str(v) for v in values)
    return f"{prefix}-{hashlib.sha1(serialised.encode('utf-8')).hexdigest()[:16]}"


def _unique_non_null(series: pd.Series) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for value in series:
        if pd.isna(value):
            continue
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            out.append(value)
    return out


def _one_or_none(series: pd.Series, field: str) -> Any:
    values = _unique_non_null(series)
    if len(values) > 1:
        raise VomhoffMaterialisationError(
            f"Field {field!r} is not constant inside a logical phase: {values!r}"
        )
    return values[0] if values else None


def _json_list(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _run_key(row: pd.Series) -> tuple[str, str, str, int]:
    return (
        str(row.get("technology")),
        str(row.get("source_application_protocol")),
        str(row.get("source_data_object")),
        int(row.get("source_run")),
    )


def _shared_reuse_keys(run_pairs: pd.DataFrame) -> dict[tuple[str, str, str, int], set[int]]:
    mapping: dict[tuple[str, str, str, int], set[int]] = defaultdict(set)
    if run_pairs.empty:
        return mapping
    strong = run_pairs.loc[run_pairs["strong_source_reuse_flag"].astype(bool)]
    for _, row in strong.iterrows():
        key = (
            str(row["technology"]),
            str(row["source_application_protocol"]),
            str(row["source_data_object"]),
            int(row["source_run"]),
        )
        mapping[key].update({int(row["figure_a"]), int(row["figure_b"])})
    return mapping


def _phase_direction(phase: str) -> str:
    if phase == "Data Request":
        return "uplink"
    if phase == "Data Download":
        return "downlink"
    return "not_applicable"


def _role_for_view(row: pd.Series) -> tuple[str, bool, str]:
    fig = int(row["source_figure"])
    protocol = str(row.get("source_application_protocol")).casefold()
    phase = str(row["source_event"])
    if fig == 5 and protocol == "mqtt" and phase == "Idle":
        return (
            FIGURE5_MQTT_IDLE_EXCLUSION,
            False,
            "Source README states MQTT Idle is discarded because the device disconnects.",
        )
    if fig == 5 and protocol == "http" and phase == "Idle":
        return (
            FIGURE5_HTTP_IDLE_ALTERNATE,
            True,
            "Figure 5 applies an Idle-specific source filter absent from Figure 4; retain as an alternate dependent view.",
        )
    if fig == 5 and protocol == "mqtt" and phase == "Standby":
        return (
            CANONICAL_ROLE,
            True,
            "README states 10 s MQTT Standby normalisation, but fig5.R does not implement it; no silent correction applied.",
        )
    return CANONICAL_ROLE, True, ""


def build_vomhoff_stage2(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    """Materialise Stage-2 Vomhoff logical phase units and summary evidence.

    Scientific policy:
    - contiguous duplicate Data Request segments within one source Figure/run are additive;
    - strong Figure-4/Figure-5 NB-IoT/HTTP source reuse maps to one physical source run;
    - exact duplicated non-Idle phase views are counted once;
    - Figure-4 and Figure-5 HTTP Idle are retained as dependent, semantically distinct views;
    - Figure-5 MQTT Idle remains in source reproduction but is not decision evidence;
    - the README-only 10 s MQTT Standby normalisation is not invented.
    """
    ind_summary, adjacency, exact_matches, run_pairs = audit_vomhoff_independence(frame)
    if not ind_summary["within_source_figure_additive_aggregation_authorised"]:
        raise VomhoffMaterialisationError("Within-run additive aggregation is not authorised.")
    if ind_summary["strong_source_reuse_run_pairs"] <= 0:
        raise VomhoffMaterialisationError("Expected cross-Figure source reuse was not detected.")

    reuse = _shared_reuse_keys(run_pairs)

    # 1) Source-Figure logical phase rows: aggregate contiguous source segments.
    phase_rows: list[dict[str, Any]] = []
    grouped = frame.groupby(list(CANDIDATE_GROUP_FIELDS), dropna=False, sort=True)
    for key, group in grouped:
        key_map = dict(zip(CANDIDATE_GROUP_FIELDS, key if isinstance(key, tuple) else (key,)))
        row: dict[str, Any] = dict(key_map)
        for field in CONST_FIELDS:
            if field in group.columns:
                row[field] = _one_or_none(group[field], field)

        row["source_view_id"] = _stable_id(
            "vomhoff-source-view",
            *[key_map.get(field) for field in CANDIDATE_GROUP_FIELDS],
        )
        row["source_segment_count"] = int(len(group))
        row["parent_observation_ids"] = _json_list(
            sorted(str(v) for v in group["observation_id"].dropna().unique())
        )
        row["source_files"] = _json_list(
            sorted(str(v) for v in group["source_file"].dropna().unique())
        )
        row["normalisation_rules"] = _json_list(
            sorted(str(v) for v in group.get("normalisation_rule", pd.Series(dtype=object)).dropna().unique())
        )
        row["timestamp_min_utc"] = pd.to_datetime(
            group["timestamp_utc"], errors="coerce", utc=True
        ).min()
        row["timestamp_max_utc"] = pd.to_datetime(
            group["timestamp_utc"], errors="coerce", utc=True
        ).max()

        for field in ADDITIVE_FIELDS:
            if field in group.columns:
                vals = pd.to_numeric(group[field], errors="coerce")
                row[field] = float(vals.sum(min_count=1)) if vals.notna().any() else np.nan

        if pd.notna(row.get("energy_j")) and pd.notna(row.get("duration_s")) and float(row["duration_s"]) > 0:
            row["phase_mean_power_w"] = float(row["energy_j"]) / float(row["duration_s"])
        else:
            row["phase_mean_power_w"] = np.nan

        run_key = _run_key(pd.Series(row))
        figures = reuse.get(run_key)
        fig = int(row["source_figure"])
        if figures and fig in figures:
            row["physical_run_id"] = _stable_id("vomhoff-run", "shared", *run_key, ",".join(map(str, sorted(figures))))
            row["cross_figure_reuse"] = True
        else:
            row["physical_run_id"] = _stable_id(
                "vomhoff-run", "singleton", fig, row.get("source_file"), *run_key
            )
            row["cross_figure_reuse"] = False

        role, eligible, note = _role_for_view(pd.Series(row))
        row["analysis_role"] = role
        row["evidence_eligible"] = bool(eligible)
        row["stage2_note"] = note
        phase_rows.append(row)

    source_views = pd.DataFrame(phase_rows).sort_values(
        ["source_figure", "technology", "source_application_protocol", "source_run", "source_event"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    # 2) Collapse only exact, semantically identical cross-Figure non-Idle views.
    retained: list[dict[str, Any]] = []
    deduped_views = 0
    grouped2 = source_views.groupby(["physical_run_id", "source_event"], dropna=False, sort=True)
    for _, group in grouped2:
        if len(group) == 1:
            row = group.iloc[0].to_dict()
            row["source_figure_contexts"] = str(int(row["source_figure"]))
            row["source_view_count"] = 1
            retained.append(row)
            continue

        phases = set(group["source_event"].astype(str))
        if phases == {"Idle"}:
            for _, item in group.iterrows():
                row = item.to_dict()
                row["source_figure_contexts"] = str(int(row["source_figure"]))
                row["source_view_count"] = 1
                retained.append(row)
            continue

        figures = set(int(v) for v in group["source_figure"])
        if figures != {4, 5}:
            raise VomhoffMaterialisationError(
                f"Unexpected multi-view physical phase outside Figures 4/5: figures={sorted(figures)}"
            )
        if set(group["analysis_role"]) != {CANONICAL_ROLE}:
            raise VomhoffMaterialisationError("Only canonical views may be cross-Figure collapsed.")

        # The independence audit established exact raw reuse. Recheck the materialised
        # additive quantities before collapsing.
        for field in ("energy_j", "duration_s", "raw_energy_j", "raw_duration_s"):
            if field in group.columns:
                vals = pd.to_numeric(group[field], errors="coerce").dropna().to_numpy(dtype=float)
                if len(vals) and not np.allclose(vals, vals[0], rtol=1e-12, atol=1e-12):
                    raise VomhoffMaterialisationError(
                        f"Cross-Figure reused phase differs after aggregation for {field}: {vals!r}"
                    )

        base = group.sort_values("source_figure", kind="stable").iloc[0].to_dict()
        base["source_figure_contexts"] = "|".join(str(v) for v in sorted(figures))
        base["source_view_count"] = int(len(group))
        base["source_segment_count"] = int(group["source_segment_count"].sum())
        obs: list[str] = []
        files: list[str] = []
        norms: list[str] = []
        for _, item in group.iterrows():
            obs.extend(json.loads(item["parent_observation_ids"]))
            files.extend(json.loads(item["source_files"]))
            norms.extend(json.loads(item["normalisation_rules"]))
        base["parent_observation_ids"] = _json_list(sorted(set(obs)))
        base["source_files"] = _json_list(sorted(set(files)))
        base["normalisation_rules"] = _json_list(sorted(set(norms)))
        base["cross_figure_reuse"] = True
        base["stage2_note"] = (
            "Exact Figure-4/Figure-5 source reuse collapsed to one physical-run phase value; "
            "both source views retained in lineage."
        )
        retained.append(base)
        deduped_views += len(group) - 1

    logical = pd.DataFrame(retained).sort_values(
        ["physical_run_id", "source_event", "analysis_role", "source_figure"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    logical["logical_phase_id"] = [
        _stable_id(
            "vomhoff-phase",
            row["physical_run_id"],
            row["source_event"],
            row["analysis_role"],
            row["source_figure_contexts"],
        )
        for _, row in logical.iterrows()
    ]

    # 3) Source-segment vs corrected within-Figure estimand audit.
    comparison_rows: list[dict[str, Any]] = []
    compare_fields = [
        "source_figure", "technology", "source_application_protocol",
        "source_data_object", "source_event"
    ]
    segment_stats = frame.groupby(compare_fields, dropna=False).agg(
        source_segment_n=("observation_id", "size"),
        source_segment_mean_energy_j=("energy_j", "mean"),
        source_segment_mean_duration_s=("duration_s", "mean"),
    ).reset_index()
    phase_stats = source_views.groupby(compare_fields, dropna=False).agg(
        logical_run_phase_n=("source_view_id", "size"),
        logical_run_phase_mean_energy_j=("energy_j", "mean"),
        logical_run_phase_mean_duration_s=("duration_s", "mean"),
    ).reset_index()
    comparison = segment_stats.merge(phase_stats, on=compare_fields, how="outer")
    comparison["energy_estimand_change_pct"] = np.where(
        comparison["source_segment_mean_energy_j"].abs() > 0,
        100.0 * (
            comparison["logical_run_phase_mean_energy_j"]
            / comparison["source_segment_mean_energy_j"] - 1.0
        ),
        np.nan,
    )
    comparison["duration_estimand_change_pct"] = np.where(
        comparison["source_segment_mean_duration_s"].abs() > 0,
        100.0 * (
            comparison["logical_run_phase_mean_duration_s"]
            / comparison["source_segment_mean_duration_s"] - 1.0
        ),
        np.nan,
    )

    # 4) Summary evidence records over canonical independent physical runs.
    evidence_records: list[dict[str, Any]] = []
    eligible = logical.loc[logical["evidence_eligible"].astype(bool)].copy()
    summary_group_fields = [
        "technology",
        "access_network",
        "transport_protocol",
        "application_protocol",
        "source_application_protocol",
        "source_data_object",
        "payload_bytes",
        "source_event",
        "analysis_role",
        "normalisation_rules",
    ]
    for key, group in eligible.groupby(summary_group_fields, dropna=False, sort=True):
        key_map = dict(zip(summary_group_fields, key if isinstance(key, tuple) else (key,)))
        n_ind = int(group["physical_run_id"].nunique())
        if n_ind <= 0:
            continue
        source_doi = _one_or_none(group["source_doi"], "source_doi")
        source_license = _one_or_none(group["source_license"], "source_license")
        study_id = _one_or_none(group["study_id"], "study_id")
        source_grade = _one_or_none(group["evidence_grade"], "evidence_grade") or "A"
        phase = str(key_map["source_event"])
        role = str(key_map["analysis_role"])
        protocol_raw = str(key_map["source_application_protocol"])
        source_figures = sorted(
            {int(v) for text in group["source_figure_contexts"].astype(str) for v in text.split("|")}
        )
        payload = key_map["payload_bytes"]
        payload_val = None if pd.isna(payload) else float(payload)
        direction = _phase_direction(phase)
        conditioning = "source_filtered" if role == FIGURE5_HTTP_IDLE_ALTERNATE else "unconditional"
        intended = "descriptive" if role != CANONICAL_ROLE else "direct_comparison"
        limitations: list[str] = []
        if role == FIGURE5_HTTP_IDLE_ALTERNATE:
            limitations.append(
                "Dependent alternate HTTP Idle view from the same physical runs as Figure 4; "
                "Figure 5 applies an additional source filter."
            )
        if protocol_raw.casefold() == "mqtt" and phase == "Standby" and 5 in source_figures:
            limitations.append(
                "Source README states 10 s Standby normalisation for MQTT, but fig5.R does not "
                "implement it; STACKWISE retains the source-script value without silent correction."
            )
        n_source = int(group["source_segment_count"].sum())
        dep_text = (
            "Independent unit is canonical physical/source run. Exact Figure-4/Figure-5 "
            "NB-IoT/HTTP source reuse is collapsed before summary statistics."
        )
        if role == FIGURE5_HTTP_IDLE_ALTERNATE:
            dep_text += " This alternate view shares the same parent runs as canonical Figure-4 HTTP Idle."

        for metric_id, family, unit, value_col, semantic in (
            (
                "device_phase_energy_j",
                "energy",
                "J",
                "energy_j",
                "Mean whole-device energy of the source-defined phase after within-run additive "
                "segment aggregation and cross-Figure source-reuse correction.",
            ),
            (
                "device_phase_duration_s",
                "duration",
                "s",
                "duration_s",
                "Mean duration of the source-defined phase after within-run additive segment "
                "aggregation and cross-Figure source-reuse correction.",
            ),
        ):
            estimate = float(pd.to_numeric(group[value_col], errors="coerce").mean())
            eid = _stable_id(
                "vomhoff-evidence",
                metric_id,
                key_map["technology"],
                protocol_raw,
                key_map["source_data_object"],
                phase,
                role,
                key_map["normalisation_rules"],
            )
            record = {
                "evidence_id": eid,
                "dataset_id": DATASET_ID,
                "study_id": None if pd.isna(study_id) else str(study_id),
                "source_doi": None if pd.isna(source_doi) else str(source_doi),
                "source_license": None if pd.isna(source_license) else str(source_license),
                "source_artifact": "data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/logical_phase_observations.parquet",
                "technology": str(key_map["technology"]),
                "access_network": None if pd.isna(key_map["access_network"]) else str(key_map["access_network"]),
                "transport_protocol": None if pd.isna(key_map["transport_protocol"]) else str(key_map["transport_protocol"]),
                "application_protocol": None if pd.isna(key_map["application_protocol"]) else str(key_map["application_protocol"]),
                "security_mode": None,
                "management_protocol": None,
                "metric_id": metric_id,
                "metric_family": family,
                "unit": unit,
                "value_semantics": semantic,
                "estimate": estimate,
                "summary_statistic": "mean",
                "system_scope": "whole_device",
                "temporal_scope": "phase",
                "accounting_basis": "per_phase",
                "conditioning": conditioning,
                "payload_basis": "source_message_size" if payload_val is not None else "not_applicable",
                "baseline_accounting": "included",
                "ack_rx_accounting": "included",
                "retry_accounting": "included",
                "path_start": "not_applicable",
                "path_end": "not_applicable",
                "payload_bytes": payload_val,
                "reporting_interval_s": None,
                "direction": direction,
                "confirmation_mode": None,
                "tx_power_dbm": None,
                "environment": _one_or_none(group["environment"], "environment") if "environment" in group else None,
                "phase_name": phase,
                "data_rate_mode": None,
                "frequency_hz": None,
                "bandwidth_hz": None,
                "spreading_factor": None,
                "coding_rate": None,
                "bit_rate_bps": None,
                "operator": None,
                "empirical_unit": "logical_phase_within_physical_source_run",
                "independence_unit": "canonical_physical_source_run",
                "n_source_observations": n_source,
                "n_independent_units": n_ind,
                "dependence_structure": dep_text,
                "source_grade": str(source_grade),
                "validation_status": "validated_with_limitations" if limitations or role != CANONICAL_ROLE else "validated",
                "derivation_class": "validated_derived",
                "parent_evidence_ids": [],
                "shared_parameter_ids": [],
                "uncertainty_basis": "replicated_independent_units" if n_ind > 1 else "single_independent_unit",
                "uncertainty_notes": (
                    "Run-level empirical values are retained in the analysis-ready Parquet; "
                    "Stage 2 does not impose a parametric distribution or artificial confidence interval."
                ),
                "applicability_domain": (
                    f"Vomhoff laboratory measurement; technology={key_map['technology']}; "
                    f"protocol={protocol_raw}; data={key_map['source_data_object']}; phase={phase}."
                ),
                "intended_use": intended,
                "bridge_requirements": (
                    "Whole reporting-cycle/device energy requires an explicit phase-composition "
                    "and session-policy model."
                ),
                "limitations": " ".join(limitations) if limitations else None,
                "notes": f"Source Figure contexts: {source_figures}; analysis_role={role}.",
            }
            evidence_records.append(record)

    excluded = logical.loc[~logical["evidence_eligible"].astype(bool)]
    alt = logical.loc[logical["analysis_role"].eq(FIGURE5_HTTP_IDLE_ALTERNATE)]
    summary: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "stage": "Stage-2 Vomhoff materialisation",
        "input_source_segment_rows": int(len(frame)),
        "within_figure_logical_phase_rows": int(len(source_views)),
        "candidate_logical_phase_groups_checkpoint": int(ind_summary["candidate_logical_phase_groups"]),
        "within_run_additive_groups": int(ind_summary["multi_segment_target_groups"]),
        "cross_figure_reuse_run_pairs": int(ind_summary["strong_source_reuse_run_pairs"]),
        "cross_figure_phase_views_collapsed": int(deduped_views),
        "logical_phase_rows_after_cross_figure_policy": int(len(logical)),
        "physical_run_units": int(logical["physical_run_id"].nunique()),
        "evidence_eligible_logical_phase_rows": int(logical["evidence_eligible"].sum()),
        "excluded_logical_phase_rows": int((~logical["evidence_eligible"]).sum()),
        "excluded_figure5_mqtt_idle_rows": int(
            excluded["analysis_role"].eq(FIGURE5_MQTT_IDLE_EXCLUSION).sum()
        ),
        "alternate_figure5_http_idle_rows": int(
            alt["analysis_role"].eq(FIGURE5_HTTP_IDLE_ALTERNATE).sum()
        ),
        "evidence_records": int(len(evidence_records)),
        "evidence_record_metrics": sorted({r["metric_id"] for r in evidence_records}),
        "cross_figure_policy": (
            "Strong Figure-4/Figure-5 NB-IoT/HTTP source reuse defines one physical/source run. "
            "Exact non-Idle phase views are collapsed; Figure-specific Idle derivations are retained "
            "as dependent views."
        ),
        "figure5_mqtt_idle_policy": (
            "Retained in source reproduction and logical-phase audit lineage but excluded from decision "
            "evidence because the source README explicitly says MQTT Idle is discarded when the device disconnects."
        ),
        "figure5_mqtt_standby_policy": (
            "No 10 s transformation is invented. The README/script discrepancy is retained as a limitation."
        ),
        "uncertainty_policy": (
            "Independent units are physical/source runs. No within-trace/source-segment pseudo-replication "
            "and no artificial confidence intervals are introduced."
        ),
    }
    return logical, evidence_records, comparison, summary
