from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.session_profile import (
    audit_summary,
    build_session_profiles,
    gap_priority_rows,
    profile_field_rows,
    readiness_rows,
    standards_evidence_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/validation/stage5j_cellular_ip_session_profiles"


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
    policy_path = ROOT / "datasets/stage5j_cellular_ip_session_profile.yml"
    stage5i_path = ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    stage5i_rows = _read_csv(stage5i_path)

    profiles = build_session_profiles(stage5i_rows, policy)
    fields = profile_field_rows(profiles, policy)
    readiness = readiness_rows(profiles, fields)
    standards = standards_evidence_rows(policy)
    gaps = gap_priority_rows(readiness)
    summary = audit_summary(profiles, fields, readiness, policy)

    OUT.mkdir(parents=True, exist_ok=True)
    profile_path = OUT / "cellular_ip_session_profiles.csv"
    field_path = OUT / "cellular_ip_session_profile_fields.csv"
    readiness_path = OUT / "candidate_session_readiness.csv"
    standards_path = OUT / "standards_constraint_ledger.csv"
    gap_path = OUT / "session_profile_gap_priorities.csv"
    _write_csv(profile_path, profiles)
    _write_csv(field_path, fields)
    _write_csv(readiness_path, readiness)
    _write_csv(standards_path, standards)
    _write_csv(gap_path, gaps)

    payload = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **summary.__dict__,
        "benchmark_lwm2m_operation": policy["scientific_policy"]["benchmark_lwm2m_operation"],
        "benchmark_payload_semantics": policy["scientific_policy"]["benchmark_payload_semantics"],
        "standards_evidence_rows": len(standards),
        "exact_tariff_volume_materialised": False,
        "canonical_report_energy_materialised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "The ten feasible IP-cellular incidences now share one reproducible telemetry transaction semantic: "
            "LwM2M Send, with scenario payload bytes defined before LwM2M/transport/security overhead and both uplink "
            "and downlink accounted for. Exact wire/session volume is intentionally not materialised because encoding, "
            "IP version, security-context lifecycle, retries and binding-specific fields remain unfrozen. The same missing "
            "session fields also prevent the Stage-5F Vomhoff source component from becoming canonical report energy."
        ),
        "preferred_next_step": "stage5k_parameterised_protocol_envelope_variants_without_claiming_empirical_usage",
        "profiles_artifact": "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profiles.csv",
        "fields_artifact": "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profile_fields.csv",
        "readiness_artifact": "results/validation/stage5j_cellular_ip_session_profiles/candidate_session_readiness.csv",
        "standards_artifact": "results/validation/stage5j_cellular_ip_session_profiles/standards_constraint_ledger.csv",
        "gap_priority_artifact": "results/validation/stage5j_cellular_ip_session_profiles/session_profile_gap_priorities.csv",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_run_manifest(
        OUT / "run_manifest.json",
        command="python scripts/audit_cellular_ip_session_profiles.py",
        inputs=[policy_path, stage5i_path],
        outputs=[profile_path, field_path, readiness_path, standards_path, gap_path, summary_path],
        parameters={"publication_mcda_authorised": False, "numeric_wire_volume_authorised": False},
    )

    print("Stage-5J cellular IP session-profile audit: OK")
    print(f"Feasible IP-cellular profile rows: {summary.feasible_ip_cellular_profile_rows}")
    print(f"CoAP/DTLS / MQTT/TLS profile rows: {summary.coap_dtls_profile_rows} / {summary.mqtt_tls_profile_rows}")
    print(f"Profile fields known-or-frozen / unresolved: {summary.known_or_frozen_field_rows} / {summary.unresolved_field_rows}")
    print(f"Profiles complete for exact tariff volume: {summary.profiles_complete_for_exact_tariff_volume}")
    print(f"Profiles complete for canonical report energy: {summary.profiles_complete_for_canonical_report_energy}")
    print("Canonical tariff-volume / report-energy rows: 0 / 0")


if __name__ == "__main__":
    main()
