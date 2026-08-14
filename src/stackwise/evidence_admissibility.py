from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd


CORE_SOURCE_IDS = (
    "vomhoff_nbiot_ltem_energy_2023",
    "insectt_wsn_power_2023",
    "lorawan_lrfhss_energy_2024",
    "loed_lorawan_edge_2020",
)

TARGET_RELATION_ORDER = ("C0_DIRECT", "C1_BRIDGEABLE", "C2_CONDITIONAL", "E0_MISSING")
FIRST_SLICE_TARGETS = (
    "expected_device_energy_per_application_report_j",
    "lifecycle_cost_eur",
)


@dataclass(frozen=True)
class EvidenceAdmissibilitySummary:
    core_sources: int
    canonical_evidence_records: int
    source_grade_a_sources: int
    source_target_relation_rows: int
    direct_relation_rows: int
    bridgeable_relation_rows: int
    conditional_relation_rows: int
    missing_relation_rows: int
    first_slice_candidate_criterion_rows: int
    canonical_ready_rows: int
    context_only_rows: int
    structural_transfer_rows: int
    blocked_other_rows: int
    canonical_complete_candidates: int
    context_complete_candidates: int
    counterfactual_bridge_complete_candidates: int
    assumption_complete_candidates: int


def source_grade_ablation(
    *,
    registry: dict[str, Any],
    evidence_summary: dict[str, Any],
    core_source_ids: Iterable[str] = CORE_SOURCE_IDS,
) -> pd.DataFrame:
    datasets = {item["id"]: item for item in registry.get("datasets", [])}
    record_counts = evidence_summary.get("records_by_dataset", {})
    missing = [dataset_id for dataset_id in core_source_ids if dataset_id not in datasets]
    if missing:
        raise ValueError(f"Core datasets missing from registry: {missing}")

    grades = {dataset_id: str(datasets[dataset_id].get("evidence_grade", "")) for dataset_id in core_source_ids}
    if any(grade not in {"A", "B", "C", "D"} for grade in grades.values()):
        raise ValueError(f"Unexpected source grades: {grades}")

    regimes = [
        ("G0_A_ONLY", {"A"}),
        ("G1_A_B", {"A", "B"}),
        ("G2_A_B_C", {"A", "B", "C"}),
        ("G3_A_B_C_D", {"A", "B", "C", "D"}),
    ]
    rows: list[dict[str, Any]] = []
    for regime_id, allowed in regimes:
        retained = [dataset_id for dataset_id, grade in grades.items() if grade in allowed]
        rows.append(
            {
                "regime_id": regime_id,
                "allowed_source_grades": "+".join(sorted(allowed)),
                "core_sources_retained": len(retained),
                "canonical_evidence_records_retained": int(sum(int(record_counts.get(dataset_id, 0)) for dataset_id in retained)),
                "all_core_sources_retained": len(retained) == len(tuple(core_source_ids)),
                "decision_admissibility_inferred_from_grade": False,
            }
        )
    return pd.DataFrame(rows)


def target_relation_ablation(target_relations: pd.DataFrame) -> pd.DataFrame:
    required = {"target_metric_id", "dataset_id", "relation_class"}
    missing = required - set(target_relations.columns)
    if missing:
        raise ValueError(f"Target relation table missing columns: {sorted(missing)}")
    expected_sources = set(CORE_SOURCE_IDS)
    if set(target_relations["dataset_id"].astype(str)) != expected_sources:
        raise ValueError("Target relation table does not cover exactly the frozen core-four sources")
    if target_relations[["target_metric_id", "dataset_id"]].duplicated().any():
        raise ValueError("Target×dataset relations must be unique")

    relation_counts = target_relations["relation_class"].value_counts().to_dict()
    unexpected = set(relation_counts) - set(TARGET_RELATION_ORDER)
    if unexpected:
        raise ValueError(f"Unexpected relation classes: {sorted(unexpected)}")

    regimes = [
        ("A0_DIRECT_ONLY", {"C0_DIRECT"}, True, False),
        ("A1_DIRECT_PLUS_BRIDGEABLE", {"C0_DIRECT", "C1_BRIDGEABLE"}, False, False),
        ("A2_PLUS_CONDITIONAL_CONTEXT", {"C0_DIRECT", "C1_BRIDGEABLE", "C2_CONDITIONAL"}, False, False),
        ("A3_SOURCE_GRADE_ONLY_NAIVE", set(TARGET_RELATION_ORDER), False, True),
    ]
    rows: list[dict[str, Any]] = []
    for regime_id, allowed, decision_authorised, naive in regimes:
        selected = target_relations[target_relations["relation_class"].isin(allowed)]
        rows.append(
            {
                "regime_id": regime_id,
                "allowed_relation_classes": "+".join(cls for cls in TARGET_RELATION_ORDER if cls in allowed),
                "source_target_relation_rows_counted_as_available": len(selected),
                "distinct_decision_targets_with_any_counted_support": int(selected["target_metric_id"].nunique()),
                "direct_rows_within_regime": int((selected["relation_class"] == "C0_DIRECT").sum()),
                "bridgeable_rows_within_regime": int((selected["relation_class"] == "C1_BRIDGEABLE").sum()),
                "conditional_rows_within_regime": int((selected["relation_class"] == "C2_CONDITIONAL").sum()),
                "missing_rows_misclassified_as_available": int((selected["relation_class"] == "E0_MISSING").sum()) if naive else 0,
                "canonical_decision_use_authorised": bool(decision_authorised and len(selected) > 0),
                "counterfactual_or_contextual_regime": not decision_authorised,
                "source_grade_only_naive": naive,
            }
        )
    return pd.DataFrame(rows)


