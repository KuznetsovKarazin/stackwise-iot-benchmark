from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'external_validation/results_public'


def test_protocol_remains_frozen_and_outcomes_permitted():
    m=json.loads((ROOT/'external_validation/protocol_manifest.json').read_text())
    assert m['freeze_state']=='PRE_DATA_FROZEN'
    assert m['outcome_analysis_permitted'] is True
    assert m['rules_changed_after_outcome_inspection'] is False


def test_all_external_cases_retained_and_no_schema_extension():
    d=pd.read_csv(OUT/'ev_rq1_scenario_portability.csv')
    assert len(d)==5
    assert d['tier_a_included'].all()
    assert d['tier_b_included'].all()
    assert int(d['schema_extensions_made'].sum())==0


def test_unmapped_external_hard_requirements_never_yield_decision_ready():
    d=pd.read_csv(OUT/'ev_rq2_candidate_readiness.csv')
    blocked=d[d.unmapped_hard_requirement_count.gt(0)]
    assert not blocked.final_readiness_state.eq('DECISION_READY').any()
    assert set(d.final_readiness_state) <= {'INFEASIBLE','UNRESOLVED','FEASIBLE_BUT_EVIDENCE_INCOMPLETE','DECISION_READY'}


def test_povalac_negative_control_passes():
    d=pd.read_csv(OUT/'ev_rq4_negative_control.csv')
    assert len(d)==1
    assert d.iloc[0].relation_class!='C0_DIRECT'
    assert bool(d.iloc[0].negative_control_pass)


def test_heldout_sources_create_no_direct_classes_and_at_least_one_pre_registered_transition():
    rel=pd.read_csv(OUT/'ev_rq3_external_source_target_relations.csv')
    assert not rel.relation_class.eq('C0_DIRECT').any()
    tr=pd.read_csv(OUT/'ev_rq3_candidate_target_transitions.csv')
    assert tr.transition.eq('E0_MISSING->C1_BRIDGEABLE').sum() >= 1


def test_preference_ordering_risk_persists_all_three_operators_full_features():
    d=pd.read_csv(OUT/'mr1_preference_operator_robustness.csv')
    x=d[(d.feature_subset_id=='full')&(d.weight_design=='simplex_step_0.25')]
    assert set(x.preference_operator)=={'weighted_sum','topsis','weighted_chebyshev'}
    assert (x.evaluable_any_infeasible_at_top_fraction > .70).all()
    assert (x.evaluable_unique_infeasible_winner_fraction > .20).all()


def test_preference_ordering_risk_persists_leave_one_feature_out():
    d=pd.read_csv(OUT/'mr1_preference_operator_robustness.csv')
    x=d[(d.feature_subset_id!='full')&(d.weight_design=='simplex_step_0.25')]
    # Any-infeasible top-set risk remains non-zero for every operator and every leave-one-out subset.
    assert (x.evaluable_any_infeasible_at_top_fraction > 0).all()


def test_accounting_factorial_grid_complete_and_material():
    s=json.loads((OUT/'mr4_accounting_factorial_overall.json').read_text())
    assert s['workload_tariff_regimes']==6*5*5*3*3
    assert s['factorial_state_rows']==s['workload_tariff_regimes']*288
    assert s['regimes_with_any_tariff_class_error_fraction'] > .5
    assert s['median_relative_billed_volume_error'] > .1


def test_external_portfolio_is_withheld_by_frozen_rule():
    s=json.loads((OUT/'ev_rq5_status.json').read_text())
    assert s['external_portfolio_analysis_authorised'] is False
    assert s['result']=='WITHHELD_BY_PRE_REGISTERED_TIER_C_RULE'
