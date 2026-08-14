from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from stackwise.vomhoff_audit import (
    DATASET_ID,
    audit_vomhoff_logical_units,
)

SOURCE_SAMPLE_PERIOD_S = 0.005
TIMESTAMP_QUANTISATION_ALLOWANCE_S = 0.001
ADJACENCY_TOLERANCE_S = SOURCE_SAMPLE_PERIOD_S + TIMESTAMP_QUANTISATION_ALLOWANCE_S

RUN_KEY_FIELDS: tuple[str, ...] = (
    "technology",
    "source_application_protocol",
    "source_data_object",
    "source_run",
)

RAW_SIGNATURE_FIELDS: tuple[str, ...] = (
    "technology",
    "source_application_protocol",
    "source_data_object",
    "source_run",
    "source_event",
    "timestamp_utc",
    "source_diff_time_s",
    "raw_duration_s",
    "raw_energy_j",
)


class VomhoffIndependenceAuditError(ValueError):
    pass


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...] | list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise VomhoffIndependenceAuditError(
            f"Vomhoff independence audit input is missing required columns: {missing}"
        )


def _normalise_scalar(value: Any) -> str:
    if value is None or pd.isna(value):
        return "<NA>"
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (float, np.floating)):
        return format(float(value), ".15g")
    return str(value)


def _signature(values: tuple[Any, ...]) -> str:
    serialised = "|".join(_normalise_scalar(v) for v in values)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _numeric_summary(series: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"min": None, "median": None, "p95": None, "max": None}
    return {
        "min": float(values.min()),
        "median": float(values.median()),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }



