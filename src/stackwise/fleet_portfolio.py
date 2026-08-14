from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class FleetPortfolioSummary:
    total_scenarios: int
    strict_serviceable_scenarios: int
    unresolved_only_scenarios: int
    strict_best_single_stack_coverage: int
    strict_best_single_technology_coverage: int
    strict_best_single_family_coverage: int
    strict_min_stacks_for_complete_coverage: int | None
    strict_min_technologies_for_complete_coverage: int | None
    strict_min_families_for_complete_coverage: int | None
    optimistic_min_stacks_for_complete_coverage: int | None
    optimistic_min_technologies_for_complete_coverage: int | None
    optimistic_min_families_for_complete_coverage: int | None


def _require(df: pd.DataFrame, cols: set[str], label: str) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")


def derive_access_technology(primary_access_component_id: str) -> str:
    value = str(primary_access_component_id)
    if "nbiot" in value:
        return "NB-IoT"
    if "ltem" in value:
        return "LTE-M"
    if value == "lorawan_lora_access":
        return "LoRaWAN-LoRa"
    if value == "lorawan_lrfhss_access":
        return "LoRaWAN-LR-FHSS"
    if "thread" in value:
        return "Thread"
    return value


def derive_access_family(access_technology: str) -> str:
    if access_technology in {"NB-IoT", "LTE-M"}:
        return "cellular"
    if access_technology in {"LoRaWAN-LoRa", "LoRaWAN-LR-FHSS"}:
        return "lorawan"
    if access_technology == "Thread":
        return "thread"
    return access_technology


def _coverage_sets(
    feasibility: pd.DataFrame,
    entities: pd.DataFrame,
    *,
    entity_col: str,
    statuses: set[str],
) -> dict[str, set[str]]:
    if entity_col == "stack_id":
        merged = feasibility.copy()
    else:
        merged = feasibility.drop(columns=[entity_col], errors="ignore").merge(
            entities[["stack_id", entity_col]], on="stack_id", validate="many_to_one"
        )
    out: dict[str, set[str]] = {}
    for entity, grp in merged.groupby(entity_col, sort=True):
        out[str(entity)] = set(grp.loc[grp["status"].isin(statuses), "scenario_id"].astype(str))
    return out


