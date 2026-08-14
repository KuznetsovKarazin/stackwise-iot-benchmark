from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

DEFAULT_REVIEW_POLICY = Path("datasets/single_trace_uncertainty_evidence.yml")


class SingleTraceUncertaintyReviewError(RuntimeError):
    pass


def load_review_policy(path: str | Path = DEFAULT_REVIEW_POLICY) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SingleTraceUncertaintyReviewError("Single-trace review policy must be a mapping")
    return value


def audit_single_trace_uncertainty(
    evidence_csv: str | Path,
    *,
    policy_path: str | Path = DEFAULT_REVIEW_POLICY,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    policy = load_review_policy(policy_path)
    frame = pd.read_csv(evidence_csv)
    datasets = policy.get("datasets")
    decision = policy.get("decision")
    if not isinstance(datasets, dict) or not isinstance(decision, dict):
        raise SingleTraceUncertaintyReviewError("Policy must contain datasets and decision mappings")

    review_rows: list[dict[str, Any]] = []
    instrument_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for dataset_id, cfg in datasets.items():
        metric_ids = list(cfg.get("metric_ids") or [])
        for metric_id in metric_ids:
            subset = frame[(frame["dataset_id"] == dataset_id) & (frame["metric_id"] == metric_id)]
            if subset.empty:
                errors.append(f"No evidence records for {dataset_id}/{metric_id}")
                continue
            n_ind = pd.to_numeric(subset["n_independent_units"], errors="coerce")
            if n_ind.isna().any() or not (n_ind == 1).all():
                errors.append(f"Expected n_independent_units=1 for {dataset_id}/{metric_id}")
            review_rows.append({
                "dataset_id": dataset_id,
                "metric_id": metric_id,
                "record_count": int(len(subset)),
                "n_independent_units_min": int(n_ind.min()),
                "n_independent_units_max": int(n_ind.max()),
                "repeatability_evidence_status": cfg["repeatability_evidence_status"],
                "numeric_population_variability_identified": bool(cfg["numeric_population_variability_identified"]),
                "numeric_probabilistic_prior_identified": bool(cfg["numeric_probabilistic_prior_identified"]),
                "instrument_sensitivity_status": cfg["instrument_sensitivity_status"],
                "primary_uncertainty_action": cfg["primary_uncertainty_action"],
            })

        if dataset_id == "lorawan_lrfhss_energy_2024":
            subset = frame[frame["dataset_id"] == dataset_id]
            instruments = sorted(set(subset["measurement_instrument"].dropna().astype(str)))
            software = sorted(set(subset.get("acquisition_software", pd.Series(dtype=str)).dropna().astype(str)))
            expected_instrument = str(cfg["measurement_hardware"])
            expected_software = str(cfg["acquisition_software"])
            if instruments != [expected_instrument]:
                errors.append(f"LR-FHSS measurement instrument mismatch: {instruments} != {[expected_instrument]}")
            if software != [expected_software]:
                errors.append(f"LR-FHSS acquisition software mismatch: {software} != {[expected_software]}")
            rec = cfg["instrumentation_reconciliation"]
            instrument_rows.append({
                "dataset_id": dataset_id,
                "dataset_label": rec["dataset_label"],
                "publication_hardware_statement": rec["publication_hardware_statement"],
                "manufacturer_14585a_statement": rec["manufacturer_14585a_statement"],
                "resolved_measurement_hardware": expected_instrument,
                "resolved_acquisition_software": expected_software,
                "resolution": rec["resolution"],
            })

    expected_families = int(decision.get("reviewed_metric_families", -1))
    if expected_families != len(review_rows):
        errors.append(f"Policy reviewed_metric_families checkpoint failed: {expected_families} != {len(review_rows)}")
    expected_priors = int(decision.get("numeric_population_priors_identified", -1))
    actual_priors = sum(bool(row["numeric_probabilistic_prior_identified"]) for row in review_rows)
    if expected_priors != actual_priors:
        errors.append(f"Policy numeric_population_priors_identified checkpoint failed: {expected_priors} != {actual_priors}")

    if errors:
        raise SingleTraceUncertaintyReviewError("; ".join(errors[:10]))

    review = pd.DataFrame(review_rows)
    instrumentation = pd.DataFrame(instrument_rows)
    summary = {
        "stage": policy.get("review_stage"),
        "datasets_reviewed": len(datasets),
        "metric_families_reviewed": int(len(review)),
        "metric_records_reviewed": int(review["record_count"].sum()),
        "numeric_population_priors_identified": int(review["numeric_probabilistic_prior_identified"].sum()),
        "insectt_repeatability_evidence_status": datasets["insectt_wsn_power_2023"]["repeatability_evidence_status"],
        "lrfhss_repeatability_evidence_status": datasets["lorawan_lrfhss_energy_2024"]["repeatability_evidence_status"],
        "lrfhss_instrumentation_reconciled": True,
        "lrfhss_measurement_hardware": datasets["lorawan_lrfhss_energy_2024"]["measurement_hardware"],
        "lrfhss_acquisition_software": datasets["lorawan_lrfhss_energy_2024"]["acquisition_software"],
        "default_cv_or_sd_authorised": bool(decision["default_cv_or_sd_authorised"]),
        "infer_cv_from_qualitative_negligible_authorised": bool(decision["infer_cv_from_qualitative_negligible_authorised"]),
        "convert_instrument_accuracy_to_population_sd_authorised": bool(decision["convert_instrument_accuracy_to_population_sd_authorised"]),
        "publication_uncertainty_sampling_authorised": bool(decision["publication_uncertainty_sampling_authorised"]),
        "publication_mcda_authorised": bool(decision["publication_mcda_authorised"]),
        "interpretation": (
            "Primary-source review does not identify a defensible numerical population-variability prior for any of the six "
            "single-trace metric families. InSecTT reports one approximately 60 s averaged trace per configuration and no "
            "replicate dispersion. LR-FHSS reports qualitatively negligible differences across several transmission processes, "
            "but no repeat count or numerical dispersion. Instrument metrology is retained separately and is not converted into "
            "run-to-run variability."
        ),
        "next_scientific_step": decision["recommended_next_step"],
    }
    return summary, review, instrumentation
