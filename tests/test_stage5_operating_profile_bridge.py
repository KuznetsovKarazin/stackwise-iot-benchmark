from pathlib import Path

import yaml

from stackwise.profile_bridge import assess_bridge_readiness, assess_profile, validate_bridge_contract, validate_operating_profile


def _policy():
    return yaml.safe_load(Path("datasets/stage5a_operating_profile_bridge_contracts.yml").read_text(encoding="utf-8"))


def test_stage5a_profiles_validate_and_remain_partial():
    profiles = _policy()["operating_profiles"]
    assert len(profiles) == 3
    assessments = []
    for profile in profiles:
        assert validate_operating_profile(profile) == []
        assessments.append(assess_profile(profile))
    assert all(a.completeness == "partial" for a in assessments)
    assert sum(len(a.unresolved_fields) for a in assessments) == 20


def test_stage5a_scenario_derived_fields_are_not_empirical():
    profiles = _policy()["operating_profiles"]
    known = [f for p in profiles for f in p["fields"] if f["status"] == "known"]
    assert len(known) == 6
    assert all(f["provenance_status"] == "scenario_derived" for f in known)
    assert all(f["provenance_status"] != "empirical_observed" for f in known)


def test_stage5a_all_bridges_blocked_and_no_profile_defaulting():
    policy = _policy()
    profiles = {(p["scenario_id"], p["stack_id"]): p for p in policy["operating_profiles"]}
    bridges = policy["bridge_contracts"]
    assert len(bridges) == 3
    results = []
    for bridge in bridges:
        assert validate_bridge_contract(bridge) == []
        results.append(assess_bridge_readiness(bridge, profiles[(bridge["scenario_id"], bridge["stack_id"])]))
    assert all(r.status == "blocked" for r in results)
    assert sum(bool(r.unresolved_profile_fields) for r in results) == 3
    assert policy["scientific_policy"]["infer_missing_profile_from_protocol_defaults"] is False
    assert policy["scientific_policy"]["infer_missing_profile_from_best_case_mode"] is False


def test_stage5a_lrfhss_contract_preserves_boundary_and_payload_mismatch():
    bridge = next(b for b in _policy()["bridge_contracts"] if b["bridge_id"] == "bridge_lrfhss_radio_to_whole_device_energy")
    assert bridge["source_evidence"]["status"] == "source_available_boundary_mismatch"
    assert bridge["source_evidence"]["source_boundary"]["system_scope"] == "radio_interface_only"
    assert bridge["source_evidence"]["source_boundary"]["payload_bytes"] == 4
    assert bridge["boundary_mapping"]["target_boundary"]["system_scope"] == "whole_device"
    assert bridge["boundary_mapping"]["target_boundary"]["payload_bytes"] == 16
    assert "linear_payload_scaling_without_validation" in bridge["boundary_mapping"]["forbidden_inferences"]
    assert "treat_radio_energy_as_whole_device_energy" in bridge["boundary_mapping"]["forbidden_inferences"]
