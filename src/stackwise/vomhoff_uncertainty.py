from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DATASET_ID = "vomhoff_nbiot_ltem_energy_2023"
CANONICAL_ROLE = "canonical"
FIGURE5_HTTP_IDLE_ALTERNATE = "alternate_source_filtered_view"


class VomhoffUncertaintyError(RuntimeError):
    pass


def _stable_id(prefix: str, *values: Any) -> str:
    serialised = "|".join("<NA>" if pd.isna(v) else str(v) for v in values)
    return f"{prefix}-{hashlib.sha1(serialised.encode('utf-8')).hexdigest()[:16]}"


def _figure_family(value: Any) -> str:
    contexts = {token.strip() for token in str(value).split("|") if token.strip()}
    if contexts and contexts.issubset({"4", "5"}):
        return "fig4_5"
    if contexts == {"3"}:
        return "fig3"
    return "fig_" + "_".join(sorted(contexts))


def _evidence_id(row: pd.Series, metric_id: str) -> str:
    return _stable_id(
        "vomhoff-evidence",
        metric_id,
        row.get("technology"),
        row.get("source_application_protocol"),
        row.get("source_data_object"),
        row.get("source_event"),
        row.get("analysis_role"),
        row.get("normalisation_rules"),
    )


def _block_id(row: pd.Series) -> str:
    return _stable_id(
        "vomhoff-uncertainty-block",
        _figure_family(row.get("source_figure_contexts")),
        row.get("technology"),
        row.get("source_application_protocol"),
        row.get("source_data_object"),
    )


def _quantile(values: pd.Series, q: float) -> float:
    return float(pd.to_numeric(values, errors="coerce").quantile(q, interpolation="linear"))


