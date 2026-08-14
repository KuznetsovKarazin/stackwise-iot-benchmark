from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ProtocolEnvelopeSummary:
    source_profile_rows: int
    anchor_designs: int
    variant_rows: int
    coap_variant_rows: int
    mqtt_variant_rows: int
    variant_rows_with_complete_stage5j_unresolved_assignments: int
    raw_tariff_overhead_budget_rows: int
    unique_reporting_profiles: int
    exact_wire_volume_rows: int
    canonical_report_energy_rows: int


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _resolve_dynamic(value: Any, profile: dict[str, Any]) -> Any:
    if value == "HALF_REPORTING_INTERVAL":
        interval = int(profile["reporting_interval_s"])
        return max(1, interval // 2)
    return value


def _baseline_assignments(policy: dict[str, Any], binding_family: str) -> dict[str, Any]:
    base = dict(policy["baseline_assignments"]["common"])
    base.update(policy["baseline_assignments"][binding_family])
    return base


def build_protocol_envelope_variants(
    profiles: Iterable[dict[str, Any]],
    stage5j_fields: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    profile_rows = list(profiles)
    field_rows = list(stage5j_fields)
    unresolved_by_profile: dict[str, set[str]] = {}
    for row in field_rows:
        if str(row["field_status"]) == "UNRESOLVED":
            unresolved_by_profile.setdefault(str(row["profile_id"]), set()).add(str(row["field_id"]))

    out: list[dict[str, Any]] = []
    for profile in profile_rows:
        binding = str(profile["binding_family"])
        profile_id = str(profile["profile_id"])
        required = unresolved_by_profile.get(profile_id, set())
        for design in policy["anchor_designs"]:
            assignments = _baseline_assignments(policy, binding)
            assignments.update(design.get("common_overrides", {}))
            assignments.update(design.get(f"{binding}_overrides", {}))
            assignments = {k: _resolve_dynamic(v, profile) for k, v in assignments.items()}

            missing = sorted(required - set(assignments))
            extra = sorted(set(assignments) - required)
            if extra:
                raise ValueError(
                    f"Stage-5K anchor {design['anchor_id']} assigns non-unresolved fields for {profile_id}: {extra}"
                )

            row = {
                "variant_id": f"{profile_id}__{design['anchor_id']}",
                "profile_id": profile_id,
                "scenario_id": profile["scenario_id"],
                "stack_id": profile["stack_id"],
                "binding_family": binding,
                "access_technology": profile["access_technology"],
                "application_payload_bytes": int(profile["application_payload_bytes"]),
                "reporting_interval_s": int(profile["reporting_interval_s"]),
                "anchor_id": design["anchor_id"],
                "changed_dimensions": design["changed_dimensions"],
                "anchor_rationale": design["rationale"],
                "variant_semantics": policy["scientific_policy"]["variant_semantics"],
                "variant_probability": "",
                "variant_weight": "",
                "missing_stage5j_unresolved_fields": "|".join(missing),
                "stage5j_unresolved_assignments_complete": not missing,
                "exact_wire_volume_ready": False,
                "canonical_report_energy_ready": False,
            }
            row.update(assignments)
            out.append(row)
    return sorted(out, key=lambda r: (str(r["scenario_id"]), str(r["stack_id"]), str(r["anchor_id"])))


def variant_field_coverage_rows(
    variants: Iterable[dict[str, Any]],
    stage5j_fields: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    variant_rows = list(variants)
    unresolved_fields = sorted({str(r["field_id"]) for r in stage5j_fields if str(r["field_status"]) == "UNRESOLVED"})
    out: list[dict[str, Any]] = []
    for field_id in unresolved_fields:
        affected = [r for r in variant_rows if field_id in r]
        values = sorted({str(r[field_id]).lower() if isinstance(r[field_id], bool) else str(r[field_id]) for r in affected})
        out.append(
            {
                "field_id": field_id,
                "variant_rows_assigned": len(affected),
                "unique_assigned_values": len(values),
                "assigned_values": "|".join(values),
                "probability_or_frequency_interpretation": False,
            }
        )
    return out


def raw_tariff_overhead_budget_rows(
    profiles: Iterable[dict[str, Any]],
    stage5i_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    stage5i = {(str(r["scenario_id"]), str(r["stack_id"])): r for r in stage5i_rows}
    mb_bytes = int(policy["scientific_policy"]["tariff_megabyte_definition_bytes"])
    out: list[dict[str, Any]] = []
    for profile in profiles:
        key = (str(profile["scenario_id"]), str(profile["stack_id"]))
        source = stage5i[key]
        if not _as_bool(source.get("dated_ip_connectivity_tariff_evidence")):
            continue
        included_mb = int(float(source["included_data_mb"]))
        reports = int(float(source["five_year_report_count"]))
        payload = int(profile["application_payload_bytes"])
        included_bytes = included_mb * mb_bytes
        total_bytes_per_report = included_bytes / reports
        overhead_budget = total_bytes_per_report - payload
        out.append(
            {
                "profile_id": profile["profile_id"],
                "scenario_id": profile["scenario_id"],
                "stack_id": profile["stack_id"],
                "binding_family": profile["binding_family"],
                "reporting_interval_s": int(profile["reporting_interval_s"]),
                "application_payload_bytes": payload,
                "five_year_report_count": reports,
                "included_data_mb": included_mb,
                "included_data_bytes": included_bytes,
                "raw_total_transport_budget_bytes_per_report": total_bytes_per_report,
                "raw_non_application_overhead_budget_bytes_per_report": overhead_budget,
                "overhead_budget_to_application_payload_ratio": overhead_budget / payload,
                "budget_is_billing_rounding_adjusted": False,
                "budget_interpretation": (
                    "Aggregate raw-byte ceiling implied by the 500-MB allowance before any unknown tariff accounting "
                    "rounding interval. It is not proof of tariff sufficiency and does not include a protocol model."
                ),
            }
        )
    return sorted(out, key=lambda r: (str(r["scenario_id"]), str(r["stack_id"])))


def standards_evidence_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in policy.get("standards_evidence", [])]


def audit_summary(
    profiles: Iterable[dict[str, Any]],
    variants: Iterable[dict[str, Any]],
    budgets: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> ProtocolEnvelopeSummary:
    p = list(profiles)
    v = list(variants)
    b = list(budgets)
    summary = ProtocolEnvelopeSummary(
        source_profile_rows=len(p),
        anchor_designs=len(policy["anchor_designs"]),
        variant_rows=len(v),
        coap_variant_rows=sum(str(r["binding_family"]) == "coap_dtls_udp" for r in v),
        mqtt_variant_rows=sum(str(r["binding_family"]) == "mqtt_tls_tcp" for r in v),
        variant_rows_with_complete_stage5j_unresolved_assignments=sum(
            bool(r["stage5j_unresolved_assignments_complete"]) for r in v
        ),
        raw_tariff_overhead_budget_rows=len(b),
        unique_reporting_profiles=len({(int(r["reporting_interval_s"]), int(r["application_payload_bytes"])) for r in p}),
        exact_wire_volume_rows=sum(bool(r["exact_wire_volume_ready"]) for r in v),
        canonical_report_energy_rows=sum(bool(r["canonical_report_energy_ready"]) for r in v),
    )
    expected = policy.get("expected", {})
    for key, actual in summary.__dict__.items():
        if key in expected and int(expected[key]) != int(actual):
            raise ValueError(f"Stage-5K checkpoint mismatch for {key}: expected={expected[key]} actual={actual}")
    return summary
