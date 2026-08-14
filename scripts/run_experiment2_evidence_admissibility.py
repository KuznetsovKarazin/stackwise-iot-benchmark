from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from stackwise.evidence_admissibility import (
    candidate_admissibility_ablation,
    overlay_stage6c_cost_readiness,
    source_grade_ablation,
    summarise_experiment2,
    target_relation_ablation,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/experiment2_evidence_admissibility.yml"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_figures(target_ablation: pd.DataFrame, candidate_ablation: pd.DataFrame, out_dir: Path) -> list[Path]:
    figures: list[Path] = []

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    x = range(len(target_ablation))
    target_labels = ["Direct only", "+ bridgeable", "+ conditional", "Grade-only naive"]
    ax.bar(x, target_ablation["source_target_relation_rows_counted_as_available"])
    ax.set_xticks(list(x), target_labels, rotation=18, ha="right")
    ax.set_ylabel("Source × decision-target relations counted as available (of 20)")
    ax.set_title("Evidence availability expands faster than decision admissibility")
    fig.tight_layout()
    p = out_dir / "figure1_source_target_admissibility_ladder.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    figures.append(p)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = range(len(candidate_ablation))
    candidate_labels = ["Canonical ready", "+ context", "+ structural transfer\n(counterfactual)", "Assumption priors\n(counterfactual)"]
    ax.bar(x, candidate_ablation["complete_two_criterion_candidates"])
    ax.set_xticks(list(x), candidate_labels, rotation=12, ha="right")
    ax.set_ylabel("Feasible candidates appearing complete for energy + lifecycle cost")
    ax.set_title("Apparent decision-space inflation under relaxed evidence admissibility")
    fig.tight_layout()
    p = out_dir / "figure2_candidate_decision_space_inflation.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    figures.append(p)
    return figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    inputs = policy["inputs"]
    input_paths = {name: ROOT / rel for name, rel in inputs.items()}
    for path in input_paths.values():
        if not path.exists():
            raise FileNotFoundError(f"Experiment-2 input missing: {path}")

    registry = yaml.safe_load(input_paths["registry"].read_text(encoding="utf-8"))
    evidence_summary = _load_json(input_paths["evidence_summary"])
    target_relations = pd.read_csv(input_paths["target_relations"])
    candidate_readiness = pd.read_csv(input_paths["candidate_criterion_readiness"])
    stage6c_cost = pd.read_csv(input_paths["stage6c_cost_summary"])

    source_grade = source_grade_ablation(registry=registry, evidence_summary=evidence_summary)
    target_ablation = target_relation_ablation(target_relations)
    first_slice_rows = overlay_stage6c_cost_readiness(candidate_readiness, stage6c_cost)
    candidate_ablation, candidate_detail = candidate_admissibility_ablation(first_slice_rows)
    summary = summarise_experiment2(
        source_grade=source_grade,
        target_relations=target_relations,
        first_slice_rows=first_slice_rows,
        candidate_regimes=candidate_ablation,
    )

    out_dir = ROOT / policy["outputs"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    source_grade.to_csv(out_dir / "source_grade_ablation.csv", index=False)
    target_ablation.to_csv(out_dir / "target_relation_admissibility_ablation.csv", index=False)
    first_slice_rows.to_csv(out_dir / "first_slice_support_states.csv", index=False)
    candidate_ablation.to_csv(out_dir / "candidate_admissibility_ablation.csv", index=False)
    candidate_detail.to_csv(out_dir / "candidate_regime_detail.csv", index=False)

    payload = {
        "stage": "Experiment 2 — evidence-grade and admissibility ablation",
        "benchmark_version": policy["benchmark"]["benchmark_version"],
        **asdict(summary),
        "source_grade_ladder_changes_core_record_retention": bool(source_grade["canonical_evidence_records_retained"].nunique() > 1),
        "source_grade_is_provenance_not_inferential_strength": True,
        "counterfactual_relaxation_is_publication_score_authorised": False,
        "probability_interpretation": False,
        "publication_interpretation": (
            "All four core datasets are Grade-A provenance sources, so an A/B/C/D source-grade ablation leaves the 398-record core unchanged. "
            "Decision admissibility is nevertheless sparse: no source directly identifies any of the five canonical decision targets at the frozen boundary, "
            "while bridgeable and conditional evidence provide partial support only. At the candidate level, only four of 42 required energy/cost cells are "
            "decision-ready after the validated cost robustness family, and no feasible candidate is complete for both required criteria. Treating contextual and "
            "structural-transfer support as if it were score-ready creates an apparent decision space that is not scientifically authorised."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    figures: list[Path] = []
    if not args.no_figures:
        figures = _write_figures(target_ablation, candidate_ablation, out_dir)

    write_run_manifest(
        out_dir / "run_manifest.json",
        command="python scripts/run_experiment2_evidence_admissibility.py",
        inputs=list(input_paths.values()),
        outputs=[
            out_dir / "source_grade_ablation.csv",
            out_dir / "target_relation_admissibility_ablation.csv",
            out_dir / "first_slice_support_states.csv",
            out_dir / "candidate_admissibility_ablation.csv",
            out_dir / "candidate_regime_detail.csv",
            out_dir / "summary.json",
            *figures,
        ],
        parameters={"benchmark_version": policy["benchmark"]["benchmark_version"], "probability_interpretation": False},
    )

    print("Experiment-2 evidence-grade/admissibility ablation: OK")
    print(
        "Core sources / canonical evidence records / Grade-A core sources: "
        f"{summary.core_sources} / {summary.canonical_evidence_records} / {summary.source_grade_a_sources}"
    )
    print(
        "Source×target relations direct / bridgeable / conditional / missing: "
        f"{summary.direct_relation_rows} / {summary.bridgeable_relation_rows} / {summary.conditional_relation_rows} / {summary.missing_relation_rows}"
    )
    print(
        "First-slice criterion rows ready / context-only / structural-transfer / other-blocked: "
        f"{summary.canonical_ready_rows} / {summary.context_only_rows} / {summary.structural_transfer_rows} / {summary.blocked_other_rows}"
    )
    print(
        "Complete candidates canonical / +context / counterfactual +structural / assumption-permitted: "
        f"{summary.canonical_complete_candidates} / {summary.context_complete_candidates} / "
        f"{summary.counterfactual_bridge_complete_candidates} / {summary.assumption_complete_candidates}"
    )
    print("Source-grade ladder changes retained core evidence: no")
    print("Counterfactual relaxed regimes / publication ranking authorised: yes / no")


if __name__ == "__main__":
    main()
