from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


ACTIVE_TARGET = "expected_device_energy_per_application_report_j"
READY = "ready_bridged"
BLOCKED = "blocked_structural_transfer_gap"


@dataclass(frozen=True)
class CellularBridgeSummary:
    feasible_candidate_incidences: int
    source_reference_contexts: int
    canonical_target_ready_rows: int
    payload_mismatch_rows: int
    exact_application_context_rows: int


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def feasible_cellular_ip_pairs(feasibility_rows: Iterable[dict[str, Any]], candidate_ids: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in feasibility_rows:
        if str(row.get("status")) != "feasible":
            continue
        stack_id = str(row.get("stack_id"))
        if stack_id in candidate_ids:
            pairs.append((str(row.get("scenario_id")), stack_id))
    return sorted(set(pairs))


def build_candidate_bridge_audit(
    *,
    feasibility_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_contexts = policy["candidate_contexts"]
    scenarios = policy["scenario_contexts"]
    source_refs = {x["reference_id"]: x for x in policy["source_reference_contexts"]}
    source_payload = int(policy["scientific_policy"]["source_payload_bytes"])
    pairs = feasible_cellular_ip_pairs(feasibility_rows, set(candidate_contexts))
    rows: list[dict[str, Any]] = []
    for scenario_id, stack_id in pairs:
        if scenario_id not in scenarios:
            raise ValueError(f"Missing Stage-5F scenario context for {scenario_id}")
        c = candidate_contexts[stack_id]
        s = scenarios[scenario_id]
        ref = source_refs[c["preferred_source_reference_id"]]
        payload = int(s["application_payload_bytes"])
        payload_match = payload == source_payload
        app_alignment = str(c["source_application_alignment"])
        exact_app = app_alignment == "exact"
        blockers: list[str] = []
        if not payload_match:
            blockers.append("source_payload_1024B_does_not_match_scenario_payload")
        if app_alignment == "mismatched_http_to_coap":
            blockers.append("http_source_does_not_identify_coap_dtls_lwm2m_energy")
        elif app_alignment == "partial_mqtt_context_alignment":
            blockers.append("source_mqtt_version_security_and_lwm2m_binding_unresolved")
        elif app_alignment.startswith("missing_ltem_mqtt"):
            blockers.append("no_lte_m_mqtt_source_context")
        blockers.extend([
            "reporting_cycle_tail_state_policy_not_identified_from_vomhoff",
            "source_active_component_excludes_standby_idle_and_sleep_cycle_mapping",
        ])
        ready = not blockers and _bool(policy["scientific_policy"]["canonical_target_materialisation_authorised"])
        rows.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "target_metric_id": ACTIVE_TARGET,
            "technology": c["technology"],
            "candidate_application_family": c["candidate_application_family"],
            "scenario_payload_bytes": payload,
            "scenario_reporting_interval_s": int(s["reporting_interval_s"]),
            "source_reference_id": ref["reference_id"],
            "source_payload_bytes": int(ref["payload_bytes"]),
            "source_application_protocol": ref["source_application_protocol"],
            "source_application_alignment": app_alignment,
            "payload_match": payload_match,
            "exact_application_context": exact_app,
            "source_active_component_available": True,
            "canonical_target_status": READY if ready else BLOCKED,
            "numeric_target_materialised": ready,
            "blocking_reasons": "|".join(blockers),
        })
    return rows


