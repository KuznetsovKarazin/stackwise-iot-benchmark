"""Prototype/smoke fleet optimiser. Configured costs are not publication evidence unless explicitly validated."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .io import load_yaml


@dataclass
class FleetSolution:
    assignment: dict[str, str]
    total_cost_usd: float
    technologies_used: tuple[str, ...]
    breakdown: dict[str, float]


def assignment_cost(
    assignment: dict[str, str],
    config: dict,
    *,
    technology_complexity_penalty_usd: float | None = None,
) -> FleetSolution:
    years = float(config.get("years", 1))
    groups = config["device_groups"]
    technologies = config["technologies"]
    used = tuple(sorted(set(assignment.values())))
    infrastructure = sum(float(technologies[t].get("infrastructure_usd", 0)) for t in used)
    device_hardware = 0.0
    service = 0.0
    maintenance = 0.0
    for group, tech in assignment.items():
        count = int(groups[group]["count"])
        spec = technologies[tech]
        device_hardware += count * float(spec.get("hardware_usd", 0))
        service += count * years * float(spec.get("annual_service_usd", 0))
        maintenance += count * years * float(spec.get("annual_maintenance_usd", 0))
    penalty = (
        float(config.get("technology_complexity_penalty_usd", 0))
        if technology_complexity_penalty_usd is None
        else float(technology_complexity_penalty_usd)
    ) * len(used)
    breakdown = {
        "infrastructure": infrastructure,
        "device_hardware": device_hardware,
        "service": service,
        "maintenance": maintenance,
        "complexity_penalty": penalty,
    }
    return FleetSolution(assignment, sum(breakdown.values()), used, breakdown)


def optimise_fleet(
    config: dict,
    *,
    max_technologies: int | None = None,
    ownership: str | None = None,
    technology_complexity_penalty_usd: float | None = None,
    extra_feasibility: Callable[[dict[str, str]], bool] | None = None,
) -> FleetSolution:
    groups = list(config["device_groups"])
    choices = []
    for group in groups:
        feasible = list(config["device_groups"][group]["feasible"])
        if ownership:
            feasible = [
                tech for tech in feasible
                if config["technologies"][tech].get("ownership") == ownership
            ]
        if not feasible:
            raise ValueError(f"No feasible technologies for group {group}")
        choices.append(feasible)

    best: FleetSolution | None = None
    for combination in itertools.product(*choices):
        assignment = dict(zip(groups, combination))
        used = set(combination)
        if max_technologies is not None and len(used) > max_technologies:
            continue
        if extra_feasibility and not extra_feasibility(assignment):
            continue
        candidate = assignment_cost(
            assignment,
            config,
            technology_complexity_penalty_usd=technology_complexity_penalty_usd,
        )
        if best is None or candidate.total_cost_usd < best.total_cost_usd:
            best = candidate
    if best is None:
        raise ValueError("No feasible fleet assignment")
    return best


def load_fleet_config(path: str | Path = "configs/fleet.yml") -> dict:
    return load_yaml(path)
