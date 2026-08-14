from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.protocol_envelope import (
    audit_summary,
    build_protocol_envelope_variants,
    raw_tariff_overhead_budget_rows,
    standards_evidence_rows,
    variant_field_coverage_rows,
)
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5k_protocol_envelope_variants"


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
    policy_path = ROOT / "datasets/stage5k_protocol_envelope_variants.yml"
    profile_path = ROOT / "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profiles.csv"
    field_path = ROOT / "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profile_fields.csv"
    stage5i_path = ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv"

    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    profiles = _read_csv(profile_path)
    fields = _read_csv(field_path)
    stage5i = _read_csv(stage5i_path)

    variants = build_protocol_envelope_variants(profiles, fields, policy)
    coverage = variant_field_coverage_rows(variants, fields)
    budgets = raw_tariff_overhead_budget_rows(profiles, stage5i, policy)
    standards = standards_evidence_rows(policy)
    summary = audit_summary(profiles, variants, budgets, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    variants_path = OUT / "protocol_envelope_variants.csv"
    coverage_path = OUT / "variant_field_coverage.csv"
    budgets_path = OUT / "raw_tariff_overhead_budgets.csv"
    standards_path = OUT / "standards_constraint_ledger.csv"
    _write_csv(variants_path, variants)
    _write_csv(coverage_path, coverage)
    _write_csv(budgets_path, budgets)
    _write_csv(standards_path, standards)

    budget_by_profile = {}
    for row in budgets:
        key = (int(row["reporting_interval_s"]), int(row["application_payload_bytes"]))
        budget_by_profile.setdefault(key, float(row["raw_non_application_overhead_budget_bytes_per_report"]))

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "variant_probabilities_assigned": False,
        "full_cartesian_product_enumerated": False,
        "raw_tariff_overhead_budget_by_reporting_profile": [
            {
                "reporting_interval_s": k[0],
                "application_payload_bytes": k[1],
                "raw_non_application_overhead_budget_bytes_per_report": v,
            }
            for k, v in sorted(budget_by_profile.items())
        ],
        "tariff_topup_count_materialised": False,
        "exact_wire_volume_materialised": False,
        "canonical_report_energy_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "Stage 5K replaces the 130 unresolved Stage-5J profile-field cells with nine deterministic sensitivity "
            "anchors per profile (90 variant rows) without assigning probabilities or claiming typical deployment. "
            "All Stage-5J unresolved fields receive explicit variant assignments, but exact wire bytes remain blocked "
            "because serialized LwM2M payload length and security/session handshake traffic are not yet computed. "
            "The 500-MB tariff implies only a raw aggregate non-application overhead budget of about 2651.93 bytes/report "
            "for the 900-s/200-B profile and 126.13 bytes/report for the 60-s/64-B profile before unknown billing granularity."
        ),
        "preferred_next_step": (
            "stage5l_standards_accounting_engine_for_steady_state_wire_bytes_then_security_session_increment_envelopes"
        ),
        "variants_artifact": "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv",
        "coverage_artifact": "results/validation/stage5k_protocol_envelope_variants/variant_field_coverage.csv",
        "tariff_budget_artifact": "results/validation/stage5k_protocol_envelope_variants/raw_tariff_overhead_budgets.csv",
        "standards_artifact": "results/validation/stage5k_protocol_envelope_variants/standards_constraint_ledger.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_protocol_envelope_variants.py",
        inputs=[policy_path, profile_path, field_path, stage5i_path],
        outputs=[variants_path, coverage_path, budgets_path, standards_path, summary_path],
        parameters={
            "variant_probabilities_assigned": False,
            "full_cartesian_product_enumerated": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5K protocol-envelope variant audit: OK")
    print(f"Source profiles / anchor designs / variant rows: {summary.source_profile_rows} / {summary.anchor_designs} / {summary.variant_rows}")
    print(f"CoAP/DTLS / MQTT/TLS variant rows: {summary.coap_variant_rows} / {summary.mqtt_variant_rows}")
    print(
        "Variants with complete Stage-5J unresolved assignments: "
        f"{summary.variant_rows_with_complete_stage5j_unresolved_assignments}"
    )
    print(f"Raw tariff overhead-budget rows: {summary.raw_tariff_overhead_budget_rows}")
    for key, value in sorted(budget_by_profile.items()):
        print(f"Raw non-application overhead budget ({key[0]} s / {key[1]} B): {value:.6f} bytes/report")
    print(f"Exact wire-volume / canonical report-energy rows: {summary.exact_wire_volume_rows} / {summary.canonical_report_energy_rows}")


if __name__ == "__main__":
    main()
