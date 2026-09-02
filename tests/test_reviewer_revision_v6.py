from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reviewer_revision/results_public'

def test_construct_validity_outputs_are_frozen_and_complete():
    s = json.loads((OUT/'r6a_construct_validity_summary.json').read_text())
    assert s['items'] == 35
    assert s['independent_raters'] == 4
    assert abs(s['four_class']['fleiss_kappa'] - 0.5366735934734087) < 1e-12
    assert abs(s['four_class']['observed_pairwise_agreement'] - 0.7952380952380952) < 1e-12
    assert 0.40 < s['four_class']['ci95_low'] < 0.42
    assert 0.62 < s['four_class']['ci95_high'] < 0.64
    assert abs(s['operational_two_class']['algorithm_vs_all_expert_votes_exact_agreement'] - 0.90) < 1e-12

def test_class_specific_confusion_counts_sum_to_140():
    d = pd.read_csv(OUT/'r6a_confusion_frozen_vs_all_expert_votes.csv')
    numeric = d.drop(columns=[d.columns[0]])
    assert int(numeric.to_numpy().sum()) == 140
    c = pd.read_csv(OUT/'r6a_class_specific_agreement.csv')
    row = c[c.frozen_class.eq('E0_MISSING')].iloc[0]
    assert int(row['items']) == 24
    assert abs(float(row['exact_vote_agreement_fraction']) - 92/96) < 1e-12

def test_expert_consensus_sensitivity_does_not_change_candidate_readiness():
    s = json.loads((OUT/'summary.json').read_text())['r6b']
    assert s['external_candidate_readiness_rows_changed']['MAJORITY_SUBSTITUTION'] == 0
    assert s['external_candidate_readiness_rows_changed']['CONSERVATIVE_MAJORITY'] == 0
    assert s['first_slice_candidate_criterion_rows_changed']['MAJORITY_SUBSTITUTION'] == 0
    assert s['first_slice_candidate_criterion_rows_changed']['CONSERVATIVE_MAJORITY'] == 0
    assert s['canonical_complete_two_criterion_candidates']['FROZEN'] == 0
    assert s['canonical_complete_two_criterion_candidates']['MAJORITY_SUBSTITUTION'] == 0
    assert s['canonical_complete_two_criterion_candidates']['CONSERVATIVE_MAJORITY'] == 0

def test_negative_control_becomes_more_conservative_under_consensus():
    s = json.loads((OUT/'summary.json').read_text())['r6b']['negative_control']
    assert s['FROZEN'] == 'C2_CONDITIONAL'
    assert s['MAJORITY_SUBSTITUTION'] == 'E0_MISSING'
    assert s['CONSERVATIVE_MAJORITY'] == 'E0_MISSING'

def test_uncertainty_label_perturbation_does_not_change_current_readiness():
    d = pd.read_csv(OUT/'r6c_uncertainty_readiness_invariance.csv')
    assert len(d) == 3
    assert d['candidate_target_rows'].eq(120).all()
    assert d['readiness_status_changes_vs_baseline'].eq(0).all()
    assert d['readiness_invariant'].all()

def test_full_stage5e_expert_consensus_changes_only_nonready_severity_not_decision_readiness():
    d = pd.read_csv(OUT/'r6b_full_stage5e_sensitivity_summary.csv')
    maj = d[d.sensitivity_scheme.eq('MAJORITY_SUBSTITUTION')].iloc[0]
    con = d[d.sensitivity_scheme.eq('CONSERVATIVE_MAJORITY')].iloc[0]
    assert int(maj['candidate_target_readiness_status_changes_vs_frozen']) == 3
    assert int(con['candidate_target_readiness_status_changes_vs_frozen']) == 3
    assert int(maj['ready_target_rows']) == 0
    assert int(con['ready_target_rows']) == 0
    assert int(maj['feasible_first_slice_fully_ready_candidates']) == 0
    assert int(con['feasible_first_slice_fully_ready_candidates']) == 0
    assert not bool(maj['decision_ready_conclusion_changed'])
    assert not bool(con['decision_ready_conclusion_changed'])
