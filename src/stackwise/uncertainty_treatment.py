from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class UncertaintyTreatmentSummary:
    vomhoff_contexts: int
    vomhoff_pairwise_comparisons: int
    vomhoff_marginal_interval_separated_pairs: int
    loed_campaign_metric_rows: int
    loed_rows_with_sd_ratio_gt_1_25: int
    loed_rows_with_sd_ratio_gt_1_50: int
    cost_candidates: int
    cost_aligned_states_per_rat: int
    cost_strict_coap_cheaper_rows_total: int
    cost_tie_rows_total: int
    cost_mqtt_cheaper_rows_total: int


def vomhoff_point_vs_bootstrap(source_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "source_reference_id", "technology", "source_application_protocol", "point_estimate_j",
        "q025_j", "median_j", "q975_j", "bootstrap_replicates",
    }
    missing = required - set(source_summary.columns)
    if missing:
        raise ValueError(f"Vomhoff source summary missing columns: {sorted(missing)}")
    if source_summary["source_reference_id"].duplicated().any():
        raise ValueError("Vomhoff source-reference IDs must be unique")
    rows = source_summary.copy()
    for c in ("point_estimate_j", "q025_j", "median_j", "q975_j"):
        rows[c] = pd.to_numeric(rows[c], errors="raise").astype(float)
    rows["bootstrap_interval_width_j"] = rows["q975_j"] - rows["q025_j"]
    rows["relative_interval_width_pct"] = 100.0 * rows["bootstrap_interval_width_j"] / rows["point_estimate_j"].abs()
    rows["deterministic_point_treatment"] = True
    rows["uncertainty_semantics"] = "nonparametric_epistemic_interval_for_conditional_mean"
    rows["population_prediction_interval"] = False
    rows["candidate_report_energy_transfer_authorised"] = False

    pairs: list[dict[str, Any]] = []
    ordered = rows.sort_values("point_estimate_j", kind="stable").reset_index(drop=True)
    for a_idx, b_idx in combinations(range(len(ordered)), 2):
        a = ordered.iloc[a_idx]
        b = ordered.iloc[b_idx]
        point_order = "a_lower" if a.point_estimate_j < b.point_estimate_j else ("tie" if a.point_estimate_j == b.point_estimate_j else "b_lower")
        separated = bool(float(a.q975_j) < float(b.q025_j) or float(b.q975_j) < float(a.q025_j))
        interval_order = "a_lower" if float(a.q975_j) < float(b.q025_j) else ("b_lower" if float(b.q975_j) < float(a.q025_j) else "overlap")
        pairs.append({
            "reference_a": str(a.source_reference_id),
            "reference_b": str(b.source_reference_id),
            "point_order": point_order,
            "marginal_95_interval_order": interval_order,
            "marginal_95_intervals_separated": separated,
            "cross_block_joint_probability_interpretation": False,
            "candidate_stack_ranking_authorised": False,
        })
    return rows.sort_values("point_estimate_j", kind="stable").reset_index(drop=True), pd.DataFrame(pairs)


def loed_point_vs_model_robustness(robustness_summary: pd.DataFrame) -> pd.DataFrame:
    required = {
        "campaign_id", "metric", "sd_max_to_min_ratio_median", "sd_max_to_min_ratio_q75",
        "robustness_width_median", "max_abs_raw_mbb_bias",
    }
    missing = required - set(robustness_summary.columns)
    if missing:
        raise ValueError(f"LoED robustness summary missing columns: {sorted(missing)}")
    out = robustness_summary.copy()
    for c in ("sd_max_to_min_ratio_median", "sd_max_to_min_ratio_q75", "robustness_width_median", "max_abs_raw_mbb_bias"):
        out[c] = pd.to_numeric(out[c], errors="raise").astype(float)
    out["sd_scale_increase_pct_median"] = 100.0 * (out["sd_max_to_min_ratio_median"] - 1.0)
    out["point_estimate_changes_across_block_models"] = False
    out["uncertainty_scale_changes_across_block_models"] = out["sd_max_to_min_ratio_median"] > 1.0 + 1e-12
    out["block_model_probability_weights_assigned"] = False
    out["robustness_envelope_is_probability_interval"] = False
    return out.sort_values(["campaign_id", "metric"], kind="stable").reset_index(drop=True)


