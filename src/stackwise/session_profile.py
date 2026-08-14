from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SessionProfileSummary:
    feasible_ip_cellular_profile_rows: int
    coap_dtls_profile_rows: int
    mqtt_tls_profile_rows: int
    field_rows: int
    known_or_frozen_field_rows: int
    unresolved_field_rows: int
    profiles_complete_for_exact_tariff_volume: int
    profiles_complete_for_canonical_report_energy: int
    canonical_tariff_volume_rows: int
    canonical_report_energy_rows: int


def standards_evidence_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in policy.get("standards_evidence", [])]


def _binding_for_stack(policy: dict[str, Any], stack_id: str) -> dict[str, Any]:
    bindings = policy.get("ip_cellular_stack_bindings", {})
    if stack_id not in bindings:
        raise ValueError(f"No Stage-5J IP binding contract for stack {stack_id!r}.")
    return dict(bindings[stack_id])


def build_session_profiles(
    stage5i_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for row in stage5i_rows:
        ip_tariff = row.get("dated_ip_connectivity_tariff_evidence")
        if isinstance(ip_tariff, str):
            ip_tariff = ip_tariff.strip().lower() in {"true", "1", "yes"}
        if not ip_tariff:
            continue
        scenario_id = str(row["scenario_id"])
        stack_id = str(row["stack_id"])
        binding = _binding_for_stack(policy, stack_id)
        profiles.append(
            {
                "profile_id": f"stage5j_{scenario_id}__{stack_id}",
                "scenario_id": scenario_id,
                "stack_id": stack_id,
                "access_technology": binding["access_technology"],
                "binding_family": binding["binding_family"],
                "transport_protocol": binding["transport_protocol"],
                "security_protocol": binding["security_protocol"],
                "application_transport": binding["application_transport"],
                "application_payload_bytes": int(row["application_payload_bytes"]),
                "reporting_interval_s": int(row["reporting_interval_s"]),
                "application_payload_boundary": policy["scientific_policy"]["benchmark_payload_semantics"],
                "lwm2m_operation": policy["scientific_policy"]["benchmark_lwm2m_operation"],
                "account_uplink_and_downlink": True,
                "profile_status": "PARTIAL_STANDARD_CONSTRAINED",
                "exact_tariff_volume_ready": False,
                "canonical_report_energy_ready": False,
            }
        )
    return sorted(profiles, key=lambda r: (r["scenario_id"], r["stack_id"]))


def _allowed_values(spec: dict[str, Any]) -> str:
    values = spec.get("allowed_values")
    if not values:
        return ""
    return "|".join(str(v).lower() if isinstance(v, bool) else str(v) for v in values)


def profile_field_rows(profiles: Iterable[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    common = list(policy.get("common_profile_fields", []))
    specific = policy.get("binding_specific_fields", {})
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        binding_family = str(profile["binding_family"])
        specs = common + list(specific.get(binding_family, []))
        for spec in specs:
            field_id = str(spec["field_id"])
            source = str(spec["status_source"])
            status = "UNRESOLVED"
            value: Any = ""
            provenance_status = "unresolved"
            provenance_ref = ""
            if source == "stage5i_scenario_profile":
                value = profile[field_id]
                status = "KNOWN"
                provenance_status = "scenario_derived"
                provenance_ref = f"stage5i:{profile['scenario_id']}"
            elif source == "benchmark_frozen":
                value = spec["value"]
                status = "FROZEN"
                provenance_status = "benchmark_definition"
                provenance_ref = "stage5j_benchmark_transaction"
            elif source == "stack_derived":
                if field_id == "transport_binding_family":
                    value = profile["binding_family"]
                elif field_id == "security_protocol":
                    value = profile["security_protocol"]
                else:
                    raise ValueError(f"Unsupported stack-derived Stage-5J field {field_id!r}.")
                status = "KNOWN"
                provenance_status = "stack_derived"
                provenance_ref = profile["stack_id"]
            elif source == "tariff_contract_frozen":
                value = spec["value"]
                status = "FROZEN"
                provenance_status = "cost_accounting_contract"
                provenance_ref = "stage5i_one_nce_data_accounting"
            elif source != "unresolved":
                raise ValueError(f"Unsupported Stage-5J status_source {source!r} for {field_id!r}.")

            rows.append(
                {
                    "profile_id": profile["profile_id"],
                    "scenario_id": profile["scenario_id"],
                    "stack_id": profile["stack_id"],
                    "binding_family": binding_family,
                    "field_id": field_id,
                    "field_status": status,
                    "value": value,
                    "allowed_values": _allowed_values(spec),
                    "provenance_status": provenance_status,
                    "provenance_ref": provenance_ref,
                    "required_for_tariff_volume": bool(spec.get("required_for_tariff_volume")),
                    "required_for_energy_bridge": bool(spec.get("required_for_energy_bridge")),
                }
            )
    return rows


def readiness_rows(profiles: Iterable[dict[str, Any]], fields: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in fields:
        by_profile.setdefault(str(row["profile_id"]), []).append(row)
    out: list[dict[str, Any]] = []
    for profile in profiles:
        prows = by_profile[str(profile["profile_id"])]
        tariff_missing = sorted(
            r["field_id"]
            for r in prows
            if r["required_for_tariff_volume"] and r["field_status"] == "UNRESOLVED"
        )
        energy_missing = sorted(
            r["field_id"]
            for r in prows
            if r["required_for_energy_bridge"] and r["field_status"] == "UNRESOLVED"
        )
        out.append(
            {
                "profile_id": profile["profile_id"],
                "scenario_id": profile["scenario_id"],
                "stack_id": profile["stack_id"],
                "binding_family": profile["binding_family"],
                "known_or_frozen_fields": sum(r["field_status"] != "UNRESOLVED" for r in prows),
                "unresolved_fields": sum(r["field_status"] == "UNRESOLVED" for r in prows),
                "tariff_volume_missing_fields": "|".join(tariff_missing),
                "energy_bridge_missing_fields": "|".join(energy_missing),
                "exact_tariff_volume_ready": not tariff_missing,
                "canonical_report_energy_ready": not energy_missing,
                "tariff_volume_status": "READY" if not tariff_missing else "BLOCKED_PROFILE_INCOMPLETE",
                "energy_bridge_status": "READY" if not energy_missing else "BLOCKED_PROFILE_INCOMPLETE_AND_SOURCE_CONTEXT_MISMATCH",
            }
        )
    return out


def gap_priority_rows(readiness: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for row in readiness:
        ident = (str(row["scenario_id"]), str(row["stack_id"]))
        for target_col, target in [
            ("tariff_volume_missing_fields", "tariff_volume"),
            ("energy_bridge_missing_fields", "report_energy"),
        ]:
            for field in [x for x in str(row[target_col]).split("|") if x]:
                counts.setdefault((target, field), set()).add(ident)
    rows: list[dict[str, Any]] = []
    for (target, field), affected in counts.items():
        rows.append(
            {
                "target": target,
                "field_id": field,
                "affected_profile_rows": len(affected),
                "scenario_ids": "|".join(sorted({s for s, _ in affected})),
                "stack_ids": "|".join(sorted({t for _, t in affected})),
            }
        )
    return sorted(rows, key=lambda r: (-int(r["affected_profile_rows"]), str(r["target"]), str(r["field_id"])))


def audit_summary(
    profiles: Iterable[dict[str, Any]],
    fields: Iterable[dict[str, Any]],
    readiness: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> SessionProfileSummary:
    p = list(profiles)
    f = list(fields)
    r = list(readiness)
    summary = SessionProfileSummary(
        feasible_ip_cellular_profile_rows=len(p),
        coap_dtls_profile_rows=sum(x["binding_family"] == "coap_dtls_udp" for x in p),
        mqtt_tls_profile_rows=sum(x["binding_family"] == "mqtt_tls_tcp" for x in p),
        field_rows=len(f),
        known_or_frozen_field_rows=sum(x["field_status"] != "UNRESOLVED" for x in f),
        unresolved_field_rows=sum(x["field_status"] == "UNRESOLVED" for x in f),
        profiles_complete_for_exact_tariff_volume=sum(bool(x["exact_tariff_volume_ready"]) for x in r),
        profiles_complete_for_canonical_report_energy=sum(bool(x["canonical_report_energy_ready"]) for x in r),
        canonical_tariff_volume_rows=0,
        canonical_report_energy_rows=0,
    )
    expected = policy.get("expected", {})
    for key, actual in summary.__dict__.items():
        if key in expected and int(expected[key]) != int(actual):
            raise ValueError(f"Stage-5J checkpoint mismatch for {key}: expected={expected[key]} actual={actual}")
    return summary