def build_vomhoff_uncertainty_calibration(
    logical: pd.DataFrame,
    evidence_records: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build the Stage-3A empirical run-level calibration for Vomhoff.

    This function calibrates only what is identifiable from repeated physical/source runs:
    marginal conditional run-to-run variability and observed cross-metric/phase dependence.
    It deliberately does *not* select a parametric family or perform a final joint bootstrap.
    Candidate joint resampling blocks are audited first because some evidence groups may have
    partially overlapping run sets.
    """
    required = {
        "physical_run_id",
        "technology",
        "source_application_protocol",
        "source_data_object",
        "source_event",
        "analysis_role",
        "normalisation_rules",
        "source_figure_contexts",
        "evidence_eligible",
        "energy_j",
        "duration_s",
    }
    missing = sorted(required - set(logical.columns))
    if missing:
        raise VomhoffUncertaintyError(f"Logical-phase artifact missing columns: {missing}")

    evidence_by_id = {str(record["evidence_id"]): record for record in evidence_records}
    if len(evidence_by_id) != len(evidence_records):
        raise VomhoffUncertaintyError("Duplicate evidence_id in Vomhoff Stage-2 evidence records")
    if any(str(record.get("dataset_id")) != DATASET_ID for record in evidence_records):
        raise VomhoffUncertaintyError("Non-Vomhoff evidence record supplied")

    eligible = logical.loc[logical["evidence_eligible"].astype(bool)].copy()
    if eligible.empty:
        raise VomhoffUncertaintyError("No evidence-eligible logical phases")

    sample_rows: list[dict[str, Any]] = []
    metric_defs = (
        ("device_phase_energy_j", "energy_j", "J"),
        ("device_phase_duration_s", "duration_s", "s"),
    )
    for _, row in eligible.iterrows():
        block_id = _block_id(row)
        family = _figure_family(row.get("source_figure_contexts"))
        for metric_id, value_col, unit in metric_defs:
            value = pd.to_numeric(pd.Series([row.get(value_col)]), errors="coerce").iloc[0]
            if pd.isna(value):
                continue
            evidence_id = _evidence_id(row, metric_id)
            if evidence_id not in evidence_by_id:
                raise VomhoffUncertaintyError(
                    f"Run-level sample maps to unknown Stage-2 evidence_id: {evidence_id}"
                )
            sample_rows.append(
                {
                    "dataset_id": DATASET_ID,
                    "evidence_id": evidence_id,
                    "metric_id": metric_id,
                    "unit": unit,
                    "physical_run_id": str(row["physical_run_id"]),
                    "experimental_block_id": block_id,
                    "figure_family": family,
                    "technology": row.get("technology"),
                    "source_application_protocol": row.get("source_application_protocol"),
                    "source_data_object": row.get("source_data_object"),
                    "phase_name": row.get("source_event"),
                    "analysis_role": row.get("analysis_role"),
                    "source_figure_contexts": row.get("source_figure_contexts"),
                    "value": float(value),
                }
            )

    samples = pd.DataFrame(sample_rows)
    if samples.empty:
        raise VomhoffUncertaintyError("No run-level metric samples materialised")

    duplicate_pairs = int(samples.duplicated(["evidence_id", "physical_run_id"]).sum())
    if duplicate_pairs:
        raise VomhoffUncertaintyError(
            f"Found {duplicate_pairs} duplicate evidence_id/physical_run_id samples"
        )

    mapped_ids = set(samples["evidence_id"])
    expected_ids = set(evidence_by_id)
    missing_ids = sorted(expected_ids - mapped_ids)
    extra_ids = sorted(mapped_ids - expected_ids)
    if missing_ids or extra_ids:
        raise VomhoffUncertaintyError(
            f"Evidence mapping mismatch; missing={missing_ids[:5]}, extra={extra_ids[:5]}"
        )

    marginal_rows: list[dict[str, Any]] = []
    run_sets: dict[str, set[str]] = {}
    for evidence_id, group in samples.groupby("evidence_id", sort=True):
        values = pd.to_numeric(group["value"], errors="coerce").dropna().astype(float)
        runs = set(group["physical_run_id"].astype(str))
        run_sets[str(evidence_id)] = runs
        record = evidence_by_id[str(evidence_id)]
        n = len(runs)
        expected_n = record.get("n_independent_units")
        if expected_n is None or int(expected_n) != n:
            raise VomhoffUncertaintyError(
                f"{evidence_id}: run-level n={n} != Stage-2 n_independent_units={expected_n}"
            )
        mean = float(values.mean())
        expected_mean = float(record["estimate"])
        if not np.isclose(mean, expected_mean, rtol=1e-11, atol=1e-12):
            raise VomhoffUncertaintyError(
                f"{evidence_id}: run-level mean {mean} != Stage-2 estimate {expected_mean}"
            )
        sd = float(values.std(ddof=1)) if n > 1 else np.nan
        cv_pct = float(100.0 * sd / abs(mean)) if n > 1 and mean != 0 else np.nan
        marginal_rows.append(
            {
                "evidence_id": evidence_id,
                "metric_id": str(record["metric_id"]),
                "technology": record.get("technology"),
                "application_protocol": record.get("application_protocol"),
                "phase_name": record.get("phase_name"),
                "analysis_role": group["analysis_role"].iloc[0],
                "experimental_block_id": group["experimental_block_id"].iloc[0],
                "n_independent_runs": n,
                "mean": mean,
                "sample_sd": sd,
                "cv_pct": cv_pct,
                "minimum": float(values.min()),
                "q05": _quantile(values, 0.05),
                "q25": _quantile(values, 0.25),
                "median": _quantile(values, 0.50),
                "q75": _quantile(values, 0.75),
                "q95": _quantile(values, 0.95),
                "maximum": float(values.max()),
                "zero_count": int((values == 0).sum()),
                "nonpositive_count": int((values <= 0).sum()),
                "aleatory_calibration_status": "empirical_run_distribution_calibrated",
                "epistemic_mean_status": "joint_block_bootstrap_pending",
                "scope": "conditional_on_original_vomhoff_lab_setup_and_source_configuration",
            }
        )
    marginal = pd.DataFrame(marginal_rows).sort_values(
        ["experimental_block_id", "metric_id", "phase_name", "analysis_role"], kind="stable"
    ).reset_index(drop=True)

    block_rows: list[dict[str, Any]] = []
    for block_id, group in samples.groupby("experimental_block_id", sort=True):
        evidence_ids = sorted(group["evidence_id"].unique())
        block_runs = set(group["physical_run_id"].astype(str))
        signatures = {
            hashlib.sha1("|".join(sorted(run_sets[eid])).encode("utf-8")).hexdigest()[:16]
            for eid in evidence_ids
        }
        n_by_record = [len(run_sets[eid]) for eid in evidence_ids]
        block_rows.append(
            {
                "experimental_block_id": block_id,
                "figure_family": group["figure_family"].iloc[0],
                "technology": group["technology"].iloc[0],
                "source_application_protocol": group["source_application_protocol"].iloc[0],
                "source_data_object": group["source_data_object"].iloc[0],
                "n_physical_runs_union": len(block_runs),
                "n_evidence_records": len(evidence_ids),
                "n_distinct_run_sets": len(signatures),
                "n_independent_runs_min": int(min(n_by_record)),
                "n_independent_runs_max": int(max(n_by_record)),
                "complete_rectangular_run_set": len(signatures) == 1,
                "joint_resampling_status": (
                    "ready_complete_rectangular"
                    if len(signatures) == 1
                    else "partial_overlap_review_required"
                ),
            }
        )
    blocks = pd.DataFrame(block_rows).sort_values(
        ["figure_family", "technology", "source_application_protocol", "source_data_object"],
        kind="stable",
    ).reset_index(drop=True)

    overlap_rows: list[dict[str, Any]] = []
    dependence_rows: list[dict[str, Any]] = []
    sample_indexed = samples.set_index(["evidence_id", "physical_run_id"])["value"]
    for block_id, group in samples.groupby("experimental_block_id", sort=True):
        evidence_ids = sorted(group["evidence_id"].unique())
        for a, b in combinations(evidence_ids, 2):
            runs_a = run_sets[a]
            runs_b = run_sets[b]
            overlap = runs_a & runs_b
            union = runs_a | runs_b
            identical = runs_a == runs_b
            overlap_rows.append(
                {
                    "experimental_block_id": block_id,
                    "evidence_id_a": a,
                    "evidence_id_b": b,
                    "metric_id_a": evidence_by_id[a]["metric_id"],
                    "metric_id_b": evidence_by_id[b]["metric_id"],
                    "phase_name_a": evidence_by_id[a].get("phase_name"),
                    "phase_name_b": evidence_by_id[b].get("phase_name"),
                    "n_a": len(runs_a),
                    "n_b": len(runs_b),
                    "n_overlap": len(overlap),
                    "overlap_fraction_a": len(overlap) / len(runs_a) if runs_a else np.nan,
                    "overlap_fraction_b": len(overlap) / len(runs_b) if runs_b else np.nan,
                    "jaccard": len(overlap) / len(union) if union else np.nan,
                    "identical_run_set": identical,
                }
            )
            if len(overlap) >= 5:
                ordered = sorted(overlap)
                va = pd.Series([float(sample_indexed.loc[(a, rid)]) for rid in ordered], dtype=float)
                vb = pd.Series([float(sample_indexed.loc[(b, rid)]) for rid in ordered], dtype=float)
                pearson = va.corr(vb, method="pearson") if va.nunique() > 1 and vb.nunique() > 1 else np.nan
                spearman = va.corr(vb, method="spearman") if va.nunique() > 1 and vb.nunique() > 1 else np.nan
                dependence_rows.append(
                    {
                        "experimental_block_id": block_id,
                        "evidence_id_a": a,
                        "evidence_id_b": b,
                        "metric_id_a": evidence_by_id[a]["metric_id"],
                        "metric_id_b": evidence_by_id[b]["metric_id"],
                        "phase_name_a": evidence_by_id[a].get("phase_name"),
                        "phase_name_b": evidence_by_id[b].get("phase_name"),
                        "n_paired_runs": len(overlap),
                        "pearson_r": None if pd.isna(pearson) else float(pearson),
                        "spearman_rho": None if pd.isna(spearman) else float(spearman),
                        "diagnostic_only": True,
                    }
                )

    overlaps = pd.DataFrame(overlap_rows)
    dependence = pd.DataFrame(dependence_rows)
    if not overlaps.empty:
        overlaps = overlaps.sort_values(
            ["experimental_block_id", "evidence_id_a", "evidence_id_b"], kind="stable"
        ).reset_index(drop=True)
    if not dependence.empty:
        dependence = dependence.sort_values(
            ["experimental_block_id", "evidence_id_a", "evidence_id_b"], kind="stable"
        ).reset_index(drop=True)

    summary = {
        "dataset_id": DATASET_ID,
        "stage": "Stage-3A Vomhoff empirical run-level uncertainty calibration",
        "logical_phase_rows": int(len(logical)),
        "evidence_eligible_logical_phase_rows": int(len(eligible)),
        "run_level_metric_samples": int(len(samples)),
        "physical_run_units": int(eligible["physical_run_id"].nunique()),
        "evidence_records_calibrated": int(len(marginal)),
        "metric_families_calibrated": sorted(marginal["metric_id"].unique().tolist()),
        "n_independent_runs_min": int(marginal["n_independent_runs"].min()),
        "n_independent_runs_max": int(marginal["n_independent_runs"].max()),
        "experimental_blocks": int(len(blocks)),
        "complete_rectangular_blocks": int(blocks["complete_rectangular_run_set"].sum()),
        "partial_overlap_blocks": int((~blocks["complete_rectangular_run_set"]).sum()),
        "run_set_overlap_pairs": int(len(overlaps)),
        "paired_dependence_pairs_n_ge_5": int(len(dependence)),
        "duplicate_evidence_run_samples": 0,
        "stage2_mean_reconciliation_errors": 0,
        "aleatory_run_variability_calibrated": True,
        "joint_block_bootstrap_authorised": bool((blocks["complete_rectangular_run_set"]).all()),
        "epistemic_mean_bootstrap_materialised": False,
        "parametric_distribution_fitted": False,
        "generic_device_or_study_random_effect_fitted": False,
        "publication_uncertainty_sampling_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Observed physical/source-run values calibrate conditional run-to-run variability under the original "
            "Vomhoff laboratory configurations. Pairwise dependence is diagnostic only. A final joint physical-run "
            "bootstrap is intentionally deferred until candidate block run-set overlap is reviewed; no parametric "
            "family, cross-device variance or generic study effect is introduced."
        ),
    }
    return samples, marginal, blocks, overlaps, dependence, summary


def load_evidence_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VomhoffUncertaintyError(
                    f"Expected object at {path}:{line_number}"
                )
            records.append(value)
    return records
