from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable
import numpy as np
import pandas as pd

RELATION_RANK = {"E0_MISSING":0,"C2_CONDITIONAL":1,"C1_BRIDGEABLE":2,"C0_DIRECT":3}


def mapping_summary(use_cases: list[dict[str, Any]]) -> pd.DataFrame:
    rows=[]
    for case in use_cases:
        req=list(case.get('requirements',[]))
        hard=[r for r in req if str(r.get('hard_or_preference'))=='hard']
        cnt={s:sum(str(r.get('mapping_status'))==s for r in hard) for s in ('exact','interpretable','unavailable')}
        conflicts=sum(bool(r.get('source_conflict',False)) for r in hard)
        mapped=cnt['exact']+cnt['interpretable']
        frac=mapped/len(hard) if hard else 0.0
        tier_a=True
        tier_b=str(case.get('requirements_status','')).startswith('EXTRACTED')
        tier_c=bool(tier_b and frac>=0.7 and conflicts==0)
        rows.append({
            'source_case_id':case['source_case_id'],'source_family':case['source_family'],'title':case['title'],
            'requirements_total':len(req),'hard_requirements':len(hard),'hard_exact':cnt['exact'],
            'hard_interpretable':cnt['interpretable'],'hard_unavailable':cnt['unavailable'],'hard_mapped_fraction':frac,
            'hard_source_conflicts':conflicts,'schema_extensions_made':0,
            'full_representation_unmapped_hard_fields':cnt['unavailable'],'tier_a_included':tier_a,
            'tier_b_included':tier_b,'tier_c_eligible':tier_c,
        })
    return pd.DataFrame(rows)


def _family(stack_id:str)->str:
    if stack_id.startswith(('nbiot_','ltem_')): return 'cellular'
    if stack_id.startswith('lorawan_'): return 'lorawan'
    if stack_id.startswith('thread_'): return 'thread'
    return 'unknown'


def external_readiness_table(use_cases: list[dict[str, Any]], candidates: pd.DataFrame, feasibility: pd.DataFrame) -> pd.DataFrame:
    """Frozen external-case portability gate used in Paper-B campaign.

    This gate deliberately does not retrofit external cases into one of the seven internal scenarios.
    It only applies hard facts that are exactly/interpretabily represented without schema extension.
    """
    rows=[]
    for case in use_cases:
        hard=[r for r in case.get('requirements',[]) if str(r.get('hard_or_preference'))=='hard']
        unmapped=sum(str(r.get('mapping_status'))=='unavailable' for r in hard)
        conflicts=sum(bool(r.get('source_conflict',False)) for r in hard)
        fixed=None
        latency_exact=False
        for r in hard:
            if str(r.get('stackwise_field'))=='external.candidate_access_family_fixed' and str(r.get('mapping_status')) in {'exact','interpretable'}:
                fixed=str(r.get('value')).strip().lower()
            if str(r.get('stackwise_field'))=='quantitative_context.target_end_to_end_latency_ms' and str(r.get('mapping_status'))=='exact':
                latency_exact=True
        for c in candidates.itertuples(index=False):
            sid=str(c.stack_id); fam=_family(sid)
            infeasible=False; reasons=[]
            if fixed=='lorawan' and fam!='lorawan':
                infeasible=True; reasons=['fixed_access_family_requires_lorawan']
            if infeasible:
                mapped='infeasible'; final='INFEASIBLE'
            else:
                mapped='not_infeasible_on_mapped_subset'; final='UNRESOLVED'
                if conflicts: reasons.append('conflicting_external_hard_requirement')
                reasons.append('frozen_access_service_availability_not_established_for_external_case')
                if unmapped: reasons.append('unmapped_external_hard_requirement')
                if latency_exact: reasons.append('verified_end_to_end_latency_capability_missing')
            rows.append({
                'source_case_id':case['source_case_id'],'source_family':case['source_family'],'stack_id':sid,
                'access_family':fam,'mapped_subset_hard_status':mapped,'final_readiness_state':final,
                'unmapped_hard_requirement_count':unmapped,'conflicting_hard_requirement_count':conflicts,
                'blocking_reasons':'|'.join(reasons),'winner_forced':False,
            })
    return pd.DataFrame(rows)