def _portfolio_frontier(
    coverage: dict[str, set[str]],
    universe: set[str],
    *,
    universe_mode: str,
    entity_level: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    entities = sorted(coverage)
    frontier_rows: list[dict[str, object]] = []
    optimal_rows: list[dict[str, object]] = []
    if not entities:
        return pd.DataFrame(), pd.DataFrame()

    first_complete: int | None = None
    for k in range(1, len(entities) + 1):
        combos: list[tuple[tuple[str, ...], set[str]]] = []
        max_covered = -1
        for combo in itertools.combinations(entities, k):
            covered = set().union(*(coverage[e] for e in combo)) & universe
            n = len(covered)
            if n > max_covered:
                max_covered = n
                combos = [(combo, covered)]
            elif n == max_covered:
                combos.append((combo, covered))
        complete = max_covered == len(universe)
        if complete and first_complete is None:
            first_complete = k
        frontier_rows.append({
            "universe_mode": universe_mode,
            "entity_level": entity_level,
            "portfolio_size": k,
            "universe_scenarios": len(universe),
            "max_covered_scenarios": max_covered,
            "serviceability_fraction": (max_covered / len(universe)) if universe else 0.0,
            "serviceability_loss_scenarios": len(universe) - max_covered,
            "serviceability_loss_fraction": ((len(universe) - max_covered) / len(universe)) if universe else 0.0,
            "complete_coverage_achieved": complete,
            "number_of_maximizing_portfolios": len(combos),
            "minimum_complete_portfolio_size": first_complete if first_complete is not None else pd.NA,
            "probability_interpretation": False,
        })
        for combo, covered in combos:
            optimal_rows.append({
                "universe_mode": universe_mode,
                "entity_level": entity_level,
                "portfolio_size": k,
                "is_minimum_complete_portfolio": bool(complete and first_complete == k),
                "portfolio_members": "|".join(combo),
                "covered_scenario_count": len(covered),
                "covered_scenarios": "|".join(sorted(covered)),
                "uncovered_scenario_count": len(universe - covered),
                "uncovered_scenarios": "|".join(sorted(universe - covered)),
                "probability_interpretation": False,
            })
        if complete:
            # Once full coverage is achieved, larger portfolios add no information about the
            # minimum-complexity frontier needed for this experiment.
            break
    return pd.DataFrame(frontier_rows), pd.DataFrame(optimal_rows)


def build_fleet_portfolio_experiment(
    feasibility: pd.DataFrame,
    candidate_stacks: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], FleetPortfolioSummary]:
    _require(feasibility, {"scenario_id", "stack_id", "status"}, "feasibility matrix")
    _require(candidate_stacks, {"stack_id", "primary_access_component_id", "name"}, "candidate stack catalog")

    statuses = set(feasibility["status"].astype(str).unique())
    unexpected = statuses - {"feasible", "infeasible", "unresolved"}
    if unexpected:
        raise ValueError(f"Unexpected feasibility statuses: {sorted(unexpected)}")
    if feasibility.duplicated(["scenario_id", "stack_id"]).any():
        raise ValueError("Feasibility matrix has duplicate scenario/stack pairs")

    stacks = candidate_stacks.copy()
    stacks["access_technology"] = stacks["primary_access_component_id"].map(derive_access_technology)
    stacks["access_family"] = stacks["access_technology"].map(derive_access_family)

    all_scenarios = set(feasibility["scenario_id"].astype(str))
    strict_serviceable = set(feasibility.loc[feasibility["status"].eq("feasible"), "scenario_id"].astype(str))
    optimistic_serviceable = set(feasibility.loc[feasibility["status"].isin(["feasible", "unresolved"]), "scenario_id"].astype(str))
    unresolved_only = optimistic_serviceable - strict_serviceable

    # Scenario-level serviceability audit.
    scenario_rows: list[dict[str, object]] = []
    lookup = stacks.set_index("stack_id")
    for scenario_id, grp in feasibility.groupby("scenario_id", sort=True):
        feasible_stacks = sorted(grp.loc[grp.status.eq("feasible"), "stack_id"].astype(str))
        unresolved_stacks = sorted(grp.loc[grp.status.eq("unresolved"), "stack_id"].astype(str))
        feasible_techs = sorted({lookup.loc[s, "access_technology"] for s in feasible_stacks})
        unresolved_techs = sorted({lookup.loc[s, "access_technology"] for s in unresolved_stacks})
        scenario_rows.append({
            "scenario_id": scenario_id,
            "feasible_stack_count": len(feasible_stacks),
            "unresolved_stack_count": len(unresolved_stacks),
            "strict_serviceable": bool(feasible_stacks),
            "optimistic_serviceable_if_unresolved_closes_positive": bool(feasible_stacks or unresolved_stacks),
            "feasible_stacks": "|".join(feasible_stacks),
            "unresolved_stacks": "|".join(unresolved_stacks),
            "feasible_access_technologies": "|".join(feasible_techs),
            "unresolved_access_technologies": "|".join(unresolved_techs),
        })
    scenario_serviceability = pd.DataFrame(scenario_rows)

    stack_strict = _coverage_sets(feasibility, stacks, entity_col="stack_id", statuses={"feasible"})
    stack_opt = _coverage_sets(feasibility, stacks, entity_col="stack_id", statuses={"feasible", "unresolved"})
    tech_strict = _coverage_sets(feasibility, stacks, entity_col="access_technology", statuses={"feasible"})
    tech_opt = _coverage_sets(feasibility, stacks, entity_col="access_technology", statuses={"feasible", "unresolved"})
    fam_strict = _coverage_sets(feasibility, stacks, entity_col="access_family", statuses={"feasible"})
    fam_opt = _coverage_sets(feasibility, stacks, entity_col="access_family", statuses={"feasible", "unresolved"})

    stack_rows: list[dict[str, object]] = []
    stack_meta = stacks.set_index("stack_id")
    for stack_id in sorted(stack_strict):
        strict_cov = stack_strict[stack_id] & strict_serviceable
        opt_cov = stack_opt[stack_id] & optimistic_serviceable
        stack_rows.append({
            "stack_id": stack_id,
            "name": stack_meta.loc[stack_id, "name"],
            "access_technology": stack_meta.loc[stack_id, "access_technology"],
            "access_family": stack_meta.loc[stack_id, "access_family"],
            "strict_covered_scenarios": len(strict_cov),
            "strict_serviceability_fraction": len(strict_cov) / len(strict_serviceable) if strict_serviceable else 0.0,
            "strict_scenarios": "|".join(sorted(strict_cov)),
            "optimistic_covered_scenarios": len(opt_cov),
            "optimistic_scenarios": "|".join(sorted(opt_cov)),
        })
    stack_coverage = pd.DataFrame(stack_rows).sort_values(["strict_covered_scenarios", "stack_id"], ascending=[False, True])

    tech_rows = []
    for tech in sorted(tech_strict):
        sc = tech_strict[tech] & strict_serviceable
        oc = tech_opt[tech] & optimistic_serviceable
        tech_rows.append({
            "access_technology": tech,
            "access_family": derive_access_family(tech),
            "candidate_stack_count": int(stacks["access_technology"].eq(tech).sum()),
            "strict_covered_scenarios": len(sc),
            "strict_serviceability_fraction": len(sc) / len(strict_serviceable) if strict_serviceable else 0.0,
            "strict_scenarios": "|".join(sorted(sc)),
            "optimistic_covered_scenarios": len(oc),
            "optimistic_scenarios": "|".join(sorted(oc)),
        })
    technology_coverage = pd.DataFrame(tech_rows).sort_values(["strict_covered_scenarios", "access_technology"], ascending=[False, True])

    family_rows = []
    for fam in sorted(fam_strict):
        sc = fam_strict[fam] & strict_serviceable
        oc = fam_opt[fam] & optimistic_serviceable
        family_rows.append({
            "access_family": fam,
            "candidate_stack_count": int(stacks["access_family"].eq(fam).sum()),
            "strict_covered_scenarios": len(sc),
            "strict_serviceability_fraction": len(sc) / len(strict_serviceable) if strict_serviceable else 0.0,
            "strict_scenarios": "|".join(sorted(sc)),
            "optimistic_covered_scenarios": len(oc),
            "optimistic_scenarios": "|".join(sorted(oc)),
        })
    family_coverage = pd.DataFrame(family_rows).sort_values(["strict_covered_scenarios", "access_family"], ascending=[False, True])

    frontier_frames: list[pd.DataFrame] = []
    optimal_frames: list[pd.DataFrame] = []
    specs = [
        ("STRICT_FEASIBLE_ONLY", "stack", stack_strict, strict_serviceable),
        ("STRICT_FEASIBLE_ONLY", "access_technology", tech_strict, strict_serviceable),
        ("STRICT_FEASIBLE_ONLY", "access_family", fam_strict, strict_serviceable),
        ("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "stack", stack_opt, optimistic_serviceable),
        ("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "access_technology", tech_opt, optimistic_serviceable),
        ("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "access_family", fam_opt, optimistic_serviceable),
    ]
    for mode, level, coverage, universe in specs:
        frontier, optimal = _portfolio_frontier(coverage, universe, universe_mode=mode, entity_level=level)
        frontier_frames.append(frontier)
        optimal_frames.append(optimal)
    portfolio_frontier = pd.concat(frontier_frames, ignore_index=True)
    optimal_portfolios = pd.concat(optimal_frames, ignore_index=True)

    def _frontier_value(mode: str, level: str, size: int, field: str) -> int:
        row = portfolio_frontier[
            portfolio_frontier.universe_mode.eq(mode)
            & portfolio_frontier.entity_level.eq(level)
            & portfolio_frontier.portfolio_size.eq(size)
        ]
        if row.empty:
            return 0
        return int(row.iloc[0][field])

    def _min_complete(mode: str, level: str) -> int | None:
        rows = portfolio_frontier[
            portfolio_frontier.universe_mode.eq(mode)
            & portfolio_frontier.entity_level.eq(level)
            & portfolio_frontier.complete_coverage_achieved.eq(True)
        ]
        if rows.empty:
            return None
        return int(rows.portfolio_size.min())

    summary = FleetPortfolioSummary(
        total_scenarios=len(all_scenarios),
        strict_serviceable_scenarios=len(strict_serviceable),
        unresolved_only_scenarios=len(unresolved_only),
        strict_best_single_stack_coverage=_frontier_value("STRICT_FEASIBLE_ONLY", "stack", 1, "max_covered_scenarios"),
        strict_best_single_technology_coverage=_frontier_value("STRICT_FEASIBLE_ONLY", "access_technology", 1, "max_covered_scenarios"),
        strict_best_single_family_coverage=_frontier_value("STRICT_FEASIBLE_ONLY", "access_family", 1, "max_covered_scenarios"),
        strict_min_stacks_for_complete_coverage=_min_complete("STRICT_FEASIBLE_ONLY", "stack"),
        strict_min_technologies_for_complete_coverage=_min_complete("STRICT_FEASIBLE_ONLY", "access_technology"),
        strict_min_families_for_complete_coverage=_min_complete("STRICT_FEASIBLE_ONLY", "access_family"),
        optimistic_min_stacks_for_complete_coverage=_min_complete("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "stack"),
        optimistic_min_technologies_for_complete_coverage=_min_complete("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "access_technology"),
        optimistic_min_families_for_complete_coverage=_min_complete("OPTIMISTIC_FEASIBLE_PLUS_UNRESOLVED", "access_family"),
    )

    return {
        "scenario_serviceability": scenario_serviceability,
        "stack_coverage": stack_coverage,
        "technology_coverage": technology_coverage,
        "family_coverage": family_coverage,
        "portfolio_frontier": portfolio_frontier,
        "optimal_portfolios": optimal_portfolios,
    }, summary
