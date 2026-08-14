import numpy as np
import pandas as pd

from stackwise.mcda import feasibility_filter, run_smaa


def test_hard_constraints_are_not_compensated():
    capabilities = pd.DataFrame({"wide_area": [1, 0], "battery": [3, 5]}, index=["A", "B"])
    feasible = feasibility_filter(capabilities, {"wide_area": 1, "min_battery": 2})
    assert feasible.to_dict() == {"A": True, "B": False}


def test_rank_acceptability_rows_sum_to_one():
    means = pd.DataFrame({"c1": [0.8, 0.5], "c2": [0.4, 0.9]}, index=["A", "B"])
    result = run_smaa(means, samples=1000, seed=1)
    assert np.allclose(result.rank_acceptability.sum(axis=1), 1.0)
