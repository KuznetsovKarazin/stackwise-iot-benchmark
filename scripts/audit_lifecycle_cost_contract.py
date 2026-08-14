from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.lifecycle_cost import (
    audit_summary,
    build_candidate_cost_readiness,
    cost_component_contract_rows,
    cost_gap_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5h_lifecycle_cost_contract"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy = yaml.safe_load((ROOT / "datasets/stage5h_lifecycle_cost_contract.yml").read_text(encoding="utf-8"))
    feasibility = read_csv(ROOT / "results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv")

    candidate_rows = build_candidate_cost_readiness(feasibility, policy)
    components = cost_component_contract_rows(policy)
    gaps = cost_gap_rows(candidate_rows)
    summary = audit_summary(candidate_rows, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "cost_component_contract.csv", components)
    write_csv(OUT / "candidate_cost_readiness.csv", candidate_rows)
    write_csv(OUT / "cost_evidence_gaps.csv", gaps)

    payload = {
        "stage": "Stage-5H lifecycle-cost accounting and evidence contract",
        "stage5_status": policy["stage5_status"],
        "feasible_candidate_rows": summary.feasible_candidate_rows,
        "operator_managed_rows": summary.operator_managed_rows,
        "private_owned_rows": summary.private_owned_rows,
        "unresolved_ownership_rows": summary.unresolved_ownership_rows,
        "rows_with_complete_required_price_evidence": summary.rows_with_complete_required_price_evidence,
        "rows_requiring_shared_cost_scale": summary.rows_requiring_shared_cost_scale,
        "canonical_target_ready_rows": summary.canonical_target_ready_rows,
        "smoke_price_rows_authorised": summary.smoke_price_rows_authorised,
        "analysis_horizon_years": policy["scientific_policy"]["analysis_horizon_years"],
        "base_currency": policy["scientific_policy"]["base_currency"],
        "price_basis_date": policy["scientific_policy"]["price_basis_date"],
        "publication_mcda_authorised": False,
        "interpretation": (
            "The lifecycle-cost accounting boundary is now frozen, but publication cost values are not yet materialised. "
            "Operator recurring costs, private shared infrastructure and device incremental CAPEX are kept separate. "
            "Smoke-test prices remain prohibited; private shared infrastructure cannot be allocated per device until a deployment scale is frozen."
        ),
        "preferred_next_step": "targeted_dated_cost_evidence_collection",
        "candidate_cost_readiness_artifact": "results/validation/stage5h_lifecycle_cost_contract/candidate_cost_readiness.csv",
        "cost_component_contract_artifact": "results/validation/stage5h_lifecycle_cost_contract/cost_component_contract.csv",
        "cost_evidence_gaps_artifact": "results/validation/stage5h_lifecycle_cost_contract/cost_evidence_gaps.csv",
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Stage-5H lifecycle-cost contract audit: OK")
    print(f"Feasible candidate rows: {summary.feasible_candidate_rows}")
    print(f"Operator/private/unresolved ownership rows: {summary.operator_managed_rows} / {summary.private_owned_rows} / {summary.unresolved_ownership_rows}")
    print(f"Rows with complete required price evidence: {summary.rows_with_complete_required_price_evidence}")
    print(f"Rows requiring shared-cost scale: {summary.rows_requiring_shared_cost_scale}")
    print(f"Canonical lifecycle-cost target ready: {summary.canonical_target_ready_rows}")
    print(f"Smoke price rows authorised: {summary.smoke_price_rows_authorised}")


if __name__ == "__main__":
    main()
