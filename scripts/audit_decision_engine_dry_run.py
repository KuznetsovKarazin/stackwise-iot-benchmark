from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.decision_engine import (
    align_cost_states,
    audit_summary,
    deterministic_weight_rows,
    engine_invariant_rows,
    run_synthetic_nested_dry_run,
    synthetic_energy_rows,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage6d_decision_engine_dry_run"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty Stage-6D artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy_path = ROOT / "datasets/stage6d_decision_engine_dry_run.yml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    cost_path = ROOT / policy["inputs"]["cost_family"]
    subset_path = ROOT / policy["inputs"]["preferred_subset"]
    cost_family = _read_csv(cost_path)
    subset = _read_csv(subset_path)

    candidate_ids = [str(x) for x in policy["preferred_subset_stack_ids"]]
    observed_subset = {str(r["stack_id"]) for r in subset}
    if observed_subset != set(candidate_ids):
        raise ValueError(
            f"Stage-6D preferred subset drift: policy={sorted(candidate_ids)}, observed={sorted(observed_subset)}"
        )

    cost_states = align_cost_states(cost_family, candidate_ids)
    energy = synthetic_energy_rows(policy, candidate_ids)
    weights = deterministic_weight_rows(policy)
    weight_summary, fixture_envelope = run_synthetic_nested_dry_run(
        cost_states=cost_states,
        energy_rows=energy,
        weight_rows=weights,
        candidate_ids=candidate_ids,
        policy=policy,
    )
    invariants = engine_invariant_rows(
        cost_states=cost_states,
        energy_rows=energy,
        weight_rows=weights,
        weight_summary_rows=weight_summary,
        fixture_envelope_rows=fixture_envelope,
        candidate_ids=candidate_ids,
        policy=policy,
    )
    summary = audit_summary(
        cost_states=cost_states,
        energy_rows=energy,
        weight_rows=weights,
        weight_summary_rows=weight_summary,
        fixture_envelope_rows=fixture_envelope,
        invariant_rows=invariants,
        candidate_ids=candidate_ids,
        policy=policy,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    cost_states_path = OUT / "aligned_cost_states.csv"
    energy_path = OUT / "synthetic_energy_fixtures.csv"
    weights_path = OUT / "deterministic_weight_grid.csv"
    weight_summary_path = OUT / "synthetic_weight_sensitivity_envelope.csv"
    rank_envelope_path = OUT / "synthetic_fixture_rank_envelope.csv"
    invariants_path = OUT / "engine_invariants.csv"
    _write_csv(cost_states_path, cost_states)
    _write_csv(energy_path, energy)
    _write_csv(weights_path, weights)
    _write_csv(weight_summary_path, weight_summary)
    _write_csv(rank_envelope_path, fixture_envelope)
    _write_csv(invariants_path, invariants)

    payload = {
        "stage": policy["stage"],
        "stage6_status": policy["stage6_status"],
        **summary.__dict__,
        "real_energy_target_materialised": False,
        "real_candidate_ranking_authorised": False,
        "publication_mcda_authorised": False,
        "cost_family_probability_interpretation": False,
        "weight_grid_probability_interpretation": False,
        "synthetic_fixture_probability_interpretation": False,
        "pooled_epistemic_rank_probability_reported": False,
        "interpretation": (
            "The nested decision/robustness engine is validated only against synthetic paired energy fixtures and the frozen "
            "Stage-6C cost family. Cost states and stakeholder-weight anchors remain unweighted enumerated sensitivities; "
            "the engine reports envelopes rather than pooling them into a global probability. Fixed external value-function "
            "anchors avoid alternative-set min/max normalisation, and tied utilities receive fractional rank mass. These "
            "synthetic fixture outputs are software validation artifacts, not scientific rankings of NB-IoT, LTE-M, CoAP or MQTT."
        ),
        "preferred_next_step": (
            "Freeze the Stage-6D engine implementation. Run the Stage-6B matched whole-device energy pilot. After pilot data "
            "pass boundary, replication and quality checks, replace synthetic fixtures with paired empirical/bootstrap energy "
            "draws while retaining the Stage-6C cost-state enumeration. Only then may the first real decision experiment be authorised."
        ),
        "aligned_cost_states_artifact": "results/validation/stage6d_decision_engine_dry_run/aligned_cost_states.csv",
        "synthetic_energy_artifact": "results/validation/stage6d_decision_engine_dry_run/synthetic_energy_fixtures.csv",
        "weight_grid_artifact": "results/validation/stage6d_decision_engine_dry_run/deterministic_weight_grid.csv",
        "weight_sensitivity_artifact": "results/validation/stage6d_decision_engine_dry_run/synthetic_weight_sensitivity_envelope.csv",
        "rank_envelope_artifact": "results/validation/stage6d_decision_engine_dry_run/synthetic_fixture_rank_envelope.csv",
        "engine_invariants_artifact": "results/validation/stage6d_decision_engine_dry_run/engine_invariants.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_decision_engine_dry_run.py",
        inputs=[policy_path, cost_path, subset_path],
        outputs=[
            cost_states_path,
            energy_path,
            weights_path,
            weight_summary_path,
            rank_envelope_path,
            invariants_path,
            summary_path,
        ],
        parameters={
            "synthetic_energy_only": True,
            "cost_states_probability_interpretation": False,
            "weight_probability_interpretation": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-6D synthetic decision-engine dry run: OK")
    print(
        "Preferred candidates / aligned cost states / synthetic fixtures: "
        f"{summary.preferred_subset_candidates} / {summary.aligned_cost_states} / {summary.synthetic_energy_fixtures}"
    )
    print(
        "Synthetic draws per fixture / deterministic weight anchors / state-weight evaluations: "
        f"{summary.synthetic_energy_draws_per_fixture} / {summary.deterministic_weight_anchors} / "
        f"{summary.conditional_state_weight_evaluations}"
    )
    print(
        "Weight-sensitivity / fixture-rank-envelope rows: "
        f"{summary.weight_sensitivity_rows} / {summary.rank_envelope_rows}"
    )
    print(f"Engine invariants passed / failed: {summary.invariants_passed} / {summary.invariants_failed}")
    print("Pooled epistemic rank probability reported: no")
    print("Real candidate ranking / publication MCDA authorised: no / no")


if __name__ == "__main__":
    main()
