from __future__ import annotations
import json, platform, sys, time
from pathlib import Path
import pandas as pd, yaml

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path: sys.path.insert(0,str(ROOT/'src'))
from stackwise.decision_readiness import build_candidate_target_readiness

OUT=ROOT/'results/reviewer_revision_v6'
POLICY=ROOT/'datasets/stage5e_decision_readiness_policy.yml'
FEAS=ROOT/'results/validation/stage4_hard_capability_review/refined_hard_feasibility_matrix.csv'
CANDS=ROOT/'results/validation/stage4_candidate_stacks/candidate_stack_catalog.csv'
PROFILES=ROOT/'results/validation/stage5_operating_profiles/operating_profiles.csv'
BRIDGES=ROOT/'results/validation/stage5_operating_profiles/bridge_contracts.csv'

policy=yaml.safe_load(POLICY.read_text())
feas=pd.read_csv(FEAS).to_dict('records'); cands=pd.read_csv(CANDS).to_dict('records')
profiles=pd.read_csv(PROFILES).to_dict('records'); bridges=pd.read_csv(BRIDGES).to_dict('records')

def one():
    return build_candidate_target_readiness(feasibility_rows=feas,candidate_rows=cands,profile_rows=profiles,bridge_rows=bridges,policy=policy)

# Warm-up
for _ in range(100): one()
N=3000
t=[]
for _ in range(N):
    a=time.perf_counter_ns(); r=one(); b=time.perf_counter_ns(); t.append((b-a)/1e6)
import numpy as np
x=np.array(t)
summary={
 'benchmark_role':'illustrative computational-overhead sanity check; not a cross-hardware performance claim',
 'iterations':N,
 'candidate_target_rows_per_iteration':len(r),
 'non_infeasible_scenario_candidate_pairs':len(r)//len(policy['decision_targets']),
 'decision_targets':len(policy['decision_targets']),
 'median_ms':float(np.median(x)),
 'p05_ms':float(np.quantile(x,.05)),
 'p95_ms':float(np.quantile(x,.95)),
 'mean_ms':float(np.mean(x)),
 'max_ms':float(np.max(x)),
 'python':sys.version,
 'platform':platform.platform(),
}
(OUT/'r6d_readiness_overhead_benchmark.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
