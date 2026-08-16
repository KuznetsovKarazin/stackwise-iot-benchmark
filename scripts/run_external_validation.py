from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:
    sys.path.insert(0,str(ROOT/'src'))

from stackwise.external_validation import (
    mapping_summary, external_readiness_table, relation_classification_rows,
    candidate_transition_rows, preference_scores, top_set, set_cover_min_cardinality,
)
from stackwise.feasibility_first import FEATURE_IDS, build_preference_feature_matrix, deterministic_simplex_weight_grid
from stackwise.lwm2m_serialization import serialized_payload_bytes
from stackwise.wire_accounting import strict_transport_floor_bytes, anchor_known_component_bytes
from stackwise.session_control_envelope import build_session_control_envelope_rows
from stackwise.provenance import write_run_manifest

MANIFEST=ROOT/'external_validation/protocol_manifest.json'
OUT=ROOT/'results/external_validation/paper_b_external_validation_v1'
TARGETS=[
    'delivery_probability','end_to_end_application_latency_ms',
    'expected_device_energy_per_application_report_j','feasible_link_probability','lifecycle_cost_eur'
]


def require_frozen():
    d=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if d.get('freeze_state')!='PRE_DATA_FROZEN' or not d.get('outcome_analysis_permitted'):
        raise SystemExit('External validation refused: PRE_DATA_FROZEN manifest required.')
    return d


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def source_profiles() -> pd.DataFrame:
    rows=[]
    # Kousias: selected held-out passive NB-IoT file.
    kp=ROOT/'external_validation/sources/kousias_nb_iot_passive.csv'
    k=pd.read_csv(kp)
    signal_cols=['NSINR-Tx0','NSINR-Tx1','NRSRP-Tx0','NRSRP-Tx1','NRSRQ-Tx0','NRSRQ-Tx1','NSSS-Power']
    rows.append({
        'external_source_id':'EV_E1_KOUSIAS_NBIOT_4G_5G_2023','selected_rows_or_traces':len(k),
        'source_boundary':'passive_operational_NB-IoT_radio_network_observations',
        'technology':'NB-IoT','empirical_unit':'passive_measurement_row','independence_caution':'repeated spatiotemporal samples within campaigns are not IID deployment replications',
        'has_attempted_transmission_denominator':False,'has_device_energy_measurement':False,
        'has_link_signal_metrics':all(c in k.columns for c in signal_cols),
        'campaign_count':int(k['campaign'].nunique()),'scenario_label_count':int(k['scenario'].nunique()),
        'n_cell_identities':int(k['CellIdentity'].nunique()),
        'rsrp_tx0_median_dbm':float(k['NRSRP-Tx0'].median()),'rsrp_tx0_q05_dbm':float(k['NRSRP-Tx0'].quantile(.05)),'rsrp_tx0_q95_dbm':float(k['NRSRP-Tx0'].quantile(.95)),
        'source_sha256':sha256(kp),
    })
    # Povalac: source is explicitly a LoRaWAN sniffer archive. Do not scan 1+ GB decompressed content.
    pp=ROOT/'external_validation/sources/povalac_lorawan_csv.zip'
    with zipfile.ZipFile(pp) as z:
        names=z.namelist(); csvs=[n for n in names if n.lower().endswith('.csv') and z.getinfo(n).file_size>0]
        prefixes=sorted({n.split('_',1)[0] for n in csvs if '_' in n})
        rows.append({
            'external_source_id':'EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','selected_rows_or_traces':np.nan,
            'source_boundary':'LoRaWAN_sniffer_observed_packet_receptions','technology':'LoRaWAN_classical_LoRa',
            'empirical_unit':'sniffer_observed_packet_record','independence_caution':'observed packets are not all attempted transmissions and repeated packets are not independent trials by default',
            'has_attempted_transmission_denominator':False,'has_device_energy_measurement':False,'has_link_signal_metrics':True,
            'archive_csv_file_count':len(csvs),'archive_dataset_prefix_count':len(prefixes),'source_sha256':sha256(pp),
        })
    # Leenders: reproduce the repository's payload-energy integration for Metingen 6.
    lp=ROOT/'external_validation/sources/leenders_nbiot_power_v1.0.zip'
    payload_energies=[]
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(lp) as z: z.extractall(td)
        base=next(Path(td).glob('guusleenders-*'))
        files=sorted((base/'Measurements'/'Power Payload'/'Metingen 6').glob('*.csv'))
        for f in files:
            try:
                df=pd.read_csv(f)
                inc=float(df['Increment'].iloc[0]); df=df.iloc[1:].copy()
                for c in ['CH1','CH2','CH3']: df[c]=pd.to_numeric(df[c],errors='coerce')
                trigger=df['CH3'].diff(); inds=df.index[trigger.abs()>=2].tolist()
                if len(inds)<2: continue
                time=np.arange(len(df))*inc
                current=(df['CH1']-df['CH2']).abs().to_numpy(float)*1000.0
                power=current*df['CH1'].to_numpy(float)
                # Repository uses label-based slices; reproduce corresponding positional interval conservatively.
                i0=max(0,df.index.get_loc(inds[0])); i1=max(i0+1,df.index.get_loc(inds[1]))
                energy=float(np.trapezoid(power[i0:i1+1],x=time[i0:i1+1]))
                parts=f.stem.split()
                ce=int(parts[-2]); payload=int(parts[-1])
                if np.isfinite(energy) and energy!=0:
                    payload_energies.append((ce,payload,energy))
            except Exception:
                continue
    pe=pd.DataFrame(payload_energies,columns=['ce_level_numeric','payload_bytes','packet_energy_mj_like_source'])
    rows.append({
        'external_source_id':'EV_E3_LEENDERS_NBIOT_POWER_2019','selected_rows_or_traces':len(pe),
        'source_boundary':'NB-IoT_measured_power_energy_components_and_packet_interval','technology':'NB-IoT',
        'empirical_unit':'measurement_trace','independence_caution':'trace/context repetitions must not be promoted to generic device-population replication',
        'has_attempted_transmission_denominator':False,'has_device_energy_measurement':True,'has_link_signal_metrics':True,
        'payload_min_bytes':int(pe.payload_bytes.min()) if len(pe) else np.nan,'payload_max_bytes':int(pe.payload_bytes.max()) if len(pe) else np.nan,
        'payload_energy_median_source_units':float(pe.packet_energy_mj_like_source.median()) if len(pe) else np.nan,
        'payload_energy_min_source_units':float(pe.packet_energy_mj_like_source.min()) if len(pe) else np.nan,
        'payload_energy_max_source_units':float(pe.packet_energy_mj_like_source.max()) if len(pe) else np.nan,
        'source_sha256':sha256(lp),
    })
    if len(pe):
        pe.to_csv(OUT/'leenders_payload_energy_reproduction.csv',index=False)
    return pd.DataFrame(rows)


