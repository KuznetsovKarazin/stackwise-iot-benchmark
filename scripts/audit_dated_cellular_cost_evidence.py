from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.dated_cost_evidence import (
    audit_summary,
    build_dated_cost_readiness,
    monetary_evidence_ledger_rows,
    remaining_gap_rows,
)
from stackwise.lifecycle_cost import build_candidate_cost_readiness

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5i_dated_cellular_cost_evidence"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    stage5h = yaml.safe_load((ROOT / "datasets/stage5h_lifecycle_cost_contract.yml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((ROOT / "datasets/stage5i_dated_cellular_cost_evidence.yml").read_text(encoding="utf-8"))
    feasibility = _read_csv(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")
    stage5h_rows = build_candidate_cost_readiness(feasibility, stage5h)
    rows = build_dated_cost_readiness(stage5h_rows, policy)
    ledger = monetary_evidence_ledger_rows(policy)
    gaps = remaining_gap_rows(rows)
    summary = audit_summary(rows, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT / "price_evidence_ledger.csv", ledger)
    _write_csv(OUT / "candidate_cost_evidence_readiness.csv", rows)
    _write_csv(OUT / "remaining_cost_gaps.csv", gaps)

    ip_rows = [r for r in rows if r["dated_ip_connectivity_tariff_evidence"]]
    floors = [
        {k: r[k] for k in [
            "scenario_id", "stack_id", "reporting_interval_s", "five_year_report_count",
            "application_payload_volume_mb_5y", "included_data_mb", "included_data_to_application_payload_ratio",
            "tariff_volume_fit_status", "reference_module_eur_qty1_ex_vat", "reference_standard_sim_eur",
            "reference_base_connectivity_cash_eur", "reference_cost_floor_eur", "cost_floor_is_canonical_target",
        ]}
        for r in ip_rows
    ]
    _write_csv(OUT / "ip_cellular_reference_cost_floors.csv", floors)

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "source_capture_date": policy["scientific_policy"]["source_capture_date"],
        "canonical_lifecycle_cost_materialised": False,
        "publication_mcda_authorised": False,
        "reference_module_price_eur_qty1_ex_vat": 33.41,
        "reference_standard_sim_price_eur": 1.0,
        "reference_connectivity_base_plan_cash_eur": 12.0,
        "interpretation": (
            "Current dated hardware and IP-connectivity price evidence is now materialised for the ten feasible IP-cellular incidences. "
            "The selected dual-mode BG95-M3 reference avoids inventing an NB-IoT/LTE-M hardware price difference. The 1NCE tariff has a finite data allowance and the source states a 1-kByte measurement/billing granularity, but it does not identify the rounding aggregation interval. "
            "STACKWISE therefore does not assume one billing unit per application report. Five-year application-payload volume is below 500 MB in all three IP-cellular scenarios, so base-plan sufficiency is not disproven but exact transport/session usage remains unresolved. The EUR 46.41 hardware+SIM+base-plan floor is not a canonical lifecycle cost. Non-IP/NIDD service pricing remains unevidenced."
        ),
        "preferred_next_step": "freeze_candidate_ip_session_profiles_then_compute_tariff_volume_envelopes",
        "candidate_readiness_artifact": "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv",
        "price_evidence_ledger_artifact": "results/validation/stage5i_dated_cellular_cost_evidence/price_evidence_ledger.csv",
        "reference_cost_floor_artifact": "results/validation/stage5i_dated_cellular_cost_evidence/ip_cellular_reference_cost_floors.csv",
        "remaining_cost_gaps_artifact": "results/validation/stage5i_dated_cellular_cost_evidence/remaining_cost_gaps.csv",
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Stage-5I dated cellular cost-evidence audit: OK")
    print(f"Feasible / operator-managed rows: {summary.feasible_candidate_rows} / {summary.operator_managed_rows}")
    print(f"IP / Non-IP cellular feasible rows: {summary.ip_cellular_feasible_rows} / {summary.nonip_cellular_feasible_rows}")
    print(f"Rows with dated module+SIM / IP tariff evidence: {summary.rows_with_dated_module_and_sim_price} / {summary.rows_with_ip_connectivity_tariff_evidence}")
    print(f"Smart-meter IP rows where base allowance is not disproven: {summary.smart_meter_ip_rows_with_base_allowance_not_disproven}")
    print(f"Tracking IP rows where base allowance is not disproven: {summary.tracking_ip_rows_with_base_allowance_not_disproven}")
    print(f"Rows where base allowance is definitely insufficient: {summary.rows_where_base_allowance_definitely_insufficient}")
    print(f"Canonical lifecycle-cost target ready: {summary.rows_with_canonical_lifecycle_cost_ready}")


if __name__ == "__main__":
    main()
