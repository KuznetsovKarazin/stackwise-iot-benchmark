from __future__ import annotations

import copy
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from stackwise.evidence_admissibility import target_relation_ablation, candidate_admissibility_ablation
from stackwise.decision_readiness import build_candidate_target_readiness

OUT = ROOT / "results" / "reviewer_revision_v6"
AUDIT = ROOT / "external_validation" / "results_public" / "audit_primary_labels_anonymized.csv"
INTERNAL_REL = ROOT / "results" / "validation" / "core_four_evidence_matrix" / "decision_target_gap_matrix.csv"
EXTERNAL_REL = ROOT / "external_validation" / "results_public" / "ev_rq3_external_source_target_relations.csv"
TRANSITIONS = ROOT / "external_validation" / "results_public" / "ev_rq3_candidate_target_transitions.csv"
EXT_READY = ROOT / "external_validation" / "results_public" / "ev_rq2_candidate_readiness.csv"
FIRST_SLICE = ROOT / "results" / "experiments" / "experiment2_evidence_admissibility" / "first_slice_support_states.csv"
POLICY = ROOT / "datasets" / "stage5e_decision_readiness_policy.yml"
FEAS = ROOT / "results" / "validation" / "stage4_hard_capability_review" / "refined_hard_feasibility_matrix.csv"
CANDS = ROOT / "results" / "validation" / "stage4_candidate_stacks" / "candidate_stack_catalog.csv"
PROFILES = ROOT / "results" / "validation" / "stage5_operating_profiles" / "operating_profiles.csv"
BRIDGES = ROOT / "results" / "validation" / "stage5_operating_profiles" / "bridge_contracts.csv"

CLASSES = ["C0_DIRECT", "C1_BRIDGEABLE", "C2_CONDITIONAL", "E0_MISSING"]
RANK = {"C0_DIRECT": 3, "C1_BRIDGEABLE": 2, "C2_CONDITIONAL": 1, "E0_MISSING": 0}
RATERS = ["rater_A_class", "rater_B_class", "rater_C_class", "rater_D_class"]
SEED = 20260816
BOOT = 20_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fleiss_kappa(counts: np.ndarray) -> tuple[float, float]:
    counts = np.asarray(counts, dtype=float)
    n_items = counts.shape[0]
    n_raters = counts.sum(axis=1)
    if not np.allclose(n_raters, n_raters[0]):
        raise ValueError("Fleiss kappa requires constant rater count")
    n = float(n_raters[0])
    p_i = ((counts ** 2).sum(axis=1) - n) / (n * (n - 1.0))
    p_bar = float(p_i.mean())
    p = counts.sum(axis=0) / (n_items * n)
    p_e = float((p ** 2).sum())
    kappa = (p_bar - p_e) / (1.0 - p_e) if p_e < 1.0 else 1.0
    return float(kappa), p_bar


def bootstrap_fleiss(counts: np.ndarray) -> dict[str, float]:
    rng = np.random.default_rng(SEED)
    base, pbar = fleiss_kappa(counts)
    vals = np.empty(BOOT, dtype=float)
    n = len(counts)
    for i in range(BOOT):
        idx = rng.integers(0, n, n)
        vals[i] = fleiss_kappa(counts[idx])[0]
    return {
        "fleiss_kappa": base,
        "observed_pairwise_agreement": pbar,
        "bootstrap_replicates": BOOT,
        "bootstrap_seed": SEED,
        "ci95_low": float(np.quantile(vals, 0.025)),
        "ci95_high": float(np.quantile(vals, 0.975)),
    }


def consensus_scheme(row: pd.Series, scheme: str) -> str:
    frozen = str(row.algorithm_class)
    consensus = str(row.primary_consensus_class)
    count = int(row.primary_consensus_count)
    valid_majority = count >= 3 and consensus in RANK
    if scheme == "FROZEN":
        return frozen
    if scheme == "MAJORITY_SUBSTITUTION":
        return consensus if valid_majority else frozen
    if scheme == "CONSERVATIVE_MAJORITY":
        if valid_majority and RANK[consensus] < RANK[frozen]:
            return consensus
        return frozen
    raise ValueError(scheme)


