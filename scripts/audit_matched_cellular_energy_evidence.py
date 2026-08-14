from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.matched_energy import audit_summary, experiment_cell_rows, source_review_rows
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage6b_matched_cellular_energy"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty Stage-6B artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policy_path = ROOT / "datasets/stage6b_matched_cellular_energy.yml"
    stage6a_subset = ROOT / "results/validation/stage6a_decision_slice_consolidation/preferred_development_subset.csv"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    sources = source_review_rows(policy)
    experiments = experiment_cell_rows(policy)
    summary = audit_summary(policy, sources, experiments)

    OUT.mkdir(parents=True, exist_ok=True)
    source_path = OUT / "external_source_admissibility.csv"
    experiment_path = OUT / "minimum_experiment_cells.csv"
    _write_csv(source_path, sources)
    _write_csv(experiment_path, experiments)

    contract = policy["minimum_experiment_contract"]
    payload = {
        "stage": policy["stage"],
        "stage6_status": policy["stage6_status"],
        **summary.__dict__,
        "matched_public_energy_source_found": False,
        "targeted_measurement_required": True,
        "canonical_energy_target_materialised": False,
        "publication_mcda_authorised": False,
        "transport_accounting_detail_frozen": True,
        "pilot_blocks": contract["pilot_blocks"],
        "final_replication_count_frozen": False,
        "preferred_measurement_boundary": contract["energy_boundary"],
        "interpretation": (
            "No reviewed public source simultaneously matches the preferred 64-B/60-s development subset across "
            "NB-IoT and LTE-M, the two candidate IP bindings, and the required whole-device report-cycle boundary. "
            "Vomhoff remains the strongest whole-device dual-RAT reference but is 1-KB/source-context bound; Sørensen "
            "provides validated dual-RAT modem-state modelling at 100-B validation payloads and long cycles; Michelinakis "
            "and Lukic add useful NB-IoT payload/configuration evidence, including a 64-B UDP example, but cannot identify "
            "the LTE-M candidate energy. A small matched repeated-measures experiment is therefore the minimal honest closure."
        ),
        "preferred_next_step": (
            "Run a five-block pilot of the four primary 64-B/60-s RAT×binding cells on one dual-mode DUT and one operator, "
            "then freeze the main replication count from observed between-block variance before collecting the main experiment. "
            "In parallel, Stage 6C may close the EUR lifecycle-cost robustness family because it is independent of these measurements."
        ),
        "external_source_admissibility_artifact": "results/validation/stage6b_matched_cellular_energy/external_source_admissibility.csv",
        "minimum_experiment_cells_artifact": "results/validation/stage6b_matched_cellular_energy/minimum_experiment_cells.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_matched_cellular_energy_evidence.py",
        inputs=[policy_path, stage6a_subset],
        outputs=[source_path, experiment_path, summary_path],
        parameters={
            "target_scenario_id": policy["scientific_policy"]["target_scenario_id"],
            "payload_bytes": policy["scientific_policy"]["target_pre_lwm2m_payload_bytes"],
            "reporting_interval_s": policy["scientific_policy"]["target_reporting_interval_s"],
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-6B matched cellular energy-evidence audit: OK")
    print(f"External sources reviewed / both-RAT sources: {summary.external_sources_reviewed} / {summary.sources_covering_both_rats}")
    print(f"Sources with exact 64-B payload / exact 60-s cycle: {summary.sources_with_exact_64b_payload} / {summary.sources_with_exact_60s_cycle}")
    print(f"Sources ready at canonical candidate boundary: {summary.sources_candidate_boundary_ready}")
    print(f"Primary / robustness experiment cells: {summary.primary_experiment_cells} / {summary.robustness_experiment_cells}")
    print("Matched public source found: no")
    print("Targeted whole-device measurement required: yes")
    print("Publication MCDA authorised: no")


if __name__ == "__main__":
    main()
