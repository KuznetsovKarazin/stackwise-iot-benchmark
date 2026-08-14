from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np


COST_STATE_FIELDS = (
    "anchor_id",
    "shape_id",
    "session_control_envelope_id",
    "billing_anchor_id",
    "procurement_anchor_id",
)


@dataclass(frozen=True)
class DecisionEngineDryRunSummary:
    preferred_subset_candidates: int
    aligned_cost_states: int
    synthetic_energy_fixtures: int
    synthetic_energy_draws_per_fixture: int
    deterministic_weight_anchors: int
    conditional_state_weight_evaluations: int
    weight_sensitivity_rows: int
    rank_envelope_rows: int
    invariants_passed: int
    invariants_failed: int


def _cost_state_signature(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(row[field]) for field in COST_STATE_FIELDS)


def _cost_state_id(signature: Sequence[str]) -> str:
    return "C__" + "__".join(signature)


def align_cost_states(
    family_rows: Iterable[dict[str, Any]],
    candidate_ids: Sequence[str],
) -> list[dict[str, Any]]:
    candidates = tuple(candidate_ids)
    expected = set(candidates)
    grouped: dict[tuple[str, ...], dict[str, float]] = defaultdict(dict)
    metadata: dict[tuple[str, ...], dict[str, str]] = {}

    for row in family_rows:
        stack_id = str(row["stack_id"])
        if stack_id not in expected:
            continue
        signature = _cost_state_signature(row)
        if stack_id in grouped[signature]:
            raise ValueError(f"Duplicate candidate in aligned cost state: {signature} / {stack_id}")
        grouped[signature][stack_id] = float(row["lifecycle_cost_eur"])
        metadata.setdefault(signature, {field: str(row[field]) for field in COST_STATE_FIELDS})

    out: list[dict[str, Any]] = []
    for signature in sorted(grouped):
        costs = grouped[signature]
        if set(costs) != expected:
            missing = sorted(expected - set(costs))
            extra = sorted(set(costs) - expected)
            raise ValueError(
                f"Cost-state candidate alignment failure for {signature}; missing={missing}, extra={extra}"
            )
        row: dict[str, Any] = {
            "cost_state_id": _cost_state_id(signature),
            **metadata[signature],
            "probability_interpretation": False,
        }
        for candidate in candidates:
            row[candidate] = costs[candidate]
        out.append(row)
    return out


def synthetic_energy_rows(
    policy: dict[str, Any],
    candidate_ids: Sequence[str],
) -> list[dict[str, Any]]:
    candidates = tuple(candidate_ids)
    rows: list[dict[str, Any]] = []
    for fixture in policy["synthetic_energy_fixtures"]:
        fixture_id = str(fixture["fixture_id"])
        means = {str(k): float(v) for k, v in fixture["mean_energy_j"].items()}
        if set(means) != set(candidates):
            raise ValueError(f"Synthetic fixture {fixture_id} does not cover the preferred subset exactly")
        draws = int(fixture["draws"])
        sigma = float(fixture["shared_log_sd"])
        rng = np.random.default_rng(int(fixture["seed"]))
        # Mean-corrected common multiplicative factor. The same factor is applied to all candidates
        # in one synthetic block so the dry run exercises paired/repeated-measures semantics.
        factor = rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=draws)
        for draw_id, common_factor in enumerate(factor):
            for candidate in candidates:
                rows.append({
                    "fixture_id": fixture_id,
                    "energy_draw_id": draw_id,
                    "stack_id": candidate,
                    "energy_j": means[candidate] * float(common_factor),
                    "synthetic_fixture_only": True,
                    "probability_interpretation": False,
                    "shared_block_factor": True,
                })
    return rows


def deterministic_weight_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    weights = [float(x) for x in policy["preference_design"]["energy_weight_grid"]]
    out: list[dict[str, Any]] = []
    for idx, w_energy in enumerate(weights):
        if not 0.0 <= w_energy <= 1.0:
            raise ValueError(f"Energy weight outside [0,1]: {w_energy}")
        out.append({
            "weight_anchor_id": f"W{idx:02d}",
            "energy_weight": w_energy,
            "cost_weight": 1.0 - w_energy,
            "probability_interpretation": False,
        })
    return out


