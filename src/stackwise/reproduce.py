from __future__ import annotations

from pathlib import Path

import pandas as pd

from .audit import write_audit
from .io import load_yaml
from .mcda import run_smaa
from .models import fit_energy_model, save_energy_model
from .optimizer import load_fleet_config, optimise_fleet
from .reporting import plot_rank_acceptability, write_solution_markdown


def reproduce_smoke(output_dir: str | Path = "results/smoke") -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    observations = pd.read_csv("data/examples/smoke_observations.csv")

    audit_paths = write_audit(output_dir=output / "audit")
    model = fit_energy_model(observations)
    model_paths = save_energy_model(model, output / "energy_model")

    profiles = pd.DataFrame({
        "energy_efficiency": [0.92, 0.82, 0.72, 0.55],
        "coverage_predictability": [0.75, 0.62, 0.90, 0.88],
        "latency_suitability": [0.45, 0.35, 0.50, 0.78],
        "delivery_reliability": [0.78, 0.70, 0.88, 0.90],
        "cost_efficiency": [0.88, 0.80, 0.55, 0.48],
        "private_control": [1.00, 0.10, 0.10, 0.10],
        "lifecycle_viability": [0.86, 0.45, 0.88, 0.92],
    }, index=["LoRaWAN", "Sigfox", "NB-IoT", "LTE-M"])
    mcda_config = load_yaml("configs/mcda.yml")
    weights = pd.Series({k: v["baseline_weight"] for k, v in mcda_config["criteria"].items()})
    smaa = run_smaa(
        profiles,
        baseline_weights=weights,
        samples=2000,
        weight_concentration=mcda_config["weight_concentration"],
        common_factor_loading=mcda_config["correlation"]["common_factor_loading"],
    )
    rank_path = output / "rank_acceptability.csv"
    smaa.rank_acceptability.to_csv(rank_path)
    rank_plot = plot_rank_acceptability(smaa.rank_acceptability, output / "rank_acceptability.png")

    fleet = load_fleet_config()
    solution = optimise_fleet(fleet)
    solution_path = write_solution_markdown(solution, output / "fleet_solution.md")

    return {
        **{f"audit_{k}": v for k, v in audit_paths.items()},
        **{f"model_{k}": v for k, v in model_paths.items()},
        "rank_acceptability": rank_path,
        "rank_plot": rank_plot,
        "fleet_solution": solution_path,
    }
