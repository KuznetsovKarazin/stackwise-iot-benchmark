from __future__ import annotations

import pandas as pd

from stackwise.accounting_simplification import build_accounting_ablation


def _fixtures():
    # One stack, two protocol anchors, one shape, one session envelope, two billing anchors, two procurement anchors.
    s5l = pd.DataFrame([
        {"scenario_id":"s","stack_id":"x","anchor_id":"A0","strict_transport_known_component_floor_bytes_per_report":100,"pre_lwm2m_application_payload_bytes":50,"five_year_report_count":10},
        {"scenario_id":"s","stack_id":"x","anchor_id":"A1","strict_transport_known_component_floor_bytes_per_report":600,"pre_lwm2m_application_payload_bytes":50,"five_year_report_count":10},
    ])
    s5m = pd.DataFrame([
        {"scenario_id":"s","stack_id":"x","anchor_id":"A0","shape_id":"S0","five_year_strict_transport_bytes":2000},
        {"scenario_id":"s","stack_id":"x","anchor_id":"A1","shape_id":"S0","five_year_strict_transport_bytes":7000},
    ])
    s5n = pd.DataFrame([
        {"scenario_id":"s","stack_id":"x","anchor_id":"A0","shape_id":"S0","envelope_id":"E0","five_year_session_control_augmented_transport_bytes":3000},
        {"scenario_id":"s","stack_id":"x","anchor_id":"A1","shape_id":"S0","envelope_id":"E0","five_year_session_control_augmented_transport_bytes":8000},
    ])
    cost_rows=[]
    for anchor,billed,topups in (("A0",12000,2),("A1",14000,2)):
        for bill in ("B0","B1"):
            for proc,price in (("P0",20.0),("P1",30.0)):
                cost_rows.append({
                    "scenario_id":"s","stack_id":"x","access_technology":"R","binding_family":"b",
                    "anchor_id":anchor,"shape_id":"S0","session_control_envelope_id":"E0","billing_anchor_id":bill,
                    "procurement_anchor_id":proc,"billed_transport_bytes_5y":billed,"topup_count":topups,
                    "module_price_eur":price,"standard_sim_eur":1.0,"base_connectivity_prepaid_eur":2.0,
                    "lifecycle_cost_eur":price+1.0+2.0+20.0,
                })
    return s5l,s5m,s5n,pd.DataFrame(cost_rows)


def test_accounting_ablation_uses_one_aligned_state_space_and_is_monotone_for_fixture():
    s5l,s5m,s5n,cost=_fixtures()
    traffic,levels,cost_summary,summary=build_accounting_ablation(
        s5l,s5m,s5n,cost,scenario_id="s",nominal_allowance_bytes=5000,topup_increment_bytes=5000,topup_price_eur=10.0
    )
    assert summary.aligned_traffic_states==4
    assert summary.procurement_expanded_cost_rows==8
    assert list(levels["exceeds_nominal_allowance_rows"])==[0,2,2,2,4]
    assert not any(traffic[c].any() for c in ["L0_to_L1_reverse_to_within","L1_to_L2_reverse_to_within","L2_to_L3_reverse_to_within","L3_to_L4_reverse_to_within"])
    assert list(levels["false_within_vs_billing_aware_rows"])==[4,2,2,2,0]
    assert cost_summary.iloc[0]["rows_underestimating_final_cost"]>0


def test_application_only_is_pre_lwm2m_payload_and_transport_level_adds_known_floor():
    s5l,s5m,s5n,cost=_fixtures()
    traffic,_,_,_=build_accounting_ablation(
        s5l,s5m,s5n,cost,scenario_id="s",nominal_allowance_bytes=5000,topup_increment_bytes=5000,topup_price_eur=10.0
    )
    a0=traffic[traffic.anchor_id.eq("A0")].iloc[0]
    assert a0.L0_bytes_per_report==50
    assert a0.L0_bytes_5y==500
    assert a0.L1_bytes_per_report==150
    assert a0.L1_bytes_5y==1500


def test_probability_interpretation_is_not_introduced():
    s5l,s5m,s5n,cost=_fixtures()
    _,levels,cost_summary,_=build_accounting_ablation(
        s5l,s5m,s5n,cost,scenario_id="s",nominal_allowance_bytes=5000,topup_increment_bytes=5000,topup_price_eur=10.0
    )
    assert levels["probability_interpretation"].eq(False).all()
    assert cost_summary["probability_interpretation"].eq(False).all()