def audit_vomhoff_independence(
    frame: pd.DataFrame,
    *,
    adjacency_tolerance_s: float = ADJACENCY_TOLERANCE_S,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Audit within-run segment adjacency and cross-figure source reuse.

    The function does not deduplicate observations and does not write Stage-2
    evidence. It establishes two prerequisites for later materialisation:

    1. whether repeated ``Data Request`` source segments can be treated as
       additive contiguous pieces of one run-level phase estimand; and
    2. whether source Figures reuse the same underlying run/segment evidence,
       which would make figure-level rows statistically dependent.

    Returns ``summary``, ``adjacency_details``, ``exact_cross_figure_matches``
    and ``cross_figure_run_pairs``.
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
        "technology",
        "timestamp_utc",
        "source_diff_time_s",
        "raw_duration_s",
        "raw_energy_j",
        "duration_s",
        "energy_j",
    ]
    _require_columns(frame, required)

    dataset_ids = set(frame["dataset_id"].dropna().astype(str).unique())
    if dataset_ids != {DATASET_ID}:
        raise VomhoffIndependenceAuditError(
            f"Expected only dataset_id={DATASET_ID!r}; found {sorted(dataset_ids)!r}"
        )

    base_summary, candidate_groups, multi_segments, _, _ = audit_vomhoff_logical_units(frame)

    adjacency_rows: list[dict[str, Any]] = []
    if not multi_segments.empty:
        for group_id, group in multi_segments.groupby("candidate_group_id", sort=True):
            ordered = group.copy()
            ordered["_timestamp"] = pd.to_datetime(
                ordered["timestamp_utc"], errors="coerce", utc=True
            )
            ordered = ordered.sort_values(
                ["_timestamp", "source_diff_time_s"], kind="stable", na_position="last"
            ).reset_index(drop=True)

            for index in range(len(ordered) - 1):
                current = ordered.iloc[index]
                following = ordered.iloc[index + 1]
                start_gap_s = (
                    (following["_timestamp"] - current["_timestamp"]).total_seconds()
                    if pd.notna(current["_timestamp"]) and pd.notna(following["_timestamp"])
                    else np.nan
                )
                current_duration_s = pd.to_numeric(
                    pd.Series([current["duration_s"]]), errors="coerce"
                ).iloc[0]
                residual_s = (
                    float(start_gap_s - current_duration_s)
                    if pd.notna(start_gap_s) and pd.notna(current_duration_s)
                    else np.nan
                )
                adjacency_rows.append(
                    {
                        "candidate_group_id": group_id,
                        "source_figure": int(current["source_figure"]),
                        "source_run": int(current["source_run"]),
                        "technology": current["technology"],
                        "source_application_protocol": current[
                            "source_application_protocol"
                        ],
                        "source_data_object": current["source_data_object"],
                        "source_event": current["source_event"],
                        "segment_index": index,
                        "current_observation_id": current["observation_id"],
                        "next_observation_id": following["observation_id"],
                        "current_start_utc": (
                            current["_timestamp"].isoformat()
                            if pd.notna(current["_timestamp"])
                            else None
                        ),
                        "next_start_utc": (
                            following["_timestamp"].isoformat()
                            if pd.notna(following["_timestamp"])
                            else None
                        ),
                        "current_duration_s": (
                            float(current_duration_s) if pd.notna(current_duration_s) else np.nan
                        ),
                        "next_start_minus_current_start_s": (
                            float(start_gap_s) if pd.notna(start_gap_s) else np.nan
                        ),
                        "continuity_residual_s": residual_s,
                        "abs_continuity_residual_s": (
                            abs(residual_s) if pd.notna(residual_s) else np.nan
                        ),
                        "within_adjacency_tolerance": (
                            bool(abs(residual_s) <= adjacency_tolerance_s)
                            if pd.notna(residual_s)
                            else False
                        ),
                    }
                )

    adjacency = pd.DataFrame(adjacency_rows)
    multi_group_phase_values = (
        sorted(set(multi_segments["source_event"].dropna().astype(str)))
        if not multi_segments.empty
        else []
    )
    all_adjacent = bool(
        not adjacency.empty and adjacency["within_adjacency_tolerance"].all()
    )
    metadata_consistent = bool(base_summary["metadata_inconsistent_candidate_groups"] == 0)
    only_data_request = multi_group_phase_values == ["Data Request"]
    max_segments = int(base_summary["max_segments_per_candidate_group"])
    additive_authorised = bool(
        all_adjacent and metadata_consistent and only_data_request and max_segments == 2
    )

    work = frame.copy()
    work["source_figure"] = pd.to_numeric(
        work["source_figure"], errors="coerce"
    ).astype("Int64")
    work["_timestamp"] = pd.to_datetime(work["timestamp_utc"], errors="coerce", utc=True)

    signature_columns: list[pd.Series] = []
    for field in RAW_SIGNATURE_FIELDS:
        if field == "timestamp_utc":
            signature_columns.append(work["_timestamp"])
        else:
            signature_columns.append(work[field])
    work["raw_segment_signature"] = [
        _signature(tuple(values)) for values in zip(*signature_columns)
    ]

    signature_stats = (
        work.groupby("raw_segment_signature", dropna=False)
        .agg(
            rows=("observation_id", "size"),
            distinct_figures=("source_figure", "nunique"),
            figure_values=("source_figure", lambda s: "|".join(str(int(v)) for v in sorted(s.dropna().unique()))),
        )
        .reset_index()
    )
    repeated_signatures = set(
        signature_stats.loc[
            signature_stats["distinct_figures"].gt(1), "raw_segment_signature"
        ]
    )
    exact_matches = work.loc[
        work["raw_segment_signature"].isin(repeated_signatures)
    ].copy()
    if not exact_matches.empty:
        exact_matches = exact_matches.sort_values(
            ["raw_segment_signature", "source_figure", "source_run", "source_event"],
            kind="stable",
        )
        exact_matches = exact_matches[
            [
                "raw_segment_signature",
                "source_figure",
                "source_file",
                "source_run",
                "technology",
                "source_application_protocol",
                "source_data_object",
                "source_event",
                "timestamp_utc",
                "source_diff_time_s",
                "raw_duration_s",
                "raw_energy_j",
                "duration_s",
                "energy_j",
                "observation_id",
            ]
        ].reset_index(drop=True)

    pair_rows: list[dict[str, Any]] = []
    grouped_runs = work.groupby(list(RUN_KEY_FIELDS), dropna=False, sort=True)
    for run_key, group in grouped_runs:
        figures = sorted(int(v) for v in group["source_figure"].dropna().unique())
        if len(figures) < 2:
            continue
        key_tuple = run_key if isinstance(run_key, tuple) else (run_key,)
        key_map = dict(zip(RUN_KEY_FIELDS, key_tuple))
        for figure_a, figure_b in combinations(figures, 2):
            a = group.loc[group["source_figure"].eq(figure_a)]
            b = group.loc[group["source_figure"].eq(figure_b)]
            sig_a = set(a["raw_segment_signature"])
            sig_b = set(b["raw_segment_signature"])
            shared = sig_a & sig_b
            if not shared:
                continue
            shared_rows = group.loc[group["raw_segment_signature"].isin(shared)]
            shared_events = sorted(set(shared_rows["source_event"].dropna().astype(str)))
            pair_rows.append(
                {
                    **key_map,
                    "figure_a": figure_a,
                    "figure_b": figure_b,
                    "segments_a": int(len(a)),
                    "segments_b": int(len(b)),
                    "exact_shared_segment_signatures": int(len(shared)),
                    "shared_event_count": int(len(shared_events)),
                    "shared_events": " | ".join(shared_events),
                    # Audit flag only, not a final physical-run identity rule.
                    "strong_source_reuse_flag": bool(
                        len(shared_events) >= 3 and len(shared) >= 3
                    ),
                }
            )

    run_pairs = pd.DataFrame(pair_rows)
    if not run_pairs.empty:
        run_pairs = run_pairs.sort_values(
            ["figure_a", "figure_b", "technology", "source_application_protocol", "source_run"],
            kind="stable",
        ).reset_index(drop=True)

    overlap_by_pair: list[dict[str, Any]] = []
    if not run_pairs.empty:
        overlap_by_pair = (
            run_pairs.groupby(
                ["figure_a", "figure_b", "technology", "source_application_protocol"],
                dropna=False,
            )
            .agg(
                overlapping_run_keys=("source_run", "size"),
                strong_source_reuse_runs=("strong_source_reuse_flag", "sum"),
                exact_shared_segment_signatures=("exact_shared_segment_signatures", "sum"),
                min_shared_events=("shared_event_count", "min"),
                median_shared_events=("shared_event_count", "median"),
                max_shared_events=("shared_event_count", "max"),
            )
            .reset_index()
            .to_dict(orient="records")
        )
        for row in overlap_by_pair:
            for key, value in list(row.items()):
                if isinstance(value, (np.integer, int)):
                    row[key] = int(value)
                elif isinstance(value, (np.floating, float)):
                    row[key] = float(value)

    summary: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "audit_scope": (
            "Stage-2 independence audit: within-run segment continuity and cross-figure source reuse"
        ),
        "input_rows": int(len(work)),
        "candidate_logical_phase_groups": int(len(candidate_groups)),
        "multi_segment_target_groups": int(
            base_summary["multi_segment_target_groups"]
        ),
        "multi_segment_phase_values": multi_group_phase_values,
        "adjacency_tolerance_s": float(adjacency_tolerance_s),
        "adjacency_basis": (
            "5 ms source sampling interval plus 1 ms timestamp-quantisation allowance"
        ),
        "adjacency_pairs": int(len(adjacency)),
        "adjacent_within_tolerance": (
            int(adjacency["within_adjacency_tolerance"].sum())
            if not adjacency.empty
            else 0
        ),
        "all_multi_segment_pairs_adjacent": all_adjacent,
        "continuity_residual_s": _numeric_summary(
            adjacency.get("continuity_residual_s", pd.Series(dtype=float))
        ),
        "abs_continuity_residual_s": _numeric_summary(
            adjacency.get("abs_continuity_residual_s", pd.Series(dtype=float))
        ),
        "metadata_inconsistent_candidate_groups": int(
            base_summary["metadata_inconsistent_candidate_groups"]
        ),
        "within_source_figure_additive_aggregation_authorised": additive_authorised,
        "within_source_figure_aggregation_rule": (
            "For the Stage-2 estimand 'total source phase within one experimental run', "
            "contiguous repeated Data Request segments are additive: sum energy, duration "
            "and charge-like extensive quantities; retain segment_count and parent observation IDs. "
            "Do not treat the source segments as independent replicates."
            if additive_authorised
            else "NOT AUTHORISED: continuity/metadata/event guards did not all pass."
        ),
        "exact_cross_figure_segment_signatures": int(len(repeated_signatures)),
        "exact_cross_figure_rows": int(len(exact_matches)),
        "cross_figure_run_pairs": int(len(run_pairs)),
        "strong_source_reuse_run_pairs": (
            int(run_pairs["strong_source_reuse_flag"].sum())
            if not run_pairs.empty
            else 0
        ),
        "cross_figure_overlap_by_pair": overlap_by_pair,
        "cross_figure_independence_interpretation": (
            "Exact raw segment reuse or strong run-level overlap means source-Figure records "
            "must not be counted as independent evidence merely because they occur in different "
            "CSV/source Figure contexts. Figure-specific transformations may still be retained "
            "as distinct derived records linked to the same parent run."
        ),
        "deduplication_authorised": False,
        "next_decision_required": (
            "Review cross-figure overlap and choose the canonical parent-run identity / "
            "figure-specific derivation policy before materialising final Vomhoff Stage-2 evidence."
        ),
    }

    return summary, adjacency, exact_matches, run_pairs
