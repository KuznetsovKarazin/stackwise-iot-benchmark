from __future__ import annotations

import pandas as pd

from stackwise.fleet_portfolio import build_fleet_portfolio_experiment


def _fixture():
    stacks = pd.DataFrame([
        {"stack_id": "a", "name": "A", "primary_access_component_id": "3gpp_ltem_eps_ip"},
        {"stack_id": "b", "name": "B", "primary_access_component_id": "lorawan_lora_access"},
        {"stack_id": "c", "name": "C", "primary_access_component_id": "thread_ipv6_mesh"},
    ])
    rows = []
    matrix = {
        "s1": {"a": "feasible", "b": "infeasible", "c": "infeasible"},
        "s2": {"a": "feasible", "b": "feasible", "c": "infeasible"},
        "s3": {"a": "infeasible", "b": "feasible", "c": "infeasible"},
        "s4": {"a": "infeasible", "b": "infeasible", "c": "unresolved"},
    }
    for scenario, vals in matrix.items():
        for stack, status in vals.items():
            rows.append({"scenario_id": scenario, "stack_id": stack, "status": status})
    return pd.DataFrame(rows), stacks


def test_strict_set_cover_and_unresolved_sensitivity_are_separated():
    feasibility, stacks = _fixture()
    tables, summary = build_fleet_portfolio_experiment(feasibility, stacks)
    assert summary.total_scenarios == 4
    assert summary.strict_serviceable_scenarios == 3
    assert summary.unresolved_only_scenarios == 1
    assert summary.strict_best_single_stack_coverage == 2
    assert summary.strict_min_stacks_for_complete_coverage == 2
    assert summary.optimistic_min_stacks_for_complete_coverage == 3
    s4 = tables["scenario_serviceability"].set_index("scenario_id").loc["s4"]
    assert not bool(s4.strict_serviceable)
    assert bool(s4.optimistic_serviceable_if_unresolved_closes_positive)


def test_portfolio_fractions_are_not_probabilities():
    feasibility, stacks = _fixture()
    tables, _ = build_fleet_portfolio_experiment(feasibility, stacks)
    assert tables["portfolio_frontier"]["probability_interpretation"].eq(False).all()
    assert tables["optimal_portfolios"]["probability_interpretation"].eq(False).all()


def test_access_technology_portfolio_preserves_radio_distinctions():
    feasibility, stacks = _fixture()
    tables, _ = build_fleet_portfolio_experiment(feasibility, stacks)
    techs = set(tables["technology_coverage"]["access_technology"])
    assert techs == {"LTE-M", "LoRaWAN-LoRa", "Thread"}
