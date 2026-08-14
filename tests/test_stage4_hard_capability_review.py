from pathlib import Path

import yaml

from stackwise.hard_capability_review import build_refined_scenarios, overlay_reviewed_capabilities
from stackwise.scenario_screening import compose_scenario_candidate_facts, load_benchmark_scenarios, validate_benchmark_scenario
from stackwise.stack_catalog import load_component_catalog
from stackwise.stack_model import evaluate_hard_constraints


def _candidates():
    return yaml.safe_load(Path("datasets/stage4_candidate_stacks.yml").read_text(encoding="utf-8"))["candidate_stacks"]


def _review():
    return yaml.safe_load(Path("datasets/stage4e_hard_capability_review.yml").read_text(encoding="utf-8"))


def test_stage4e_mobility_is_split_not_chosen_post_hoc():
    scenarios, changes = build_refined_scenarios(load_benchmark_scenarios())
    ids = {s["scenario_id"] for s in scenarios}
    assert len(scenarios) == 7
    assert "asset_tracking_mobility" not in ids
    assert {c["refined_scenario_id"] for c in changes} == {
        "asset_tracking_periodic_cross_cell", "asset_tracking_connected_handover"
    }
    assert all(c["post_hoc_preference_choice"] is False for c in changes)
    assert all(validate_benchmark_scenario(s) == [] for s in scenarios)


def test_stage4e_cellular_mobility_capabilities_keep_modes_distinct():
    catalog = load_component_catalog()
    review = _review()
    rows = {s["stack_id"]: overlay_reviewed_capabilities(s, catalog, review) for s in _candidates()}
    assert rows["nbiot_ip_coap_dtls_lwm2m"]["idle_cell_reselection_supported_verified"] is True
    assert rows["nbiot_ip_coap_dtls_lwm2m"]["connected_mode_handover_supported_verified"] is False
    assert rows["ltem_ip_coap_dtls_lwm2m"]["idle_cell_reselection_supported_verified"] is True
    assert rows["ltem_ip_coap_dtls_lwm2m"]["connected_mode_handover_supported_verified"] is True


def test_stage4e_does_not_invent_thread_latency_or_lorawan_whole_device_energy():
    catalog = load_component_catalog()
    review = _review()
    rows = {s["stack_id"]: overlay_reviewed_capabilities(s, catalog, review) for s in _candidates()}
    assert rows["thread_coap_dtls_lwm2m"]["guaranteed_max_end_to_end_latency_ms"] is None
    assert rows["lorawan_lora_lwm2m_nonip"]["expected_device_energy_per_report_j"] is None
    assert rows["lorawan_lrfhss_lwm2m_nonip"]["expected_device_energy_per_report_j"] is None


def test_stage4e_refined_screen_has_only_three_decision_blockers():
    catalog = load_component_catalog()
    review = _review()
    scenarios, _ = build_refined_scenarios(load_benchmark_scenarios())
    candidates = _candidates()
    caps = {s["stack_id"]: overlay_reviewed_capabilities(s, catalog, review) for s in candidates}
    counts = {"feasible":0,"infeasible":0,"unresolved":0}
    blockers = []
    by_scenario = {}
    for scenario in scenarios:
        for stack in candidates:
            facts = compose_scenario_candidate_facts(caps[stack["stack_id"]], scenario)
            a = evaluate_hard_constraints(facts, scenario["hard_constraints"])
            counts[a.status.value] += 1
            by_scenario.setdefault(scenario["scenario_id"], {"feasible":0,"infeasible":0,"unresolved":0})[a.status.value] += 1
            if a.status.value == "unresolved":
                blockers.extend(r for r in a.results if r.status == "unknown")
    assert counts == {"feasible":21,"infeasible":39,"unresolved":3}
    assert len(blockers) == 3
    assert by_scenario["asset_tracking_periodic_cross_cell"] == {"feasible":6,"infeasible":3,"unresolved":0}
    assert by_scenario["asset_tracking_connected_handover"] == {"feasible":3,"infeasible":6,"unresolved":0}
