
from __future__ import annotations

import pandas as pd

from stackwise.vomhoff_evidence import (
    CANONICAL_ROLE,
    FIGURE5_HTTP_IDLE_ALTERNATE,
    FIGURE5_MQTT_IDLE_EXCLUSION,
    build_vomhoff_stage2,
)


def _row(
    *,
    figure: int,
    run: int,
    protocol: str,
    event: str,
    timestamp: str,
    duration: float,
    energy: float,
    obs: str,
    normalisation_rule: str = "none",
) -> dict:
    return {
        "dataset_id": "vomhoff_nbiot_ltem_energy_2023",
        "study_id": "vomhoff_2023",
        "source_file": f"energy_measurements_fig{figure}.csv",
        "source_figure": figure,
        "source_run": run,
        "source_event": event,
        "source_application_protocol": protocol,
        "source_data_object": "1K.data",
        "source_diff_time_s": duration,
        "technology": "NB-IoT",
        "energy_j": energy,
        "duration_s": duration,
        "raw_energy_j": energy,
        "raw_duration_s": duration,
        "normalisation_rule": normalisation_rule,
        "timestamp_utc": timestamp,
        "observation_id": obs,
        "access_network": "NB-IoT",
        "transport_protocol": None,
        "application_protocol": protocol.upper(),
        "security_mode": None,
        "payload_bytes": 1024,
        "direction": "uplink",
        "measurement_boundary": "transfer",
        "evidence_grade": "A",
        "source_license": "CC-BY-4.0",
        "source_doi": "10.5281/zenodo.7603641",
        "environment": "laboratory",
        "charge_as": energy / 3.3,
        "sample_count": int(round(duration / 0.005)),
    }


def _shared_http_rows() -> list[dict]:
    rows = []
    # Non-Idle phases are exact duplicates across Figures 4 and 5.
    for fig in (4, 5):
        rows.extend(
            [
                _row(
                    figure=fig, run=2, protocol="http",
                    event="Connection Establishment",
                    timestamp="2023-01-17T16:05:20.000Z",
                    duration=1.0, energy=0.5, obs=f"f{fig}-conn",
                ),
                _row(
                    figure=fig, run=2, protocol="http",
                    event="Data Request",
                    timestamp="2023-01-17T16:05:25.584Z",
                    duration=0.294158, energy=0.105, obs=f"f{fig}-req1",
                ),
                _row(
                    figure=fig, run=2, protocol="http",
                    event="Data Request",
                    timestamp="2023-01-17T16:05:25.879Z",
                    duration=1.836121, energy=0.685, obs=f"f{fig}-req2",
                ),
                _row(
                    figure=fig, run=2, protocol="http",
                    event="Data Download",
                    timestamp="2023-01-17T16:05:30.000Z",
                    duration=2.0, energy=0.9, obs=f"f{fig}-down",
                ),
            ]
        )
    # Same physical run, but deliberately different source-defined Idle derivations.
    rows.append(
        _row(
            figure=4, run=2, protocol="http", event="Idle",
            timestamp="2023-01-17T16:05:40.000Z",
            duration=20.0, energy=0.4, obs="f4-idle",
            normalisation_rule="idle_20s",
        )
    )
    rows.append(
        _row(
            figure=5, run=2, protocol="http", event="Idle",
            timestamp="2023-01-17T16:05:40.000Z",
            duration=20.0, energy=0.3, obs="f5-idle",
            normalisation_rule="filtered_idle_20s",
        )
    )
    return rows


def test_materialisation_sums_data_request_and_collapses_reused_non_idle_views():
    logical, records, comparison, summary = build_vomhoff_stage2(
        pd.DataFrame(_shared_http_rows())
    )

    req = logical.loc[logical["source_event"].eq("Data Request")]
    assert len(req) == 1
    assert abs(float(req.iloc[0]["energy_j"]) - 0.790) < 1e-12
    assert int(req.iloc[0]["source_view_count"]) == 2
    assert req.iloc[0]["source_figure_contexts"] == "4|5"

    idle = logical.loc[logical["source_event"].eq("Idle")]
    assert len(idle) == 2
    assert set(idle["analysis_role"]) == {CANONICAL_ROLE, FIGURE5_HTTP_IDLE_ALTERNATE}
    assert idle["physical_run_id"].nunique() == 1

    assert summary["cross_figure_phase_views_collapsed"] == 3
    assert summary["alternate_figure5_http_idle_rows"] == 1
    assert summary["excluded_figure5_mqtt_idle_rows"] == 0
    assert {r["metric_id"] for r in records} == {
        "device_phase_energy_j", "device_phase_duration_s"
    }

    dr_cmp = comparison.loc[
        comparison["source_event"].eq("Data Request")
        & comparison["source_figure"].eq(4)
    ].iloc[0]
    assert int(dr_cmp["source_segment_n"]) == 2
    assert int(dr_cmp["logical_run_phase_n"]) == 1
    assert float(dr_cmp["logical_run_phase_mean_energy_j"]) > float(
        dr_cmp["source_segment_mean_energy_j"]
    )


def test_figure5_mqtt_idle_is_retained_but_not_evidence_eligible():
    rows = _shared_http_rows()
    rows.extend(
        [
            _row(
                figure=5, run=101, protocol="mqtt", event="Connection Establishment",
                timestamp="2023-01-18T10:00:00.000Z",
                duration=1.2, energy=0.6, obs="mqtt-conn",
            ),
            _row(
                figure=5, run=101, protocol="mqtt", event="Idle",
                timestamp="2023-01-18T10:00:10.000Z",
                duration=20.0, energy=0.2, obs="mqtt-idle",
                normalisation_rule="filtered_idle_20s",
            ),
        ]
    )
    logical, records, _, summary = build_vomhoff_stage2(pd.DataFrame(rows))
    mqtt_idle = logical.loc[
        logical["source_application_protocol"].eq("mqtt")
        & logical["source_event"].eq("Idle")
    ]
    assert len(mqtt_idle) == 1
    assert mqtt_idle.iloc[0]["analysis_role"] == FIGURE5_MQTT_IDLE_EXCLUSION
    assert bool(mqtt_idle.iloc[0]["evidence_eligible"]) is False
    assert summary["excluded_figure5_mqtt_idle_rows"] == 1

    assert not any(
        "protocol=mqtt" in r["applicability_domain"] and "phase=Idle" in r["applicability_domain"]
        for r in records
    )
