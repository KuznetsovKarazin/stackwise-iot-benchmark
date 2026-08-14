from __future__ import annotations

import json
from pathlib import Path

from stackwise.publication_consolidation import consolidate_publication_results

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    return json.loads((ROOT / f"results/experiments/{name}/summary.json").read_text(encoding="utf-8"))


def test_consolidation_freezes_expected_experiment_checkpoints():
    h,c,f,t,s = consolidate_publication_results(
        _load("experiment1_feasibility_first"),
        _load("experiment2_evidence_admissibility"),
        _load("experiment3_uncertainty_treatment"),
        _load("experiment4_accounting_simplification"),
    )
    assert s.experiments_closed == 4
    assert s.headline_result_rows == 9
    assert s.strong_claims == 5
    assert s.open_claims == 3
    assert s.fleet_experiment_recommended is True
    assert s.full_global_mcda_authorised is False
    assert len(h) == 9
    assert c.loc[c.claim_id.eq("C7_FLEET_LEVEL_OPTIMISATION"), "publication_claim_authorised"].item() == False


def test_claim_matrix_does_not_overclaim_global_mcda_or_matched_energy():
    _,claims,_,_,_ = consolidate_publication_results(
        _load("experiment1_feasibility_first"),
        _load("experiment2_evidence_admissibility"),
        _load("experiment3_uncertainty_treatment"),
        _load("experiment4_accounting_simplification"),
    )
    blocked = claims[claims.claim_id.isin(["C6_GLOBAL_STOCHASTIC_MCDA","C8_MATCHED_CELLULAR_REPORT_ENERGY"])]
    assert blocked.publication_claim_authorised.eq(False).all()


def test_figure_and_table_plan_is_compact():
    _,_,figures,tables,s = consolidate_publication_results(
        _load("experiment1_feasibility_first"),
        _load("experiment2_evidence_admissibility"),
        _load("experiment3_uncertainty_treatment"),
        _load("experiment4_accounting_simplification"),
    )
    assert s.main_figures_recommended == 6
    assert s.main_tables_recommended == 3
    assert (figures.role == "SUPPLEMENT").sum() == 3
    assert (tables.role == "SUPPLEMENT").sum() == 3
