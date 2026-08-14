from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from stackwise.decision_engine import (
    align_cost_states,
    audit_summary,
    deterministic_weight_rows,
    engine_invariant_rows,
    fractional_tie_rank_mass,
    linear_minimize_value,
    run_synthetic_nested_dry_run,
    sample_dirichlet_weights,
    synthetic_energy_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return yaml.safe_load((ROOT / "datasets/stage6d_decision_engine_dry_run.yml").read_text(encoding="utf-8"))


def _csv(path: str):
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def _build():
    policy = _policy()
    candidates = list(policy["preferred_subset_stack_ids"])
    family = _csv(policy["inputs"]["cost_family"])
    states = align_cost_states(family, candidates)
    energy = synthetic_energy_rows(policy, candidates)
    weights = deterministic_weight_rows(policy)
    weight_summary, rank_envelope = run_synthetic_nested_dry_run(
        cost_states=states,
        energy_rows=energy,
        weight_rows=weights,
        candidate_ids=candidates,
        policy=policy,
    )
    invariants = engine_invariant_rows(
        cost_states=states,
        energy_rows=energy,
        weight_rows=weights,
        weight_summary_rows=weight_summary,
        fixture_envelope_rows=rank_envelope,
        candidate_ids=candidates,
        policy=policy,
    )
    return policy, candidates, states, energy, weights, weight_summary, rank_envelope, invariants


def test_stage6d_aligns_144_cost_states_across_all_four_candidates():
    policy, candidates, states, *_ = _build()
    assert len(states) == 144
    assert all(set(candidates).issubset(state) for state in states)
    assert all(state["probability_interpretation"] is False for state in states)
    assert len({state["cost_state_id"] for state in states}) == 144


def test_stage6d_synthetic_energy_fixtures_are_paired_and_never_publication_evidence():
    policy, candidates, _, energy, *_ = _build()
    assert len(energy) == 3 * 64 * 4
    assert {r["fixture_id"] for r in energy} == {
        "F0_ltem_energy_advantage",
        "F1_binding_tradeoff_rat_symmetry",
        "F2_nbiot_energy_advantage",
    }
    assert all(r["synthetic_fixture_only"] is True for r in energy)
    assert all(r["probability_interpretation"] is False for r in energy)
    # Same multiplicative block factor => within-fixture candidate ratios stay constant across draws.
    for fixture in {r["fixture_id"] for r in energy}:
        rows = [r for r in energy if r["fixture_id"] == fixture]
        by_draw = {}
        for r in rows:
            by_draw.setdefault(r["energy_draw_id"], {})[r["stack_id"]] = r["energy_j"]
        ratios = [
            d[candidates[0]] / d[candidates[1]]
            for d in by_draw.values()
        ]
        assert np.allclose(ratios, ratios[0])


def test_stage6d_fixed_value_function_is_monotone_and_not_alternative_normalized():
    x = np.array([0.0, 3.0, 6.0, 9.0])
    score = linear_minimize_value(x, best=0.0, worst=6.0)
    assert np.allclose(score, [1.0, 0.5, 0.0, 0.0])
    # Adding another alternative cannot alter the score of the original values because anchors are fixed externally.
    extended = linear_minimize_value(np.array([0.0, 3.0, 6.0, 9.0, 100.0]), best=0.0, worst=6.0)
    assert np.allclose(score, extended[:4])


def test_stage6d_fractional_tie_rank_mass_conserves_rank_mass():
    utilities = np.array([[1.0, 1.0, 0.5, 0.0], [2.0, 1.0, 1.0, 1.0]])
    mass = fractional_tie_rank_mass(utilities)
    assert np.allclose(mass.sum(axis=2), 1.0)
    assert np.allclose(mass.sum(axis=1), 1.0)
    assert np.allclose(mass[0, 0, :2], [0.5, 0.5])
    assert np.allclose(mass[0, 1, :2], [0.5, 0.5])


def test_stage6d_dirichlet_helper_is_reproducible_but_not_used_by_audit_policy():
    a = sample_dirichlet_weights([0.5, 0.5], concentration=20.0, samples=100, seed=26)
    b = sample_dirichlet_weights([0.5, 0.5], concentration=20.0, samples=100, seed=26)
    assert np.allclose(a, b)
    assert np.allclose(a.sum(axis=1), 1.0)
    policy = _policy()
    assert policy["preference_design"]["mode"] == "deterministic_grid"
    assert policy["scientific_policy"]["stakeholder_weight_probability_interpretation"] is False


def test_stage6d_nested_dry_run_reports_envelopes_not_pooled_epistemic_probabilities():
    policy, candidates, states, energy, weights, weight_summary, rank_envelope, invariants = _build()
    assert len(weight_summary) == 3 * 21 * 4
    assert len(rank_envelope) == 3 * 4
    assert all(r["cost_state_probability_interpretation"] is False for r in weight_summary)
    assert all(r["weight_probability_interpretation"] is False for r in weight_summary)
    assert all(r["pooled_global_rank_probability_reported"] is False for r in rank_envelope)
    assert all(r["publication_interpretation"] == "PROHIBITED_SYNTHETIC_FIXTURE_ONLY" for r in rank_envelope)
    summary = audit_summary(
        cost_states=states,
        energy_rows=energy,
        weight_rows=weights,
        weight_summary_rows=weight_summary,
        fixture_envelope_rows=rank_envelope,
        invariant_rows=invariants,
        candidate_ids=candidates,
        policy=policy,
    )
    assert summary.conditional_state_weight_evaluations == 9072
    assert summary.invariants_failed == 0


def test_stage6d_synthetic_fixtures_exercise_rat_reversal_and_exact_ties():
    _, _, _, _, _, weight_summary, _, invariants = _build()
    checks = {r["check_id"]: r["passed"] for r in invariants}
    assert checks["fixture_f0_ltem_energy_order_is_preserved"] is True
    assert checks["fixture_f2_nbiot_energy_order_is_preserved"] is True
    assert checks["fixture_f1_rat_symmetry_is_exact"] is True
    assert checks["fixture_f1_exhibits_preference_weight_sensitivity"] is True
    # In the F1 exact-RAT-tie fixture the within-binding candidates must have identical rank envelopes per weight.
    f1 = [r for r in weight_summary if r["fixture_id"] == "F1_binding_tradeoff_rat_symmetry"]
    by_key = {(r["weight_anchor_id"], r["stack_id"]): r for r in f1}
    for weight in {r["weight_anchor_id"] for r in f1}:
        for a, b in [
            ("nbiot_ip_coap_dtls_lwm2m", "ltem_ip_coap_dtls_lwm2m"),
            ("nbiot_ip_mqtt_tls_lwm2m", "ltem_ip_mqtt_tls_lwm2m"),
        ]:
            assert by_key[(weight, a)]["rank1_acceptability_min_across_cost_states"] == by_key[(weight, b)]["rank1_acceptability_min_across_cost_states"]
            assert by_key[(weight, a)]["rank1_acceptability_max_across_cost_states"] == by_key[(weight, b)]["rank1_acceptability_max_across_cost_states"]


def test_stage6d_publication_ranking_remains_blocked_until_real_energy_exists():
    policy, *_rest, invariants = _build()
    checks = {r["check_id"]: r["passed"] for r in invariants}
    assert checks["publication_ranking_remains_prohibited"] is True
    assert policy["scientific_policy"]["publication_mcda_authorised"] is False
    assert policy["scientific_policy"]["real_candidate_ranking_authorised"] is False
