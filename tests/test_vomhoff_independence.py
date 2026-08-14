from __future__ import annotations

import pandas as pd

from stackwise.vomhoff_independence import audit_vomhoff_independence


def _row(*, figure: int, source_file: str, event: str, timestamp: str,
         duration: float, energy: float, obs: str) -> dict:
    return {
        "dataset_id": "vomhoff_nbiot_ltem_energy_2023",
        "study_id": "vomhoff_2023",
        "source_file": source_file,
        "source_figure": figure,
        "source_run": 2,
        "source_event": event,
        "source_application_protocol": "http",
        "source_data_object": "1K.data",
        "source_diff_time_s": duration,
        "technology": "NB-IoT",
        "energy_j": energy,
        "duration_s": duration,
        "raw_energy_j": energy,
        "raw_duration_s": duration,
        "normalisation_rule": "none",
        "timestamp_utc": timestamp,
        "observation_id": obs,
        "access_network": "NB-IoT",
        "application_protocol": "HTTP",
        "payload_bytes": 1024,
        "direction": "uplink",
        "measurement_boundary": "transfer",
        "evidence_grade": "A",
        "source_license": "CC BY 4.0",
        "source_doi": "10.5281/zenodo.7603641",
    }


def test_contiguous_data_request_is_additive_and_cross_figure_reuse_detected():
    rows = []
    for fig in (4, 5):
        sf = f"energy_measurements_fig{fig}.csv"
        rows.extend([
            _row(figure=fig, source_file=sf, event="Connection Establishment",
                 timestamp="2023-01-17T16:05:20.000Z", duration=1.0, energy=0.5,
                 obs=f"f{fig}-conn"),
            _row(figure=fig, source_file=sf, event="Data Request",
                 timestamp="2023-01-17T16:05:25.584Z", duration=0.294158, energy=0.105,
                 obs=f"f{fig}-req1"),
            _row(figure=fig, source_file=sf, event="Data Request",
                 timestamp="2023-01-17T16:05:25.879Z", duration=1.836121, energy=0.685,
                 obs=f"f{fig}-req2"),
            _row(figure=fig, source_file=sf, event="Data Download",
                 timestamp="2023-01-17T16:05:30.000Z", duration=2.0, energy=0.9,
                 obs=f"f{fig}-down"),
        ])
    summary, adjacency, exact, run_pairs = audit_vomhoff_independence(pd.DataFrame(rows))
    assert summary["within_source_figure_additive_aggregation_authorised"] is True
    assert summary["adjacency_pairs"] == 2
    assert summary["all_multi_segment_pairs_adjacent"] is True
    assert summary["exact_cross_figure_segment_signatures"] == 4
    assert len(run_pairs) == 1
    assert bool(run_pairs.iloc[0]["strong_source_reuse_flag"]) is True
    assert int(run_pairs.iloc[0]["shared_event_count"]) == 3
    assert len(exact) == 8


def test_nonadjacent_repeated_segment_blocks_additive_authorisation():
    sf = "energy_measurements_fig4.csv"
    rows = [
        _row(figure=4, source_file=sf, event="Data Request",
             timestamp="2023-01-17T16:05:25.000Z", duration=0.3, energy=0.1,
             obs="a"),
        _row(figure=4, source_file=sf, event="Data Request",
             timestamp="2023-01-17T16:05:26.000Z", duration=0.4, energy=0.2,
             obs="b"),
    ]
    summary, adjacency, _, _ = audit_vomhoff_independence(pd.DataFrame(rows))
    assert summary["within_source_figure_additive_aggregation_authorised"] is False
    assert summary["all_multi_segment_pairs_adjacent"] is False
    assert not bool(adjacency.iloc[0]["within_adjacency_tolerance"])
