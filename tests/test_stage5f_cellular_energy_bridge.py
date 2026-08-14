from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from stackwise.cellular_energy_bridge import audit_summary, build_candidate_bridge_audit, materialise_source_active_components


def _policy():
    return yaml.safe_load(Path("datasets/stage5f_cellular_ip_energy_bridge.yml").read_text(encoding="utf-8"))


def _feasibility():
    rows=[]
    p=_policy()
    for scenario in p["scenario_contexts"]:
        for stack in p["candidate_contexts"]:
            feasible = not (scenario == "asset_tracking_connected_handover" and stack.startswith("nbiot_"))
            rows.append({"scenario_id":scenario,"stack_id":stack,"status":"feasible" if feasible else "infeasible"})
    return rows


def test_stage5f_audits_ten_feasible_cellular_ip_incidences_and_blocks_all_targets():
    rows=build_candidate_bridge_audit(feasibility_rows=_feasibility(), policy=_policy())
    s=audit_summary(rows,_policy())
    assert len(rows)==10
    assert s.canonical_target_ready_rows==0
    assert s.payload_mismatch_rows==10
    assert s.exact_application_context_rows==0
    assert all(r["numeric_target_materialised"] is False for r in rows)


def test_stage5f_does_not_silently_transfer_http_mqtt_or_payload():
    rows=build_candidate_bridge_audit(feasibility_rows=_feasibility(), policy=_policy())
    assert all("source_payload_1024B_does_not_match_scenario_payload" in r["blocking_reasons"] for r in rows)
    ltem_mqtt=[r for r in rows if r["stack_id"]=="ltem_ip_mqtt_tls_lwm2m"]
    assert all("no_lte_m_mqtt_source_context" in r["blocking_reasons"] for r in ltem_mqtt)
    coap=[r for r in rows if "_coap_" in r["stack_id"]]
    assert all("http_source_does_not_identify_coap_dtls_lwm2m_energy" in r["blocking_reasons"] for r in coap)


def test_stage5f_source_active_component_preserves_same_bootstrap_replicates():
    p=_policy()
    phases=p["scientific_policy"]["source_active_phases"]
    refs=p["source_reference_contexts"]
    marginal=[]; draws=[]
    eid=0
    for ridx,ref in enumerate(refs):
        block=f"b{ridx}"
        for phidx,phase in enumerate(phases):
            eid += 1
            evid=f"e{eid}"
            val=float(phidx+1+ridx)
            marginal.append({"evidence_id":evid,"metric_id":"device_phase_energy_j","technology":ref["technology"],"application_protocol":ref["source_application_protocol"],"phase_name":phase,"experimental_block_id":block,"mean":val})
            for rep in range(4):
                draws.append({"experimental_block_id":block,"bootstrap_rep":rep,"evidence_id":evid,"bootstrap_mean":val+0.1*rep})
    summary, comp_draws=materialise_source_active_components(marginal=pd.DataFrame(marginal), bootstrap_draws=pd.DataFrame(draws), policy=p)
    assert len(summary)==3
    assert len(comp_draws)==12
    assert all(summary["canonical_application_report_target"] == False)  # noqa: E712
    first=summary.iloc[0]
    assert first["point_estimate_j"]==10.0
    # same replicate is summed across four phases: rep 1 adds 0.4 J, not independently shuffled values
    d=comp_draws[comp_draws.source_reference_id==refs[0]["reference_id"]].sort_values("bootstrap_rep")
    assert d.iloc[1].active_component_energy_j==10.4


def test_stage5f_policy_explicitly_prohibits_publication_shortcuts():
    sp=_policy()["scientific_policy"]
    assert sp["scale_payload_without_validated_model"] is False
    assert sp["infer_ltem_mqtt_from_nbiot_mqtt_delta"] is False
    assert sp["infer_coap_from_http"] is False
    assert sp["scale_idle_or_standby_to_reporting_interval_without_state_model"] is False
    assert sp["canonical_target_materialisation_authorised"] is False
    assert sp["publication_mcda_authorised"] is False
