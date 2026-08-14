from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


LEVELS = (
    "L0_APPLICATION_PAYLOAD_ONLY",
    "L1_TRANSPORT_AWARE_1TO1_PAYLOAD",
    "L2_SERIALIZATION_AWARE",
    "L3_SESSION_CONTROL_AWARE",
    "L4_BILLING_AWARE",
)


@dataclass(frozen=True)
class AccountingSimplificationSummary:
    aligned_traffic_states: int
    procurement_expanded_cost_rows: int
    level0_exceed_rows: int
    level1_exceed_rows: int
    level2_exceed_rows: int
    level3_exceed_rows: int
    level4_exceed_rows: int
    level0_false_within_vs_final: int
    level1_false_within_vs_final: int
    level2_false_within_vs_final: int
    level3_false_within_vs_final: int
    level0_to_level1_new_exceed_rows: int
    level1_to_level2_new_exceed_rows: int
    level2_to_level3_new_exceed_rows: int
    level3_to_level4_new_exceed_rows: int


def _require(df: pd.DataFrame, cols: set[str], label: str) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")


def _topups(bytes_5y: pd.Series, allowance: int, increment: int) -> pd.Series:
    values = pd.to_numeric(bytes_5y, errors="raise").astype(float).to_numpy()
    return pd.Series(
        np.maximum(0, np.ceil((values - float(allowance)) / float(increment))).astype(int),
        index=bytes_5y.index,
    )


