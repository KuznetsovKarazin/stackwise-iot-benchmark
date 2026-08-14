from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.cost_robustness import (
    audit_summary,
    billing_anchor_rows,
    build_candidate_cost_summary_rows,
    build_cost_family_rows,
    procurement_anchor_rows,
    source_evidence_rows,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage6c_lifecycle_cost_robustness"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty Stage-6C artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy_path = ROOT / "datasets/stage6c_lifecycle_cost_robustness.yml"
    stage5n_path = ROOT / "results/validation/stage5n_security_session_control_envelope/session_control_envelope.csv"
    subset_path = ROOT / "results/validation/stage6a_decision_slice_consolidation/preferred_development_subset.csv"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    stage5n = _read_csv(stage5n_path)
    subset = _read_csv(subset_path)

    family = build_cost_family_rows(stage5n, subset, policy)
    candidates = build_candidate_cost_summary_rows(family)
    evidence = source_evidence_rows(policy)
    billing = billing_anchor_rows(policy)
    procurement = procurement_anchor_rows(policy)
    summary = audit_summary(family, candidates, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    family_path = OUT / "preferred_subset_lifecycle_cost_family.csv"
    candidate_path = OUT / "preferred_subset_cost_summary.csv"
    evidence_path = OUT / "source_evidence_updates.csv"
    billing_path = OUT / "billing_session_anchors.csv"
    procurement_path = OUT / "procurement_anchors.csv"
    _write_csv(family_path, family)
    _write_csv(candidate_path, candidates)
    _write_csv(evidence_path, evidence)
    _write_csv(billing_path, billing)
    _write_csv(procurement_path, procurement)

    payload = {
        "stage": policy["stage"],
        "stage6_status": policy["stage6_status"],
        **summary.__dict__,
        "lifecycle_cost_target_status": "READY_ROBUSTNESS_FAMILY",
        "energy_target_status": "BLOCKED",
        "first_slice_ready": False,
        "probability_interpretation": False,
        "publication_mcda_authorised": False,
        "decision_engine_development_authorised_for_cost_only": True,
        "interpretation": (
            "The preferred periodic-tracking 2x2 IP-cellular subset now has a finite EUR lifecycle-cost robustness family. "
            "The family retains every Stage-5N protocol/serialization/session-control row, crosses it with two official-"
            "documentation PDP-session billing anchors and two dated DigiKey procurement observations, and applies the "
            "published 1NCE base-plan/TopUp cashflow. Family members are unweighted epistemic/deployment sensitivities, "
            "not market or behavioural probabilities. NB-IoT and LTE-M have identical cost families within a binding under "
            "the shared dual-mode BG95 reference hardware/operator. Energy remains blocked, so no candidate ranking is authorised."
        ),
        "preferred_next_step": (
            "Freeze Stage-6C cost input as READY_ROBUSTNESS_FAMILY for decision-engine development. Await the Stage-6B matched "
            "energy pilot for candidate-boundary report energy; meanwhile implement a score-free stochastic/robustness engine "
            "dry-run using synthetic energy fixtures only in tests, not publication results."
        ),
        "cost_family_artifact": "results/validation/stage6c_lifecycle_cost_robustness/preferred_subset_lifecycle_cost_family.csv",
        "candidate_summary_artifact": "results/validation/stage6c_lifecycle_cost_robustness/preferred_subset_cost_summary.csv",
        "billing_anchor_artifact": "results/validation/stage6c_lifecycle_cost_robustness/billing_session_anchors.csv",
        "procurement_anchor_artifact": "results/validation/stage6c_lifecycle_cost_robustness/procurement_anchors.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/build_lifecycle_cost_robustness_family.py",
        inputs=[policy_path, stage5n_path, subset_path],
        outputs=[family_path, candidate_path, evidence_path, billing_path, procurement_path, summary_path],
        parameters={
            "family_semantics": policy["scientific_policy"]["family_semantics"],
            "probability_interpretation": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-6C lifecycle-cost robustness audit: OK")
    print(f"Preferred subset / Stage-5N source rows: {summary.preferred_subset_candidates} / {summary.source_stage5n_rows}")
    print(f"Billing / procurement anchors / cost-family rows: {summary.billing_anchors} / {summary.procurement_anchors} / {summary.cost_family_rows}")
    print(f"Cost-ready / energy-ready / first-slice-ready candidates: {summary.cost_ready_candidates} / {summary.energy_ready_candidates} / {summary.first_slice_ready_candidates}")
    print(f"Candidates with identical NB-IoT/LTE-M cost family within binding: {summary.candidates_with_identical_nb_iot_lte_m_cost_family_within_binding}")
    print("Lifecycle cost status: READY_ROBUSTNESS_FAMILY")
    print("Publication MCDA authorised: no")


if __name__ == "__main__":
    main()
