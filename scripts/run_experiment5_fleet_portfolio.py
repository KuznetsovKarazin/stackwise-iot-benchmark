from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from stackwise.fleet_portfolio import build_fleet_portfolio_experiment
from stackwise.io import load_yaml
from stackwise.provenance import write_run_manifest

POLICY = ROOT / "datasets" / "experiment5_fleet_portfolio.yml"


def _figures(tables: dict[str, pd.DataFrame], out_dir: Path) -> list[Path]:
    frontier = tables["portfolio_frontier"]
    strict = frontier[frontier.universe_mode.eq("STRICT_FEASIBLE_ONLY")]
    fig1 = out_dir / "figure1_portfolio_serviceability_frontier.png"
    plt.figure(figsize=(7.5, 4.8))
    for level, grp in strict.groupby("entity_level", sort=True):
        plt.plot(grp["portfolio_size"], grp["serviceability_fraction"], marker="o", label=level)
    plt.xlabel("Portfolio cardinality")
    plt.ylabel("Strictly serviceable scenario fraction")
    plt.ylim(0, 1.05)
    plt.xticks(sorted(strict["portfolio_size"].unique()))
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig1, dpi=180)
    plt.close()

    scen = tables["scenario_serviceability"].copy()
    scen = scen.sort_values(["strict_serviceable", "scenario_id"], ascending=[False, True])
    fig2 = out_dir / "figure2_scenario_serviceability_status.png"
    plt.figure(figsize=(8.5, 4.8))
    y = range(len(scen))
    vals = [2 if x else (1 if yv else 0) for x, yv in zip(scen["strict_serviceable"], scen["optimistic_serviceable_if_unresolved_closes_positive"])]
    plt.barh(list(y), vals)
    plt.yticks(list(y), scen["scenario_id"])
    plt.xticks([0, 1, 2], ["blocked", "unresolved-only", "strict feasible"])
    plt.xlabel("Serviceability status")
    plt.tight_layout()
    plt.savefig(fig2, dpi=180)
    plt.close()
    return [fig1, fig2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    policy = load_yaml(POLICY)
    paths = {k: ROOT / v for k, v in policy["inputs"].items()}
    tables, summary = build_fleet_portfolio_experiment(
        pd.read_csv(paths["refined_hard_feasibility_matrix"]),
        pd.read_csv(paths["candidate_stack_catalog"]),
    )

    out_dir = ROOT / policy["outputs"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    strict_min = tables["optimal_portfolios"][
        tables["optimal_portfolios"].universe_mode.eq("STRICT_FEASIBLE_ONLY")
        & tables["optimal_portfolios"].is_minimum_complete_portfolio.eq(True)
    ]
    strict_stack_min = strict_min[strict_min.entity_level.eq("stack")]
    strict_tech_min = strict_min[strict_min.entity_level.eq("access_technology")]
    strict_family_min = strict_min[strict_min.entity_level.eq("access_family")]

    payload = {
        "stage": "Experiment 5 — fleet portfolio feasibility and simplification penalty",
        "benchmark_version": policy["benchmark"]["benchmark_version"],
        **asdict(summary),
        "strict_single_stack_serviceability_loss_fraction": 1.0 - summary.strict_best_single_stack_coverage / summary.strict_serviceable_scenarios,
        "strict_single_technology_serviceability_loss_fraction": 1.0 - summary.strict_best_single_technology_coverage / summary.strict_serviceable_scenarios,
        "strict_single_family_serviceability_loss_fraction": 1.0 - summary.strict_best_single_family_coverage / summary.strict_serviceable_scenarios,
        "strict_minimum_complete_stack_portfolios": len(strict_stack_min),
        "strict_minimum_complete_technology_portfolios": len(strict_tech_min),
        "strict_minimum_complete_family_portfolios": len(strict_family_min),
        "strict_minimum_complete_stack_examples": strict_stack_min["portfolio_members"].astype(str).tolist(),
        "strict_minimum_complete_technology_examples": strict_tech_min["portfolio_members"].astype(str).tolist(),
        "strict_minimum_complete_family_examples": strict_family_min["portfolio_members"].astype(str).tolist(),
        "unresolved_sensitivity_is_not_feasibility_claim": True,
        "device_count_weighting_performed": False,
        "lifecycle_cost_optimisation_performed": False,
        "soft_score_optimisation_performed": False,
        "probability_interpretation": False,
        "global_candidate_ranking_performed": False,
        "publication_mcda_authorised": False,
        "publication_interpretation": (
            "Across the five benchmark scenario classes with at least one strictly feasible candidate, the best single stack, access technology, "
            "or access family covers only four classes, leaving a 20% structural serviceability loss. Complete strict coverage requires a minimum "
            "portfolio of two stacks and two access technologies; every minimum technology portfolio combines LTE-M with one LoRaWAN radio option. "
            "At family level, cellular plus LoRaWAN is the unique minimum complete portfolio. The two remaining benchmark scenarios have no strictly "
            "feasible candidate under the frozen evidence matrix. If unresolved relations are treated only as an optimistic evidence-closure sensitivity, "
            "covering all seven scenario classes requires three stack/technology/family elements and adds Thread. This experiment is a hard-feasibility "
            "set-cover result, not a lifecycle-cost optimisation, device-count-weighted fleet design, or probabilistic MCDA result."
        ),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    figures: list[Path] = []
    if not args.no_figures:
        figures = _figures(tables, out_dir)

    outputs = [out_dir / f"{name}.csv" for name in tables] + [summary_path, *figures]
    write_run_manifest(
        out_dir / "run_manifest.json",
        command="python scripts/run_experiment5_fleet_portfolio.py",
        inputs=[POLICY, *paths.values()],
        outputs=outputs,
        parameters={
            "benchmark_version": policy["benchmark"]["benchmark_version"],
            "primary_universe": "strict feasible only",
            "unresolved_sensitivity": "optimistic only",
            "device_count_weighting": False,
            "lifecycle_cost_optimisation": False,
            "soft_scores": False,
            "probability_interpretation": False,
        },
    )

    print("Experiment-5 fleet portfolio feasibility/simplification: OK")
    print(
        "Benchmark scenarios / strict-serviceable / unresolved-only: "
        f"{summary.total_scenarios} / {summary.strict_serviceable_scenarios} / {summary.unresolved_only_scenarios}"
    )
    print(
        "Best single stack / technology / family strict coverage: "
        f"{summary.strict_best_single_stack_coverage} / {summary.strict_best_single_technology_coverage} / {summary.strict_best_single_family_coverage} "
        f"of {summary.strict_serviceable_scenarios}"
    )
    print(
        "Minimum stacks / technologies / families for complete strict coverage: "
        f"{summary.strict_min_stacks_for_complete_coverage} / {summary.strict_min_technologies_for_complete_coverage} / {summary.strict_min_families_for_complete_coverage}"
    )
    print(
        "Minimum stacks / technologies / families for optimistic feasible+unresolved coverage: "
        f"{summary.optimistic_min_stacks_for_complete_coverage} / {summary.optimistic_min_technologies_for_complete_coverage} / {summary.optimistic_min_families_for_complete_coverage}"
    )
    print(
        "Strict minimum complete stack / technology / family portfolios: "
        f"{len(strict_stack_min)} / {len(strict_tech_min)} / {len(strict_family_min)}"
    )
    print("Lifecycle-cost/device-count/soft-score optimisation performed: no / no / no")
    print("State-space probability interpretation / publication MCDA authorised: no / no")


if __name__ == "__main__":
    main()
