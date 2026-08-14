from stackwise.optimizer import load_fleet_config, optimise_fleet

solution = optimise_fleet(load_fleet_config())
print(solution)
