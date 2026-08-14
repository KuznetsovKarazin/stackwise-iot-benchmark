from pathlib import Path

import pandas as pd

from stackwise.single_trace_uncertainty import audit_single_trace_uncertainty, load_review_policy


def test_review_policy_has_no_numeric_priors():
    policy = load_review_policy()
    assert policy["decision"]["numeric_population_priors_identified"] == 0
    assert policy["decision"]["infer_cv_from_qualitative_negligible_authorised"] is False
    assert policy["decision"]["convert_instrument_accuracy_to_population_sd_authorised"] is False
    assert policy["datasets"]["insectt_wsn_power_2023"]["repeatability_evidence_status"] == "none_reported"
    assert policy["datasets"]["lorawan_lrfhss_energy_2024"]["repeatability_evidence_status"] == "qualitative_low_variability_only"


def test_audit_reconciles_lrfhss_instrumentation(tmp_path: Path):
    rows = []
    for dataset_id, metrics, n in [
        ("insectt_wsn_power_2023", ["trace_mean_current_a", "trace_charge_c", "derived_mean_power_w", "derived_capture_energy_j"], 2),
        ("lorawan_lrfhss_energy_2024", ["radio_full_capture_energy_j", "radio_incremental_transaction_energy_j"], 2),
    ]:
        for metric in metrics:
            for idx in range(n):
                rows.append({
                    "dataset_id": dataset_id,
                    "metric_id": metric,
                    "n_independent_units": 1,
                    "measurement_instrument": "Keysight N6705A DC Power Analyzer" if dataset_id.startswith("lorawan") else "Nordic Power Profiler Kit II (source mode)",
                    "acquisition_software": "Keysight 14585A Control and Analysis Software" if dataset_id.startswith("lorawan") else None,
                })
    path = tmp_path / "evidence.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    summary, review, instrumentation = audit_single_trace_uncertainty(path)
    assert summary["metric_families_reviewed"] == 6
    assert summary["numeric_population_priors_identified"] == 0
    assert summary["lrfhss_instrumentation_reconciled"] is True
    assert len(instrumentation) == 1
    assert instrumentation.iloc[0]["resolved_measurement_hardware"] == "Keysight N6705A DC Power Analyzer"
    assert set(review["n_independent_units_min"]) == {1}
