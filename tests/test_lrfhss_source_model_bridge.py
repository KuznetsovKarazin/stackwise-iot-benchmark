from __future__ import annotations

import math

from stackwise.lrfhss_source_model import (
    airtime_breakdown,
    confirmed_expected_incremental_radio_energy_j,
    unconfirmed_incremental_radio_energy_j,
)


def test_table6_numeric_convention_reproduces_source_rows() -> None:
    cases = [
        (1, 8, 700.4, 870.4, 2.475, 1573.3),
        (50, 8, 700.4, 3379.2, 7.875, 4087.5),
        (1, 9, 466.9, 435.2, 1.350, 903.5),
        (115, 9, 466.9, 3353.6, 7.650, 3828.2),
    ]
    for payload, dr, header, body, hops, total in cases:
        a = airtime_breakdown(payload, dr)
        assert round(a.header_duration_s * 1000, 1) == header
        assert round(a.payload_duration_s * 1000, 1) == body
        assert round(a.hop_duration_s * 1000, 3) == hops
        assert round(a.tx_total_duration_s * 1000, 1) == total


def test_rendered_eq6_and_table6_operationalisation_are_kept_distinct() -> None:
    a = airtime_breakdown(50, 8)
    assert not math.isclose(a.payload_duration_s, a.rendered_eq6_payload_duration_s)
    assert math.isclose(a.payload_duration_s * 1000, 3379.2, abs_tol=1e-9)
    assert math.isclose(a.rendered_eq6_payload_duration_s * 1000, 3366.4, abs_tol=1e-9)


def test_4byte_unconfirmed_reference_energies() -> None:
    assert math.isclose(unconfirmed_incremental_radio_energy_j(4, 8), 0.1522310339781, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(unconfirmed_incremental_radio_energy_j(4, 9), 0.0880272301194, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(unconfirmed_incremental_radio_energy_j(4, 10), 0.1522310339781, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(unconfirmed_incremental_radio_energy_j(4, 11), 0.0880272301194, rel_tol=0, abs_tol=1e-12)


def test_4byte_confirmed_expected_reference_energies() -> None:
    assert math.isclose(confirmed_expected_incremental_radio_energy_j(4, 8), 0.1639129851381, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(confirmed_expected_incremental_radio_energy_j(4, 9), 0.0974116223619, rel_tol=0, abs_tol=1e-12)


def test_16byte_unconfirmed_component_values_cross_budget_by_dr_family() -> None:
    e8 = unconfirmed_incremental_radio_energy_j(16, 8)
    e9 = unconfirmed_incremental_radio_energy_j(16, 9)
    assert math.isclose(e8, 0.2043920784906, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(e9, 0.11410775237565, rel_tol=0, abs_tol=1e-12)
    assert e8 > 0.2
    assert e9 < 0.2
