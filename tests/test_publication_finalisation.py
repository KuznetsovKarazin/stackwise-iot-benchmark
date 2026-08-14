from __future__ import annotations

import json
from pathlib import Path

from stackwise.publication_finalisation import finalise_publication_results

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    return json.loads((ROOT / f"results/experiments/{name}/summary.json").read_text(encoding="utf-8"))


def _run():
    return finalise_publication_results(
        _load("experiment1_feasibility_first"),
        _load("experiment2_evidence_admissibility"),
        _load("experiment3_uncertainty_treatment"),
        _load("experiment4_accounting_simplification"),
        _load("experiment5_fleet_portfolio"),
    )


def test_final_consolidation_closes_fleet_claim_but_not_global_mcda():
    headlines, claims, _, _, _, summary = _run()
    assert summary.experiments_closed == 5
    assert summary.headline_result_rows == 11
    assert summary.strong_claims == 6
    assert summary.open_claims == 2
    assert summary.broad_methodology_article_ready is True
    assert summary.global_mcda_authorised is False
    fleet = claims.loc[claims.claim_id.eq("C6_FLEET_PORTFOLIO_SIMPLIFICATION")].iloc[0]
    assert bool(fleet.publication_claim_authorised)
    blocked = claims[claims.claim_id.isin(["C7_GLOBAL_STOCHASTIC_MCDA", "C8_MATCHED_CELLULAR_REPORT_ENERGY"])]
    assert blocked.publication_claim_authorised.eq(False).all()
    assert len(headlines) == 11


def test_two_paper_split_excludes_experiments_from_data_paper():
    _, _, split, _, _, summary = _run()
    exp_rows = split[split.content_block.str.startswith("Experiment ")]
    assert exp_rows.data_paper.eq("EXCLUDE").all()
    assert exp_rows.method_paper.eq("PRIMARY").all()
    assert summary.two_paper_split_recommended is True


def test_final_figure_table_plan_is_compact():
    _, _, _, figures, tables, summary = _run()
    assert summary.methodology_main_figures == 6
    assert summary.methodology_main_tables == 3
    assert ((figures.paper == "DATA_PAPER") & figures.role.str.startswith("MAIN")).sum() == 2
    assert ((tables.paper == "DATA_PAPER") & (tables.role == "MAIN")).sum() == 3