def run_mr1(feature:pd.DataFrame, feas:pd.DataFrame):
    rows=[]; detail=[]
    ops=['weighted_sum','topsis','weighted_chebyshev']
    all_features=list(FEATURE_IDS)
    subset_specs=[('full',all_features)] + [(f'leave_out_{f}',[x for x in all_features if x!=f]) for f in all_features]
    for subset_id, feats in subset_specs:
        grids=[]
        simp=deterministic_simplex_weight_grid(feature_ids=feats,step=0.25)
        grids.append(('simplex_step_0.25',simp))
        equal=pd.DataFrame([{'weight_anchor_id':'EQUAL','probability_interpretation':False,**{f:1/len(feats) for f in feats}}])
        grids.append(('equal_weights',equal))
        fmat=feature[['stack_id',*feats]].copy()
        for operator in ops:
            for design_id,grid in grids:
                case_rows=[]
                for scenario_id, sg in feas.groupby('scenario_id',sort=True):
                    merged=sg[['stack_id','status']].merge(fmat,on='stack_id',how='left')
                    X=merged[feats].to_numpy(float)
                    feasible_exists=bool((merged.status=='feasible').any())
                    for _,wr in grid.iterrows():
                        w=wr[feats].to_numpy(float); w=w/w.sum()
                        scores=preference_scores(X,w,operator)
                        idx=top_set(scores)
                        statuses=merged.iloc[idx].status.astype(str).tolist()
                        any_inf='infeasible' in statuses
                        all_inf=bool(statuses) and all(s=='infeasible' for s in statuses)
                        unique_inf=len(statuses)==1 and statuses[0]=='infeasible'
                        rec={
                            'feature_subset_id':subset_id,'preference_operator':operator,'weight_design':design_id,
                            'scenario_id':scenario_id,'weight_anchor_id':str(wr['weight_anchor_id']),
                            'top_set_size':len(statuses),'any_infeasible_at_top':any_inf,'all_infeasible_at_top':all_inf,
                            'unique_infeasible_winner':unique_inf,'feasible_candidate_exists':feasible_exists,
                            'feasible_exists_but_all_top_infeasible':feasible_exists and all_inf,
                        }
                        case_rows.append(rec); detail.append(rec)
                d=pd.DataFrame(case_rows)
                evald=d[d.feasible_candidate_exists]
                rows.append({
                    'feature_subset_id':subset_id,'feature_count':len(feats),'preference_operator':operator,'weight_design':design_id,
                    'evaluations':len(d),'evaluable_with_feasible_candidate':len(evald),
                    'any_infeasible_at_top_fraction':float(d.any_infeasible_at_top.mean()),
                    'all_infeasible_at_top_fraction':float(d.all_infeasible_at_top.mean()),
                    'unique_infeasible_winner_fraction':float(d.unique_infeasible_winner.mean()),
                    'evaluable_any_infeasible_at_top_fraction':float(evald.any_infeasible_at_top.mean()) if len(evald) else np.nan,
                    'evaluable_all_infeasible_at_top_fraction':float(evald.all_infeasible_at_top.mean()) if len(evald) else np.nan,
                    'evaluable_unique_infeasible_winner_fraction':float(evald.unique_infeasible_winner.mean()) if len(evald) else np.nan,
                })
    return pd.DataFrame(rows),pd.DataFrame(detail)