def relation_classification_rows() -> pd.DataFrame:
    # Frozen deterministic boundary-policy output. Kept as explicit rows so the audit has a stable, reviewable contract.
    data=[
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','delivery_probability','E0_MISSING','Passive radio/network measurements do not contain attempted-transmission outcomes/denominator.'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','end_to_end_application_latency_ms','E0_MISSING','Selected passive NB-IoT file contains radio/network measurements, not end-to-end application latency.'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','expected_device_energy_per_application_report_j','E0_MISSING','Selected passive NB-IoT file contains no device energy measurement.'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','feasible_link_probability','C1_BRIDGEABLE','Operational NB-IoT RSRP/RSRQ/SINR and serving-cell context can support a threshold/model bridge to link feasibility, but do not directly measure a probability estimand.'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','lifecycle_cost_eur','E0_MISSING','No lifecycle procurement/tariff cost estimand in the selected file.'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','delivery_probability','C2_CONDITIONAL','LoRaWAN sniffer records are observed receptions; without all attempted transmissions the delivery denominator is absent, so only conditional traffic/reception characterization is admissible.'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','end_to_end_application_latency_ms','E0_MISSING','Sniffer packet observations do not identify matched application end-to-end latency.'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','expected_device_energy_per_application_report_j','E0_MISSING','No device energy measurement.'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','feasible_link_probability','C1_BRIDGEABLE','Received-packet PHY/context can support an explicit observational link-context bridge, not a direct probability of serviceability.'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','lifecycle_cost_eur','E0_MISSING','No lifecycle cost estimand.'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','delivery_probability','E0_MISSING','Energy traces do not identify attempted-versus-delivered message probability.'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','end_to_end_application_latency_ms','E0_MISSING','Trace segmentation does not identify application end-to-end latency.'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','expected_device_energy_per_application_report_j','C1_BRIDGEABLE','Measured NB-IoT modem/device-side energy components and packet energy require an explicit bridge to the STACKWISE whole-device application-report boundary and workload.'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','feasible_link_probability','C2_CONDITIONAL','RSRP/RSSI/SINR/RSRQ and coverage-enhancement context accompany energy measurements but do not directly identify operational link-feasibility probability.'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','lifecycle_cost_eur','E0_MISSING','No procurement/tariff lifecycle cost estimand.'),
    ]
    return pd.DataFrame(data,columns=['external_source_id','target_metric_id','relation_class','rule_reason'])


def candidate_transition_rows(candidates: pd.DataFrame) -> pd.DataFrame:
    present=set(candidates.stack_id.astype(str))
    data=[
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','nbiot_ip_coap_dtls_lwm2m','feasible_link_probability','E0_MISSING','C1_BRIDGEABLE','new_bridgeable_link_evidence_not_direct_probability'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','nbiot_ip_coap_dtls_lwm2m','expected_device_energy_per_application_report_j','C1_BRIDGEABLE','C1_BRIDGEABLE','independent_measured_component_support_added_boundary_still_requires_bridge'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','nbiot_ip_mqtt_tls_lwm2m','feasible_link_probability','E0_MISSING','C1_BRIDGEABLE','new_bridgeable_link_evidence_not_direct_probability'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','nbiot_ip_mqtt_tls_lwm2m','expected_device_energy_per_application_report_j','C1_BRIDGEABLE','C1_BRIDGEABLE','independent_measured_component_support_added_boundary_still_requires_bridge'),
('EV_E1_KOUSIAS_NBIOT_4G_5G_2023','nbiot_nonip_lwm2m','feasible_link_probability','E0_MISSING','C1_BRIDGEABLE','new_bridgeable_link_evidence_not_direct_probability'),
('EV_E3_LEENDERS_NBIOT_POWER_2019','nbiot_nonip_lwm2m','expected_device_energy_per_application_report_j','E0_MISSING','C2_CONDITIONAL','new_nbiot_energy_context_but_nonip_application_boundary_not_identified'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','lorawan_lora_lwm2m_nonip','delivery_probability','C2_CONDITIONAL','C2_CONDITIONAL','independent_sniffer_context_added_denominator_gap_remains'),
('EV_E2_POVALAC_LORAWAN_TRAFFIC_2023','lorawan_lora_lwm2m_nonip','feasible_link_probability','C1_BRIDGEABLE','C1_BRIDGEABLE','independent_receive_side_link_context_added'),
    ]
    rows=[]
    for src,stack,tgt,before,after,effect in data:
        if stack not in present: continue
        rows.append({'external_source_id':src,'stack_id':stack,'target_metric_id':tgt,'before_class':before,'after_class':after,
                     'transition':f'{before}->{after}','readiness_effect':effect})
    return pd.DataFrame(rows)


def preference_scores(X: np.ndarray, w: np.ndarray, operator: str) -> np.ndarray:
    X=np.asarray(X,float); w=np.asarray(w,float)
    if operator=='weighted_sum':
        return X @ w
    if operator=='topsis':
        norms=np.linalg.norm(X,axis=0); norms=np.where(norms==0,1.0,norms)
        V=(X/norms)*w
        ideal=V.max(axis=0); anti=V.min(axis=0)
        dplus=np.linalg.norm(V-ideal,axis=1); dminus=np.linalg.norm(V-anti,axis=1)
        den=dplus+dminus
        return np.divide(dminus,den,out=np.zeros_like(dminus),where=den>0)
    if operator=='weighted_chebyshev':
        # Higher is better; score is negative weighted L-infinity distance to the componentwise ideal 1.
        return -np.max(w*(1.0-X),axis=1)
    raise ValueError(operator)


def top_set(scores: np.ndarray, tolerance: float=1e-12) -> np.ndarray:
    scores=np.asarray(scores,float)
    return np.flatnonzero(np.isclose(scores,np.nanmax(scores),rtol=0.0,atol=tolerance))


def set_cover_min_cardinality(coverage: dict[str,set[str]], universe:set[str]) -> tuple[int,list[tuple[str,...]]]:
    keys=sorted(coverage)
    if not universe: return 0,[tuple()]
    for k in range(1,len(keys)+1):
        sol=[]
        for comb in combinations(keys,k):
            u=set()
            for key in comb: u |= set(coverage[key])
            if universe <= u: sol.append(comb)
        if sol: return k,sol
    return len(keys)+1,[]
