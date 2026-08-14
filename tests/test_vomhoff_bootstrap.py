from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from stackwise.vomhoff_bootstrap import build_vomhoff_joint_bootstrap


def _policy(tmp_path: Path, replicates: int = 500) -> Path:
    path = tmp_path / "policy.yml"
    path.write_text(yaml.safe_dump({
        "version": 1,
        "replicates": replicates,
        "master_seed": 20260811,
        "resampling_unit": "physical_run_id",
        "partial_overlap_policy": "union_run_resampling_preserve_structural_missingness",
    }), encoding="utf-8")
    return path


def _inputs(partial: bool = False):
    block_id = "block-a"
    rows = []
    evidence = ["energy", "duration", "download_energy"]
    for run in range(1, 7):
        rows.append({"evidence_id": "energy", "metric_id": "device_phase_energy_j", "physical_run_id": f"r{run}", "experimental_block_id": block_id, "value": 1.0 + run})
        rows.append({"evidence_id": "duration", "metric_id": "device_phase_duration_s", "physical_run_id": f"r{run}", "experimental_block_id": block_id, "value": 10.0 + 2 * run})
        if not (partial and run == 6):
            rows.append({"evidence_id": "download_energy", "metric_id": "device_phase_energy_j", "physical_run_id": f"r{run}", "experimental_block_id": block_id, "value": 0.2 + 0.1 * run})
    samples = pd.DataFrame(rows)
    counts = samples.groupby("evidence_id")["physical_run_id"].nunique()
    means = samples.groupby("evidence_id")["value"].mean()
    marginal = pd.DataFrame({"evidence_id": evidence, "mean": [means[e] for e in evidence]})
    blocks = pd.DataFrame([{
        "experimental_block_id": block_id,
        "n_physical_runs_union": 6,
        "n_evidence_records": 3,
        "complete_rectangular_run_set": not partial,
        "joint_resampling_status": "ready_complete_rectangular" if not partial else "partial_overlap_review_required",
    }])
    return samples, blocks, marginal, counts


def test_rectangular_joint_bootstrap_is_deterministic_and_shared(tmp_path: Path):
    samples, blocks, marginal, _ = _inputs(partial=False)
    policy = _policy(tmp_path)
    out1 = build_vomhoff_joint_bootstrap(samples, blocks, marginal, policy_path=policy)
    out2 = build_vomhoff_joint_bootstrap(samples, blocks, marginal, policy_path=policy)
    draws1, summary1, block_policy1, sensitivity1, dependence1, meta1 = out1
    draws2 = out2[0]

    pd.testing.assert_frame_equal(draws1, draws2)
    assert meta1["joint_within_block_bootstrap_materialised"] is True
    assert meta1["cross_block_joint_distribution_asserted"] is False
    assert meta1["structural_missingness_imputed"] is False
    assert meta1["listwise_deletion_used"] is False
    assert len(draws1) == 3 * 500
    assert summary1["bootstrap_observed_positions_min"].min() == 6
    assert summary1["bootstrap_observed_positions_max"].max() == 6
    assert bool(block_policy1.iloc[0]["complete_rectangular_run_set"]) is True
    assert sensitivity1["n_complete_case_runs"].min() == 6
    assert not dependence1.empty

    # duration is an affine transform of energy and must preserve perfect shared-run dependence.
    pair = dependence1.loc[
        ((dependence1["evidence_id_a"] == "duration") & (dependence1["evidence_id_b"] == "energy")) |
        ((dependence1["evidence_id_a"] == "energy") & (dependence1["evidence_id_b"] == "duration"))
    ].iloc[0]
    assert np.isclose(pair["bootstrap_mean_pearson_r"], 1.0)


def test_partial_overlap_preserves_missingness_without_listwise_deletion(tmp_path: Path):
    samples, blocks, marginal, counts = _inputs(partial=True)
    policy = _policy(tmp_path, replicates=1000)
    draws, summary, block_policy, sensitivity, _, meta = build_vomhoff_joint_bootstrap(
        samples, blocks, marginal, policy_path=policy
    )

    assert meta["partial_overlap_blocks"] == 1
    assert meta["partial_overlap_union_runs"] == 6
    assert meta["partial_overlap_complete_case_runs"] == 5
    assert meta["structural_missingness_imputed"] is False
    assert meta["listwise_deletion_used"] is False
    assert block_policy.iloc[0]["bootstrap_policy"] == "union_run_resampling_preserve_structural_missingness"

    dsum = summary.loc[summary["evidence_id"] == "download_energy"].iloc[0]
    assert dsum["n_original_runs"] == 5
    assert dsum["n_block_union_runs"] == 6
    assert dsum["bootstrap_observed_positions_min"] < 6
    assert dsum["bootstrap_observed_positions_max"] <= 6

    # Records observed on all six runs remain six-position statistics; no listwise drop to five.
    esum = summary.loc[summary["evidence_id"] == "energy"].iloc[0]
    assert esum["n_original_runs"] == 6
    assert esum["bootstrap_observed_positions_min"] == 6
    assert esum["bootstrap_observed_positions_max"] == 6
    assert sensitivity.loc[sensitivity["evidence_id"] == "energy", "n_complete_case_runs"].iloc[0] == 5

    # The partial record has exactly its original available-case point estimate.
    assert np.isclose(dsum["point_estimate"], marginal.set_index("evidence_id").loc["download_energy", "mean"])
    assert len(draws) == 3 * 1000
