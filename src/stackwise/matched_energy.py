from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MatchedEnergyAuditSummary:
    external_sources_reviewed: int
    sources_covering_both_rats: int
    sources_with_exact_64b_payload: int
    sources_with_exact_60s_cycle: int
    sources_candidate_boundary_ready: int
    primary_experiment_cells: int
    robustness_experiment_cells: int


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def source_review_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in policy["external_source_review"]:
        row = dict(source)
        row["source_role"] = "EXTERNAL_EVIDENCE_REVIEW"
        row["canonical_energy_target_authorised"] = _bool(source["candidate_boundary_ready"])
        rows.append(row)
    return rows


def experiment_cell_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    contract = policy["minimum_experiment_contract"]
    out: list[dict[str, Any]] = []
    for stack in policy["preferred_subset_stacks"]:
        for session_id, session_policy, required in [
            ("S0_fresh_session_each_report", contract["primary_session_policy"], True),
            ("S1_resumption_or_context_reuse", contract["robustness_session_policy"], False),
        ]:
            out.append({
                "scenario_id": policy["scientific_policy"]["target_scenario_id"],
                "stack_id": stack["stack_id"],
                "rat": stack["rat"],
                "binding_family": stack["binding_family"],
                "pre_lwm2m_application_payload_bytes": policy["scientific_policy"]["target_pre_lwm2m_payload_bytes"],
                "reporting_interval_s": policy["scientific_policy"]["target_reporting_interval_s"],
                "payload_shape": contract["primary_payload_shape"],
                "session_profile_id": session_id,
                "session_policy": session_policy,
                "required_for_first_slice": required,
                "replication_unit": contract["replication_unit"],
                "blocking_unit": contract["blocking_unit"],
                "energy_boundary": contract["energy_boundary"],
                "measurement_status": "MEASUREMENT_REQUIRED",
                "canonical_target_ready": False,
                "score_authorised": False,
            })
    return out


def audit_summary(policy: dict[str, Any], source_rows: Iterable[dict[str, Any]], experiment_rows: Iterable[dict[str, Any]]) -> MatchedEnergyAuditSummary:
    sources = list(source_rows)
    experiments = list(experiment_rows)
    summary = MatchedEnergyAuditSummary(
        external_sources_reviewed=len(sources),
        sources_covering_both_rats=sum(_bool(r["both_rats"]) for r in sources),
        sources_with_exact_64b_payload=sum(_bool(r["exact_64b_payload"]) for r in sources),
        sources_with_exact_60s_cycle=sum(_bool(r["exact_60s_cycle"]) for r in sources),
        sources_candidate_boundary_ready=sum(_bool(r["candidate_boundary_ready"]) for r in sources),
        primary_experiment_cells=sum(_bool(r["required_for_first_slice"]) for r in experiments),
        robustness_experiment_cells=sum(not _bool(r["required_for_first_slice"]) for r in experiments),
    )
    expected = policy["expected"]
    for key, value in summary.__dict__.items():
        if int(expected[key]) != value:
            raise ValueError(f"Stage-6B expected {key}={expected[key]}, observed {value}")
    if summary.sources_candidate_boundary_ready != 0:
        raise ValueError("Stage-6B must not claim a matched public candidate-boundary energy source")
    if any(_bool(r["canonical_target_ready"]) or _bool(r["score_authorised"]) for r in experiments):
        raise ValueError("Unmeasured Stage-6B experiment cells cannot be score-ready")
    return summary
