from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.stack_catalog import load_component_catalog, validate_component_catalog
from stackwise.stack_model import StructuralStatus, assess_stack_structure, validate_stack_candidate


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/materialise the STACKWISE Stage-4B verified component catalog.")
    parser.add_argument("--catalog", type=Path, default=Path("datasets/stack_component_catalog.yml"))
    parser.add_argument("--policy", type=Path, default=Path("datasets/stage4_component_catalog_policy.yml"))
    parser.add_argument("--stacks", type=Path, default=Path("tests/fixtures_stage4b_verified_stacks.yml"))
    parser.add_argument("--output", type=Path, default=Path("results/validation/stage4_component_catalog"))
    args = parser.parse_args()

    catalog = load_component_catalog(args.catalog)
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    fixture = yaml.safe_load(args.stacks.read_text(encoding="utf-8")) or {}
    errors = validate_component_catalog(catalog)

    components = catalog.get("components") or []
    sources = catalog.get("sources") or {}
    claims = catalog.get("claims") or {}
    edges = catalog.get("compatibility_edges") or []
    alignments = catalog.get("evidence_alignment") or []
    gaps = catalog.get("unresolved_catalog_gaps") or []
    verified = [c for c in components if c.get("catalog_status") == "primary_source_verified"]
    pending = [c for c in components if c.get("catalog_status") != "primary_source_verified"]

    stacks = fixture.get("stacks") or {}
    expected_status = fixture.get("expected_status") or {}
    structural = {}
    for name, stack in stacks.items():
        for err in validate_stack_candidate(stack):
            errors.append(f"verification_stack_schema:{name}:{err}")
        assessment = assess_stack_structure(stack, components)
        structural[name] = assessment
        if assessment.status.value != expected_status.get(name):
            errors.append(f"verification_stack_status:{name}:expected={expected_status.get(name)}:actual={assessment.status.value}")

    compatible = sum(a.status is StructuralStatus.COMPATIBLE for a in structural.values())
    incompatible = sum(a.status is StructuralStatus.INCOMPATIBLE for a in structural.values())
    expected = policy.get("expected") or {}
    checkpoints = {
        "primary_sources": len(sources),
        "verified_claims": len(claims),
        "catalog_components": len(components),
        "primary_source_verified_components": len(verified),
        "evidence_only_pending_components": len(pending),
        "verified_compatibility_edges": sum(e.get("status") == "primary_source_verified_compatible" for e in edges),
        "evidence_alignment_records": len(alignments),
        "unresolved_catalog_gaps": len(gaps),
        "structural_verification_stacks": len(stacks),
        "compatible_verification_stacks": compatible,
        "incompatible_verification_stacks": incompatible,
    }
    for key, actual in checkpoints.items():
        if actual != expected.get(key):
            errors.append(f"checkpoint:{key}:expected={expected.get(key)}:actual={actual}")

    guards = policy.get("scientific_guards") or {}
    for key in [
        "standards_claim_without_primary_source_authorised",
        "unverified_binding_counts_as_compatible",
        "evidence_alignment_implies_component_causality",
        "ephesos_verified_stack_authorised",
        "lora_link_evidence_reused_for_lrfhss_authorised",
        "insectt_ble_reused_as_ipsp_energy_authorised",
        "mcda_authorised",
        "ranking_authorised",
        "stakeholder_weights_authorised",
    ]:
        if guards.get(key) is not False:
            errors.append(f"scientific_guard_not_false:{key}")

    # High-leverage semantic assertions from the primary-source review.
    cmap = {c["component_id"]: c for c in components}
    if "ip_packet_service" in cmap["lorawan_lora_access"]["provides"]:
        errors.append("lorawan_lora_must_not_silently_provide_ip")
    if "ip_packet_service" in cmap["bluetooth_le_access"]["provides"]:
        errors.append("bare_ble_must_not_silently_provide_ip")
    if "ip_packet_service" not in cmap["bluetooth_ipsp_ipv6"]["provides"]:
        errors.append("ble_ipsp_must_provide_ip")
    if "ciot_nonip_service" not in cmap["3gpp_nbiot_eps_nonip"]["provides"]:
        errors.append("nbiot_nonip_variant_missing")
    lwm2m_alternatives = {item for group in cmap["lwm2m12"].get("requires_any") or [] for item in group}
    for required in ["lorawan_nonip_transport_service", "ciot_nonip_service", "secure_mqtt_message_service", "secure_http_message_service"]:
        if required not in lwm2m_alternatives:
            errors.append(f"lwm2m_binding_missing:{required}")

    if errors:
        raise SystemExit("Stage-4B component catalog validation failed: " + "; ".join(sorted(set(errors))[:50]))

    args.output.mkdir(parents=True, exist_ok=True)
    summary = {
        "stage": policy.get("stage"),
        "stage4_status": policy.get("stage4_status"),
        **checkpoints,
        "verification_stack_status": {name: a.status.value for name, a in structural.items()},
        "requires_any_contract_materialised": True,
        "cellular_ip_nonip_variants_separated": True,
        "ble_bare_vs_ipsp_variants_separated": True,
        "lorawan_lora_vs_lrfhss_modes_separated": True,
        "ephesos_interoperable_standard_verified": False,
        "all_verified_components_have_primary_source_claims": True,
        "mcda_authorised": False,
        "ranking_authorised": False,
        "next_scientific_step": policy.get("next_scientific_step"),
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    component_rows=[]
    for c in components:
        component_rows.append({
            "component_id":c["component_id"],"name":c["name"],"catalog_status":c.get("catalog_status"),
            "roles":"|".join(c.get("roles") or []),"placements":"|".join(c.get("supported_placements") or []),
            "provides":"|".join(c.get("provides") or []),"requires":"|".join(c.get("requires") or []),
            "requires_any":";".join("|".join(g) for g in c.get("requires_any") or []),
            "claim_ids":"|".join(c.get("claim_ids") or []),"notes":c.get("notes") or "",
        })
    component_csv=args.output/"component_catalog.csv"
    _write_csv(component_csv,component_rows,["component_id","name","catalog_status","roles","placements","provides","requires","requires_any","claim_ids","notes"])

    edge_csv=args.output/"compatibility_edges.csv"
    _write_csv(edge_csv,edges,["edge_id","from_component_id","to_component_id","interface","relation","status","scope","limitations"])
    alignment_csv=args.output/"evidence_alignment.csv"
    _write_csv(alignment_csv,alignments,["alignment_id","dataset_id","component_id","status","measurement_scope_note","decision_use_note"])
    gap_csv=args.output/"unresolved_catalog_gaps.csv"
    _write_csv(gap_csv,gaps,["gap_id","status","description","consequence"])
    claim_rows=[]
    for cid, claim in claims.items():
        claim_rows.append({"claim_id":cid,"statement":claim["statement"],"source_ids":"|".join(claim["source_ids"]),"verification_status":claim["verification_status"]})
    claims_csv=args.output/"standards_claims.csv"
    _write_csv(claims_csv,claim_rows,["claim_id","statement","source_ids","verification_status"])

    manifest=args.output/"run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/validate_stage4_component_catalog.py",
        inputs=[args.catalog,args.policy,args.stacks],
        outputs=[summary_path,component_csv,edge_csv,alignment_csv,gap_csv,claims_csv],
        parameters={"stage4_status":summary["stage4_status"],"mcda_authorised":False},
    )
    print("Stage-4B component catalog: OK")
    print(f"Primary sources: {len(sources)}")
    print(f"Verified claims: {len(claims)}")
    print(f"Catalog components: {len(components)} ({len(verified)} primary-source verified, {len(pending)} evidence-only/pending)")
    print(f"Verified compatibility edges: {checkpoints['verified_compatibility_edges']}")
    print(f"Evidence alignment records: {len(alignments)}")
    print(f"Explicit unresolved catalog gaps: {len(gaps)}")
    print(f"Structural verification stacks: {len(stacks)} ({compatible} compatible, {incompatible} incompatible)")
    print("Cellular IP and Non-IP variants conflated: NO")
    print("Bare BLE and IPSP/IPv6 conflated: NO")
    print("LoRa link evidence reused as LR-FHSS link evidence: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