def sample_dirichlet_weights(
    baseline: Sequence[float],
    *,
    concentration: float,
    samples: int,
    seed: int,
) -> np.ndarray:
    """Explicit stochastic-weight helper for later use; never called by the Stage-6D audit."""
    baseline_arr = np.asarray(baseline, dtype=float)
    if baseline_arr.ndim != 1 or len(baseline_arr) < 2:
        raise ValueError("baseline must be a one-dimensional vector with at least two criteria")
    if np.any(baseline_arr <= 0) or not np.isfinite(baseline_arr).all():
        raise ValueError("baseline weights must be finite and strictly positive")
    baseline_arr = baseline_arr / baseline_arr.sum()
    if concentration <= 0 or samples <= 0:
        raise ValueError("concentration and samples must be positive")
    rng = np.random.default_rng(seed)
    return rng.dirichlet(baseline_arr * float(concentration), size=int(samples))


def linear_minimize_value(value: np.ndarray | float, *, best: float, worst: float) -> np.ndarray:
    if not np.isfinite(best) or not np.isfinite(worst) or worst <= best:
        raise ValueError("Fixed value-function anchors require finite worst > best")
    arr = np.asarray(value, dtype=float)
    scaled = 1.0 - (arr - best) / (worst - best)
    return np.clip(scaled, 0.0, 1.0)


def fractional_tie_rank_mass(utilities: np.ndarray, *, tolerance: float = 1e-12) -> np.ndarray:
    """Return rank mass [draw, alternative, rank], splitting tied groups across occupied ranks."""
    values = np.asarray(utilities, dtype=float)
    if values.ndim != 2:
        raise ValueError("utilities must have shape [draw, alternative]")
    n_draws, n_alt = values.shape
    mass = np.zeros((n_draws, n_alt, n_alt), dtype=float)
    for d in range(n_draws):
        order = np.argsort(-values[d], kind="stable")
        start = 0
        while start < n_alt:
            end = start + 1
            reference = values[d, order[start]]
            while end < n_alt and abs(values[d, order[end]] - reference) <= tolerance:
                end += 1
            group = order[start:end]
            share = 1.0 / len(group)
            for alt in group:
                mass[d, alt, start:end] = share
            start = end
    return mass


