from stackwise.optimizer import load_fleet_config, optimise_fleet


def test_optimizer_returns_feasible_assignment():
    config = load_fleet_config()
    solution = optimise_fleet(config)
    assert set(solution.assignment) == set(config["device_groups"])
    for group, technology in solution.assignment.items():
        assert technology in config["device_groups"][group]["feasible"]


def test_two_technology_constraint():
    solution = optimise_fleet(load_fleet_config(), max_technologies=2)
    assert len(solution.technologies_used) <= 2
