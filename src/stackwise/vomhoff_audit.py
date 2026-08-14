from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd


DATASET_ID = "vomhoff_nbiot_ltem_energy_2023"

# These are the phases that the source Figure 3--5 scripts explicitly place on
# the plotted phase axis. Auxiliary instrumentation/log events remain in the
# harmonised source-reproduction table but are not automatically promoted to
# Stage-2 evidence.
TARGET_PHASES_BY_FIGURE: dict[int, tuple[str, ...]] = {
    3: (
        "Changing RAT Type",
        "Connecting",
        "Idle Connected",
        "Idle Not Connected",
    ),
    4: (
        "Connection Establishment",
        "Data Request",
        "Data Download",
        "Postprocessing",
        "Standby",
        "Idle",
    ),
    5: (
        "Connection Establishment",
        "Data Request",
        "Data Download",
        "Postprocessing",
        "Standby",
        "Idle",
    ),
}

CANDIDATE_GROUP_FIELDS: tuple[str, ...] = (
    "source_file",
    "source_figure",
    "source_run",
    "technology",
    "source_application_protocol",
    "source_data_object",
    "source_event",
)

# Fields that must be constant within a candidate logical run/phase group before
# any later aggregation can even be considered. Constancy is necessary, not
# sufficient: this audit deliberately does not authorise summing/averaging.
CONDITION_FIELDS: tuple[str, ...] = (
    "access_network",
    "application_protocol",
    "payload_bytes",
    "direction",
    "measurement_boundary",
    "evidence_grade",
    "source_license",
    "source_doi",
)


class VomhoffAuditError(ValueError):
    pass


def _normalise_event(value: Any) -> str:
    return str(value).strip().casefold()


def _target_phase_lookup() -> dict[tuple[int, str], bool]:
    return {
        (figure, _normalise_event(phase)): True
        for figure, phases in TARGET_PHASES_BY_FIGURE.items()
        for phase in phases
    }


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...] | list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise VomhoffAuditError(f"Vomhoff audit input is missing required columns: {missing}")


def _stable_group_id(values: tuple[Any, ...]) -> str:
    serialised = "|".join("<NA>" if pd.isna(value) else str(value) for value in values)
    digest = hashlib.sha1(serialised.encode("utf-8")).hexdigest()[:14]
    return f"vomhoff-logical-phase-{digest}"


def _jsonable_number(value: Any) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return float(value)


def _safe_numeric_summary(series: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"min": None, "median": None, "max": None}
    return {
        "min": float(values.min()),
        "median": float(values.median()),
        "max": float(values.max()),
    }


def _unique_non_null(series: pd.Series) -> list[Any]:
    values: list[Any] = []
    seen: set[str] = set()
    for value in series:
        if pd.isna(value):
            continue
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            values.append(value)
    return values


def _joined_unique(series: pd.Series) -> str:
    values = _unique_non_null(series)
    return " | ".join(str(value) for value in values)


def _group_condition_consistency(group: pd.DataFrame) -> tuple[bool, str]:
    inconsistent: list[str] = []
    for field in CONDITION_FIELDS:
        if field not in group.columns:
            continue
        values = _unique_non_null(group[field])
        if len(values) > 1:
            inconsistent.append(field)
    return (not inconsistent, " | ".join(inconsistent))