def build_accounting_ablation(
    stage5l: pd.DataFrame,
    stage5m: pd.DataFrame,
    stage5n: pd.DataFrame,
    stage6c: pd.DataFrame,
    *,
    scenario_id: str,
    nominal_allowance_bytes: int = 500_000_000,
    topup_increment_bytes: int = 500_000_000,
    topup_price_eur: float = 10.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, AccountingSimplificationSummary]:
    _require(stage5l, {
        "scenario_id", "stack_id", "anchor_id", "strict_transport_known_component_floor_bytes_per_report",
        "pre_lwm2m_application_payload_bytes", "five_year_report_count",
    }, "Stage-5L")
    _require(stage5m, {
        "scenario_id", "stack_id", "anchor_id", "shape_id", "five_year_strict_transport_bytes",
    }, "Stage-5M")
    _require(stage5n, {
        "scenario_id", "stack_id", "anchor_id", "shape_id", "envelope_id",
        "five_year_session_control_augmented_transport_bytes",
    }, "Stage-5N")
    _require(stage6c, {
        "scenario_id", "stack_id", "access_technology", "binding_family", "anchor_id", "shape_id",
        "session_control_envelope_id", "billing_anchor_id", "procurement_anchor_id",
        "billed_transport_bytes_5y", "topup_count", "module_price_eur", "standard_sim_eur",
        "base_connectivity_prepaid_eur", "lifecycle_cost_eur",
    }, "Stage-6C")

    s5l = stage5l.loc[stage5l["scenario_id"].astype(str).eq(scenario_id)].copy()
    s5m = stage5m.loc[stage5m["scenario_id"].astype(str).eq(scenario_id)].copy()
    s5n = stage5n.loc[stage5n["scenario_id"].astype(str).eq(scenario_id)].copy()
    cost = stage6c.loc[stage6c["scenario_id"].astype(str).eq(scenario_id)].copy()
    if cost.empty:
        raise ValueError(f"No Stage-6C rows for scenario {scenario_id!r}")

    traffic_state_cols = [
        "stack_id", "access_technology", "binding_family", "anchor_id", "shape_id",
        "session_control_envelope_id", "billing_anchor_id",
    ]
    traffic = cost.drop_duplicates(traffic_state_cols).copy()
    if len(traffic) * cost["procurement_anchor_id"].nunique() != len(cost):
        raise ValueError("Stage-6C procurement expansion is not a complete aligned product")

    l1 = s5l[[
        "stack_id", "anchor_id", "strict_transport_known_component_floor_bytes_per_report",
        "pre_lwm2m_application_payload_bytes", "five_year_report_count",
    ]].copy()
    if l1.duplicated(["stack_id", "anchor_id"]).any():
        raise ValueError("Stage-5L has duplicate stack/anchor rows")
    l1["L0_bytes_per_report"] = pd.to_numeric(l1["pre_lwm2m_application_payload_bytes"], errors="raise").astype(float)
    l1["L0_bytes_5y"] = l1["L0_bytes_per_report"] * pd.to_numeric(l1["five_year_report_count"], errors="raise").astype(float)
    # L1 preserves the observed pre-LwM2M application byte count but assumes 1:1 serialization,
    # then adds only the Stage-5L known transport/control floor (which was calculated with encoded payload set to zero).
    l1["L1_bytes_per_report"] = (
        pd.to_numeric(l1["strict_transport_known_component_floor_bytes_per_report"], errors="raise").astype(float)
        + l1["L0_bytes_per_report"]
    )
    l1["L1_bytes_5y"] = l1["L1_bytes_per_report"] * pd.to_numeric(l1["five_year_report_count"], errors="raise").astype(float)
    l1 = l1[["stack_id", "anchor_id", "L0_bytes_per_report", "L0_bytes_5y", "L1_bytes_per_report", "L1_bytes_5y"]]

    l2 = s5m[["stack_id", "anchor_id", "shape_id", "five_year_strict_transport_bytes"]].copy()
    if l2.duplicated(["stack_id", "anchor_id", "shape_id"]).any():
        raise ValueError("Stage-5M has duplicate stack/anchor/shape rows")
    l2 = l2.rename(columns={"five_year_strict_transport_bytes": "L2_bytes_5y"})

    l3 = s5n[[
        "stack_id", "anchor_id", "shape_id", "envelope_id",
        "five_year_session_control_augmented_transport_bytes",
    ]].copy()
    if l3.duplicated(["stack_id", "anchor_id", "shape_id", "envelope_id"]).any():
        raise ValueError("Stage-5N has duplicate stack/anchor/shape/envelope rows")
    l3 = l3.rename(columns={
        "envelope_id": "session_control_envelope_id",
        "five_year_session_control_augmented_transport_bytes": "L3_bytes_5y",
    })

    traffic = traffic.merge(l1, on=["stack_id", "anchor_id"], validate="many_to_one")
    traffic = traffic.merge(l2, on=["stack_id", "anchor_id", "shape_id"], validate="many_to_one")
    traffic = traffic.merge(l3, on=["stack_id", "anchor_id", "shape_id", "session_control_envelope_id"], validate="many_to_one")
    traffic["L4_bytes_5y"] = pd.to_numeric(traffic["billed_transport_bytes_5y"], errors="raise").astype(float)

    for idx in range(5):
        bcol = f"L{idx}_bytes_5y"
        traffic[f"L{idx}_exceeds_nominal_allowance"] = pd.to_numeric(traffic[bcol], errors="raise").astype(float) > float(nominal_allowance_bytes)
    final = traffic["L4_exceeds_nominal_allowance"]
    for idx in range(4):
        cur = traffic[f"L{idx}_exceeds_nominal_allowance"]
        traffic[f"L{idx}_false_within_vs_L4"] = (~cur) & final
        traffic[f"L{idx}_false_exceed_vs_L4"] = cur & (~final)
    for idx in range(1, 5):
        prev = traffic[f"L{idx-1}_exceeds_nominal_allowance"]
        cur = traffic[f"L{idx}_exceeds_nominal_allowance"]
        traffic[f"L{idx-1}_to_L{idx}_new_exceed"] = (~prev) & cur
        traffic[f"L{idx-1}_to_L{idx}_reverse_to_within"] = prev & (~cur)

    level_rows: list[dict[str, object]] = []
    total = len(traffic)
    for idx, level in enumerate(LEVELS):
        cur = traffic[f"L{idx}_exceeds_nominal_allowance"]
        row = {
            "level_index": idx,
            "level_id": level,
            "aligned_traffic_states": total,
            "exceeds_nominal_allowance_rows": int(cur.sum()),
            "within_nominal_allowance_rows": int((~cur).sum()),
            "exceed_state_space_fraction": float(cur.mean()),
            "probability_interpretation": False,
        }
        if idx < 4:
            false_within = traffic[f"L{idx}_false_within_vs_L4"]
            false_exceed = traffic[f"L{idx}_false_exceed_vs_L4"]
            row.update({
                "false_within_vs_billing_aware_rows": int(false_within.sum()),
                "false_exceed_vs_billing_aware_rows": int(false_exceed.sum()),
                "misclassification_fraction_vs_billing_aware": float((false_within | false_exceed).mean()),
            })
        else:
            row.update({
                "false_within_vs_billing_aware_rows": 0,
                "false_exceed_vs_billing_aware_rows": 0,
                "misclassification_fraction_vs_billing_aware": 0.0,
            })
        if idx == 0:
            row["new_exceed_rows_from_previous_level"] = 0
            row["reverse_to_within_rows_from_previous_level"] = 0
        else:
            row["new_exceed_rows_from_previous_level"] = int(traffic[f"L{idx-1}_to_L{idx}_new_exceed"].sum())
            row["reverse_to_within_rows_from_previous_level"] = int(traffic[f"L{idx-1}_to_L{idx}_reverse_to_within"].sum())
        level_rows.append(row)
    level_summary = pd.DataFrame(level_rows)

    # Expand the same accounting ladder to procurement-aware cost rows. L0-L3 deliberately
    # apply a naive aggregate-raw-volume tariff interpretation; L4 is the actual Stage-6C billing-aware result.
    cost_detail = cost.merge(
        traffic[[
            "stack_id", "access_technology", "binding_family", "anchor_id", "shape_id",
            "session_control_envelope_id", "billing_anchor_id",
            "L0_bytes_5y", "L1_bytes_5y", "L2_bytes_5y", "L3_bytes_5y", "L4_bytes_5y",
        ]],
        on=traffic_state_cols,
        validate="many_to_one",
    )
    base_cost = (
        pd.to_numeric(cost_detail["module_price_eur"], errors="raise").astype(float)
        + pd.to_numeric(cost_detail["standard_sim_eur"], errors="raise").astype(float)
        + pd.to_numeric(cost_detail["base_connectivity_prepaid_eur"], errors="raise").astype(float)
    )
    for idx in range(4):
        topups = _topups(cost_detail[f"L{idx}_bytes_5y"], nominal_allowance_bytes, topup_increment_bytes)
        cost_detail[f"L{idx}_naive_aggregate_topup_count"] = topups
        cost_detail[f"L{idx}_naive_lifecycle_cost_eur"] = base_cost + float(topup_price_eur) * topups
        cost_detail[f"L{idx}_cost_underestimation_vs_L4_eur"] = (
            pd.to_numeric(cost_detail["lifecycle_cost_eur"], errors="raise").astype(float)
            - cost_detail[f"L{idx}_naive_lifecycle_cost_eur"]
        )
    cost_detail["L4_billing_aware_topup_count"] = pd.to_numeric(cost_detail["topup_count"], errors="raise").astype(int)
    cost_detail["L4_billing_aware_lifecycle_cost_eur"] = pd.to_numeric(cost_detail["lifecycle_cost_eur"], errors="raise").astype(float)

    cost_rows: list[dict[str, object]] = []
    for idx, level in enumerate(LEVELS):
        if idx < 4:
            under = cost_detail[f"L{idx}_cost_underestimation_vs_L4_eur"]
            topups = cost_detail[f"L{idx}_naive_aggregate_topup_count"]
            cost_rows.append({
                "level_index": idx,
                "level_id": level,
                "procurement_expanded_rows": len(cost_detail),
                "median_estimated_topups": float(topups.median()),
                "max_estimated_topups": int(topups.max()),
                "rows_underestimating_final_cost": int((under > 1e-12).sum()),
                "mean_cost_underestimation_eur": float(under.mean()),
                "median_cost_underestimation_eur": float(under.median()),
                "max_cost_underestimation_eur": float(under.max()),
                "probability_interpretation": False,
            })
        else:
            topups = cost_detail["L4_billing_aware_topup_count"]
            cost_rows.append({
                "level_index": idx,
                "level_id": level,
                "procurement_expanded_rows": len(cost_detail),
                "median_estimated_topups": float(topups.median()),
                "max_estimated_topups": int(topups.max()),
                "rows_underestimating_final_cost": 0,
                "mean_cost_underestimation_eur": 0.0,
                "median_cost_underestimation_eur": 0.0,
                "max_cost_underestimation_eur": 0.0,
                "probability_interpretation": False,
            })
    cost_summary = pd.DataFrame(cost_rows)

    summary = AccountingSimplificationSummary(
        aligned_traffic_states=int(len(traffic)),
        procurement_expanded_cost_rows=int(len(cost_detail)),
        level0_exceed_rows=int(traffic["L0_exceeds_nominal_allowance"].sum()),
        level1_exceed_rows=int(traffic["L1_exceeds_nominal_allowance"].sum()),
        level2_exceed_rows=int(traffic["L2_exceeds_nominal_allowance"].sum()),
        level3_exceed_rows=int(traffic["L3_exceeds_nominal_allowance"].sum()),
        level4_exceed_rows=int(traffic["L4_exceeds_nominal_allowance"].sum()),
        level0_false_within_vs_final=int(traffic["L0_false_within_vs_L4"].sum()),
        level1_false_within_vs_final=int(traffic["L1_false_within_vs_L4"].sum()),
        level2_false_within_vs_final=int(traffic["L2_false_within_vs_L4"].sum()),
        level3_false_within_vs_final=int(traffic["L3_false_within_vs_L4"].sum()),
        level0_to_level1_new_exceed_rows=int(traffic["L0_to_L1_new_exceed"].sum()),
        level1_to_level2_new_exceed_rows=int(traffic["L1_to_L2_new_exceed"].sum()),
        level2_to_level3_new_exceed_rows=int(traffic["L2_to_L3_new_exceed"].sum()),
        level3_to_level4_new_exceed_rows=int(traffic["L3_to_L4_new_exceed"].sum()),
    )
    return traffic, level_summary, cost_summary, summary