def _energy_arrays(
    rows: Iterable[dict[str, Any]],
    candidate_ids: Sequence[str],
) -> dict[str, np.ndarray]:
    candidates = tuple(candidate_ids)
    by_fixture: dict[str, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        by_fixture[str(row["fixture_id"])][int(row["energy_draw_id"])][str(row["stack_id"])] = float(row["energy_j"])

    out: dict[str, np.ndarray] = {}
    for fixture_id, draws in by_fixture.items():
        draw_ids = sorted(draws)
        matrix = np.empty((len(draw_ids), len(candidates)), dtype=float)
        for i, draw_id in enumerate(draw_ids):
            if set(draws[draw_id]) != set(candidates):
                raise ValueError(f"Energy draw {fixture_id}/{draw_id} does not cover all candidates")
            matrix[i] = [draws[draw_id][candidate] for candidate in candidates]
        out[fixture_id] = matrix
    return out


def run_synthetic_nested_dry_run(
    *,
    cost_states: Iterable[dict[str, Any]],
    energy_rows: Iterable[dict[str, Any]],
    weight_rows: Iterable[dict[str, Any]],
    candidate_ids: Sequence[str],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run a synthetic-only nested robustness dry run.

    Energy draws are the only sampled layer. Cost states and weight anchors are enumerated and are never pooled
    into a probability distribution. Returned summaries therefore contain envelopes and state counts, not global
    rank probabilities.
    """
    candidates = tuple(candidate_ids)
    states = list(cost_states)
    weights = list(weight_rows)
    energy = _energy_arrays(energy_rows, candidates)
    vf = policy["synthetic_value_functions"]
    e_best = float(vf["energy_j"]["best"])
    e_worst = float(vf["energy_j"]["worst"])
    c_best = float(vf["lifecycle_cost_eur"]["best"])
    c_worst = float(vf["lifecycle_cost_eur"]["worst"])
    tie_tol = float(policy["engine_policy"]["tie_tolerance"])

    # fixture -> weight -> candidate -> list of per-cost-state rank vectors
    grouped: dict[str, dict[str, dict[str, list[np.ndarray]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for fixture_id, e_values in energy.items():
        e_scores = linear_minimize_value(e_values, best=e_best, worst=e_worst)
        for state in states:
            c_values = np.array([float(state[c]) for c in candidates], dtype=float)
            c_scores = linear_minimize_value(c_values, best=c_best, worst=c_worst)
            for wrow in weights:
                w_e = float(wrow["energy_weight"])
                w_c = float(wrow["cost_weight"])
                utilities = w_e * e_scores + w_c * c_scores[None, :]
                rank_mass = fractional_tie_rank_mass(utilities, tolerance=tie_tol).mean(axis=0)
                for idx, candidate in enumerate(candidates):
                    grouped[fixture_id][str(wrow["weight_anchor_id"])][candidate].append(rank_mass[idx])

    weight_summary: list[dict[str, Any]] = []
    fixture_envelope: list[dict[str, Any]] = []
    weight_lookup = {str(r["weight_anchor_id"]): r for r in weights}

    for fixture_id in sorted(grouped):
        fixture_candidate_all: dict[str, list[np.ndarray]] = defaultdict(list)
        for weight_id in sorted(grouped[fixture_id]):
            for candidate in candidates:
                state_rank = np.vstack(grouped[fixture_id][weight_id][candidate])
                fixture_candidate_all[candidate].extend(grouped[fixture_id][weight_id][candidate])
                possible = np.where(state_rank.max(axis=0) > 0)[0]
                weight_summary.append({
                    "fixture_id": fixture_id,
                    "weight_anchor_id": weight_id,
                    "energy_weight": weight_lookup[weight_id]["energy_weight"],
                    "cost_weight": weight_lookup[weight_id]["cost_weight"],
                    "stack_id": candidate,
                    "rank1_acceptability_min_across_cost_states": float(state_rank[:, 0].min()),
                    "rank1_acceptability_max_across_cost_states": float(state_rank[:, 0].max()),
                    "cost_states_with_nonzero_rank1": int(np.sum(state_rank[:, 0] > 0)),
                    "best_rank_possible": int(possible.min() + 1),
                    "worst_rank_possible": int(possible.max() + 1),
                    "cost_states_enumerated": int(state_rank.shape[0]),
                    "cost_state_probability_interpretation": False,
                    "weight_probability_interpretation": False,
                    "synthetic_energy_only": True,
                })

        for candidate in candidates:
            all_rank = np.vstack(fixture_candidate_all[candidate])
            possible = np.where(all_rank.max(axis=0) > 0)[0]
            fixture_envelope.append({
                "fixture_id": fixture_id,
                "stack_id": candidate,
                "rank1_acceptability_min_across_all_cost_states_and_weights": float(all_rank[:, 0].min()),
                "rank1_acceptability_max_across_all_cost_states_and_weights": float(all_rank[:, 0].max()),
                "best_rank_possible": int(possible.min() + 1),
                "worst_rank_possible": int(possible.max() + 1),
                "pooled_global_rank_probability_reported": False,
                "publication_interpretation": "PROHIBITED_SYNTHETIC_FIXTURE_ONLY",
            })

    return weight_summary, fixture_envelope


def engine_invariant_rows(
    *,
    cost_states: list[dict[str, Any]],
    energy_rows: list[dict[str, Any]],
    weight_rows: list[dict[str, Any]],
    weight_summary_rows: list[dict[str, Any]],
    fixture_envelope_rows: list[dict[str, Any]],
    candidate_ids: Sequence[str],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = tuple(candidate_ids)
    e_arrays = _energy_arrays(energy_rows, candidates)
    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "aligned_cost_states_are_unweighted",
        all(r.get("probability_interpretation") is False for r in cost_states),
        "Stage-6C protocol/billing/procurement states remain enumerated epistemic/deployment states.",
    ))
    checks.append((
        "deterministic_weight_grid_is_unweighted",
        all(r.get("probability_interpretation") is False for r in weight_rows),
        "Stakeholder weights are sensitivity anchors, not sampled stakeholder probabilities in Stage 6D.",
    ))
    checks.append((
        "synthetic_energy_is_never_publication_evidence",
        all(bool(r.get("synthetic_fixture_only")) and r.get("probability_interpretation") is False for r in energy_rows),
        "Synthetic draws exercise the engine only and must never be exported as scientific evidence.",
    ))

    # Fixed value functions must not depend on the alternative set.
    checks.append((
        "fixed_value_functions_no_alternative_set_normalisation",
        str(policy["engine_policy"]["normalisation_mode"]) == "fixed_external_linear_value_anchors",
        "Value transformation uses policy anchors rather than min/max of the alternatives under comparison.",
    ))

    # Rank-mass conservation including exact ties.
    toy = np.array([[1.0, 1.0, 0.5, 0.0], [2.0, 1.0, 1.0, 1.0]])
    toy_mass = fractional_tie_rank_mass(toy, tolerance=float(policy["engine_policy"]["tie_tolerance"]))
    tie_ok = np.allclose(toy_mass.sum(axis=2), 1.0) and np.allclose(toy_mass.sum(axis=1), 1.0)
    checks.append((
        "fractional_tie_rank_mass_conserves_probability_mass",
        bool(tie_ok),
        "Each alternative receives unit total rank mass and each occupied rank receives unit cross-alternative mass.",
    ))

    # Permutation invariance of rank mass.
    base = np.array([[0.7, 0.7, 0.2, 0.1], [0.9, 0.4, 0.4, 0.2]])
    perm = np.array([2, 0, 3, 1])
    inv = np.argsort(perm)
    m1 = fractional_tie_rank_mass(base)
    m2 = fractional_tie_rank_mass(base[:, perm])[:, inv, :]
    checks.append((
        "rank_engine_is_alternative_permutation_invariant",
        bool(np.allclose(m1, m2)),
        "Reordering candidates does not change rank mass after mapping candidate labels back.",
    ))

    # Synthetic fixture ordering invariants.
    idx = {candidate: i for i, candidate in enumerate(candidates)}
    f0 = e_arrays["F0_ltem_energy_advantage"]
    ltem_better = np.all(f0[:, idx["ltem_ip_coap_dtls_lwm2m"]] < f0[:, idx["nbiot_ip_coap_dtls_lwm2m"]]) and np.all(
        f0[:, idx["ltem_ip_mqtt_tls_lwm2m"]] < f0[:, idx["nbiot_ip_mqtt_tls_lwm2m"]]
    )
    checks.append((
        "fixture_f0_ltem_energy_order_is_preserved",
        bool(ltem_better),
        "Synthetic fixture F0 must preserve the intentionally imposed LTE-M energy advantage in every paired draw.",
    ))

    f2 = e_arrays["F2_nbiot_energy_advantage"]
    nbiot_better = np.all(f2[:, idx["nbiot_ip_coap_dtls_lwm2m"]] < f2[:, idx["ltem_ip_coap_dtls_lwm2m"]]) and np.all(
        f2[:, idx["nbiot_ip_mqtt_tls_lwm2m"]] < f2[:, idx["ltem_ip_mqtt_tls_lwm2m"]]
    )
    checks.append((
        "fixture_f2_nbiot_energy_order_is_preserved",
        bool(nbiot_better),
        "Synthetic fixture F2 must preserve the intentionally imposed NB-IoT energy advantage in every paired draw.",
    ))

    f1 = e_arrays["F1_binding_tradeoff_rat_symmetry"]
    rat_tie = np.allclose(f1[:, idx["nbiot_ip_coap_dtls_lwm2m"]], f1[:, idx["ltem_ip_coap_dtls_lwm2m"]]) and np.allclose(
        f1[:, idx["nbiot_ip_mqtt_tls_lwm2m"]], f1[:, idx["ltem_ip_mqtt_tls_lwm2m"]]
    )
    checks.append((
        "fixture_f1_rat_symmetry_is_exact",
        bool(rat_tie),
        "F1 deliberately ties NB-IoT and LTE-M within each binding to exercise tie handling.",
    ))

    # Cost symmetry within binding under shared BG95/operator reference must still hold across aligned states.
    cost_symmetry = all(
        abs(float(s["nbiot_ip_coap_dtls_lwm2m"]) - float(s["ltem_ip_coap_dtls_lwm2m"])) <= 1e-12
        and abs(float(s["nbiot_ip_mqtt_tls_lwm2m"]) - float(s["ltem_ip_mqtt_tls_lwm2m"])) <= 1e-12
        for s in cost_states
    )
    checks.append((
        "stage6c_rat_cost_symmetry_is_preserved",
        bool(cost_symmetry),
        "Shared dual-mode hardware/operator must keep NB-IoT and LTE-M cost equal within a binding in Stage-6C states.",
    ))

    # F1 must be preference-sensitive: at least one candidate can be rank-1 under one weight condition and not under another.
    f1_rows = [r for r in weight_summary_rows if r["fixture_id"] == "F1_binding_tradeoff_rat_symmetry"]
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in f1_rows:
        by_candidate[str(row["stack_id"])].append(row)
    sensitivity = any(
        max(float(r["rank1_acceptability_max_across_cost_states"]) for r in rows) > 0
        and min(float(r["rank1_acceptability_max_across_cost_states"]) for r in rows) == 0
        for rows in by_candidate.values()
    )
    checks.append((
        "fixture_f1_exhibits_preference_weight_sensitivity",
        bool(sensitivity),
        "The trade-off fixture must produce a real change in rank-1 possibility across the deterministic weight grid.",
    ))

    checks.append((
        "no_pooled_epistemic_rank_probability_is_reported",
        all(not bool(r["pooled_global_rank_probability_reported"]) for r in fixture_envelope_rows),
        "Cost states and weight anchors are summarised by envelopes; they are never averaged into a global probability.",
    ))

    checks.append((
        "publication_ranking_remains_prohibited",
        not bool(policy["scientific_policy"]["publication_mcda_authorised"]),
        "Stage 6D validates software only; matched Stage-6B energy measurements are still absent.",
    ))

    return [
        {"check_id": check_id, "passed": passed, "interpretation": interpretation}
        for check_id, passed, interpretation in checks
    ]


def audit_summary(
    *,
    cost_states: list[dict[str, Any]],
    energy_rows: list[dict[str, Any]],
    weight_rows: list[dict[str, Any]],
    weight_summary_rows: list[dict[str, Any]],
    fixture_envelope_rows: list[dict[str, Any]],
    invariant_rows: list[dict[str, Any]],
    candidate_ids: Sequence[str],
    policy: dict[str, Any],
) -> DecisionEngineDryRunSummary:
    fixture_ids = sorted({str(r["fixture_id"]) for r in energy_rows})
    draws_by_fixture = {
        fixture_id: len({int(r["energy_draw_id"]) for r in energy_rows if str(r["fixture_id"]) == fixture_id})
        for fixture_id in fixture_ids
    }
    if len(set(draws_by_fixture.values())) != 1:
        raise ValueError(f"Synthetic fixtures have inconsistent draw counts: {draws_by_fixture}")
    draws_per_fixture = next(iter(draws_by_fixture.values()))
    result = DecisionEngineDryRunSummary(
        preferred_subset_candidates=len(candidate_ids),
        aligned_cost_states=len(cost_states),
        synthetic_energy_fixtures=len(fixture_ids),
        synthetic_energy_draws_per_fixture=draws_per_fixture,
        deterministic_weight_anchors=len(weight_rows),
        conditional_state_weight_evaluations=len(cost_states) * len(weight_rows) * len(fixture_ids),
        weight_sensitivity_rows=len(weight_summary_rows),
        rank_envelope_rows=len(fixture_envelope_rows),
        invariants_passed=sum(bool(r["passed"]) for r in invariant_rows),
        invariants_failed=sum(not bool(r["passed"]) for r in invariant_rows),
    )
    expected = policy["expected"]
    for key, actual in result.__dict__.items():
        if key in expected and actual != int(expected[key]):
            raise ValueError(f"Stage-6D expected {key}={expected[key]}, observed {actual}")
    if result.invariants_failed:
        failed = [r["check_id"] for r in invariant_rows if not bool(r["passed"])]
        raise ValueError(f"Stage-6D engine invariant failure(s): {failed}")
    return result
