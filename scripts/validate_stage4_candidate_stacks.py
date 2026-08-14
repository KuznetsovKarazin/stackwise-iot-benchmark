from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import jsonschema
import yaml

from stackwise.provenance import write_run_manifest
from stackwise.stack_catalog import assess_verified_candidate_stack, load_component_catalog
from stackwise.stack_model import StructuralStatus, validate_stack_candidate


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _schema_errors(record: dict, path: Path) -> list[str]:
    schema=json.loads(path.read_text(encoding="utf-8"))
    return sorted(e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(record))


def main() -> None:
    ap=argparse.ArgumentParser(description="Validate/materialise Stage-4C verified reference candidate stacks.")
    ap.add_argument("--catalog",type=Path,default=Path("datasets/stack_component_catalog.yml"))
    ap.add_argument("--candidates",type=Path,default=Path("datasets/stage4_candidate_stacks.yml"))
    ap.add_argument("--policy",type=Path,default=Path("datasets/stage4_candidate_stack_policy.yml"))
    ap.add_argument("--evidence-schema",type=Path,default=Path("datasets/schema/stack_candidate_evidence.schema.json"))
    ap.add_argument("--output",type=Path,default=Path("results/validation/stage4_candidate_stacks"))
    args=ap.parse_args()

    catalog=load_component_catalog(args.catalog)
    payload=yaml.safe_load(args.candidates.read_text(encoding="utf-8")) or {}
    policy=yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    stacks=payload.get("candidate_stacks") or []
    support=payload.get("candidate_evidence_support") or []
    deferred=payload.get("deferred_candidate_families") or []
    errors=[]

    sid=set()
    assessments={}
    total_instances=total_bindings=verified_binding_matches=0
    for stack in stacks:
        stack_id=str(stack.get("stack_id"))
        if stack_id in sid: errors.append(f"duplicate_stack_id:{stack_id}")
        sid.add(stack_id)
        for err in validate_stack_candidate(stack): errors.append(f"stack_schema:{stack_id}:{err}")
        assessment=assess_verified_candidate_stack(stack,catalog)
        assessments[stack_id]=assessment
        if assessment.status is not StructuralStatus.COMPATIBLE:
            errors.append(f"candidate_not_verified_compatible:{stack_id}:{'|'.join(assessment.errors)}")
        total_instances += len(stack.get("component_instances") or [])
        total_bindings += len(stack.get("bindings") or [])
        verified_binding_matches += len(stack.get("bindings") or []) if not any(x.startswith("binding_not_primary_source_verified:") for x in assessment.errors) else 0

    alignments={a["alignment_id"]:a for a in catalog.get("evidence_alignment") or []}
    stack_map={s["stack_id"]:s for s in stacks}
    support_classes={}
    any_alignment=0
    full_support=0
    for rec in support:
        rid=rec.get("stack_id")
        for err in _schema_errors(rec,args.evidence_schema): errors.append(f"evidence_schema:{rid}:{err}")
        if rid not in stack_map: errors.append(f"support_unknown_stack:{rid}")
        stack_components={i["component_id"] for i in stack_map.get(rid,{}).get("component_instances") or []}
        for aid in rec.get("alignment_ids") or []:
            a=alignments.get(aid)
            if a is None: errors.append(f"support_unknown_alignment:{rid}:{aid}")
            elif a["component_id"] not in stack_components: errors.append(f"support_alignment_component_not_in_stack:{rid}:{aid}")
        if rec.get("alignment_ids"): any_alignment += 1
        if rec.get("full_end_to_end_empirical_support") is True: full_support += 1
        support_classes[rec["support_class"]]=support_classes.get(rec["support_class"],0)+1
    if len(support)!=len(stacks): errors.append("one_evidence_support_record_required_per_stack")

    expected=policy.get("expected") or {}
    checkpoints={
      "candidate_stacks":len(stacks),
      "verified_candidate_stacks":sum(a.status is StructuralStatus.COMPATIBLE for a in assessments.values()),
      "candidate_component_instances":total_instances,
      "candidate_bindings":total_bindings,
      "verified_binding_matches":verified_binding_matches,
      "candidate_evidence_support_records":len(support),
      "candidates_with_any_core_four_alignment":any_alignment,
      "candidates_with_full_end_to_end_empirical_support":full_support,
      "partial_stack_context_only":support_classes.get("partial_stack_context_only",0),
      "component_direct_boundary_only":support_classes.get("component_direct_boundary_only",0),
      "no_direct_core_four_alignment":support_classes.get("no_direct_core_four_alignment",0),
      "deferred_candidate_families":len(deferred),
    }
    for k,v in checkpoints.items():
        if expected.get(k)!=v: errors.append(f"checkpoint:{k}:expected={expected.get(k)}:actual={v}")
    guards=policy.get("scientific_guards") or {}
    for k,v in guards.items():
        if v is not False: errors.append(f"scientific_guard_not_false:{k}")
    if errors: raise SystemExit("Stage-4C candidate stack validation failed: "+"; ".join(sorted(set(errors))[:80]))

    args.output.mkdir(parents=True,exist_ok=True)
    summary={"stage":policy.get("stage"),"stage4_status":policy.get("stage4_status"),**checkpoints,
      "all_candidate_bindings_primary_source_verified":True,"candidate_set_is_exhaustive":False,
      "full_end_to_end_empirical_support_available":False,"hard_scenario_screening_authorised":False,
      "mcda_authorised":False,"ranking_authorised":False,"next_scientific_step":policy.get("next_scientific_step")}
    summary_path=args.output/"summary.json"; summary_path.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")

    rows=[]
    for s in stacks:
        comps=[i["component_id"] for i in s["component_instances"]]
        primary=next(i["component_id"] for i in s["component_instances"] if i["instance_id"]==s["primary_access_instance_id"])
        rows.append({"stack_id":s["stack_id"],"name":s["name"],"primary_access_component_id":primary,
          "component_count":len(comps),"binding_count":len(s["bindings"]),"component_ids":"|".join(comps),
          "structural_status":assessments[s["stack_id"]].status.value,"scientific_status":s["scientific_status"],"notes":s.get("notes") or ""})
    stack_csv=args.output/"candidate_stack_catalog.csv"
    _write_csv(stack_csv,rows,["stack_id","name","primary_access_component_id","component_count","binding_count","component_ids","structural_status","scientific_status","notes"])

    edge_lookup={(e["from_component_id"],e["to_component_id"],e["interface"],e["relation"]):e for e in catalog.get("compatibility_edges") or [] if e.get("status")=="primary_source_verified_compatible"}
    binding_rows=[]
    for s in stacks:
        im={i["instance_id"]:i for i in s["component_instances"]}
        for b in s["bindings"]:
            sig=(im[b["from_instance_id"]]["component_id"],im[b["to_instance_id"]]["component_id"],b["interface"],b["relation"]); e=edge_lookup[sig]
            binding_rows.append({"stack_id":s["stack_id"],"from_component_id":sig[0],"to_component_id":sig[1],"interface":sig[2],"relation":sig[3],"verified_edge_id":e["edge_id"],"edge_status":e["status"]})
    binding_csv=args.output/"candidate_binding_verification.csv"
    _write_csv(binding_csv,binding_rows,["stack_id","from_component_id","to_component_id","interface","relation","verified_edge_id","edge_status"])

    support_rows=[]
    for r in support:
        support_rows.append({"stack_id":r["stack_id"],"support_class":r["support_class"],"alignment_ids":"|".join(r.get("alignment_ids") or []),"full_end_to_end_empirical_support":r["full_end_to_end_empirical_support"],"limitations":" | ".join(r["limitations"])})
    support_csv=args.output/"candidate_evidence_support.csv"
    _write_csv(support_csv,support_rows,["stack_id","support_class","alignment_ids","full_end_to_end_empirical_support","limitations"])

    deferred_csv=args.output/"deferred_candidate_families.csv"
    _write_csv(deferred_csv,deferred,["family_id","status","reason"])
    manifest=args.output/"run_manifest.json"
    write_run_manifest(manifest,command="python scripts/validate_stage4_candidate_stacks.py",inputs=[args.catalog,args.candidates,args.policy,args.evidence_schema],outputs=[summary_path,stack_csv,binding_csv,support_csv,deferred_csv],parameters={"mcda_authorised":False,"ranking_authorised":False})
    print("Stage-4C verified reference candidate stacks: OK")
    print(f"Candidate stacks: {len(stacks)}")
    print(f"Primary-source-verified bindings: {total_bindings}")
    print(f"Candidates with any core-four alignment: {any_alignment}")
    print(f"Candidates with full end-to-end empirical support: {full_support}")
    print(f"Deferred candidate families: {len(deferred)}")
    print("Hard scenario screening authorised: NO")
    print("Publication MCDA authorised: NO")
    print(f"Summary: {summary_path}")

if __name__=="__main__": main()
