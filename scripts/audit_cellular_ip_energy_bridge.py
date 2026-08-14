from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from stackwise.cellular_energy_bridge import (
    audit_summary,
    build_candidate_bridge_audit,
    materialise_source_active_components,
)
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
    ap = argparse.ArgumentParser(description="Stage-5F audit of the Vomhoff cellular-IP report-energy bridge.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5f_cellular_ip_energy_bridge.yml"))
    ap.add_argument("--feasibility", type=Path, default=Path("results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv"))
    ap.add_argument("--marginal", type=Path, default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/marginal_calibration.csv"))
    ap.add_argument("--bootstrap", type=Path, default=Path("data/analysis_ready/vomhoff_nbiot_ltem_energy_2023/uncertainty/block_bootstrap_means.parquet"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_cellular_ip_energy_bridge"))
    ap.add_argument("--contract-only", action="store_true", help="Audit transfer contract without reading local data/ bootstrap artifacts.")
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    feasibility = _read_csv(args.feasibility)
    audit_rows = build_candidate_bridge_audit(feasibility_rows=feasibility, policy=policy)
    summary_obj = audit_summary(audit_rows, policy)

    args.output.mkdir(parents=True, exist_ok=True)
    audit_path = args.output / "candidate_bridge_audit.csv"
    _write_csv(audit_path, audit_rows)

    source_summary_path = args.output / "source_active_component_summary.csv"
    source_draws_path = args.output / "source_active_component_bootstrap.parquet"
    numeric_source_component_materialised = False
    source_summary_rows = 0
    if not args.contract_only:
        marginal = pd.read_csv(args.marginal)
        draws = pd.read_parquet(args.bootstrap)
        source_summary, source_draws = materialise_source_active_components(
            marginal=marginal, bootstrap_draws=draws, policy=policy
        )
        source_summary.to_csv(source_summary_path, index=False)
        source_draws.to_parquet(source_draws_path, index=False)
        numeric_source_component_materialised = True
        source_summary_rows = len(source_summary)

    handoff_rows = [
        {"rule_id":"canonical_target_remains_blocked","policy_state":"required","rule":"Do not write expected_device_energy_per_application_report_j for any Stage-5F cellular-IP candidate incidence from Vomhoff alone."},
        {"rule_id":"payload_bridge_needed","policy_state":"required","rule":"All frozen feasible cellular-IP scenarios use 64 B or 200 B application payloads, whereas retained Vomhoff transfer evidence is 1024 B; no payload scaling is identified by the retained dataset."},
        {"rule_id":"upper_layer_bridge_needed","policy_state":"required","rule":"HTTP cannot be silently transferred to CoAP/DTLS/LwM2M; NB-IoT MQTT is only partial context and LTE-M has no MQTT source in the retained Vomhoff evidence."},
        {"rule_id":"report_cycle_bridge_needed","policy_state":"required","rule":"The source active component excludes Standby/Idle; reporting-interval energy requires an explicit connected/idle/PSM/eDRX state model rather than scaling the source tail phases."},
        {"rule_id":"source_component_use","policy_state":"authorised_diagnostic_only","rule":"The dependence-preserving 1 KB source active transaction component may be reported as a source-boundary diagnostic and used to validate future transfer models."},
        {"rule_id":"next_stage","policy_state":"authorised","rule":"Stage 5G should close the transfer gap with targeted external/model/testbed evidence for payload scaling, upper-layer protocol context and reporting-cycle state energy; lifecycle-cost contract remains mandatory in parallel."},
        {"rule_id":"publication_mcda","policy_state":"prohibited","rule":"Publication MCDA remains blocked."},
    ]
    handoff_path = args.output / "stage5g_handoff_rules.csv"
    _write_csv(handoff_path, handoff_rows)

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        "feasible_cellular_ip_candidate_incidences": summary_obj.feasible_candidate_incidences,
        "source_reference_contexts": summary_obj.source_reference_contexts,
        "canonical_target_ready_rows": summary_obj.canonical_target_ready_rows,
        "payload_mismatch_rows": summary_obj.payload_mismatch_rows,
        "exact_application_context_rows": summary_obj.exact_application_context_rows,
        "numeric_source_active_component_materialised": numeric_source_component_materialised,
        "source_active_component_summary_rows": source_summary_rows,
        "canonical_target_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": "Vomhoff can support a dependence-preserving whole-device source-active transaction component at its retained 1 KB HTTP/MQTT contexts, but it does not identify the canonical 64/200-byte candidate-stack application-report energy. Payload transfer, exact upper-layer context and report-cycle state accounting remain structural gaps.",
        "next_scientific_step": "Stage 5G: obtain or validate targeted transfer evidence/model(s) for payload dependence, candidate upper-layer context and reporting-cycle state energy. Do not add broad datasets; close these explicit bridge gaps. In parallel, build the dated lifecycle-cost contract.",
        "candidate_bridge_audit_artifact": str(audit_path),
        "source_active_component_summary_artifact": str(source_summary_path) if numeric_source_component_materialised else None,
        "source_active_component_bootstrap_artifact": str(source_draws_path) if numeric_source_component_materialised else None,
        "stage5g_handoff_rules_artifact": str(handoff_path),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest_path = args.output / "run_manifest.json"
    inputs = [args.policy, args.feasibility]
    if not args.contract_only:
        inputs += [args.marginal, args.bootstrap]
    outputs = [audit_path, handoff_path, summary_path]
    if numeric_source_component_materialised:
        outputs += [source_summary_path, source_draws_path]
    write_run_manifest(
        manifest_path,
        command="python scripts/audit_cellular_ip_energy_bridge.py" + (" --contract-only" if args.contract_only else ""),
        inputs=inputs,
        outputs=outputs,
        parameters={
            "source_active_component_diagnostic_only": True,
            "canonical_target_materialisation_authorised": False,
            "payload_scaling_without_model": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5F cellular-IP energy bridge audit: OK")
    print(f"Feasible cellular-IP incidences: {summary_obj.feasible_candidate_incidences}")
    print(f"Source reference contexts: {summary_obj.source_reference_contexts}")
    print(f"Canonical target ready: {summary_obj.canonical_target_ready_rows}")
    print(f"Payload mismatch rows: {summary_obj.payload_mismatch_rows}")
    print(f"Exact application-context rows: {summary_obj.exact_application_context_rows}")
    if numeric_source_component_materialised:
        print(f"Source active-component rows materialised: {source_summary_rows}")
    else:
        print("Source active-component numeric materialisation: skipped (--contract-only)")


if __name__ == "__main__":
    main()
