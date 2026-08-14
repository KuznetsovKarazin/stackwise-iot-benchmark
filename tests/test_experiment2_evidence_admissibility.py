from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from stackwise.evidence_admissibility import (
    candidate_admissibility_ablation,
    overlay_stage6c_cost_readiness,
    source_grade_ablation,
    summarise_experiment2,
    target_relation_ablation,
)

ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    registry = yaml.safe_load((ROOT / "datasets/registry.yml").read_text(encoding="utf-8"))
    evidence_summary = json.loads((ROOT / "results/validation/core_four_evidence_matrix/summary.json").read_text(encoding="utf-8"))
    target_relations = pd.read_csv(ROOT / "results/validation/core_four_evidence_matrix/decision_target_gap_matrix.csv")
    readiness = pd.read_csv(ROOT / "results/validation/stage6a_decision_slice_consolidation/candidate_criterion_readiness.csv")
    cost = pd.read_csv(ROOT / "results/validation/stage6c_lifecycle_cost_robustness/preferred_subset_cost_summary.csv")
    return registry, evidence_summary, target_relations, readiness, cost


def test_experiment2_source_grade_ablation_is_degenerate_for_core_four():
    registry, summary, *_ = _inputs()
    table = source_grade_ablation(registry=registry, evidence_summary=summary)
    assert len(table) == 4
    assert table["core_sources_retained"].eq(4).all()
    assert table["canonical_evidence_records_retained"].eq(398).all()
    assert table["decision_admissibility_inferred_from_grade"].eq(False).all()


def test_experiment2_target_relation_classes_match_frozen_stage2_contract():
    _, _, relations, *_ = _inputs()
    table = target_relation_ablation(relations)
    counts = relations["relation_class"].value_counts().to_dict()
    assert counts.get("C0_DIRECT", 0) == 0
    assert counts.get("C1_BRIDGEABLE", 0) == 5
    assert counts.get("C2_CONDITIONAL", 0) == 1
    assert counts.get("E0_MISSING", 0) == 14
    assert table.loc[table.regime_id == "A1_DIRECT_PLUS_BRIDGEABLE", "source_target_relation_rows_counted_as_available"].item() == 5
    assert table.loc[table.regime_id == "A2_PLUS_CONDITIONAL_CONTEXT", "source_target_relation_rows_counted_as_available"].item() == 6
    assert table.loc[table.regime_id == "A3_SOURCE_GRADE_ONLY_NAIVE", "missing_rows_misclassified_as_available"].item() == 14


def test_experiment2_stage6c_overlay_upgrades_only_four_cost_rows():
    *_, readiness, cost = _inputs()
    rows = overlay_stage6c_cost_readiness(readiness, cost)
    assert len(rows) == 42
    counts = rows["experiment2_support_state"].value_counts().to_dict()
    assert counts.get("READY_ROBUSTNESS_FAMILY", 0) == 4
    assert counts.get("CONTEXT_ONLY", 0) == 6
    assert counts.get("STRUCTURAL_TRANSFER_ONLY", 0) == 10
    assert sum(counts.values()) == 42


def test_experiment2_admissibility_ladder_quantifies_decision_space_inflation():
    *_, readiness, cost = _inputs()
    rows = overlay_stage6c_cost_readiness(readiness, cost)
    regimes, detail = candidate_admissibility_ablation(rows)
    r = regimes.set_index("regime_id")
    assert r.loc["D0_CANONICAL_READY_ONLY", "complete_two_criterion_candidates"] == 0
    assert r.loc["D1_READY_PLUS_CONTEXT", "complete_two_criterion_candidates"] == 0
    assert r.loc["D2_CONTEXT_PLUS_STRUCTURAL_TRANSFER_COUNTERFACTUAL", "complete_two_criterion_candidates"] == 10
    assert r.loc["D2_CONTEXT_PLUS_STRUCTURAL_TRANSFER_COUNTERFACTUAL", "scenarios_with_at_least_two_complete_candidates"] == 3
    assert r.loc["D3_EXPLICIT_ASSUMPTION_PRIOR_COUNTERFACTUAL", "complete_two_criterion_candidates"] == 21
    assert r.loc["D3_EXPLICIT_ASSUMPTION_PRIOR_COUNTERFACTUAL", "scenarios_with_at_least_two_complete_candidates"] == 5
    assert detail["probability_interpretation"].eq(False).all()


def test_experiment2_counterfactual_regimes_never_authorise_publication_decision_use():
    *_, readiness, cost = _inputs()
    rows = overlay_stage6c_cost_readiness(readiness, cost)
    regimes, _ = candidate_admissibility_ablation(rows)
    counter = regimes[regimes["counterfactual"]]
    assert counter["decision_use_authorised"].eq(False).all()


def test_experiment2_summary_matches_expected_checkpoint():
    registry, ev_summary, relations, readiness, cost = _inputs()
    source = source_grade_ablation(registry=registry, evidence_summary=ev_summary)
    first = overlay_stage6c_cost_readiness(readiness, cost)
    regimes, _ = candidate_admissibility_ablation(first)
    summary = summarise_experiment2(
        source_grade=source,
        target_relations=relations,
        first_slice_rows=first,
        candidate_regimes=regimes,
    )
    assert summary.core_sources == 4
    assert summary.canonical_evidence_records == 398
    assert summary.direct_relation_rows == 0
    assert summary.bridgeable_relation_rows == 5
    assert summary.conditional_relation_rows == 1
    assert summary.missing_relation_rows == 14
    assert summary.first_slice_candidate_criterion_rows == 42
    assert summary.canonical_ready_rows == 4
    assert summary.context_only_rows == 6
    assert summary.structural_transfer_rows == 10
    assert summary.blocked_other_rows == 22
    assert summary.canonical_complete_candidates == 0
    assert summary.context_complete_candidates == 0
    assert summary.counterfactual_bridge_complete_candidates == 10
    assert summary.assumption_complete_candidates == 21