def overlay_stage6c_cost_readiness(
    candidate_readiness: pd.DataFrame,
    stage6c_cost_summary: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "scenario_id",
        "stack_id",
        "target_metric_id",
        "first_slice_required",
        "stage6a_decision_use_status",
        "evidence_maturity",
    }
    missing = required - set(candidate_readiness.columns)
    if missing:
        raise ValueError(f"Candidate readiness table missing columns: {sorted(missing)}")
    cost_required = {"scenario_id", "stack_id", "cost_decision_use_status"}
    missing_cost = cost_required - set(stage6c_cost_summary.columns)
    if missing_cost:
        raise ValueError(f"Stage-6C cost summary missing columns: {sorted(missing_cost)}")

    out = candidate_readiness[candidate_readiness["first_slice_required"].astype(bool)].copy()
    if set(out["target_metric_id"].unique()) != set(FIRST_SLICE_TARGETS):
        raise ValueError("First-slice target set drifted from frozen energy+cost contract")

    cost_ready_keys = {
        (str(row.scenario_id), str(row.stack_id))
        for row in stage6c_cost_summary.itertuples(index=False)
        if str(row.cost_decision_use_status) == "READY_ROBUSTNESS_FAMILY"
    }

    support_states: list[str] = []
    for row in out.itertuples(index=False):
        key = (str(row.scenario_id), str(row.stack_id))
        target = str(row.target_metric_id)
        maturity = str(row.evidence_maturity)
        stage6a = str(row.stage6a_decision_use_status)
        if target == "lifecycle_cost_eur" and key in cost_ready_keys:
            state = "READY_ROBUSTNESS_FAMILY"
        elif stage6a == "CONTEXT_ONLY":
            state = "CONTEXT_ONLY"
        elif maturity == "STRUCTURAL_TRANSFER_SUPPORT_ONLY":
            state = "STRUCTURAL_TRANSFER_ONLY"
        elif maturity == "PROFILE_UNRESOLVED":
            state = "PROFILE_UNRESOLVED"
        elif maturity == "INCOMPATIBLE":
            state = "INCOMPATIBLE"
        elif maturity in {"MISSING", "COST_TARGET_NOT_IDENTIFIED"}:
            state = "MISSING_OR_UNIDENTIFIED"
        else:
            state = "BLOCKED_OTHER"
        support_states.append(state)
    out["experiment2_support_state"] = support_states
    return out