def materialise_source_active_components(
    *,
    marginal: pd.DataFrame,
    bootstrap_draws: pd.DataFrame,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compose source-aligned active transaction energy from joint block bootstrap means.

    This is a diagnostic source-boundary quantity only. It deliberately excludes Idle and
    Standby and is not the canonical application-report energy target.
    """
    active_phases = set(map(str, policy["scientific_policy"]["source_active_phases"]))
    references = policy["source_reference_contexts"]
    required_marginal = {
        "evidence_id", "metric_id", "technology", "application_protocol", "phase_name",
        "experimental_block_id", "mean",
    }
    missing = required_marginal - set(marginal.columns)
    if missing:
        raise ValueError(f"Marginal calibration missing columns: {sorted(missing)}")
    required_draws = {"experimental_block_id", "bootstrap_rep", "evidence_id", "bootstrap_mean"}
    missing = required_draws - set(bootstrap_draws.columns)
    if missing:
        raise ValueError(f"Bootstrap draws missing columns: {sorted(missing)}")

    energy = marginal.loc[marginal["metric_id"].astype(str) == "device_phase_energy_j"].copy()
    energy["application_protocol_norm"] = energy["application_protocol"].astype(str).str.upper()
    summaries: list[dict[str, Any]] = []
    draw_frames: list[pd.DataFrame] = []
    for ref in references:
        sub = energy.loc[
            (energy["technology"].astype(str) == str(ref["technology"]))
            & (energy["application_protocol_norm"] == str(ref["source_application_protocol"]).upper())
            & (energy["phase_name"].astype(str).isin(active_phases))
        ].copy()
        observed_phases = set(sub["phase_name"].astype(str))
        if observed_phases != active_phases:
            raise ValueError(f"{ref['reference_id']}: active phase set mismatch: {sorted(observed_phases)}")
        block_ids = set(sub["experimental_block_id"].astype(str))
        if len(block_ids) != 1:
            raise ValueError(f"{ref['reference_id']}: active phases span {len(block_ids)} bootstrap blocks")
        block_id = next(iter(block_ids))
        evidence_ids = set(sub["evidence_id"].astype(str))
        d = bootstrap_draws.loc[
            (bootstrap_draws["experimental_block_id"].astype(str) == block_id)
            & (bootstrap_draws["evidence_id"].astype(str).isin(evidence_ids))
        ].copy()
        counts = d.groupby("bootstrap_rep")["evidence_id"].nunique()
        if counts.empty or (counts != len(evidence_ids)).any():
            raise ValueError(f"{ref['reference_id']}: incomplete phase coverage in bootstrap draws")
        comp = d.groupby("bootstrap_rep", sort=True)["bootstrap_mean"].sum().astype(float)
        point = float(pd.to_numeric(sub["mean"], errors="coerce").sum())
        summaries.append({
            "source_reference_id": ref["reference_id"],
            "technology": ref["technology"],
            "source_application_protocol": ref["source_application_protocol"],
            "source_payload_bytes": int(ref["payload_bytes"]),
            "component_metric_id": "vomhoff_source_active_transaction_component_energy_j",
            "component_boundary": "whole_device_source_active_phases_only",
            "included_phases": "|".join(sorted(active_phases)),
            "excluded_tail_phases": "|".join(map(str, policy["scientific_policy"]["source_tail_phases"])),
            "experimental_block_id": block_id,
            "phase_evidence_records": len(evidence_ids),
            "point_estimate_j": point,
            "bootstrap_mean_j": float(comp.mean()),
            "bootstrap_sd_of_mean_j": float(comp.std(ddof=1)),
            "q025_j": float(comp.quantile(0.025)),
            "median_j": float(comp.quantile(0.5)),
            "q975_j": float(comp.quantile(0.975)),
            "bootstrap_replicates": int(len(comp)),
            "canonical_application_report_target": False,
            "interpretation": "Source-aligned active-phase component; not transferable to scenario report energy without payload/application/report-cycle bridge evidence.",
        })
        dd = comp.rename("active_component_energy_j").reset_index()
        dd.insert(0, "source_reference_id", ref["reference_id"])
        draw_frames.append(dd)
    return pd.DataFrame(summaries), pd.concat(draw_frames, ignore_index=True)


def audit_summary(rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> CellularBridgeSummary:
    rows = list(rows)
    result = CellularBridgeSummary(
        feasible_candidate_incidences=len(rows),
        source_reference_contexts=len(policy["source_reference_contexts"]),
        canonical_target_ready_rows=sum(str(r["canonical_target_status"]) == READY for r in rows),
        payload_mismatch_rows=sum(not _bool(r["payload_match"]) for r in rows),
        exact_application_context_rows=sum(_bool(r["exact_application_context"]) for r in rows),
    )
    expected = policy["expected"]
    checks = {
        "feasible_cellular_ip_candidate_incidences": result.feasible_candidate_incidences,
        "source_reference_contexts": result.source_reference_contexts,
        "canonical_target_ready_rows": result.canonical_target_ready_rows,
        "payload_mismatch_rows": result.payload_mismatch_rows,
        "exact_application_context_rows": result.exact_application_context_rows,
    }
    for key, value in checks.items():
        if int(expected[key]) != int(value):
            raise ValueError(f"Stage-5F expected {key}={expected[key]}, observed {value}")
    return result
