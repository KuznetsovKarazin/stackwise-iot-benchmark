from __future__ import annotations

import pandas as pd

from stackwise.uncertainty_treatment import (
    cost_point_vs_robustness_family,
    loed_point_vs_model_robustness,
    summarise_experiment3,
    vomhoff_point_vs_bootstrap,
)


def _vomhoff_fixture() -> pd.DataFrame:
    return pd.DataFrame([
        {"source_reference_id":"nb_http","technology":"NB-IoT","source_application_protocol":"HTTP","point_estimate_j":10.0,"q025_j":9.8,"median_j":10.0,"q975_j":10.2,"bootstrap_replicates":10000},
        {"source_reference_id":"lte_http","technology":"LTE-M","source_application_protocol":"HTTP","point_estimate_j":1.0,"q025_j":0.9,"median_j":1.0,"q975_j":1.1,"bootstrap_replicates":10000},
        {"source_reference_id":"nb_mqtt","technology":"NB-IoT","source_application_protocol":"MQTT","point_estimate_j":7.0,"q025_j":6.8,"median_j":7.0,"q975_j":7.2,"bootstrap_replicates":10000},
    ])


def _loed_fixture() -> pd.DataFrame:
    return pd.DataFrame([
        {"campaign_id":"c1","metric":"rssi","sd_max_to_min_ratio_median":1.4,"sd_max_to_min_ratio_q75":1.5,"robustness_width_median":1.2,"max_abs_raw_mbb_bias":0.3},
        {"campaign_id":"c1","metric":"snr","sd_max_to_min_ratio_median":1.3,"sd_max_to_min_ratio_q75":1.4,"robustness_width_median":0.9,"max_abs_raw_mbb_bias":0.2},
        {"campaign_id":"c2","metric":"rssi","sd_max_to_min_ratio_median":1.45,"sd_max_to_min_ratio_q75":1.6,"robustness_width_median":1.5,"max_abs_raw_mbb_bias":0.3},
        {"campaign_id":"c2","metric":"snr","sd_max_to_min_ratio_median":1.7,"sd_max_to_min_ratio_q75":1.9,"robustness_width_median":1.8,"max_abs_raw_mbb_bias":0.4},
    ])


def _cost_fixture() -> pd.DataFrame:
    rows=[]
    for rat in ("NB-IoT","LTE-M"):
        for binding, stack in (("coap_dtls_udp",f"{rat}_coap"),("mqtt_tls_tcp",f"{rat}_mqtt")):
            for i,(bill,proc) in enumerate((("B0","P1"),("B1","P1"),("B2","P1"))):
                coap=[46.0,90.0,80.0][i]
                diff=[10.0,0.0,30.0][i]
                val=coap if binding=="coap_dtls_udp" else coap+diff
                rows.append({
                    "stack_id":stack,"access_technology":rat,"binding_family":binding,"lifecycle_cost_eur":val,
                    "anchor_id":"A0","shape_id":"S0","session_control_envelope_id":"E0",
                    "billing_anchor_id":bill,"procurement_anchor_id":proc,
                })
    return pd.DataFrame(rows)


def test_vomhoff_point_order_is_qualified_by_marginal_bootstrap_intervals():
    rows,pairs=vomhoff_point_vs_bootstrap(_vomhoff_fixture())
    assert len(rows)==3
    assert len(pairs)==3
    assert pairs["marginal_95_intervals_separated"].all()
    assert not pairs["cross_block_joint_probability_interpretation"].any()
    assert not rows["candidate_report_energy_transfer_authorised"].any()


def test_loed_point_can_be_fixed_while_uncertainty_scale_changes():
    rows=loed_point_vs_model_robustness(_loed_fixture())
    assert len(rows)==4
    assert (~rows["point_estimate_changes_across_block_models"]).all()
    assert rows["uncertainty_scale_changes_across_block_models"].all()
    assert (rows["sd_max_to_min_ratio_median"]>1.25).sum()==4
    assert (rows["sd_max_to_min_ratio_median"]>1.50).sum()==1


def test_cost_pairing_prevents_false_reversal_inference_from_overlapping_ranges():
    summary,pairs,detail=cost_point_vs_robustness_family(
        _cost_fixture(),
        reference_state={"anchor_id":"A0","shape_id":"S0","session_control_envelope_id":"E0","billing_anchor_id":"B0","procurement_anchor_id":"P1"},
    )
    assert summary["stack_id"].nunique()==4
    assert len(pairs)==2
    assert pairs["naive_marginal_ranges_overlap"].all()
    assert pairs["aligned_states_mqtt_cheaper"].eq(0).all()
    assert pairs["aligned_states_coap_cheaper"].eq(2).all()
    assert pairs["aligned_states_tied"].eq(1).all()
    assert detail["probability_interpretation"].eq(False).all()


def test_experiment3_summary_preserves_mixed_uncertainty_semantics():
    vr,vp=vomhoff_point_vs_bootstrap(_vomhoff_fixture())
    lr=loed_point_vs_model_robustness(_loed_fixture())
    cs,cp,_=cost_point_vs_robustness_family(
        _cost_fixture(),
        reference_state={"anchor_id":"A0","shape_id":"S0","session_control_envelope_id":"E0","billing_anchor_id":"B0","procurement_anchor_id":"P1"},
    )
    s=summarise_experiment3(vr,vp,lr,cs,cp)
    assert s.vomhoff_contexts==3
    assert s.vomhoff_marginal_interval_separated_pairs==3
    assert s.loed_rows_with_sd_ratio_gt_1_25==4
    assert s.loed_rows_with_sd_ratio_gt_1_50==1
    assert s.cost_candidates==4
    assert s.cost_aligned_states_per_rat==3
    assert s.cost_strict_coap_cheaper_rows_total==4
    assert s.cost_tie_rows_total==2
    assert s.cost_mqtt_cheaper_rows_total==0
