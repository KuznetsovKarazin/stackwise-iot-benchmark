from __future__ import annotations

import pandas as pd

from stackwise.vomhoff_evidence import build_vomhoff_stage2
from stackwise.vomhoff_uncertainty import build_vomhoff_uncertainty_calibration


def _row(*, figure: int, run: int, event: str, timestamp: str, duration: float, energy: float, obs: str, normalisation_rule: str = "none") -> dict:
    return {
        "dataset_id": "vomhoff_nbiot_ltem_energy_2023",
        "study_id": "vomhoff_2023",
        "source_file": f"energy_measurements_fig{figure}.csv",
        "source_figure": figure,
        "source_run": run,
        "source_event": event,
        "source_application_protocol": "http",
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
        "application_protocol": "HTTP",
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


def _source_rows(*, missing_alt_idle_last_run: bool = False) -> list[dict]:
    rows: list[dict] = []
    for run in range(1, 7):
        # Exact reuse across Figures 4 and 5 for non-Idle phases.
        for fig in (4, 5):
            rows.append(_row(
                figure=fig, run=run, event="Connection Establishment",
                timestamp=f"2023-01-{run:02d}T10:00:00.000Z",
                duration=1.0 + 0.01 * run, energy=0.4 + 0.01 * run,
                obs=f"f{fig}-r{run}-conn",
            ))
            rows.append(_row(
                figure=fig, run=run, event="Data Request",
                timestamp=f"2023-01-{run:02d}T10:00:05.000Z",
                duration=0.30, energy=0.10 + 0.002 * run,
                obs=f"f{fig}-r{run}-req1",
            ))
            rows.append(_row(
                figure=fig, run=run, event="Data Request",
                timestamp=f"2023-01-{run:02d}T10:00:05.300Z",
                duration=1.70, energy=0.60 + 0.004 * run,
                obs=f"f{fig}-r{run}-req2",
            ))
            rows.append(_row(
                figure=fig, run=run, event="Data Download",
                timestamp=f"2023-01-{run:02d}T10:00:10.000Z",
                duration=2.0 + 0.02 * run, energy=0.8 + 0.02 * run,
                obs=f"f{fig}-r{run}-down",
            ))
        rows.append(_row(
            figure=4, run=run, event="Idle",
            timestamp=f"2023-01-{run:02d}T10:00:20.000Z",
            duration=20.0, energy=0.30 + 0.003 * run,
            obs=f"f4-r{run}-idle", normalisation_rule="idle_20s",
        ))
        if not (missing_alt_idle_last_run and run == 6):
            rows.append(_row(
                figure=5, run=run, event="Idle",
                timestamp=f"2023-01-{run:02d}T10:00:20.000Z",
                duration=20.0, energy=0.25 + 0.002 * run,
                obs=f"f5-r{run}-idle", normalisation_rule="filtered_idle_20s",
            ))
    return rows


def test_vomhoff_uncertainty_reconciles_stage2_means_and_preserves_runs():
    logical, records, _, _ = build_vomhoff_stage2(pd.DataFrame(_source_rows()))
    samples, marginal, blocks, overlaps, dependence, summary = build_vomhoff_uncertainty_calibration(
        logical, records
    )

    assert summary["evidence_records_calibrated"] == len(records)
    assert summary["stage2_mean_reconciliation_errors"] == 0
    assert summary["duplicate_evidence_run_samples"] == 0
    assert summary["aleatory_run_variability_calibrated"] is True
    assert summary["parametric_distribution_fitted"] is False
    assert samples["physical_run_id"].nunique() == 6
    assert marginal["n_independent_runs"].min() == 6
    assert marginal["n_independent_runs"].max() == 6
    assert (marginal["sample_sd"] > 0).any()
    assert len(blocks) == 1
    assert bool(blocks.iloc[0]["complete_rectangular_run_set"]) is True
    assert summary["joint_block_bootstrap_authorised"] is True
    assert not overlaps.empty
    assert not dependence.empty


def test_partial_run_sets_block_joint_bootstrap_until_review():
    logical, records, _, _ = build_vomhoff_stage2(
        pd.DataFrame(_source_rows(missing_alt_idle_last_run=True))
    )
    _, marginal, blocks, overlaps, _, summary = build_vomhoff_uncertainty_calibration(
        logical, records
    )

    assert marginal["n_independent_runs"].min() == 5
    assert marginal["n_independent_runs"].max() == 6
    assert len(blocks) == 1
    assert bool(blocks.iloc[0]["complete_rectangular_run_set"]) is False
    assert blocks.iloc[0]["joint_resampling_status"] == "partial_overlap_review_required"
    assert summary["joint_block_bootstrap_authorised"] is False
    assert (overlaps["identical_run_set"] == False).any()  # noqa: E712