def uncertainty_contracts():
    return pd.DataFrame([
        {
            'diagnostic_id':'U1_VOMHOFF_PHYSICAL_RUN_BOOTSTRAP','epistemic_type':'empirical_resampling',
            'resampling_unit':'physical_run_id within experimental block','replicates':10000,'seed':'20260811',
            'interval_or_statistic':'arithmetic-mean bootstrap; q0.025/q0.975 marginal intervals',
            'dependence_preserved':'shared physical-run resampling within block; structural missingness preserved',
            'prohibited_interpretation':'no cross-block joint probability; no sample-level pseudo-replication; no generic cross-device population inference',
        },
        {
            'diagnostic_id':'U2_LOED_TEMPORAL_MODEL_ROBUSTNESS','epistemic_type':'model-form/temporal robustness',
            'resampling_unit':'noncircular overlapping moving blocks of source days','replicates':5000,'seed':'20260811',
            'interval_or_statistic':'3/7/14-day block families; bootstrap SD and percentile-width sensitivity',
            'dependence_preserved':'all PHY strata and both RSSI/SNR metrics for a sampled source day; observed gateway composition',
            'prohibited_interpretation':'no probability weights over block lengths/campaigns; no single publication distribution; no cross-campaign replicate alignment',
        },
        {
            'diagnostic_id':'U3_LIFECYCLE_COST_ALIGNED_STATES','epistemic_type':'bounded finite state sensitivity',
            'resampling_unit':'none; deterministic aligned state enumeration','replicates':0,'seed':'not_applicable',
            'interval_or_statistic':'paired aligned-state cost gap and reversal/tie counts',
            'dependence_preserved':'same anchor/shape/session/billing/procurement state used for paired candidate comparison',
            'prohibited_interpretation':'state counts are not deployment probabilities; marginal ranges are not independent random draws',
        },
    ])