def candidate_admissibility_ablation(first_slice_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"scenario_id", "stack_id", "target_metric_id", "experiment2_support_state"}
    missing = required - set(first_slice_rows.columns)
    if missing:
        raise ValueError(f"First-slice rows missing columns: {sorted(missing)}")
    if first_slice_rows[["scenario_id", "stack_id", "target_metric_id"]].duplicated().any():
        raise ValueError("Candidate criterion rows must be unique")

    regimes = [
        {
            "regime_id": "D0_CANONICAL_READY_ONLY",
            "allowed_states": {"READY_ROBUSTNESS_FAMILY"},
            "decision_use_authorised": True,
            "counterfactual": False,
        },
        {
            "regime_id": "D1_READY_PLUS_CONTEXT",
            "allowed_states": {"READY_ROBUSTNESS_FAMILY", "CONTEXT_ONLY"},
            "decision_use_authorised": False,
            "counterfactual": False,
        },
        {
            "regime_id": "D2_CONTEXT_PLUS_STRUCTURAL_TRANSFER_COUNTERFACTUAL",
            "allowed_states": {"READY_ROBUSTNESS_FAMILY", "CONTEXT_ONLY", "STRUCTURAL_TRANSFER_ONLY"},
            "decision_use_authorised": False,
            "counterfactual": True,
        },
        {
            "regime_id": "D3_EXPLICIT_ASSUMPTION_PRIOR_COUNTERFACTUAL",
            "allowed_states": set(first_slice_rows["experiment2_support_state"].astype(str).unique()),
            "decision_use_authorised": False,
            "counterfactual": True,
        },
    ]

    candidate_keys = first_slice_rows[["scenario_id", "stack_id"]].drop_duplicates()
    expected_targets = set(FIRST_SLICE_TARGETS)
    regime_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for regime in regimes:
        allowed = regime["allowed_states"]
        row_mask = first_slice_rows["experiment2_support_state"].isin(allowed)
        counted_rows = first_slice_rows[row_mask]
        complete_count = 0
        complete_scenarios: set[str] = set()
        for candidate in candidate_keys.itertuples(index=False):
            subset = first_slice_rows[
                (first_slice_rows["scenario_id"] == candidate.scenario_id)
                & (first_slice_rows["stack_id"] == candidate.stack_id)
            ]
            counted_targets = set(
                subset.loc[subset["experiment2_support_state"].isin(allowed), "target_metric_id"].astype(str)
            )
            complete = counted_targets == expected_targets
            if complete:
                complete_count += 1
                complete_scenarios.add(str(candidate.scenario_id))
            candidate_rows.append(
                {
                    "regime_id": regime["regime_id"],
                    "scenario_id": str(candidate.scenario_id),
                    "stack_id": str(candidate.stack_id),
                    "counted_target_count": len(counted_targets),
                    "complete_two_criterion_candidate": complete,
                    "decision_use_authorised": regime["decision_use_authorised"],
                    "counterfactual": regime["counterfactual"],
                    "probability_interpretation": False,
                }
            )
        candidate_frame = pd.DataFrame(candidate_rows)
        current_complete = candidate_frame[
            (candidate_frame["regime_id"] == regime["regime_id"])
            & candidate_frame["complete_two_criterion_candidate"]
        ]
        scenario_complete_counts = current_complete.groupby("scenario_id")["stack_id"].nunique()
        scenarios_with_two = int((scenario_complete_counts >= 2).sum()) if not scenario_complete_counts.empty else 0
        regime_rows.append(
            {
                "regime_id": regime["regime_id"],
                "allowed_support_states": "+".join(sorted(allowed)),
                "first_slice_criterion_rows_counted_as_available": len(counted_rows),
                "first_slice_criterion_row_fraction": len(counted_rows) / len(first_slice_rows),
                "complete_two_criterion_candidates": complete_count,
                "scenarios_with_at_least_one_complete_candidate": len(complete_scenarios),
                "scenarios_with_at_least_two_complete_candidates": scenarios_with_two,
                "decision_use_authorised": regime["decision_use_authorised"],
                "counterfactual": regime["counterfactual"],
                "probability_interpretation": False,
            }
        )
    return pd.DataFrame(regime_rows), pd.DataFrame(candidate_rows)


def summarise_experiment2(
    *,
    source_grade: pd.DataFrame,
    target_relations: pd.DataFrame,
    first_slice_rows: pd.DataFrame,
    candidate_regimes: pd.DataFrame,
) -> EvidenceAdmissibilitySummary:
    relation_counts = target_relations["relation_class"].value_counts()
    support_counts = first_slice_rows["experiment2_support_state"].value_counts()
    regime_lookup = candidate_regimes.set_index("regime_id")
    return EvidenceAdmissibilitySummary(
        core_sources=int(source_grade.iloc[-1]["core_sources_retained"]),
        canonical_evidence_records=int(source_grade.iloc[-1]["canonical_evidence_records_retained"]),
        source_grade_a_sources=int(source_grade.iloc[0]["core_sources_retained"]),
        source_target_relation_rows=len(target_relations),
        direct_relation_rows=int(relation_counts.get("C0_DIRECT", 0)),
        bridgeable_relation_rows=int(relation_counts.get("C1_BRIDGEABLE", 0)),
        conditional_relation_rows=int(relation_counts.get("C2_CONDITIONAL", 0)),
        missing_relation_rows=int(relation_counts.get("E0_MISSING", 0)),
        first_slice_candidate_criterion_rows=len(first_slice_rows),
        canonical_ready_rows=int(support_counts.get("READY_ROBUSTNESS_FAMILY", 0)),
        context_only_rows=int(support_counts.get("CONTEXT_ONLY", 0)),
        structural_transfer_rows=int(support_counts.get("STRUCTURAL_TRANSFER_ONLY", 0)),
        blocked_other_rows=int(len(first_slice_rows) - support_counts.get("READY_ROBUSTNESS_FAMILY", 0) - support_counts.get("CONTEXT_ONLY", 0) - support_counts.get("STRUCTURAL_TRANSFER_ONLY", 0)),
        canonical_complete_candidates=int(regime_lookup.loc["D0_CANONICAL_READY_ONLY", "complete_two_criterion_candidates"]),
        context_complete_candidates=int(regime_lookup.loc["D1_READY_PLUS_CONTEXT", "complete_two_criterion_candidates"]),
        counterfactual_bridge_complete_candidates=int(regime_lookup.loc["D2_CONTEXT_PLUS_STRUCTURAL_TRANSFER_COUNTERFACTUAL", "complete_two_criterion_candidates"]),
        assumption_complete_candidates=int(regime_lookup.loc["D3_EXPLICIT_ASSUMPTION_PRIOR_COUNTERFACTUAL", "complete_two_criterion_candidates"]),
    )
