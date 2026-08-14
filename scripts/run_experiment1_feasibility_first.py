from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from stackwise.feasibility_first import (
    FEATURE_IDS,
    build_preference_feature_matrix,
    deterministic_simplex_weight_grid,
    run_feasibility_first_experiment,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/experiment1_feasibility_first.yml"


def _resolve(root: Path, relative: str) -> Path:
    return root / relative


def _write_figures(scenario_summary: pd.DataFrame, outcomes: pd.DataFrame, out_dir: Path) -> list[Path]:
    figures: list[Path] = []
    labels = scenario_summary["scenario_id"].tolist()
    x = range(len(labels))
    bottom = [0] * len(labels)
    columns = [
        ("score_first_top_feasible_only_anchors", "feasible-only top set"),
        ("score_first_top_feasible_infeasible_mixed_anchors", "mixed feasible/infeasible top set"),
        ("score_first_top_unresolved_only_anchors", "unresolved-only top set"),
        ("score_first_top_unresolved_infeasible_mixed_anchors", "mixed unresolved/infeasible top set"),
        ("score_first_top_infeasible_only_anchors", "infeasible-only top set"),
    ]
    fig, ax = plt.subplots(figsize=(12, 6))
    for column, legend in columns:
        values = scenario_summary[column].to_numpy(dtype=float)
        ax.bar(x, values, bottom=bottom, label=legend)
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set_ylabel("Deterministic preference anchors (n=35 per scenario)")
    ax.set_xlabel("Benchmark scenario")
    ax.set_xticks(list(x), labels, rotation=35, ha="right")
    ax.legend(loc="upper right")
    ax.set_title("Score-first top-set feasibility under the frozen preference envelope")
    fig.tight_layout()
    path = out_dir / "figure1_score_first_topset_feasibility.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    figures.append(path)

    evaluable = outcomes[outcomes["feasible_candidate_count"] > 0].copy()
    by_scenario = [
        evaluable.loc[evaluable["scenario_id"] == scenario, "soft_score_concession_for_feasibility"].dropna().to_numpy(dtype=float)
        for scenario in scenario_summary.loc[scenario_summary["feasible_candidate_count"] > 0, "scenario_id"]
    ]
    box_labels = scenario_summary.loc[scenario_summary["feasible_candidate_count"] > 0, "scenario_id"].tolist()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.boxplot(by_scenario, tick_labels=box_labels, showfliers=False)
    ax.set_ylabel("Soft-score concession required by feasibility filtering")
    ax.set_xlabel("Benchmark scenario")
    ax.tick_params(axis="x", rotation=35)
    ax.set_title("Preference-score concession after hard-feasibility filtering")
    fig.tight_layout()
    path = out_dir / "figure2_soft_score_concession.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    figures.append(path)
    return figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-root",
        type=Path,
        default=None,
        help="Override the frozen Benchmark v1.0.0 release root.",
    )
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    release_root = args.release_root or (ROOT / policy["benchmark"]["release_root"])
    inputs = policy["benchmark"]["inputs"]
    candidate_path = _resolve(release_root, inputs["candidate_stacks"])
    component_path = _resolve(release_root, inputs["component_catalog"])
    feasibility_path = _resolve(release_root, inputs["hard_feasibility"])
    for path in (candidate_path, component_path, feasibility_path):
        if not path.exists():
            raise FileNotFoundError(
                f"Frozen Benchmark v1.0.0 input missing: {path}. Build the final benchmark release first."
            )

    candidate_stacks = pd.read_csv(candidate_path)
    component_catalog = pd.read_csv(component_path)
    hard_feasibility = pd.read_csv(feasibility_path)
    feature_matrix = build_preference_feature_matrix(candidate_stacks, component_catalog)
    step = float(policy["preference_design"]["simplex_step"])
    weight_grid = deterministic_simplex_weight_grid(step=step)
    expected = int(policy["preference_design"]["expected_anchor_count"])
    if len(weight_grid) != expected:
        raise RuntimeError(f"Unexpected preference-anchor count: {len(weight_grid)} != {expected}")

    outcomes, scenario_summary, summary = run_feasibility_first_experiment(
        feature_matrix=feature_matrix,
        weight_grid=weight_grid,
        hard_feasibility=hard_feasibility,
        tie_tolerance=float(policy["preference_design"]["tie_tolerance"]),
    )

    out_dir = ROOT / policy["outputs"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    feature_path = out_dir / "preference_feature_matrix.csv"
    weight_path = out_dir / "preference_weight_anchors.csv"
    outcome_path = out_dir / "scenario_anchor_outcomes.csv"
    scenario_path = out_dir / "scenario_summary.csv"
    feature_matrix.to_csv(feature_path, index=False)
    weight_grid.to_csv(weight_path, index=False)
    outcomes.to_csv(outcome_path, index=False)
    scenario_summary.to_csv(scenario_path, index=False)

    with_feasible = outcomes[outcomes["feasible_candidate_count"] > 0]
    without_feasible = outcomes[outcomes["feasible_candidate_count"] == 0]
    aggregate_rows = [
        {
            "scope": "all_scenario_anchor_evaluations",
            "rows": len(outcomes),
            "score_first_any_infeasible_top_rows": int(outcomes["score_first_top_contains_infeasible"].sum()),
            "score_first_only_infeasible_top_rows": int(outcomes["score_first_top_only_infeasible"].sum()),
            "score_first_purely_feasible_top_rows": int((~outcomes["score_first_top_contains_infeasible"] & outcomes["score_first_top_contains_feasible"]).sum()),
            "score_first_returns_top_without_feasible_candidate_rows": len(without_feasible),
            "grid_coverage_fraction_any_infeasible_top": float(outcomes["score_first_top_contains_infeasible"].mean()),
            "grid_coverage_fraction_only_infeasible_top": float(outcomes["score_first_top_only_infeasible"].mean()),
            "probability_interpretation": False,
        },
        {
            "scope": "scenarios_with_at_least_one_feasible_candidate",
            "rows": len(with_feasible),
            "score_first_any_infeasible_top_rows": int(with_feasible["score_first_top_contains_infeasible"].sum()),
            "score_first_only_infeasible_top_rows": int(with_feasible["score_first_top_only_infeasible"].sum()),
            "score_first_purely_feasible_top_rows": int((~with_feasible["score_first_top_contains_infeasible"] & with_feasible["score_first_top_contains_feasible"]).sum()),
            "score_first_returns_top_without_feasible_candidate_rows": 0,
            "grid_coverage_fraction_any_infeasible_top": float(with_feasible["score_first_top_contains_infeasible"].mean()),
            "grid_coverage_fraction_only_infeasible_top": float(with_feasible["score_first_top_only_infeasible"].mean()),
            "probability_interpretation": False,
        },
        {
            "scope": "scenarios_without_feasible_candidate",
            "rows": len(without_feasible),
            "score_first_any_infeasible_top_rows": int(without_feasible["score_first_top_contains_infeasible"].sum()),
            "score_first_only_infeasible_top_rows": int(without_feasible["score_first_top_only_infeasible"].sum()),
            "score_first_purely_feasible_top_rows": 0,
            "score_first_returns_top_without_feasible_candidate_rows": len(without_feasible),
            "grid_coverage_fraction_any_infeasible_top": float(without_feasible["score_first_top_contains_infeasible"].mean()),
            "grid_coverage_fraction_only_infeasible_top": float(without_feasible["score_first_top_only_infeasible"].mean()),
            "probability_interpretation": False,
        },
    ]
    aggregate = pd.DataFrame(aggregate_rows)
    aggregate_path = out_dir / "aggregate_results.csv"
    aggregate.to_csv(aggregate_path, index=False)

    sensitivity_rows = []
    for sensitivity_step in policy["preference_design"]["grid_resolution_sensitivity_steps"]:
        sensitivity_grid = deterministic_simplex_weight_grid(step=float(sensitivity_step))
        sensitivity_outcomes, _, sensitivity_summary = run_feasibility_first_experiment(
            feature_matrix=feature_matrix,
            weight_grid=sensitivity_grid,
            hard_feasibility=hard_feasibility,
            tie_tolerance=float(policy["preference_design"]["tie_tolerance"]),
        )
        sensitivity_evaluable = sensitivity_outcomes[sensitivity_outcomes["feasible_candidate_count"] > 0]
        sensitivity_rows.append({
            "simplex_step": float(sensitivity_step),
            "preference_anchor_count": len(sensitivity_grid),
            "scenario_anchor_rows": len(sensitivity_outcomes),
            "overall_grid_fraction_any_infeasible_top": float(sensitivity_outcomes["score_first_top_contains_infeasible"].mean()),
            "overall_grid_fraction_only_infeasible_top": float(sensitivity_outcomes["score_first_top_only_infeasible"].mean()),
            "evaluable_grid_fraction_any_infeasible_top": float(sensitivity_evaluable["score_first_top_contains_infeasible"].mean()),
            "evaluable_grid_fraction_only_infeasible_top": float(sensitivity_evaluable["score_first_top_only_infeasible"].mean()),
            "probability_interpretation": False,
        })
    grid_sensitivity = pd.DataFrame(sensitivity_rows)
    grid_sensitivity_path = out_dir / "grid_resolution_sensitivity.csv"
    grid_sensitivity.to_csv(grid_sensitivity_path, index=False)

    concessions = with_feasible["soft_score_concession_for_feasibility"].dropna().astype(float)
    payload = {
        "stage": "Experiment 1 — feasibility-first vs score-first",
        "benchmark_version": policy["benchmark"]["benchmark_version"],
        **asdict(summary),
        "evaluable_rows_with_purely_feasible_score_first_top_set": int(
            (~with_feasible["score_first_top_contains_infeasible"] & with_feasible["score_first_top_contains_feasible"]).sum()
        ),
        "median_soft_score_concession_across_evaluable_anchors": float(concessions.median()),
        "mean_soft_score_concession_across_evaluable_anchors": float(concessions.mean()),
        "max_soft_score_concession_across_evaluable_anchors": float(concessions.max()),
        "preference_anchor_probability_interpretation": False,
        "real_candidate_mcda_performed": False,
        "empirical_soft_metric_imputation_performed": False,
        "publication_interpretation": (
            "Across a deterministic structural-preference envelope, score-first ranking can place hard-infeasible "
            "candidates in the top set and can return a seemingly decisive top set even when no feasible candidate exists. "
            "Feasibility-first removes these violations before any preference comparison. Anchor counts are stress-test "
            "coverage, not probabilities over stakeholder preferences."
        ),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    figure_paths: list[Path] = []
    if not args.no_figures:
        figure_paths = _write_figures(scenario_summary, outcomes, out_dir)

    manifest_path = out_dir / "run_manifest.json"
    write_run_manifest(
        manifest_path,
        command="python scripts/run_experiment1_feasibility_first.py",
        inputs=[POLICY, candidate_path, component_path, feasibility_path],
        outputs=[feature_path, weight_path, outcome_path, scenario_path, aggregate_path, grid_sensitivity_path, summary_path, *figure_paths],
        parameters={
            "benchmark_version": policy["benchmark"]["benchmark_version"],
            "feature_ids": list(FEATURE_IDS),
            "simplex_step": step,
            "preference_probability_interpretation": False,
            "real_candidate_mcda": False,
        },
    )

    print("Experiment-1 feasibility-first vs score-first: OK")
    print(
        "Scenarios / candidates / preference anchors / scenario-anchor evaluations: "
        f"{summary.scenarios} / {summary.candidates} / {summary.preference_anchors} / {summary.scenario_anchor_evaluations}"
    )
    print(
        "Scenarios with / without at least one feasible candidate: "
        f"{summary.scenarios_with_feasible_candidates} / {summary.scenarios_without_feasible_candidates}"
    )
    print(
        "Score-first rows with any / only hard-infeasible candidate in the top set: "
        f"{summary.score_first_any_infeasible_top_rows} / {summary.score_first_only_infeasible_top_rows}"
    )
    print(
        "Among evaluable scenario-anchor rows, any / only infeasible top-set contamination: "
        f"{summary.evaluable_rows_with_any_infeasible_top} / {summary.evaluable_rows_with_only_infeasible_top}"
    )
    print(
        "No-feasible scenario-anchor rows where score-first still returns a top set / feasibility-first forces a decision: "
        f"{summary.no_feasible_rows_where_score_first_still_returns_top} / "
        f"{summary.feasibility_first_forced_decisions_without_feasible_candidate}"
    )
    print("Preference-anchor probability interpretation: no")
    print("Real candidate MCDA / empirical soft-metric imputation performed: no / no")


if __name__ == "__main__":
    main()