def run_mr4():
    variants=pd.read_csv(ROOT/'results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv')
    variants=variants[variants.scenario_id.eq('asset_tracking_periodic_cross_cell')].copy()
    ser_policy=yaml.safe_load((ROOT/'datasets/stage5m_lwm2m_serialization_envelope.yml').read_text())
    sess_policy=yaml.safe_load((ROOT/'datasets/stage5n_security_session_control_envelope.yml').read_text())
    payloads=[32,64,128,256,512,1024]; intervals=[300,900,3600,21600,86400]
    allowances=[50,100,250,500,1000]; increments=[50,100,500]; horizons=[1,3,5]
    shapes=[s['shape_id'] for s in ser_policy['serialization_surrogates']]
    base=[]
    for payload in payloads:
      for interval in intervals:
        mod=[]
        serrows=[]
        for _,vr in variants.iterrows():
            v=vr.to_dict(); v['application_payload_bytes']=payload; v['reporting_interval_s']=interval
            v['variant_id']=f"{vr['variant_id']}__P{payload}__I{interval}"; mod.append(v)
            for shape in shapes:
                enc=str(v['lwm2m_payload_encoding'])
                encoded=serialized_payload_bytes(payload,enc,shape,object_id=int(ser_policy['scientific_policy']['synthetic_test_object_id']))
                strict0=strict_transport_floor_bytes(v,0)
                l1=strict0+payload
                l2=strict_transport_floor_bytes(v,encoded)
                anchor=anchor_known_component_bytes(v,encoded,include_ip=False)
                serrows.append({
                    'serialization_row_id':f"{v['variant_id']}__{shape}",'variant_id':v['variant_id'],'profile_id':v['profile_id'],
                    'scenario_id':v['scenario_id'],'stack_id':v['stack_id'],'binding_family':v['binding_family'],'access_technology':v['access_technology'],
                    'anchor_id':v['anchor_id'],'shape_id':shape,'lwm2m_payload_encoding':enc,'serialized_lwm2m_payload_bytes':encoded,
                    'anchor_transport_bytes_per_report_with_surrogate':anchor,'five_year_report_count':1,'included_data_bytes':10**18,
                    '_L0':payload,'_L1':l1,'_L2':l2,
                })
        env=build_session_control_envelope_rows(serrows,mod,sess_policy)
        sr={r['serialization_row_id']:r for r in serrows}
        for e in env:
            s=sr[e['serialization_row_id']]
            for billing in ['B0_persistent_pdp','B1_pdp_per_report']:
                base.append({
                    'payload_bytes':payload,'reporting_interval_s':interval,'stack_id':e['stack_id'],'binding_family':e['binding_family'],
                    'anchor_id':e['anchor_id'],'shape_id':e['shape_id'],'envelope_id':e['envelope_id'],'billing_anchor_id':billing,
                    'L0_bytes_per_report':float(s['_L0']),'L1_bytes_per_report':float(s['_L1']),'L2_bytes_per_report':float(s['_L2']),
                    'L3_bytes_per_report':float(e['session_control_augmented_transport_bytes_per_report']),
                })
    base=pd.DataFrame(base)
    rounding=1000
    rows=[]
    year_seconds=365.25*86400
    for horizon in horizons:
      for allowance_mb in allowances:
       allowance=allowance_mb*1_000_000
       for increment_mb in increments:
        increment=increment_mb*1_000_000
        d=base.copy()
        reports=np.ceil(horizon*year_seconds/d.reporting_interval_s.to_numpy(float)).astype(np.int64)
        d['horizon_years']=horizon; d['allowance_mb']=allowance_mb; d['billing_increment_mb']=increment_mb; d['report_count']=reports
        for level in range(4): d[f'L{level}_bytes']=d[f'L{level}_bytes_per_report']*reports
        raw=d['L3_bytes'].to_numpy(float); per=d['L3_bytes_per_report'].to_numpy(float)
        b0=np.ceil(raw/rounding)*rounding
        b1=np.ceil(per/rounding)*rounding*reports
        d['L4_billed_bytes']=np.where(d.billing_anchor_id.eq('B0_persistent_pdp'),b0,b1)
        d['payload_only_relative_billed_volume_error']=(d['L4_billed_bytes']-d['L0_bytes'])/d['L4_billed_bytes']
        for lvl in range(4):
            top=np.maximum(0,np.ceil((d[f'L{lvl}_bytes']-allowance)/increment)).astype(int)
            d[f'L{lvl}_topup_class']=top
        d['L4_topup_class']=np.maximum(0,np.ceil((d['L4_billed_bytes']-allowance)/increment)).astype(int)
        d['payload_only_tariff_class_error']=d.L0_topup_class.ne(d.L4_topup_class)
        d['payload_only_false_within_allowance']=(d.L0_bytes<=allowance)&(d.L4_billed_bytes>allowance)
        rows.append(d)
    detail=pd.concat(rows,ignore_index=True)
    # Summarise by workload/tariff grid while retaining deterministic protocol state expansion.
    group_cols=['payload_bytes','reporting_interval_s','horizon_years','allowance_mb','billing_increment_mb']
    summ=detail.groupby(group_cols,as_index=False).agg(
        states=('stack_id','size'),
        median_relative_billed_volume_error=('payload_only_relative_billed_volume_error','median'),
        q05_relative_billed_volume_error=('payload_only_relative_billed_volume_error',lambda x:x.quantile(.05)),
        q95_relative_billed_volume_error=('payload_only_relative_billed_volume_error',lambda x:x.quantile(.95)),
        tariff_class_error_fraction=('payload_only_tariff_class_error','mean'),
        false_within_allowance_fraction=('payload_only_false_within_allowance','mean'),
    )
    overall={
        'factorial_state_rows':len(detail),'workload_tariff_regimes':len(summ),
        'tariff_class_error_fraction_over_all_states':float(detail.payload_only_tariff_class_error.mean()),
        'regimes_with_any_tariff_class_error_fraction':float((summ.tariff_class_error_fraction>0).mean()),
        'regimes_with_majority_tariff_class_error_fraction':float((summ.tariff_class_error_fraction>0.5).mean()),
        'median_relative_billed_volume_error':float(detail.payload_only_relative_billed_volume_error.median()),
        'q05_relative_billed_volume_error':float(detail.payload_only_relative_billed_volume_error.quantile(.05)),
        'q95_relative_billed_volume_error':float(detail.payload_only_relative_billed_volume_error.quantile(.95)),
        'max_relative_billed_volume_error':float(detail.payload_only_relative_billed_volume_error.max()),
        'probability_interpretation':False,
    }
    return detail,summ,overall


