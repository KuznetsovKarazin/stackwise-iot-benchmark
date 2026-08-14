from pathlib import Path
import csv
import yaml

from stackwise.feasibility_closure import freeze_decision_blockers, lrfhss_radio_bound_diagnostic


def _policy():
    return yaml.safe_load(Path("datasets/stage4f_feasibility_closure.yml").read_text(encoding="utf-8"))


def test_stage4f_freezes_exactly_three_blockers_and_requires_profiles():
    blockers = [
        {"scenario_id":"industrial_private_ipv6_low_latency","stack_id":"thread_coap_dtls_lwm2m","constraint_id":"latency_ceiling","overall_status":"unresolved"},
        {"scenario_id":"remote_agriculture_energy_budget","stack_id":"lorawan_lora_lwm2m_nonip","constraint_id":"whole_device_energy_budget","overall_status":"unresolved"},
        {"scenario_id":"remote_agriculture_energy_budget","stack_id":"lorawan_lrfhss_lwm2m_nonip","constraint_id":"whole_device_energy_budget","overall_status":"unresolved"},
    ]
    rows = freeze_decision_blockers(blockers, _policy())
    assert len(rows) == 3
    assert all(r["stage4f_status"] == "unresolved" for r in rows)
    assert all(r["operating_profile_required"] is True for r in rows)
    assert all(r["resolved_from_existing_evidence"] is False for r in rows)


def test_stage4f_lrfhss_bound_diagnostic_never_promotes_radio_to_whole_device():
    records=[]
    vals=[("DR8","confirmed",0.327), ("DR8","unconfirmed",0.150), ("DR9","confirmed",0.172), ("DR9","unconfirmed",0.089), ("DR10","confirmed",0.325), ("DR10","unconfirmed",0.151), ("DR11","confirmed",0.202), ("DR11","unconfirmed",0.089)]
    for dr,mode,e in vals:
        records.append({"metric_id":"radio_incremental_transaction_energy_j","estimate":e,"payload_bytes":4,"tx_power_dbm":14,"data_rate_mode":dr,"confirmation_mode":mode})
    rows=lrfhss_radio_bound_diagnostic(records,budget_j=0.2,scenario_payload_bytes=16)
    assert len(rows)==8
    assert sum(r["measured_radio_energy_exceeds_budget"] for r in rows)==3
    assert sum(r["payload_matches_scenario"] for r in rows)==0
    assert all(r["whole_device_feasibility_resolved"] is False for r in rows)
