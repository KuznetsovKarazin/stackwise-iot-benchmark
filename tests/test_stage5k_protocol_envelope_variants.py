from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from stackwise.protocol_envelope import (
    audit_summary,
    build_protocol_envelope_variants,
    raw_tariff_overhead_budget_rows,
    variant_field_coverage_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inputs():
    policy = yaml.safe_load((ROOT / "datasets/stage5k_protocol_envelope_variants.yml").read_text(encoding="utf-8"))
    profiles = _csv(ROOT / "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profiles.csv")
    fields = _csv(ROOT / "results/validation/stage5j_cellular_ip_session_profiles/cellular_ip_session_profile_fields.csv")
    stage5i = _csv(ROOT / "results/validation/stage5i_dated_cellular_cost_evidence/candidate_cost_evidence_readiness.csv")
    variants = build_protocol_envelope_variants(profiles, fields, policy)
    budgets = raw_tariff_overhead_budget_rows(profiles, stage5i, policy)
    return policy, profiles, fields, variants, budgets


def test_stage5k_materialises_nine_anchors_per_profile_without_cartesian_product():
    policy, profiles, _, variants, budgets = _inputs()
    summary = audit_summary(profiles, variants, budgets, policy)
    assert summary.source_profile_rows == 10
    assert summary.anchor_designs == 9
    assert summary.variant_rows == 90
    assert summary.coap_variant_rows == 45
    assert summary.mqtt_variant_rows == 45
    assert policy["scientific_policy"]["enumerate_full_cartesian_product"] is False


def test_stage5k_assigns_every_stage5j_unresolved_field_in_every_variant():
    policy, profiles, fields, variants, budgets = _inputs()
    summary = audit_summary(profiles, variants, budgets, policy)
    assert summary.variant_rows_with_complete_stage5j_unresolved_assignments == 90
    assert all(not row["missing_stage5j_unresolved_fields"] for row in variants)
    coverage = variant_field_coverage_rows(variants, fields)
    assert len(coverage) == 21
    assert all(int(row["variant_rows_assigned"]) > 0 for row in coverage)


def test_stage5k_variants_have_no_probabilities_or_frequency_weights():
    policy, _, _, variants, _ = _inputs()
    assert policy["scientific_policy"]["assign_variant_probabilities"] is False
    assert policy["scientific_policy"]["use_variant_frequency_weights"] is False
    assert all(row["variant_probability"] == "" for row in variants)
    assert all(row["variant_weight"] == "" for row in variants)


def test_stage5k_compact_grid_covers_all_three_lwm2m_send_encodings_and_both_ip_families():
    _, _, _, variants, _ = _inputs()
    assert {row["lwm2m_payload_encoding"] for row in variants} == {"SenML_CBOR", "LwM2M_CBOR", "SenML_JSON"}
    assert {row["ip_version"] for row in variants} == {"IPv4", "IPv6"}


def test_stage5k_binding_sensitivity_covers_coap_confirmability_and_all_mqtt_qos_levels():
    _, _, _, variants, _ = _inputs()
    coap = [r for r in variants if r["binding_family"] == "coap_dtls_udp"]
    mqtt = [r for r in variants if r["binding_family"] == "mqtt_tls_tcp"]
    assert {r["coap_message_type"] for r in coap} == {"NON", "CON"}
    assert {int(r["mqtt_qos"]) for r in mqtt} == {0, 1, 2}


def test_stage5k_security_and_retry_axes_are_deterministic_sensitivity_anchors():
    _, _, _, variants, _ = _inputs()
    security = {r["security_context_lifecycle"] for r in variants}
    retries = {r["failure_retry_retransmission_profile"] for r in variants}
    assert security == {"persistent_across_reports", "resumed_security_context", "full_security_context_reestablishment"}
    assert retries == {"no_application_retry", "one_full_transaction_retry_per_application_report"}


def test_stage5k_tariff_budget_is_raw_aggregate_not_billing_rounding_claim():
    _, _, _, _, budgets = _inputs()
    assert len(budgets) == 10
    assert all(row["budget_is_billing_rounding_adjusted"] is False for row in budgets)
    by_profile = {}
    for row in budgets:
        by_profile.setdefault((int(row["reporting_interval_s"]), int(row["application_payload_bytes"])), row)
    assert float(by_profile[(900, 200)]["raw_non_application_overhead_budget_bytes_per_report"]) == pytest.approx(2651.9279032626055)
    assert float(by_profile[(60, 64)]["raw_non_application_overhead_budget_bytes_per_report"]) == pytest.approx(126.12852688417371)


def test_stage5k_does_not_authorise_exact_wire_volume_energy_or_mcda():
    policy, profiles, _, variants, budgets = _inputs()
    summary = audit_summary(profiles, variants, budgets, policy)
    assert summary.exact_wire_volume_rows == 0
    assert summary.canonical_report_energy_rows == 0
    assert policy["scientific_policy"]["exact_wire_volume_authorised"] is False
    assert policy["scientific_policy"]["canonical_report_energy_authorised"] is False
    assert policy["scientific_policy"]["publication_mcda_authorised"] is False
