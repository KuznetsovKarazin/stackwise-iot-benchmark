from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.decision_slice import (
    audit_summary,
    build_candidate_slice_rows,
    build_criterion_readiness_rows,
    build_scenario_summary_rows,
    gap_priority_rows,
    hard_unresolved_exclusion_rows,
    preferred_subset_rows,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage6a_decision_slice_consolidation"


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty Stage-6A artifact: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy_path = ROOT / "datasets/stage6a_decision_slice_consolidation.yml"
    feasibility_path = ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv"
    stage5e_path = ROOT / "results/validation/stage5_decision_readiness/candidate_target_readiness.csv"
    stage5g_path = ROOT / "results/validation/stage5g_cellular_transfer_evidence/candidate_transfer_admissibility.csv"
    cost_path = ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv"
    robustness_path = ROOT / "results/validation/stage5n_security_session_control_envelope/session_control_allowance_robustness.csv"

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    feasibility = _csv(feasibility_path)
    stage5e = _csv(stage5e_path)
    stage5g = _csv(stage5g_path)
    costs = _csv(cost_path)
    robustness = _csv(robustness_path)

    criteria = build_criterion_readiness_rows(
        stage5e_rows=stage5e,
        cost_rows=costs,
        stage5n_robustness_rows=robustness,
        stage5g_energy_rows=stage5g,
    )
    candidates = build_candidate_slice_rows(criteria)
    scenarios = build_scenario_summary_rows(candidates)
    unresolved = hard_unresolved_exclusion_rows(feasibility)
    subset = preferred_subset_rows(candidates, policy)
    gaps = gap_priority_rows(policy)
    summary = audit_summary(
        feasibility_rows=feasibility,
        criterion_rows=criteria,
        candidate_rows=candidates,
        scenario_rows=scenarios,
        unresolved_rows=unresolved,
        subset_rows=subset,
        policy=policy,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    criteria_path = OUT / "candidate_criterion_readiness.csv"
    candidates_path = OUT / "feasible_candidate_decision_slice.csv"
    scenarios_path = OUT / "scenario_decision_slice_summary.csv"
    unresolved_path = OUT / "hard_unresolved_exclusions.csv"
    subset_path = OUT / "preferred_development_subset.csv"
    gaps_path = OUT / "stage6b_gap_priorities.csv"
    _write_csv(criteria_path, criteria)
    _write_csv(candidates_path, candidates)
    _write_csv(scenarios_path, scenarios)
    _write_csv(unresolved_path, unresolved)
    _write_csv(subset_path, subset)
    _write_csv(gaps_path, gaps)

    payload = {
        "stage": policy["stage"],
        "stage6_status": policy["stage6_status"],
        **summary.__dict__,
        "first_slice_required_soft_targets": policy["scientific_policy"]["first_slice_required_soft_targets"],
        "full_decision_ready_slice_materialised": False,
        "publication_mcda_authorised": False,
        "stochastic_engine_candidate_scoring_authorised": False,
        "transport_accounting_detail_frozen": True,
        "preferred_development_subset_id": policy["preferred_development_subset"]["subset_id"],
        "preferred_development_subset_scenario": policy["preferred_development_subset"]["scenario_id"],
        "preferred_development_subset_scope": policy["preferred_development_subset"]["publication_scope"],
        "interpretation": (
            "Stage 6A consolidates the frozen feasibility matrix with the completed Stage-5 evidence, cost and "
            "transport-accounting work. No feasible candidate currently has both required first-slice soft targets "
            "in a scoreable form: candidate-boundary report energy remains blocked for all 21 feasible rows, while "
            "the ten feasible IP-cellular rows now have dated cost-floor plus tariff-volume context only, not a "
            "canonical EUR lifecycle-cost uncertainty representation. The Stage-5N traffic results are therefore "
            "retained as contextual robustness evidence and are not scored. The periodic 60-s/64-B IP-cellular 2x2 "
            "subset is selected only as the preferred development benchmark for closing the remaining energy/cost "
            "inputs; it is not the optimum over the full scenario because two feasible Non-IP candidates remain excluded."
        ),
        "preferred_next_step": (
            "Stage 6B: close matched cellular-IP whole-device report energy and materialise an explicit EUR lifecycle-cost "
            "robustness family for the preferred periodic-tracking IP-cellular subset; do not reopen transport detail."
        ),
        "criterion_readiness_artifact": "results/validation/stage6a_decision_slice_consolidation/candidate_criterion_readiness.csv",
        "candidate_slice_artifact": "results/validation/stage6a_decision_slice_consolidation/feasible_candidate_decision_slice.csv",
        "scenario_summary_artifact": "results/validation/stage6a_decision_slice_consolidation/scenario_decision_slice_summary.csv",
        "hard_unresolved_exclusions_artifact": "results/validation/stage6a_decision_slice_consolidation/hard_unresolved_exclusions.csv",
        "preferred_development_subset_artifact": "results/validation/stage6a_decision_slice_consolidation/preferred_development_subset.csv",
        "stage6b_gap_priorities_artifact": "results/validation/stage6a_decision_slice_consolidation/stage6b_gap_priorities.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/consolidate_first_decision_slice.py",
        inputs=[policy_path, feasibility_path, stage5e_path, stage5g_path, cost_path, robustness_path],
        outputs=[criteria_path, candidates_path, scenarios_path, unresolved_path, subset_path, gaps_path, summary_path],
        parameters={
            "required_soft_targets": policy["scientific_policy"]["first_slice_required_soft_targets"],
            "publication_mcda_authorised": False,
            "transport_accounting_detail_frozen": True,
        },
    )

    print("Stage-6A first decision-slice consolidation: OK")
    print(
        "Frozen Stage-4 feasible / infeasible / unresolved: "
        f"{summary.stage4_feasible_rows} / {summary.stage4_infeasible_rows} / {summary.stage4_unresolved_rows}"
    )
    print(
        "Feasible candidates / criterion rows / required soft rows: "
        f"{summary.feasible_candidate_rows} / {summary.criterion_rows} / {summary.required_soft_criterion_rows}"
    )
    print(
        "Required soft rows ready / context-only / blocked: "
        f"{summary.ready_required_soft_criterion_rows} / {summary.context_only_required_soft_criterion_rows} / "
        f"{summary.blocked_required_soft_criterion_rows}"
    )
    print(
        "Feasible candidates ready for first slice / with cost context: "
        f"{summary.feasible_candidates_ready_for_first_slice} / {summary.feasible_candidates_with_cost_context}"
    )
    print(
        "IP cost context robust-within / robust-exceed / protocol-envelope-sensitive candidates: "
        f"{summary.cost_context_robust_within_candidates} / {summary.cost_context_robust_exceed_candidates} / "
        f"{summary.cost_context_protocol_envelope_sensitive_candidates}"
    )
    print(
        "Preferred periodic-tracking IP development subset rows / ready rows: "
        f"{summary.preferred_development_subset_rows} / {summary.preferred_development_subset_ready_rows}"
    )
    print("Publication MCDA authorised: no")


if __name__ == "__main__":
    main()
