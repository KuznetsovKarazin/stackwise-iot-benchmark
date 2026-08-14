from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.cellular_transfer_evidence import audit_summary, build_transfer_admissibility_rows, source_review_rows
from stackwise.provenance import write_run_manifest


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Stage-5G audit of targeted external cellular energy transfer evidence.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5g_cellular_transfer_evidence.yml"))
    ap.add_argument("--stage5f", type=Path, default=Path("results/validation/stage5_cellular_ip_energy_bridge/candidate_bridge_audit.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5g_cellular_transfer_evidence"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    stage5f_rows = _read_csv(args.stage5f)
    rows = build_transfer_admissibility_rows(stage5f_rows, policy)
    summary_obj = audit_summary(rows, policy)
    sources = source_review_rows(policy)

    args.output.mkdir(parents=True, exist_ok=True)
    audit_path = args.output / "candidate_transfer_admissibility.csv"
    source_path = args.output / "external_source_review.csv"
    _write_csv(audit_path, rows)
    _write_csv(source_path, sources)

    next_rows = []
    for option in policy["next_step_policy"]["options"]:
        next_rows.append({
            "option_id": option["option_id"],
            "priority": int(option["priority"]),
            "rule": option["rule"],
        })
    next_path = args.output / "stage5h_next_step_options.csv"
    _write_csv(next_path, next_rows)

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        "feasible_cellular_ip_candidate_incidences": summary_obj.feasible_candidate_incidences,
        "external_sources_reviewed": summary_obj.external_sources_reviewed,
        "payload_structural_support_rows": summary_obj.payload_structural_support_rows,
        "reporting_cycle_structural_support_rows": summary_obj.reporting_cycle_structural_support_rows,
        "exact_upper_layer_support_rows": summary_obj.exact_upper_layer_support_rows,
        "absolute_external_calibration_authorised_rows": summary_obj.absolute_external_calibration_authorised_rows,
        "canonical_target_ready_rows": summary_obj.canonical_target_ready_rows,
        "canonical_target_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": "A validated external NB-IoT/LTE-M state/procedure model supports the existence and structure of payload- and reporting-cycle effects, but it cannot numerically recalibrate the retained Vomhoff whole-device source component because the external boundary is modem-only, device/network parameters are implementation-specific, and candidate upper-layer contexts remain unmatched.",
        "preferred_next_step": policy["next_step_policy"]["preferred"],
        "candidate_transfer_admissibility_artifact": str(audit_path),
        "external_source_review_artifact": str(source_path),
        "next_step_options_artifact": str(next_path),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest_path = args.output / "run_manifest.json"
    write_run_manifest(
        manifest_path,
        command="python scripts/audit_cellular_transfer_evidence.py",
        inputs=[args.policy, args.stage5f],
        outputs=[audit_path, source_path, next_path, summary_path],
        parameters={
            "external_absolute_recalibration": False,
            "external_structural_support": True,
            "canonical_target_materialisation_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5G cellular transfer-evidence audit: OK")
    print(f"Feasible cellular-IP incidences: {summary_obj.feasible_candidate_incidences}")
    print(f"External sources reviewed: {summary_obj.external_sources_reviewed}")
    print(f"Payload structural support rows: {summary_obj.payload_structural_support_rows}")
    print(f"Report-cycle structural support rows: {summary_obj.reporting_cycle_structural_support_rows}")
    print(f"Exact upper-layer support rows: {summary_obj.exact_upper_layer_support_rows}")
    print(f"External absolute calibration authorised: {summary_obj.absolute_external_calibration_authorised_rows}")
    print(f"Canonical target ready: {summary_obj.canonical_target_ready_rows}")


if __name__ == "__main__":
    main()