def audit_vomhoff_logical_units(
    frame: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Audit candidate logical run/phase units without aggregating them.

    Returns ``summary``, ``candidate_groups``, ``multi_segment_segments``,
    ``non_target_event_counts`` and ``figure5_standby``.

    The key methodological rule is intentionally conservative: repeated source
    ``diff_time`` segments are *identified* but are neither summed nor averaged.
    The output exists to decide that rule from the real 1,671-row harmonised
    table before Stage-2 evidence materialisation.
    """

    required = [
        "dataset_id",
        "observation_id",
        "source_file",
        "source_figure",
        "source_run",
        "source_event",
        "source_application_protocol",
        "source_data_object",
        "source_diff_time_s",
        "technology",
        "energy_j",
        "duration_s",
        "raw_energy_j",
        "raw_duration_s",
        "normalisation_rule",
        "timestamp_utc",
    ]
    _require_columns(frame, required)

    dataset_ids = set(frame["dataset_id"].dropna().astype(str).unique())
    if dataset_ids != {DATASET_ID}:
        raise VomhoffAuditError(
            f"Expected only dataset_id={DATASET_ID!r}; found {sorted(dataset_ids)!r}"
        )

    work = frame.copy()
    work["source_figure"] = pd.to_numeric(work["source_figure"], errors="coerce").astype("Int64")
    work["_event_normal"] = work["source_event"].map(_normalise_event)
    target_lookup = _target_phase_lookup()
    work["is_source_target_phase"] = [
        bool(target_lookup.get((int(figure), event), False)) if not pd.isna(figure) else False
        for figure, event in zip(work["source_figure"], work["_event_normal"])
    ]

    target = work.loc[work["is_source_target_phase"]].copy()
    non_target = work.loc[~work["is_source_target_phase"]].copy()

    group_rows: list[dict[str, Any]] = []
    segment_rows: list[pd.DataFrame] = []

    if not target.empty:
        grouped = target.groupby(list(CANDIDATE_GROUP_FIELDS), dropna=False, sort=True)
        for key, group in grouped:
            key_tuple = key if isinstance(key, tuple) else (key,)
            group_id = _stable_group_id(key_tuple)
            metadata_consistent, inconsistent_fields = _group_condition_consistency(group)
            timestamp_values = pd.to_datetime(group["timestamp_utc"], errors="coerce", utc=True)
            segment_count = int(len(group))
            source_diff_values = _unique_non_null(group["source_diff_time_s"])
            normalisation_rules = _unique_non_null(group["normalisation_rule"])

            row = {field: value for field, value in zip(CANDIDATE_GROUP_FIELDS, key_tuple)}
            row.update(
                {
                    "candidate_group_id": group_id,
                    "segment_count": segment_count,
                    "distinct_source_diff_time_count": len(source_diff_values),
                    "source_diff_time_values_s": " | ".join(str(v) for v in source_diff_values),
                    "normalisation_rules": " | ".join(str(v) for v in normalisation_rules),
                    "metadata_conditions_consistent": bool(metadata_consistent),
                    "inconsistent_condition_fields": inconsistent_fields,
                    "timestamp_min_utc": (
                        timestamp_values.min().isoformat() if timestamp_values.notna().any() else None
                    ),
                    "timestamp_max_utc": (
                        timestamp_values.max().isoformat() if timestamp_values.notna().any() else None
                    ),
                    # Candidate summaries only. They are diagnostic and do not
                    # authorise a scientific aggregation rule.
                    "candidate_energy_sum_j": float(pd.to_numeric(group["energy_j"], errors="coerce").sum(min_count=1)),
                    "candidate_energy_mean_j": float(pd.to_numeric(group["energy_j"], errors="coerce").mean()),
                    "candidate_duration_sum_s": float(pd.to_numeric(group["duration_s"], errors="coerce").sum(min_count=1)),
                    "candidate_duration_mean_s": float(pd.to_numeric(group["duration_s"], errors="coerce").mean()),
                    "candidate_raw_energy_sum_j": float(pd.to_numeric(group["raw_energy_j"], errors="coerce").sum(min_count=1)),
                    "candidate_raw_duration_sum_s": float(pd.to_numeric(group["raw_duration_s"], errors="coerce").sum(min_count=1)),
                }
            )
            group_rows.append(row)

            if segment_count > 1:
                selected = group.copy()
                selected.insert(0, "candidate_group_id", group_id)
                keep = [
                    "candidate_group_id",
                    *CANDIDATE_GROUP_FIELDS,
                    "observation_id",
                    "timestamp_utc",
                    "source_diff_time_s",
                    "raw_duration_s",
                    "duration_s",
                    "raw_energy_j",
                    "energy_j",
                    "normalisation_rule",
                    "measurement_boundary",
                    "payload_bytes",
                    "direction",
                    "application_protocol",
                ]
                keep = [column for column in keep if column in selected.columns]
                selected = selected[keep].sort_values(
                    ["candidate_group_id", "timestamp_utc", "source_diff_time_s"],
                    kind="stable",
                    na_position="last",
                )
                segment_rows.append(selected)

    candidate_groups = pd.DataFrame(group_rows)
    if not candidate_groups.empty:
        candidate_groups = candidate_groups.sort_values(
            ["source_figure", "technology", "source_application_protocol", "source_run", "source_event"],
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)

    if segment_rows:
        multi_segment_segments = pd.concat(segment_rows, ignore_index=True, sort=False)
    else:
        multi_segment_segments = pd.DataFrame(
            columns=["candidate_group_id", *CANDIDATE_GROUP_FIELDS, "observation_id"]
        )

    if non_target.empty:
        non_target_event_counts = pd.DataFrame(
            columns=["source_figure", "source_event", "rows", "distinct_runs"]
        )
    else:
        non_target_event_counts = (
            non_target.groupby(["source_figure", "source_event"], dropna=False)
            .agg(rows=("observation_id", "size"), distinct_runs=("source_run", "nunique"))
            .reset_index()
            .sort_values(["source_figure", "rows", "source_event"], ascending=[True, False, True])
            .reset_index(drop=True)
        )

    fig5_standby = target.loc[
        target["source_figure"].eq(5) & target["_event_normal"].eq("standby")
    ].copy()
    fig5_keep = [
        "source_run",
        "technology",
        "source_application_protocol",
        "source_data_object",
        "observation_id",
        "source_diff_time_s",
        "raw_duration_s",
        "duration_s",
        "raw_energy_j",
        "energy_j",
        "normalisation_rule",
    ]
    fig5_keep = [column for column in fig5_keep if column in fig5_standby.columns]
    fig5_standby = fig5_standby[fig5_keep].sort_values(
        [column for column in ["source_application_protocol", "source_run", "source_diff_time_s"] if column in fig5_keep],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    segment_distribution: dict[str, int] = {}
    multi_by_phase: list[dict[str, Any]] = []
    metadata_inconsistent_groups = 0
    if not candidate_groups.empty:
        counts = Counter(int(value) for value in candidate_groups["segment_count"])
        segment_distribution = {str(key): int(counts[key]) for key in sorted(counts)}
        metadata_inconsistent_groups = int((~candidate_groups["metadata_conditions_consistent"]).sum())
        multi = candidate_groups.loc[candidate_groups["segment_count"].gt(1)]
        if not multi.empty:
            multi_by_phase = (
                multi.groupby(["source_figure", "source_event"], dropna=False)
                .agg(
                    groups=("candidate_group_id", "size"),
                    max_segments=("segment_count", "max"),
                )
                .reset_index()
                .sort_values(["source_figure", "groups", "source_event"], ascending=[True, False, True])
                .to_dict(orient="records")
            )

    fig5_standby_duration = _safe_numeric_summary(fig5_standby.get("duration_s", pd.Series(dtype=float)))
    fig5_standby_raw_duration = _safe_numeric_summary(
        fig5_standby.get("raw_duration_s", pd.Series(dtype=float))
    )
    fig5_rules = (
        sorted(str(v) for v in _unique_non_null(fig5_standby["normalisation_rule"]))
        if "normalisation_rule" in fig5_standby
        else []
    )

    summary: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "audit_scope": "Stage-2 logical-unit audit of validated harmonised source segments",
        "aggregation_authorised": False,
        "aggregation_decision_required": (
            "Inspect multi-segment target groups to determine whether repeated source diff_time "
            "segments are additive parts of one logical phase or repeated occurrences of a phase estimand."
        ),
        "input_rows": int(len(work)),
        "duplicate_observation_ids": int(work["observation_id"].duplicated().sum()),
        "source_figures": sorted(int(v) for v in work["source_figure"].dropna().unique()),
        "target_phase_rows": int(len(target)),
        "non_target_event_rows": int(len(non_target)),
        "target_phase_row_fraction": float(len(target) / len(work)) if len(work) else None,
        "candidate_logical_phase_groups": int(len(candidate_groups)),
        "multi_segment_target_groups": (
            int(candidate_groups["segment_count"].gt(1).sum()) if not candidate_groups.empty else 0
        ),
        "max_segments_per_candidate_group": (
            int(candidate_groups["segment_count"].max()) if not candidate_groups.empty else 0
        ),
        "segment_count_distribution": segment_distribution,
        "metadata_inconsistent_candidate_groups": metadata_inconsistent_groups,
        "multi_segment_groups_by_phase": multi_by_phase,
        "target_phases_by_figure": {
            str(figure): list(phases) for figure, phases in TARGET_PHASES_BY_FIGURE.items()
        },
        "candidate_group_fields": list(CANDIDATE_GROUP_FIELDS),
        "condition_fields_checked_for_constancy": list(CONDITION_FIELDS),
        "source_reproduction_semantics": (
            "The harmonised 1,671-row layer preserves run x event x source diff_time segments "
            "and source-defined normalisation. This audit does not alter that layer."
        ),
        "figure5_standby_source_discrepancy_audit": {
            "readme_target_duration_s": 10.0,
            "source_r_script_explicit_standby_normalisation": False,
            "rows": int(len(fig5_standby)),
            "duration_s": fig5_standby_duration,
            "raw_duration_s": fig5_standby_raw_duration,
            "normalisation_rules": fig5_rules,
            "interpretation": (
                "The source README states that Figure 5 Standby is calculated for 10 s, while "
                "fig5.R contains an explicit 20 s normalisation only for Idle. The validated "
                "source-reproduction adapter follows fig5.R. This audit reports the realised "
                "Standby durations; it does not silently impose a 10 s transformation."
            ),
        },
    }

    return summary, candidate_groups, multi_segment_segments, non_target_event_counts, fig5_standby
