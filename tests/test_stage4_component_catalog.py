from pathlib import Path

import yaml

from stackwise.stack_catalog import load_component_catalog, validate_component_catalog
from stackwise.stack_model import StructuralStatus, assess_stack_structure, validate_stack_candidate


def test_stage4b_catalog_is_internally_verified():
    catalog = load_component_catalog()
    assert validate_component_catalog(catalog) == []
    components = catalog["components"]
    assert len(components) == 25
    assert sum(c["catalog_status"] == "primary_source_verified" for c in components) == 24
    assert len(catalog["compatibility_edges"]) == 32
    assert len(catalog["unresolved_catalog_gaps"]) == 6


def test_alternative_requirements_allow_real_protocol_bindings_without_false_and_semantics():
    catalog = load_component_catalog()
    cmap = {c["component_id"]: c for c in catalog["components"]}
    lwm2m = cmap["lwm2m12"]
    alternatives = set(lwm2m["requires_any"][0])
    assert "lorawan_nonip_transport_service" in alternatives
    assert "ciot_nonip_service" in alternatives
    assert "secure_mqtt_message_service" in alternatives
    assert "secure_http_message_service" in alternatives


def test_ble_ip_is_explicit_profile_not_bare_ble_assumption():
    catalog = load_component_catalog()
    cmap = {c["component_id"]: c for c in catalog["components"]}
    assert "ip_packet_service" not in cmap["bluetooth_le_access"]["provides"]
    assert "ip_packet_service" in cmap["bluetooth_ipsp_ipv6"]["provides"]
    assert cmap["bluetooth_ipsp_ipv6"]["requires"] == ["ble_le_l2cap_service"]


def test_cellular_ip_and_nonip_are_separate_variants():
    catalog = load_component_catalog()
    cmap = {c["component_id"]: c for c in catalog["components"]}
    assert "ip_packet_service" in cmap["3gpp_nbiot_eps_ip"]["provides"]
    assert "ciot_nonip_service" in cmap["3gpp_nbiot_eps_nonip"]["provides"]
    assert "ip_packet_service" not in cmap["3gpp_nbiot_eps_nonip"]["provides"]


def test_lora_and_lrfhss_are_distinct_evidence_modes():
    catalog = load_component_catalog()
    amap = {a["alignment_id"]: a for a in catalog["evidence_alignment"]}
    assert amap["loed_lora_direct"]["component_id"] == "lorawan_lora_access"
    assert amap["lrfhss_direct"]["component_id"] == "lorawan_lrfhss_access"
    assert any(g["gap_id"] == "loed_vs_lrfhss_link_mode" for g in catalog["unresolved_catalog_gaps"])


def test_real_component_structural_verification_stacks_have_expected_status():
    catalog = load_component_catalog()
    fixture = yaml.safe_load(Path("tests/fixtures_stage4b_verified_stacks.yml").read_text(encoding="utf-8"))
    for name, stack in fixture["stacks"].items():
        assert validate_stack_candidate(stack) == []
        assessment = assess_stack_structure(stack, catalog["components"])
        assert assessment.status.value == fixture["expected_status"][name]
    assert assess_stack_structure(fixture["stacks"]["lrfhss_lwm2m_nonip"], catalog["components"]).status is StructuralStatus.COMPATIBLE
