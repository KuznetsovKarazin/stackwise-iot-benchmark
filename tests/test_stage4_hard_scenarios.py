from pathlib import Path

import yaml

from stackwise.scenario_screening import (
    derive_candidate_hard_capabilities,
    load_benchmark_scenarios,
    screening_matrix,
    validate_benchmark_scenario,
)
from stackwise.stack_catalog import load_component_catalog


def _candidates():
    return yaml.safe_load(Path("datasets/stage4_candidate_stacks.yml").read_text(encoding="utf-8"))["candidate_stacks"]


def test_stage4d_scenarios_validate_and_context_is_not_automatically_hard():
    payload = load_benchmark_scenarios()
    assert payload["scientific_policy"]["quantitative_context_implies_hard_constraint"] is False
    assert len(payload["scenarios"]) == 6
    for scenario in payload["scenarios"]:
        assert validate_benchmark_scenario(scenario) == []


def test_stage4d_candidate_hard_capabilities_preserve_unknown_numeric_facts():
    catalog = load_component_catalog()
    rows = [derive_candidate_hard_capabilities(s, catalog) for s in _candidates()]
    assert len(rows) == 9
    assert all(r["max_application_payload_bytes"] is None for r in rows)
    assert all(r["guaranteed_max_end_to_end_latency_ms"] is None for r in rows)
    assert all(r["expected_device_energy_per_report_j"] is None for r in rows)
    assert all(r["mobility_supported_verified"] is None for r in rows)
    by_id = {r["stack_id"]: r for r in rows}
    assert by_id["nbiot_ip_coap_dtls_lwm2m"]["device_network_mode"] == "ip"
    assert by_id["nbiot_nonip_lwm2m"]["device_network_mode"] == "nonip"
    assert by_id["lorawan_lora_lwm2m_nonip"]["requires_lorawan_service"] is True
    assert by_id["thread_coap_dtls_lwm2m"]["requires_thread_border_router"] is True


def test_stage4d_frozen_screening_status_counts_are_tri_state_and_noncompensatory():
    catalog = load_component_catalog()
    scenarios = load_benchmark_scenarios()["scenarios"]
    rows = screening_matrix(_candidates(), catalog, scenarios)
    assert len(rows) == 54
    counts = {k: sum(r["status"] == k for r in rows) for k in ["feasible", "infeasible", "unresolved"]}
    assert counts == {"feasible": 12, "infeasible": 33, "unresolved": 9}
    by_scenario = {}
    for row in rows:
        d = by_scenario.setdefault(row["scenario_id"], {"feasible": 0, "infeasible": 0, "unresolved": 0})
        d[row["status"]] += 1
    assert by_scenario["environmental_private_lorawan"] == {"feasible": 2, "infeasible": 7, "unresolved": 0}
    assert by_scenario["smart_meter_public_cellular"] == {"feasible": 6, "infeasible": 3, "unresolved": 0}
    assert by_scenario["industrial_private_ipv6_low_latency"] == {"feasible": 0, "infeasible": 8, "unresolved": 1}
    assert by_scenario["urban_nonip_dual_access"] == {"feasible": 4, "infeasible": 5, "unresolved": 0}
    assert by_scenario["asset_tracking_mobility"] == {"feasible": 0, "infeasible": 3, "unresolved": 6}
    assert by_scenario["remote_agriculture_energy_budget"] == {"feasible": 0, "infeasible": 7, "unresolved": 2}


def test_stage4d_unknown_hard_capability_blocks_feasible_claim():
    catalog = load_component_catalog()
    scenarios = {s["scenario_id"]: s for s in load_benchmark_scenarios()["scenarios"]}
    stacks = {s["stack_id"]: s for s in _candidates()}
    rows = screening_matrix(
        [stacks["thread_coap_dtls_lwm2m"]], catalog, [scenarios["industrial_private_ipv6_low_latency"]]
    )
    assert rows[0]["status"] == "unresolved"
    latency = next(r for r in rows[0]["constraint_results"] if r["constraint_id"] == "latency_ceiling")
    assert latency["status"] == "unknown"


def test_stage4d_infeasible_precedes_unknown_when_a_hard_constraint_fails():
    catalog = load_component_catalog()
    scenarios = {s["scenario_id"]: s for s in load_benchmark_scenarios()["scenarios"]}
    stacks = {s["stack_id"]: s for s in _candidates()}
    rows = screening_matrix(
        [stacks["nbiot_ip_coap_dtls_lwm2m"]], catalog, [scenarios["industrial_private_ipv6_low_latency"]]
    )
    assert rows[0]["status"] == "infeasible"
    assert any(r["status"] == "fail" for r in rows[0]["constraint_results"])
    assert any(r["status"] == "unknown" for r in rows[0]["constraint_results"])
