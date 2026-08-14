from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


FEATURE_IDS = (
    "stack_parsimony",
    "explicit_transport_security",
    "operator_independence",
    "ip_interoperability",
)
VALID_STATUSES = {"feasible", "infeasible", "unresolved"}


@dataclass(frozen=True)
class FeasibilityFirstSummary:
    scenarios: int
    candidates: int
    preference_features: int
    preference_anchors: int
    scenario_anchor_evaluations: int
    scenarios_with_feasible_candidates: int
    scenarios_without_feasible_candidates: int
    evaluable_scenario_anchor_rows: int
    score_first_any_infeasible_top_rows: int
    score_first_only_infeasible_top_rows: int
    evaluable_rows_with_any_infeasible_top: int
    evaluable_rows_with_only_infeasible_top: int
    no_feasible_rows_where_score_first_still_returns_top: int
    feasibility_first_forced_decisions_without_feasible_candidate: int


def _tokens(value: Any) -> set[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return set()
    return {token for token in str(value).split("|") if token}


def build_preference_feature_matrix(
    candidate_stacks: pd.DataFrame,
    component_catalog: pd.DataFrame,
) -> pd.DataFrame:
    required_stack = {
        "stack_id",
        "primary_access_component_id",
        "component_count",
        "binding_count",
        "component_ids",
    }
    required_component = {"component_id", "roles", "provides"}
    missing_stack = required_stack - set(candidate_stacks.columns)
    missing_component = required_component - set(component_catalog.columns)
    if missing_stack:
        raise ValueError(f"candidate stack table missing columns: {sorted(missing_stack)}")
    if missing_component:
        raise ValueError(f"component catalog missing columns: {sorted(missing_component)}")
    if candidate_stacks["stack_id"].duplicated().any():
        raise ValueError("candidate stack IDs must be unique")
    if component_catalog["component_id"].duplicated().any():
        raise ValueError("component IDs must be unique")

    comp_lookup = component_catalog.set_index("component_id").to_dict("index")
    component_counts = candidate_stacks["component_count"].astype(float)
    binding_counts = candidate_stacks["binding_count"].astype(float)

    def inverse_minmax(values: pd.Series) -> pd.Series:
        lo = float(values.min())
        hi = float(values.max())
        if hi <= lo:
            return pd.Series(np.ones(len(values)), index=values.index, dtype=float)
        return 1.0 - (values - lo) / (hi - lo)

    component_parsimony = inverse_minmax(component_counts)
    binding_parsimony = inverse_minmax(binding_counts)

    rows: list[dict[str, Any]] = []
    for idx, stack in candidate_stacks.reset_index(drop=True).iterrows():
        component_ids = [token for token in str(stack["component_ids"]).split("|") if token]
        unknown = [component_id for component_id in component_ids if component_id not in comp_lookup]
        if unknown:
            raise ValueError(f"Unknown component IDs for {stack['stack_id']}: {unknown}")
        component_rows = [comp_lookup[component_id] for component_id in component_ids]
        roles = set().union(*(_tokens(row.get("roles")) for row in component_rows))
        provides = set().union(*(_tokens(row.get("provides")) for row in component_rows))
        primary_id = str(stack["primary_access_component_id"])
        if primary_id not in comp_lookup:
            raise ValueError(f"Unknown primary access component: {primary_id}")
        primary_provides = _tokens(comp_lookup[primary_id].get("provides"))
        rows.append(
            {
                "stack_id": str(stack["stack_id"]),
                "stack_parsimony": 0.5 * float(component_parsimony.iloc[idx])
                + 0.5 * float(binding_parsimony.iloc[idx]),
                "explicit_transport_security": float("end_to_end_security" in roles),
                "operator_independence": float("operator_managed_access" not in primary_provides),
                "ip_interoperability": float("ip_packet_service" in provides),
                "feature_source": "STACKWISE_BENCHMARK_V1.0.0_STRUCTURAL_DEFINITION",
                "probability_interpretation": False,
            }
        )
    out = pd.DataFrame(rows).sort_values("stack_id").reset_index(drop=True)
    if not np.isfinite(out[list(FEATURE_IDS)].to_numpy(dtype=float)).all():
        raise ValueError("Preference feature matrix contains non-finite values")
    if ((out[list(FEATURE_IDS)] < 0) | (out[list(FEATURE_IDS)] > 1)).any().any():
        raise ValueError("Preference features must lie in [0,1]")
    return out


def deterministic_simplex_weight_grid(
    feature_ids: Sequence[str] = FEATURE_IDS,
    *,
    step: float = 0.25,
) -> pd.DataFrame:
    if step <= 0 or step > 1:
        raise ValueError("simplex step must be in (0,1]")
    units_float = 1.0 / step
    units = int(round(units_float))
    if not np.isclose(units * step, 1.0):
        raise ValueError("simplex step must divide 1 exactly")
    n = len(feature_ids)
    rows: list[dict[str, Any]] = []
    anchor = 0
    for allocation in product(range(units + 1), repeat=n):
        if sum(allocation) != units:
            continue
        weights = [value / units for value in allocation]
        row: dict[str, Any] = {
            "weight_anchor_id": f"W{anchor:02d}",
            "probability_interpretation": False,
        }
        row.update({feature_id: weight for feature_id, weight in zip(feature_ids, weights)})
        rows.append(row)
        anchor += 1
    return pd.DataFrame(rows)


def _top_set(frame: pd.DataFrame, *, score_col: str, tolerance: float) -> pd.DataFrame:
    max_score = float(frame[score_col].max())
    return frame[np.isclose(frame[score_col].to_numpy(dtype=float), max_score, atol=tolerance, rtol=0.0)]


def _status_signature(statuses: Iterable[str]) -> str:
    status_set = set(statuses)
    ordered = [status for status in ("feasible", "unresolved", "infeasible") if status in status_set]
    return "+".join(ordered)


def run_feasibility_first_experiment(
    *,
    feature_matrix: pd.DataFrame,
    weight_grid: pd.DataFrame,
    hard_feasibility: pd.DataFrame,
    tie_tolerance: float = 1e-12,
) -> tuple[pd.DataFrame, pd.DataFrame, FeasibilityFirstSummary]:
    required_feas = {"scenario_id", "stack_id", "status"}
    if required_feas - set(hard_feasibility.columns):
        raise ValueError("hard feasibility table missing scenario_id/stack_id/status")
    statuses = set(hard_feasibility["status"].astype(str))
    if not statuses <= VALID_STATUSES:
        raise ValueError(f"Unexpected feasibility statuses: {sorted(statuses - VALID_STATUSES)}")
    if hard_feasibility[["scenario_id", "stack_id"]].duplicated().any():
        raise ValueError("hard feasibility scenario×stack pairs must be unique")

    stack_ids = set(feature_matrix["stack_id"])
    feas_stack_ids = set(hard_feasibility["stack_id"])
    if stack_ids != feas_stack_ids:
        raise ValueError(
            f"Feature/feasibility candidate mismatch: missing={sorted(feas_stack_ids-stack_ids)}, "
            f"extra={sorted(stack_ids-feas_stack_ids)}"
        )

    feature_lookup = feature_matrix.set_index("stack_id")
    weight_columns = list(FEATURE_IDS)
    outcome_rows: list[dict[str, Any]] = []

    for scenario_id, scenario in hard_feasibility.groupby("scenario_id", sort=True):
        scenario = scenario[["scenario_id", "stack_id", "status"]].copy()
        scenario = scenario.merge(feature_matrix[["stack_id", *FEATURE_IDS]], on="stack_id", how="left")
        feasible_count = int((scenario["status"] == "feasible").sum())
        unresolved_count = int((scenario["status"] == "unresolved").sum())
        infeasible_count = int((scenario["status"] == "infeasible").sum())
        for _, weight_row in weight_grid.iterrows():
            weights = weight_row[weight_columns].to_numpy(dtype=float)
            if not np.isclose(weights.sum(), 1.0):
                raise ValueError("Preference weights must sum to 1")
            scores = scenario[weight_columns].to_numpy(dtype=float) @ weights
            scored = scenario.assign(soft_score=scores)
            score_top = _top_set(scored, score_col="soft_score", tolerance=tie_tolerance)
            score_statuses = score_top["status"].astype(str).tolist()

            feasible_scored = scored[scored["status"] == "feasible"]
            if feasible_scored.empty:
                feasible_top_ids: list[str] = []
                feasible_top_score = np.nan
                decision_status = "NO_FEASIBLE_DECISION"
                concession = np.nan
            else:
                feasible_top = _top_set(feasible_scored, score_col="soft_score", tolerance=tie_tolerance)
                feasible_top_ids = sorted(feasible_top["stack_id"].astype(str))
                feasible_top_score = float(feasible_top["soft_score"].max())
                decision_status = "FEASIBLE_TOP_SET_AVAILABLE"
                concession = float(score_top["soft_score"].max()) - feasible_top_score

            outcome_rows.append(
                {
                    "scenario_id": str(scenario_id),
                    "weight_anchor_id": str(weight_row["weight_anchor_id"]),
                    "feasible_candidate_count": feasible_count,
                    "infeasible_candidate_count": infeasible_count,
                    "unresolved_candidate_count": unresolved_count,
                    "score_first_top_score": float(score_top["soft_score"].max()),
                    "score_first_top_set": "|".join(sorted(score_top["stack_id"].astype(str))),
                    "score_first_top_set_size": len(score_top),
                    "score_first_top_status_signature": _status_signature(score_statuses),
                    "score_first_top_contains_feasible": "feasible" in score_statuses,
                    "score_first_top_contains_infeasible": "infeasible" in score_statuses,
                    "score_first_top_contains_unresolved": "unresolved" in score_statuses,
                    "score_first_top_only_infeasible": set(score_statuses) == {"infeasible"},
                    "score_first_top_only_unresolved": set(score_statuses) == {"unresolved"},
                    "feasibility_first_decision_status": decision_status,
                    "feasibility_first_top_score": feasible_top_score,
                    "feasibility_first_top_set": "|".join(feasible_top_ids),
                    "soft_score_concession_for_feasibility": concession,
                    "preference_anchor_probability_interpretation": False,
                    "publication_interpretation": "PREFERENCE_ENVELOPE_STRESS_TEST_NOT_REAL_MCDA",
                }
            )

    outcomes = pd.DataFrame(outcome_rows)
    summary_rows: list[dict[str, Any]] = []
    for scenario_id, group in outcomes.groupby("scenario_id", sort=True):
        has_feasible = bool(int(group["feasible_candidate_count"].iloc[0]) > 0)
        concessions = group["soft_score_concession_for_feasibility"].dropna().astype(float)
        category_counts = group["score_first_top_status_signature"].value_counts().to_dict()
        summary_rows.append(
            {
                "scenario_id": scenario_id,
                "feasible_candidate_count": int(group["feasible_candidate_count"].iloc[0]),
                "infeasible_candidate_count": int(group["infeasible_candidate_count"].iloc[0]),
                "unresolved_candidate_count": int(group["unresolved_candidate_count"].iloc[0]),
                "preference_anchor_count": len(group),
                "score_first_top_contains_any_infeasible_anchors": int(group["score_first_top_contains_infeasible"].sum()),
                "score_first_top_only_infeasible_anchors": int(group["score_first_top_only_infeasible"].sum()),
                "score_first_top_contains_any_feasible_anchors": int(group["score_first_top_contains_feasible"].sum()),
                "score_first_top_contains_any_unresolved_anchors": int(group["score_first_top_contains_unresolved"].sum()),
                "score_first_top_feasible_only_anchors": int(category_counts.get("feasible", 0)),
                "score_first_top_feasible_infeasible_mixed_anchors": int(category_counts.get("feasible+infeasible", 0)),
                "score_first_top_infeasible_only_anchors": int(category_counts.get("infeasible", 0)),
                "score_first_top_unresolved_only_anchors": int(category_counts.get("unresolved", 0)),
                "score_first_top_unresolved_infeasible_mixed_anchors": int(category_counts.get("unresolved+infeasible", 0)),
                "feasibility_first_returns_no_decision": not has_feasible,
                "median_soft_score_concession_for_feasibility": float(concessions.median()) if len(concessions) else np.nan,
                "max_soft_score_concession_for_feasibility": float(concessions.max()) if len(concessions) else np.nan,
                "probability_interpretation": False,
            }
        )
    scenario_summary = pd.DataFrame(summary_rows)

    with_feasible = outcomes[outcomes["feasible_candidate_count"] > 0]
    without_feasible = outcomes[outcomes["feasible_candidate_count"] == 0]
    summary = FeasibilityFirstSummary(
        scenarios=int(outcomes["scenario_id"].nunique()),
        candidates=int(feature_matrix["stack_id"].nunique()),
        preference_features=len(FEATURE_IDS),
        preference_anchors=int(weight_grid["weight_anchor_id"].nunique()),
        scenario_anchor_evaluations=len(outcomes),
        scenarios_with_feasible_candidates=int(scenario_summary["feasible_candidate_count"].gt(0).sum()),
        scenarios_without_feasible_candidates=int(scenario_summary["feasible_candidate_count"].eq(0).sum()),
        evaluable_scenario_anchor_rows=len(with_feasible),
        score_first_any_infeasible_top_rows=int(outcomes["score_first_top_contains_infeasible"].sum()),
        score_first_only_infeasible_top_rows=int(outcomes["score_first_top_only_infeasible"].sum()),
        evaluable_rows_with_any_infeasible_top=int(with_feasible["score_first_top_contains_infeasible"].sum()),
        evaluable_rows_with_only_infeasible_top=int(with_feasible["score_first_top_only_infeasible"].sum()),
        no_feasible_rows_where_score_first_still_returns_top=len(without_feasible),
        feasibility_first_forced_decisions_without_feasible_candidate=int(
            (without_feasible["feasibility_first_decision_status"] != "NO_FEASIBLE_DECISION").sum()
        ),
    )
    return outcomes, scenario_summary, summary
