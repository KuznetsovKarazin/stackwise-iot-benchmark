from pathlib import Path
import sys
import pandas as pd

LABELS=["C0_DIRECT","C1_BRIDGEABLE","C2_CONDITIONAL","E0_MISSING"]

def kappa(a,b):
    n=len(a)
    if n==0: return float("nan")
    po=sum(x==y for x,y in zip(a,b))/n
    pa={lab:sum(x==lab for x in a)/n for lab in LABELS}
    pb={lab:sum(x==lab for x in b)/n for lab in LABELS}
    pe=sum(pa[l]*pb[l] for l in LABELS)
    return (po-pe)/(1-pe) if pe < 1 else 1.0

if len(sys.argv)!=2:
    raise SystemExit("Usage: python score_independent_admissibility_audit.py <returned_expert_csv>")
root=Path(__file__).resolve().parent
exp=pd.read_csv(sys.argv[1])
key=pd.read_csv(root/"STACKWISE_admissibility_audit_algorithm_key_DO_NOT_SEND.csv")
d=exp.merge(key,on=["audit_item_id","validation_partition","source_id","target_metric_id"],how="inner",validate="one_to_one")
d=d[d.expert_class.isin(LABELS)].copy()
if not len(d): raise SystemExit("No scorable expert rows")
d["agreement"]=d.expert_class.eq(d.algorithm_class)
print(f"Scorable rows: {len(d)}")
print(f"Exact agreement: {d.agreement.mean():.3f} ({d.agreement.sum()}/{len(d)})")
print(f"Cohen kappa: {kappa(d.algorithm_class.tolist(),d.expert_class.tolist()):.3f}")
print("\nBy partition:")
for part,g in d.groupby("validation_partition"):
    print(part, f"agreement={g.agreement.mean():.3f}", f"n={len(g)}", f"kappa={kappa(g.algorithm_class.tolist(),g.expert_class.tolist()):.3f}")
print("\nDisagreements:")
cols=["audit_item_id","source_id","target_metric_id","algorithm_class","expert_class","expert_confidence","expert_rationale"]
print(d.loc[~d.agreement,cols].to_string(index=False))
