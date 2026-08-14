import math
import pandas as pd

from stackwise.adapters.utils import integrate_trace
from stackwise.metrics import battery_life_years


def test_trace_integration_constant_power():
    result = integrate_trace(
        pd.Series([0.0, 1.0, 2.0]),
        current_a=pd.Series([0.1, 0.1, 0.1]),
        voltage_v=3.0,
    )
    assert math.isclose(result["energy_j"], 0.6, rel_tol=1e-9)
    assert result["sample_count"] == 3


def test_no_voltage_means_no_energy_guess():
    result = integrate_trace(
        pd.Series([0.0, 1.0]),
        current_a=pd.Series([0.1, 0.1]),
    )
    assert result["energy_j"] is None


def test_battery_planning_cap():
    ideal, planning = battery_life_years(
        capacity_wh=10,
        report_energy_j=0.001,
        reports_per_day=1,
        planning_cap_years=10,
    )
    assert ideal > 10
    assert planning == 10