def cost_point_vs_robustness_family(
    cost_family: pd.DataFrame,
    *,
    reference_state: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {
        "stack_id", "access_technology", "binding_family", "lifecycle_cost_eur",
        "anchor_id", "shape_id", "session_control_envelope_id", "billing_anchor_id", "procurement_anchor_id",
    }
    missing = required - set(cost_family.columns)
    if missing:
        raise ValueError(f"Cost family missing columns: {sorted(missing)}")
    state_cols = ["anchor_id", "shape_id", "session_control_envelope_id", "billing_anchor_id", "procurement_anchor_id"]
    family = cost_family.copy()
    family["lifecycle_cost_eur"] = pd.to_numeric(family["lifecycle_cost_eur"], errors="raise").astype(float)
    if family.duplicated(["stack_id", *state_cols]).any():
        raise ValueError("Cost family must have one row per stack and aligned robustness state")

    mask = pd.Series(True, index=family.index)
    for col, value in reference_state.items():
        if col not in state_cols:
            raise ValueError(f"Unsupported reference-state field {col!r}")
        mask &= family[col].astype(str).eq(str(value))
    ref = family.loc[mask].copy()
    if ref["stack_id"].nunique() != family["stack_id"].nunique():
        raise ValueError("Reference state does not select exactly one row for every stack")
    if ref.duplicated("stack_id").any():
        raise ValueError("Reference state selects multiple rows for at least one stack")

    summaries = family.groupby(["stack_id", "access_technology", "binding_family"], sort=True)["lifecycle_cost_eur"].agg(
        family_rows="size", family_min_eur="min", family_max_eur="max", family_median_eur="median"
    ).reset_index()
    ref = ref[["stack_id", "lifecycle_cost_eur"]].rename(columns={"lifecycle_cost_eur": "reference_point_cost_eur"})
    summaries = summaries.merge(ref, on="stack_id", how="left", validate="one_to_one")
    summaries["deterministic_reference_is_probability_weighted"] = False
    summaries["family_is_probability_distribution"] = False

    pair_rows: list[dict[str, Any]] = []
    detail_frames: list[pd.DataFrame] = []
    for rat, group in family.groupby("access_technology", sort=True):
        bindings = set(group["binding_family"].astype(str))
        if bindings != {"coap_dtls_udp", "mqtt_tls_tcp"}:
            raise ValueError(f"Expected CoAP and MQTT cost families for {rat}, got {sorted(bindings)}")
        pivot = group.pivot(index=state_cols, columns="binding_family", values="lifecycle_cost_eur")
        if pivot.isna().any().any():
            raise ValueError(f"Cost robustness states are not aligned for {rat}")
        diff = pivot["mqtt_tls_tcp"] - pivot["coap_dtls_udp"]
        detail = pivot.reset_index()
        detail.insert(0, "access_technology", rat)
        detail["mqtt_minus_coap_eur"] = diff.to_numpy(float)
        detail["statewise_order"] = np.where(detail["mqtt_minus_coap_eur"] > 1e-12, "coap_cheaper", np.where(detail["mqtt_minus_coap_eur"] < -1e-12, "mqtt_cheaper", "tie"))
        detail["probability_interpretation"] = False
        detail_frames.append(detail)

        s_coap = summaries[(summaries.access_technology == rat) & (summaries.binding_family == "coap_dtls_udp")].iloc[0]
        s_mqtt = summaries[(summaries.access_technology == rat) & (summaries.binding_family == "mqtt_tls_tcp")].iloc[0]
        pair_rows.append({
            "access_technology": rat,
            "aligned_robustness_states": int(len(diff)),
            "deterministic_reference_coap_eur": float(s_coap.reference_point_cost_eur),
            "deterministic_reference_mqtt_eur": float(s_mqtt.reference_point_cost_eur),
            "deterministic_reference_mqtt_minus_coap_eur": float(s_mqtt.reference_point_cost_eur - s_coap.reference_point_cost_eur),
            "coap_family_min_eur": float(s_coap.family_min_eur),
            "coap_family_max_eur": float(s_coap.family_max_eur),
            "mqtt_family_min_eur": float(s_mqtt.family_min_eur),
            "mqtt_family_max_eur": float(s_mqtt.family_max_eur),
            "naive_marginal_ranges_overlap": bool(max(s_coap.family_min_eur, s_mqtt.family_min_eur) <= min(s_coap.family_max_eur, s_mqtt.family_max_eur)),
            "aligned_states_coap_cheaper": int((diff > 1e-12).sum()),
            "aligned_states_tied": int((diff.abs() <= 1e-12).sum()),
            "aligned_states_mqtt_cheaper": int((diff < -1e-12).sum()),
            "aligned_difference_min_eur": float(diff.min()),
            "aligned_difference_median_eur": float(diff.median()),
            "aligned_difference_max_eur": float(diff.max()),
            "paired_state_dependence_preserved": True,
            "probability_interpretation": False,
        })
    return summaries, pd.DataFrame(pair_rows), pd.concat(detail_frames, ignore_index=True)


def summarise_experiment3(
    vomhoff_rows: pd.DataFrame,
    vomhoff_pairs: pd.DataFrame,
    loed_rows: pd.DataFrame,
    cost_summary: pd.DataFrame,
    cost_pairs: pd.DataFrame,
) -> UncertaintyTreatmentSummary:
    return UncertaintyTreatmentSummary(
        vomhoff_contexts=int(len(vomhoff_rows)),
        vomhoff_pairwise_comparisons=int(len(vomhoff_pairs)),
        vomhoff_marginal_interval_separated_pairs=int(vomhoff_pairs["marginal_95_intervals_separated"].sum()),
        loed_campaign_metric_rows=int(len(loed_rows)),
        loed_rows_with_sd_ratio_gt_1_25=int((loed_rows["sd_max_to_min_ratio_median"] > 1.25).sum()),
        loed_rows_with_sd_ratio_gt_1_50=int((loed_rows["sd_max_to_min_ratio_median"] > 1.50).sum()),
        cost_candidates=int(cost_summary["stack_id"].nunique()),
        cost_aligned_states_per_rat=int(cost_pairs["aligned_robustness_states"].min()),
        cost_strict_coap_cheaper_rows_total=int(cost_pairs["aligned_states_coap_cheaper"].sum()),
        cost_tie_rows_total=int(cost_pairs["aligned_states_tied"].sum()),
        cost_mqtt_cheaper_rows_total=int(cost_pairs["aligned_states_mqtt_cheaper"].sum()),
    )
