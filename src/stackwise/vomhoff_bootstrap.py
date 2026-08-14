from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

DEFAULT_POLICY = Path("datasets/vomhoff_bootstrap_policy.yml")


class VomhoffBootstrapError(RuntimeError):
    pass


def load_bootstrap_policy(path: str | Path = DEFAULT_POLICY) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VomhoffBootstrapError("Vomhoff bootstrap policy must be a mapping")
    required = {"replicates", "master_seed", "resampling_unit", "partial_overlap_policy"}
    missing = sorted(required - set(value))
    if missing:
        raise VomhoffBootstrapError(f"Bootstrap policy missing fields: {missing}")
    if int(value["replicates"]) < 100:
        raise VomhoffBootstrapError("Bootstrap replicates must be >= 100")
    if str(value["resampling_unit"]) != "physical_run_id":
        raise VomhoffBootstrapError("Only physical_run_id resampling is authorised")
    if str(value["partial_overlap_policy"]) != "union_run_resampling_preserve_structural_missingness":
        raise VomhoffBootstrapError("Unsupported partial-overlap policy")
    return value


def _block_seed(master_seed: int, block_id: str) -> int:
    digest = hashlib.sha256(f"{master_seed}|{block_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def _q(values: np.ndarray, q: float) -> float:
    return float(np.quantile(values, q, method="linear"))


def build_vomhoff_joint_bootstrap(
    samples: pd.DataFrame,
    blocks: pd.DataFrame,
    marginal: pd.DataFrame,
    *,
    policy_path: str | Path = DEFAULT_POLICY,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Materialise block-wise nonparametric bootstrap distributions for Vomhoff means.

    Replicate indices are meaningful only within an experimental block. No cross-block
    joint distribution is asserted. Four rectangular blocks use the usual shared physical-run
    resample. Partial-overlap blocks use the union run set and preserve the observed structural
    missingness without imputation or listwise deletion.
    """
    policy = load_bootstrap_policy(policy_path)
    n_boot = int(policy["replicates"])
    master_seed = int(policy["master_seed"])

    required_samples = {
        "evidence_id", "metric_id", "physical_run_id", "experimental_block_id", "value"
    }
    missing_samples = sorted(required_samples - set(samples.columns))
    if missing_samples:
        raise VomhoffBootstrapError(f"run_level_samples missing columns: {missing_samples}")
    required_blocks = {
        "experimental_block_id", "n_physical_runs_union", "n_evidence_records",
        "complete_rectangular_run_set", "joint_resampling_status",
    }
    missing_blocks = sorted(required_blocks - set(blocks.columns))
    if missing_blocks:
        raise VomhoffBootstrapError(f"resampling_blocks missing columns: {missing_blocks}")
    if "evidence_id" not in marginal.columns or "mean" not in marginal.columns:
        raise VomhoffBootstrapError("marginal_calibration must contain evidence_id and mean")

    if samples.duplicated(["evidence_id", "physical_run_id"]).any():
        raise VomhoffBootstrapError("Duplicate evidence_id/physical_run_id samples")

    marginal_mean = marginal.set_index("evidence_id")["mean"].astype(float).to_dict()
    known_evidence = set(marginal_mean)
    if set(samples["evidence_id"].astype(str)) != known_evidence:
        raise VomhoffBootstrapError("Evidence IDs differ between samples and marginal calibration")

    draw_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    dependence_rows: list[dict[str, Any]] = []
    block_policy_rows: list[dict[str, Any]] = []

    for _, block in blocks.sort_values("experimental_block_id", kind="stable").iterrows():
        block_id = str(block["experimental_block_id"])
        group = samples.loc[samples["experimental_block_id"].astype(str) == block_id].copy()
        if group.empty:
            raise VomhoffBootstrapError(f"No samples for block {block_id}")

        union_runs = sorted(group["physical_run_id"].astype(str).unique())
        if len(union_runs) != int(block["n_physical_runs_union"]):
            raise VomhoffBootstrapError(f"{block_id}: union-run checkpoint mismatch")
        evidence_ids = sorted(group["evidence_id"].astype(str).unique())
        if len(evidence_ids) != int(block["n_evidence_records"]):
            raise VomhoffBootstrapError(f"{block_id}: evidence-record checkpoint mismatch")

        run_sets = {
            eid: set(group.loc[group["evidence_id"].astype(str) == eid, "physical_run_id"].astype(str))
            for eid in evidence_ids
        }
        intersection_runs = set(union_runs)
        for run_set in run_sets.values():
            intersection_runs &= run_set

        rectangular = bool(block["complete_rectangular_run_set"])
        if rectangular and any(run_sets[eid] != set(union_runs) for eid in evidence_ids):
            raise VomhoffBootstrapError(f"{block_id}: rectangular flag inconsistent with run sets")

        missingness_policy = (
            "shared_physical_run_resample_complete_rectangular"
            if rectangular
            else "union_run_resampling_preserve_structural_missingness"
        )
        seed = _block_seed(master_seed, block_id)
        rng = np.random.default_rng(seed)
        sampled_indices = rng.integers(0, len(union_runs), size=(n_boot, len(union_runs)), endpoint=False)

        block_draw_wide: dict[str, np.ndarray] = {}
        for eid in evidence_ids:
            sub = group.loc[group["evidence_id"].astype(str) == eid, ["physical_run_id", "value"]]
            value_map = dict(zip(sub["physical_run_id"].astype(str), sub["value"].astype(float)))
            vector = np.array([value_map.get(run_id, np.nan) for run_id in union_runs], dtype=float)
            sampled = vector[sampled_indices]
            observed_counts = np.sum(~np.isnan(sampled), axis=1).astype(int)
            if np.any(observed_counts == 0):
                raise VomhoffBootstrapError(f"{block_id}/{eid}: bootstrap replicate with zero observed positions")
            means = np.nansum(sampled, axis=1) / observed_counts
            block_draw_wide[eid] = means

            point = float(marginal_mean[eid])
            original_n = int(np.sum(~np.isnan(vector)))
            boot_mean = float(means.mean())
            boot_sd = float(means.std(ddof=1))
            summary_rows.append({
                "experimental_block_id": block_id,
                "evidence_id": eid,
                "metric_id": str(group.loc[group["evidence_id"].astype(str) == eid, "metric_id"].iloc[0]),
                "n_original_runs": original_n,
                "n_block_union_runs": len(union_runs),
                "n_complete_case_runs_in_block": len(intersection_runs),
                "bootstrap_replicates": n_boot,
                "point_estimate": point,
                "bootstrap_mean": boot_mean,
                "bootstrap_bias": boot_mean - point,
                "bootstrap_sd_of_mean": boot_sd,
                "q025": _q(means, 0.025),
                "q05": _q(means, 0.05),
                "median": _q(means, 0.50),
                "q95": _q(means, 0.95),
                "q975": _q(means, 0.975),
                "bootstrap_observed_positions_min": int(observed_counts.min()),
                "bootstrap_observed_positions_q05": _q(observed_counts.astype(float), 0.05),
                "bootstrap_observed_positions_median": _q(observed_counts.astype(float), 0.50),
                "bootstrap_observed_positions_q95": _q(observed_counts.astype(float), 0.95),
                "bootstrap_observed_positions_max": int(observed_counts.max()),
                "missingness_policy": missingness_policy,
                "interval_interpretation": "nonparametric_percentile_interval_for_conditional_mean",
            })

            complete_values = [value_map[rid] for rid in sorted(intersection_runs) if rid in value_map]
            complete_mean = float(np.mean(complete_values)) if complete_values else np.nan
            delta = complete_mean - point if np.isfinite(complete_mean) else np.nan
            sensitivity_rows.append({
                "experimental_block_id": block_id,
                "evidence_id": eid,
                "n_original_runs": original_n,
                "n_complete_case_runs": len(complete_values),
                "full_available_case_mean": point,
                "complete_case_mean": complete_mean,
                "complete_case_minus_full_mean": delta,
                "relative_shift_pct": (100.0 * delta / abs(point)) if np.isfinite(delta) and point != 0 else np.nan,
                "diagnostic_only": True,
            })

            draw_frames.append(pd.DataFrame({
                "experimental_block_id": block_id,
                "bootstrap_rep": np.arange(n_boot, dtype=int),
                "evidence_id": eid,
                "bootstrap_mean": means,
                "n_observed_positions": observed_counts,
            }))

        # Within-block dependence of bootstrap mean estimates. Replicate IDs do not cross blocks.
        for i, a in enumerate(evidence_ids):
            for b in evidence_ids[i + 1:]:
                va = pd.Series(block_draw_wide[a])
                vb = pd.Series(block_draw_wide[b])
                dependence_rows.append({
                    "experimental_block_id": block_id,
                    "evidence_id_a": a,
                    "evidence_id_b": b,
                    "bootstrap_replicates": n_boot,
                    "bootstrap_mean_pearson_r": float(va.corr(vb, method="pearson")),
                    "bootstrap_mean_spearman_rho": float(va.corr(vb, method="spearman")),
                    "within_block_only": True,
                })

        block_policy_rows.append({
            "experimental_block_id": block_id,
            "n_union_runs": len(union_runs),
            "n_complete_case_runs": len(intersection_runs),
            "n_evidence_records": len(evidence_ids),
            "complete_rectangular_run_set": rectangular,
            "bootstrap_policy": missingness_policy,
            "block_seed": seed,
            "bootstrap_replicates": n_boot,
            "cross_block_joint_distribution_asserted": False,
        })

    draws = pd.concat(draw_frames, ignore_index=True)
    bootstrap_summary = pd.DataFrame(summary_rows).sort_values(
        ["experimental_block_id", "evidence_id"], kind="stable"
    ).reset_index(drop=True)
    sensitivity = pd.DataFrame(sensitivity_rows).sort_values(
        ["experimental_block_id", "evidence_id"], kind="stable"
    ).reset_index(drop=True)
    dependence = pd.DataFrame(dependence_rows).sort_values(
        ["experimental_block_id", "evidence_id_a", "evidence_id_b"], kind="stable"
    ).reset_index(drop=True)
    block_policy = pd.DataFrame(block_policy_rows).sort_values(
        "experimental_block_id", kind="stable"
    ).reset_index(drop=True)

    partial_blocks = block_policy.loc[~block_policy["complete_rectangular_run_set"]]
    summary = {
        "dataset_id": "vomhoff_nbiot_ltem_energy_2023",
        "stage": "Stage-3B Vomhoff joint nonparametric mean bootstrap",
        "experimental_blocks": int(len(block_policy)),
        "rectangular_blocks": int(block_policy["complete_rectangular_run_set"].sum()),
        "partial_overlap_blocks": int((~block_policy["complete_rectangular_run_set"]).sum()),
        "evidence_records_bootstrapped": int(bootstrap_summary["evidence_id"].nunique()),
        "bootstrap_replicates_per_block": n_boot,
        "bootstrap_mean_draw_rows": int(len(draws)),
        "within_block_dependence_pairs": int(len(dependence)),
        "partial_overlap_policy": str(policy["partial_overlap_policy"]),
        "partial_overlap_union_runs": None if partial_blocks.empty else int(partial_blocks.iloc[0]["n_union_runs"]),
        "partial_overlap_complete_case_runs": None if partial_blocks.empty else int(partial_blocks.iloc[0]["n_complete_case_runs"]),
        "joint_within_block_bootstrap_materialised": True,
        "structural_missingness_imputed": False,
        "listwise_deletion_used": False,
        "parametric_distribution_fitted": False,
        "cross_block_dependence_identified": False,
        "cross_block_joint_distribution_asserted": False,
        "vomhoff_epistemic_mean_uncertainty_materialised": True,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Bootstrap draws represent nonparametric epistemic uncertainty of conditional Vomhoff phase means. "
            "Physical runs are resampled jointly within each experimental block. Partial run-set overlap is handled "
            "by resampling the union run set and preserving observed structural missingness; no imputation or listwise "
            "deletion is used. Replicate indices have no cross-block joint meaning."
        ),
    }
    return draws, bootstrap_summary, block_policy, sensitivity, dependence, summary