def operational_class(x: str) -> str:
    return "NO_EXTERNAL_ASSUMPTION" if x in {"C0_DIRECT", "C1_BRIDGEABLE"} else "ASSUMPTION_OR_MISSING"


def audit_construct_outputs(audit: pd.DataFrame) -> dict[str, object]:
    audit = audit.sort_values("audit_item_id").reset_index(drop=True)
    vote_rows = []
    for row in audit.itertuples(index=False):
        frozen = str(row.algorithm_class)
        for rater in RATERS:
            vote_rows.append({"audit_item_id": row.audit_item_id, "algorithm_class": frozen, "expert_class": str(getattr(row, rater))})
    votes = pd.DataFrame(vote_rows)
    confusion = pd.crosstab(votes.algorithm_class, votes.expert_class).reindex(index=CLASSES, columns=CLASSES, fill_value=0)
    confusion.index.name = "frozen_algorithm_class"
    confusion.to_csv(OUT / "r6a_confusion_frozen_vs_all_expert_votes.csv")

    per_class = []
    for c in CLASSES:
        items = audit[audit.algorithm_class.eq(c)]
        v = votes[votes.algorithm_class.eq(c)]
        if len(items) == 0:
            per_class.append({
                "frozen_class": c, "items": 0, "expert_votes": 0,
                "exact_vote_agreement_count": 0, "exact_vote_agreement_fraction": np.nan,
                "items_with_3of4_or_4of4_consensus_matching_frozen": 0,
                "item_level_majority_match_fraction": np.nan,
                "unanimous_items_matching_frozen": 0,
            })
            continue
        majority_match = (items.primary_consensus_count.ge(3) & items.primary_consensus_class.eq(c))
        unanimous_match = (items.primary_consensus_count.eq(4) & items.primary_consensus_class.eq(c))
        per_class.append({
            "frozen_class": c, "items": len(items), "expert_votes": len(v),
            "exact_vote_agreement_count": int(v.expert_class.eq(c).sum()),
            "exact_vote_agreement_fraction": float(v.expert_class.eq(c).mean()),
            "items_with_3of4_or_4of4_consensus_matching_frozen": int(majority_match.sum()),
            "item_level_majority_match_fraction": float(majority_match.mean()),
            "unanimous_items_matching_frozen": int(unanimous_match.sum()),
        })
    pd.DataFrame(per_class).to_csv(OUT / "r6a_class_specific_agreement.csv", index=False)

    counts = []
    for row in audit.itertuples(index=False):
        vals = [str(getattr(row, r)) for r in RATERS]
        counts.append([vals.count(c) for c in CLASSES])
    counts = np.asarray(counts, dtype=float)
    four = bootstrap_fleiss(counts)

    # Operational collapse relevant to deterministic-bridge authorization.
    op_cats = ["NO_EXTERNAL_ASSUMPTION", "ASSUMPTION_OR_MISSING"]
    op_counts = []
    op_vote_rows = []
    for row in audit.itertuples(index=False):
        vals = [operational_class(str(getattr(row, r))) for r in RATERS]
        op_counts.append([vals.count(c) for c in op_cats])
        for v in vals:
            op_vote_rows.append({"algorithm_operational_class": operational_class(str(row.algorithm_class)), "expert_operational_class": v})
    op_counts = np.asarray(op_counts, dtype=float)
    op_k, op_pbar = fleiss_kappa(op_counts)
    op_votes = pd.DataFrame(op_vote_rows)
    op_conf = pd.crosstab(op_votes.algorithm_operational_class, op_votes.expert_operational_class).reindex(index=op_cats, columns=op_cats, fill_value=0)
    op_conf.index.name = "frozen_operational_class"
    op_conf.to_csv(OUT / "r6a_operational_boundary_confusion.csv")
    op_algorithm_vote_agreement = float((op_votes.algorithm_operational_class == op_votes.expert_operational_class).mean())

    result = {
        "four_class": four,
        "operational_two_class": {
            "definition": "C0/C1=no_external_assumption; C2/E0=assumption_or_missing",
            "expert_fleiss_kappa": op_k,
            "expert_observed_pairwise_agreement": op_pbar,
            "algorithm_vs_all_expert_votes_exact_agreement": op_algorithm_vote_agreement,
        },
        "items": len(audit),
        "independent_raters": len(RATERS),
        "class_distribution_frozen": {c: int(audit.algorithm_class.eq(c).sum()) for c in CLASSES},
    }
    (OUT / "r6a_construct_validity_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def make_scheme_maps(audit: pd.DataFrame) -> dict[str, pd.DataFrame]:
    schemes = {}
    for scheme in ["FROZEN", "MAJORITY_SUBSTITUTION", "CONSERVATIVE_MAJORITY"]:
        d = audit[["audit_item_id", "validation_partition", "source_id", "target_metric_id", "algorithm_class", "primary_consensus_class", "primary_consensus_count", "primary_consensus_status"]].copy()
        d["sensitivity_scheme"] = scheme
        d["sensitivity_class"] = audit.apply(lambda r: consensus_scheme(r, scheme), axis=1)
        d["class_changed_from_frozen"] = d.sensitivity_class.ne(d.algorithm_class)
        schemes[scheme] = d
    pd.concat(schemes.values(), ignore_index=True).to_csv(OUT / "r6b_audit_label_schemes.csv", index=False)
    return schemes


def internal_relation_sensitivity(audit_schemes: dict[str, pd.DataFrame], internal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rel = []
    ladders = []
    for scheme, amap in audit_schemes.items():
        m = amap[amap.validation_partition.eq("internal_frozen_benchmark")][["source_id", "target_metric_id", "sensitivity_class"]]
        d = internal.merge(m, left_on=["dataset_id", "target_metric_id"], right_on=["source_id", "target_metric_id"], how="left", validate="one_to_one")
        if d.sensitivity_class.isna().any():
            raise ValueError(f"Missing internal audit mapping under {scheme}")
        d["frozen_relation_class"] = d["relation_class"]
        d["relation_class"] = d["sensitivity_class"]
        d["sensitivity_scheme"] = scheme
        all_rel.append(d.drop(columns=["source_id", "sensitivity_class"]))
        lad = target_relation_ablation(d[["target_metric_id", "dataset_id", "relation_class"]]).copy()
        lad.insert(0, "sensitivity_scheme", scheme)
        ladders.append(lad)
    rel_out = pd.concat(all_rel, ignore_index=True)
    ladder_out = pd.concat(ladders, ignore_index=True)
    rel_out.to_csv(OUT / "r6b_internal_relation_sensitivity.csv", index=False)
    ladder_out.to_csv(OUT / "r6b_internal_admissibility_ladder_sensitivity.csv", index=False)
    return rel_out, ladder_out


def external_relation_sensitivity(audit_schemes: dict[str, pd.DataFrame], external: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scheme, amap in audit_schemes.items():
        m = amap[amap.validation_partition.eq("held_out_external_source")][["source_id", "target_metric_id", "sensitivity_class"]]
        d = external.merge(m, left_on=["external_source_id", "target_metric_id"], right_on=["source_id", "target_metric_id"], how="left", validate="one_to_one")
        if d.sensitivity_class.isna().any():
            raise ValueError(f"Missing external audit mapping under {scheme}")
        d["frozen_relation_class"] = d["relation_class"]
        d["relation_class"] = d["sensitivity_class"]
        d["sensitivity_scheme"] = scheme
        rows.append(d.drop(columns=["source_id", "sensitivity_class"]))
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUT / "r6b_external_relation_sensitivity.csv", index=False)
    return out


def best_class(a: str, b: str) -> str:
    return a if RANK[a] >= RANK[b] else b


def transition_sensitivity(audit_schemes: dict[str, pd.DataFrame], transitions: pd.DataFrame) -> pd.DataFrame:
    # Only generic source-target classes that actually change are perturbed. Candidate-specific restrictions already
    # embedded in the frozen transition remain unless a changed generic class is more restrictive than the frozen
    # candidate contribution. This avoids promoting a candidate on a generic label alone.
    rows = []
    for scheme, amap in audit_schemes.items():
        ext = amap[amap.validation_partition.eq("held_out_external_source")]
        lookup = {(r.source_id, r.target_metric_id): (r.algorithm_class, r.sensitivity_class) for r in ext.itertuples(index=False)}
        for r in transitions.itertuples(index=False):
            key = (r.external_source_id, r.target_metric_id)
            frozen_generic, new_generic = lookup[key]
            new_after = r.after_class
            rationale = "generic_source_target_class_unchanged"
            if new_generic != frozen_generic:
                # A more conservative generic source class cannot improve a candidate. Preserve any stronger pre-held-out evidence.
                if RANK[new_generic] < RANK[frozen_generic]:
                    new_after = best_class(r.before_class, new_generic)
                    rationale = "heldout_generic_relation_downgraded_preserve_stronger_preheldout_relation"
                else:
                    # A generic upgrade cannot override candidate-specific boundary restrictions; retain frozen candidate result.
                    new_after = r.after_class
                    rationale = "generic_upgrade_does_not_override_candidate_specific_boundary_contract"
            rows.append({
                **r._asdict(), "sensitivity_scheme": scheme, "heldout_generic_frozen_class": frozen_generic,
                "heldout_generic_sensitivity_class": new_generic, "sensitivity_after_class": new_after,
                "candidate_transition_changed": new_after != r.after_class, "sensitivity_rationale": rationale,
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "r6b_candidate_target_transition_sensitivity.csv", index=False)
    return out


def candidate_readiness_sensitivity(audit_schemes: dict[str, pd.DataFrame], ext_ready: pd.DataFrame, first_slice: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # External scenario readiness is ontology/feasibility driven and independent of held-out audit relation relabeling.
    ext_rows = []
    for scheme in audit_schemes:
        d = ext_ready.copy()
        d["sensitivity_scheme"] = scheme
        d["sensitivity_final_readiness_state"] = d["final_readiness_state"]
        d["state_changed"] = False
        ext_rows.append(d)
    ext_out = pd.concat(ext_rows, ignore_index=True)
    ext_out.to_csv(OUT / "r6b_external_candidate_readiness_sensitivity.csv", index=False)

    # First-slice candidate support states are candidate-specific. Determine whether any majority relabel touches a
    # first-slice source-target pair and whether the existing candidate-specific gate allows promotion.
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    source_lookup = {}
    for rule in policy["evidence_rules"]:
        tgt = str(rule["target_metric_id"])
        for stack in rule["stack_ids"]:
            source_lookup[(str(stack), tgt)] = tuple(map(str, rule.get("source_dataset_ids", [])))

    fs_rows = []
    for scheme, amap in audit_schemes.items():
        ilook = {(r.source_id, r.target_metric_id): (r.algorithm_class, r.sensitivity_class) for r in amap[amap.validation_partition.eq("internal_frozen_benchmark")].itertuples(index=False)}
        for r in first_slice.itertuples(index=False):
            sources = source_lookup.get((str(r.stack_id), str(r.target_metric_id)), tuple())
            changes = []
            for src in sources:
                if (src, str(r.target_metric_id)) in ilook:
                    f, n = ilook[(src, str(r.target_metric_id))]
                    if f != n:
                        changes.append((src, f, n))
            new_state = str(r.experiment2_support_state)
            rationale = "no_audited_source_target_relabeling_for_candidate_target"
            if changes:
                # Generic source-target labels are necessary but not sufficient. They cannot override an already
                # recorded candidate-specific transfer/profile/boundary blocker. All affected first-slice rows in the
                # frozen project are BLOCKED/structural/incompatible rather than direct-ready.
                rationale = "generic_relation_relabeling_does_not_override_candidate_specific_transfer_or_boundary_blocker"
            fs_rows.append({
                **r._asdict(), "sensitivity_scheme": scheme,
                "audited_relation_changes_touching_row": "|".join(f"{s}:{f}->{n}" for s,f,n in changes),
                "sensitivity_support_state": new_state,
                "support_state_changed": new_state != str(r.experiment2_support_state),
                "sensitivity_rationale": rationale,
            })
    fs_out = pd.DataFrame(fs_rows)
    fs_out.to_csv(OUT / "r6b_first_slice_candidate_readiness_sensitivity.csv", index=False)

    regime_rows = []
    for scheme in audit_schemes:
        d = fs_out[fs_out.sensitivity_scheme.eq(scheme)].copy()
        d["experiment2_support_state"] = d["sensitivity_support_state"]
        ab, _ = candidate_admissibility_ablation(d[["scenario_id", "stack_id", "target_metric_id", "experiment2_support_state"]])
        ab.insert(0, "sensitivity_scheme", scheme)
        regime_rows.append(ab)
    regime_out = pd.concat(regime_rows, ignore_index=True)
    regime_out.to_csv(OUT / "r6b_candidate_ablation_sensitivity.csv", index=False)
    return ext_out, fs_out, regime_out



def full_stage5e_consensus_sensitivity(audit_schemes: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    feas = pd.read_csv(FEAS).to_dict("records")
    cands = pd.read_csv(CANDS).to_dict("records")
    profiles = pd.read_csv(PROFILES).to_dict("records")
    bridges = pd.read_csv(BRIDGES).to_dict("records")
    relation_to_class = {
        "DIRECT": "C0_DIRECT", "BRIDGEABLE": "C1_BRIDGEABLE",
        "CONDITIONAL_INPUT_ONLY": "C2_CONDITIONAL", "MISSING": "E0_MISSING", "INCOMPATIBLE": "E0_MISSING",
    }
    class_to_relation = {
        "C0_DIRECT": "DIRECT", "C1_BRIDGEABLE": "BRIDGEABLE",
        "C2_CONDITIONAL": "CONDITIONAL_INPUT_ONLY", "E0_MISSING": "MISSING",
    }
    baseline_df = None
    detail_rows=[]; summary_rows=[]
    for scheme, amap in audit_schemes.items():
        p = copy.deepcopy(base_policy)
        ilook = {(r.source_id, r.target_metric_id): r.sensitivity_class for r in amap[amap.validation_partition.eq("internal_frozen_benchmark")].itertuples(index=False)}
        changed_rules=[]
        for rule in p["evidence_rules"]:
            sources=list(map(str,rule.get("source_dataset_ids",[])))
            if len(sources)!=1:
                continue
            src=sources[0]; tgt=str(rule["target_metric_id"])
            if (src,tgt) not in ilook:
                continue
            base_rel=str(rule["evidence_relation"]); base_cls=relation_to_class[base_rel]
            generic_cls=str(ilook[(src,tgt)])
            # Candidate-specific relation and source-target relation are conjunctive gates: use the less permissive class.
            eff_cls = base_cls if RANK[base_cls] <= RANK[generic_cls] else generic_cls
            eff_rel = class_to_relation[eff_cls]
            if base_rel == "INCOMPATIBLE":
                eff_rel = "INCOMPATIBLE"
            if eff_rel != base_rel:
                changed_rules.append((str(rule['rule_id']),base_rel,eff_rel,src,tgt,generic_cls))
                rule["evidence_relation"] = eff_rel
        rr = pd.DataFrame(build_candidate_target_readiness(feasibility_rows=feas,candidate_rows=cands,profile_rows=profiles,bridge_rows=bridges,policy=p))
        rr=rr.sort_values(["scenario_id","stack_id","target_metric_id"]).reset_index(drop=True)
        if baseline_df is None:
            baseline_df=rr.copy()
        rr["baseline_readiness_status"] = baseline_df["readiness_status"]
        rr["readiness_status_changed"] = rr["readiness_status"].ne(rr["baseline_readiness_status"])
        rr["sensitivity_scheme"] = scheme
        detail_rows.append(rr)
        feasible=rr[rr.feasibility_status.eq('feasible')]
        first=feasible[feasible.first_slice_required.astype(bool)]
        by_candidate=first.groupby(["scenario_id","stack_id"])["readiness_status"].apply(lambda x: bool(set(x).issubset({"READY_DIRECT","READY_BRIDGED"})))
        summary_rows.append({
            "sensitivity_scheme":scheme,
            "candidate_target_rows":len(rr),
            "candidate_target_readiness_status_changes_vs_frozen":int(rr.readiness_status_changed.sum()),
            "changed_candidate_specific_rules":"|".join(f"{a}:{b}->{c}" for a,b,c,_,_,_ in changed_rules),
            "changed_rule_count":len(changed_rules),
            "ready_target_rows":int(rr.readiness_status.isin({"READY_DIRECT","READY_BRIDGED"}).sum()),
            "feasible_first_slice_fully_ready_candidates":int(by_candidate.sum()),
            "decision_ready_conclusion_changed":bool(int(by_candidate.sum()) != 0),
        })
    detail=pd.concat(detail_rows,ignore_index=True)
    summ=pd.DataFrame(summary_rows)
    detail.to_csv(OUT/"r6b_full_stage5e_candidate_readiness_sensitivity.csv",index=False)
    summ.to_csv(OUT/"r6b_full_stage5e_sensitivity_summary.csv",index=False)
    return detail,summ


def uncertainty_invariance() -> pd.DataFrame:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    feas = pd.read_csv(FEAS).to_dict("records")
    cands = pd.read_csv(CANDS).to_dict("records")
    profiles = pd.read_csv(PROFILES).to_dict("records")
    bridges = pd.read_csv(BRIDGES).to_dict("records")

    variants = {
        "BASELINE": None,
        "ALL_PESSIMISTIC_LABELS": "maximally_conservative_epistemic_uncertainty",
        "ALL_OPTIMISTIC_LABELS": "precision_contract_treated_as_resolved_for_sensitivity_only",
    }
    baseline = None
    rows = []
    for name, replacement in variants.items():
        p = copy.deepcopy(policy)
        if replacement is not None:
            for rule in p["evidence_rules"]:
                rule["uncertainty_state"] = replacement
        rr = build_candidate_target_readiness(
            feasibility_rows=feas, candidate_rows=cands, profile_rows=profiles, bridge_rows=bridges, policy=p
        )
        d = pd.DataFrame(rr)[["scenario_id", "stack_id", "target_metric_id", "readiness_status"]].copy()
        d = d.sort_values(["scenario_id", "stack_id", "target_metric_id"]).reset_index(drop=True)
        if baseline is None:
            baseline = d.copy()
        changed = int((d.readiness_status != baseline.readiness_status).sum())
        rows.append({
            "uncertainty_variant": name,
            "candidate_target_rows": len(d),
            "readiness_status_changes_vs_baseline": changed,
            "readiness_invariant": changed == 0,
            "interpretation": "Current Stage-5E has no probabilistic precision threshold; uncertainty metadata cannot upgrade/downgrade admissibility or hard feasibility by itself.",
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "r6c_uncertainty_readiness_invariance.csv", index=False)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = pd.read_csv(AUDIT)
    if len(audit) != 35 or any(c not in audit.columns for c in RATERS):
        raise ValueError("Frozen independent-audit input drift")
    construct = audit_construct_outputs(audit)
    schemes = make_scheme_maps(audit)
    internal = pd.read_csv(INTERNAL_REL)
    external = pd.read_csv(EXTERNAL_REL)
    transitions = pd.read_csv(TRANSITIONS)
    ext_ready = pd.read_csv(EXT_READY)
    first_slice = pd.read_csv(FIRST_SLICE)

    internal_rel, ladder = internal_relation_sensitivity(schemes, internal)
    external_rel = external_relation_sensitivity(schemes, external)
    trans = transition_sensitivity(schemes, transitions)
    ext_sens, fs_sens, candidate_ab = candidate_readiness_sensitivity(schemes, ext_ready, first_slice)
    stage5_detail, stage5_summary = full_stage5e_consensus_sensitivity(schemes)
    unc = uncertainty_invariance()

    summary = {
        "campaign": "reviewer_revision_v6",
        "baseline_project_version": "0.1.62",
        "benchmark_version": "1.0.0",
        "confirmatory_external_campaign_modified": False,
        "frozen_classifier_modified": False,
        "r6a": construct,
        "r6b": {
            "schemes": list(schemes),
            "internal_relation_class_counts": {
                s: internal_rel[internal_rel.sensitivity_scheme.eq(s)].relation_class.value_counts().to_dict() for s in schemes
            },
            "external_relation_class_counts": {
                s: external_rel[external_rel.sensitivity_scheme.eq(s)].relation_class.value_counts().to_dict() for s in schemes
            },
            "candidate_target_transition_rows_changed": {
                s: int(trans[trans.sensitivity_scheme.eq(s)].candidate_transition_changed.sum()) for s in schemes
            },
            "external_candidate_readiness_rows_changed": {
                s: int(ext_sens[ext_sens.sensitivity_scheme.eq(s)].state_changed.sum()) for s in schemes
            },
            "first_slice_candidate_criterion_rows_changed": {
                s: int(fs_sens[fs_sens.sensitivity_scheme.eq(s)].support_state_changed.sum()) for s in schemes
            },
            "full_stage5e_candidate_target_status_changes": {s: int(stage5_summary[stage5_summary.sensitivity_scheme.eq(s)].candidate_target_readiness_status_changes_vs_frozen.iloc[0]) for s in schemes},
            "full_stage5e_first_slice_fully_ready_candidates": {s: int(stage5_summary[stage5_summary.sensitivity_scheme.eq(s)].feasible_first_slice_fully_ready_candidates.iloc[0]) for s in schemes},
            "canonical_complete_two_criterion_candidates": {
                s: int(candidate_ab[(candidate_ab.sensitivity_scheme.eq(s)) & (candidate_ab.regime_id.eq("D0_CANONICAL_READY_ONLY"))].complete_two_criterion_candidates.iloc[0]) for s in schemes
            },
            "negative_control": {
                s: str(external_rel[(external_rel.sensitivity_scheme.eq(s)) & (external_rel.external_source_id.eq("EV_E2_POVALAC_LORAWAN_TRAFFIC_2023")) & (external_rel.target_metric_id.eq("delivery_probability"))].relation_class.iloc[0]) for s in schemes
            },
        },
        "r6c": unc.to_dict("records"),
        "interpretive_guardrail": "Sensitivity results are post-review/non-confirmatory and do not overwrite frozen labels or primary outcomes.",
        "python": sys.version,
        "platform": platform.platform(),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    with (OUT / "SHA256SUMS.txt").open("w", encoding="utf-8") as f:
        for p in files:
            f.write(f"{sha256(p)}  {p.name}\n")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
