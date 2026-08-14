from pathlib import Path

import yaml

from stackwise.stack_catalog import assess_verified_candidate_stack, load_component_catalog
from stackwise.stack_model import StructuralStatus


def _payload():
    return yaml.safe_load(Path("datasets/stage4_candidate_stacks.yml").read_text(encoding="utf-8"))


def test_stage4c_all_reference_candidates_require_verified_catalog_edges():
    catalog=load_component_catalog(); payload=_payload()
    assert len(payload["candidate_stacks"])==9
    for stack in payload["candidate_stacks"]:
        a=assess_verified_candidate_stack(stack,catalog)
        assert a.status is StructuralStatus.COMPATIBLE, (stack["stack_id"],a.errors)
        assert not any(e.startswith("binding_not_primary_source_verified:") for e in a.errors)


def test_stage4c_relation_mismatch_is_not_promoted_by_interface_match():
    catalog=load_component_catalog(); stack=dict(_payload()["candidate_stacks"][2])
    stack["component_instances"]=[dict(x) for x in stack["component_instances"]]
    stack["bindings"]=[dict(x) for x in stack["bindings"]]
    stack["bindings"][2]["relation"]="secures"  # TLS -> MQTT uses the same interface but verified relation is carries.
    a=assess_verified_candidate_stack(stack,catalog)
    assert a.status is StructuralStatus.INCOMPATIBLE
    assert any(e.startswith("binding_not_primary_source_verified:") for e in a.errors)


def test_stage4c_verified_candidate_cannot_use_evidence_only_component():
    catalog=load_component_catalog(); stack={
      "stack_id":"bad_ephesos","name":"bad","component_instances":[{"instance_id":"access","component_id":"ephesos_experimental_access","placement":"device"}],
      "bindings":[],"environment_capabilities":[],"primary_access_instance_id":"access","scientific_status":"verified_candidate"}
    a=assess_verified_candidate_stack(stack,catalog)
    assert a.status is StructuralStatus.INCOMPATIBLE
    assert any(e.startswith("verified_candidate_uses_unverified_component:") for e in a.errors)


def test_stage4c_empirical_support_is_never_full_end_to_end():
    payload=_payload(); support=payload["candidate_evidence_support"]
    assert len(support)==9
    assert all(r["full_end_to_end_empirical_support"] is False for r in support)
    assert sum(bool(r["alignment_ids"]) for r in support)==7
    classes={}
    for r in support: classes[r["support_class"]]=classes.get(r["support_class"],0)+1
    assert classes=={"partial_stack_context_only":5,"component_direct_boundary_only":2,"no_direct_core_four_alignment":2}


def test_stage4c_deferred_families_preserve_known_catalog_gaps():
    deferred={x["family_id"] for x in _payload()["deferred_candidate_families"]}
    assert deferred=={"bluetooth_ipsp_remote_service","bluetooth_gatt_gateway_service","uwb_remote_service","ephesos_remote_service"}