def internal_leave_one_out(feas:pd.DataFrame,cands:pd.DataFrame):
    # access-family level only; this is the publication-level fleet claim in v1.
    def fam(s):
        if s.startswith(('nbiot_','ltem_')): return 'cellular'
        if s.startswith('lorawan_'): return 'lorawan'
        if s.startswith('thread_'): return 'thread'
        return 'unknown'
    stackfam={s:fam(s) for s in cands.stack_id.astype(str)}
    strict=feas[feas.status.eq('feasible')]
    all_serviceable=set(strict.scenario_id.astype(str))
    coverage={}
    for family in sorted(set(stackfam.values())):
        stacks=[s for s,f in stackfam.items() if f==family]
        coverage[family]=set(strict[strict.stack_id.isin(stacks)].scenario_id.astype(str))
    rows=[]
    for omitted in [None,*sorted(all_serviceable)]:
        universe=set(all_serviceable)
        if omitted is not None: universe.remove(omitted)
        k,sol=set_cover_min_cardinality(coverage,universe)
        rows.append({'omitted_scenario':omitted or 'NONE','universe_size':len(universe),'minimum_family_cardinality':k,'minimum_family_portfolios':'||'.join('|'.join(x) for x in sol)})
    return pd.DataFrame(rows)


def main():
    manifest=require_frozen(); OUT.mkdir(parents=True,exist_ok=True)
    use=yaml.safe_load((ROOT/'datasets/external_validation_use_cases.yml').read_text())['use_cases']
    cands=pd.read_csv(ROOT/'release/stackwise_benchmark_v1.0.0/tables/L3_benchmark_definitions/candidate_stack_catalog.csv')
    comps=pd.read_csv(ROOT/'release/stackwise_benchmark_v1.0.0/tables/L3_benchmark_definitions/component_catalog.csv')
    feas=pd.read_csv(ROOT/'release/stackwise_benchmark_v1.0.0/tables/L4_feasibility_and_support/refined_hard_feasibility_matrix.csv')

    # EV-RQ1
    port=mapping_summary(use); port.to_csv(OUT/'ev_rq1_scenario_portability.csv',index=False)
    # EV-RQ2
    readiness=external_readiness_table(use,cands,feas); readiness.to_csv(OUT/'ev_rq2_candidate_readiness.csv',index=False)
    rs=readiness.groupby(['source_case_id','source_family','final_readiness_state']).size().unstack(fill_value=0).reset_index()
    rs.to_csv(OUT/'ev_rq2_scenario_state_counts.csv',index=False)
    # EV-RQ3/4
    profiles=source_profiles(); profiles.to_csv(OUT/'heldout_source_profiles.csv',index=False)
    relations=relation_classification_rows(); relations.to_csv(OUT/'ev_rq3_external_source_target_relations.csv',index=False)
    transitions=candidate_transition_rows(cands); transitions.to_csv(OUT/'ev_rq3_candidate_target_transitions.csv',index=False)
    neg=relations[(relations.external_source_id=='EV_E2_POVALAC_LORAWAN_TRAFFIC_2023')&(relations.target_metric_id=='delivery_probability')].copy()
    neg['negative_control_pass']=neg.relation_class.ne('C0_DIRECT')
    neg.to_csv(OUT/'ev_rq4_negative_control.csv',index=False)
    # EV-RQ5 eligibility: frozen Tier-C threshold decides whether external portfolio may be run.
    ev5=port[['source_case_id','source_family','hard_mapped_fraction','hard_source_conflicts','tier_c_eligible']].copy()
    ev5.to_csv(OUT/'ev_rq5_external_portfolio_eligibility.csv',index=False)
    tierc=ev5[ev5.tier_c_eligible]
    families=tierc.source_family.nunique()
    ev5_status={
        'tier_c_eligible_cases':int(len(tierc)),'tier_c_source_families':int(families),
        'external_portfolio_analysis_authorised':bool(len(tierc)>=3 and families>=2),
        'result':'RUN' if len(tierc)>=3 and families>=2 else 'WITHHELD_BY_PRE_REGISTERED_TIER_C_RULE',
        'interpretation':'External set-cover claim is withheld rather than extending the frozen ontology or resolving source conflicts post hoc.'
    }
    (OUT/'ev_rq5_status.json').write_text(json.dumps(ev5_status,indent=2)+'\n')

    # MR1
    feature=build_preference_feature_matrix(cands,comps)
    mr1,mr1detail=run_mr1(feature,feas); mr1.to_csv(OUT/'mr1_preference_operator_robustness.csv',index=False); mr1detail.to_csv(OUT/'mr1_preference_operator_detail.csv',index=False)
    # MR2 is the deterministic relation audit itself plus rule reasons.
    relations.assign(primary_classifier='frozen_deterministic_boundary_policy').to_csv(OUT/'mr2_admissibility_audit.csv',index=False)
    # MR3
    uc=uncertainty_contracts(); uc.to_csv(OUT/'mr3_uncertainty_contracts.csv',index=False)
    # MR4
    mr4detail,mr4summary,mr4overall=run_mr4(); mr4detail.to_csv(OUT/'mr4_accounting_factorial_detail.csv',index=False); mr4summary.to_csv(OUT/'mr4_accounting_factorial_summary.csv',index=False)
    (OUT/'mr4_accounting_factorial_overall.json').write_text(json.dumps(mr4overall,indent=2)+'\n')
    # MR5 internal LOO; external/combined withheld unless Tier-C condition passes.
    mr5=internal_leave_one_out(feas,cands); mr5.to_csv(OUT/'mr5_internal_family_leave_one_out.csv',index=False)

    class_counts=relations.relation_class.value_counts().to_dict()
    trans_counts=transitions.transition.value_counts().to_dict()
    states=readiness.final_readiness_state.value_counts().to_dict()
    full_mr1=mr1[(mr1.feature_subset_id=='full')&(mr1.weight_design=='simplex_step_0.25')]
    summary={
      'campaign_id':'paper_b_external_validation_v1','protocol_freeze_created_utc':manifest['created_utc'],
      'protocol_freeze_state':manifest['freeze_state'],'external_scenarios':len(use),
      'tier_a_cases':int(port.tier_a_included.sum()),'tier_b_cases':int(port.tier_b_included.sum()),'tier_c_cases':int(port.tier_c_eligible.sum()),
      'hard_requirement_mapping':{
          'exact':int(port.hard_exact.sum()),'interpretable':int(port.hard_interpretable.sum()),'unavailable':int(port.hard_unavailable.sum()),'source_conflicts':int(port.hard_source_conflicts.sum())},
      'external_candidate_readiness_states':{k:int(v) for k,v in states.items()},
      'external_source_target_relation_classes':{k:int(v) for k,v in class_counts.items()},
      'candidate_target_transition_counts':{k:int(v) for k,v in trans_counts.items()},
      'negative_control_pass':bool(neg.negative_control_pass.all()),
      'inappropriate_direct_transition_count':int(((relations.relation_class=='C0_DIRECT') & relations.external_source_id.isin(['EV_E2_POVALAC_LORAWAN_TRAFFIC_2023'])).sum()),
      'external_portfolio_status':ev5_status,
      'mr1_full_feature_simplex':full_mr1.to_dict('records'),
      'mr4':mr4overall,
      'rules_changed_after_outcome_inspection':False,
      'benchmark_v1_0_0_modified':False,
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')

    outputs=[p for p in OUT.iterdir() if p.is_file() and p.name!='run_manifest.json']
    write_run_manifest(OUT/'run_manifest.json',command='python scripts/run_external_validation.py',inputs=[MANIFEST,ROOT/'datasets/external_validation_use_cases.yml',ROOT/'datasets/external_validation_evidence_sources.yml',ROOT/'datasets/external_validation_admissibility_policy.yml',ROOT/'external_validation/sources/kousias_nb_iot_passive.csv',ROOT/'external_validation/sources/povalac_lorawan_csv.zip',ROOT/'external_validation/sources/leenders_nbiot_power_v1.0.zip'],outputs=outputs,parameters={'freeze_state':'PRE_DATA_FROZEN','probability_interpretation':False,'external_portfolio_tier_c_rule':'3 cases / 2 publication families'})
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
