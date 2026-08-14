from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from typing import Any, Iterable


@dataclass(frozen=True)
class CostRobustnessSummary:
    preferred_subset_candidates: int
    source_stage5n_rows: int
    billing_anchors: int
    procurement_anchors: int
    cost_family_rows: int
    cost_ready_candidates: int
    energy_ready_candidates: int
    first_slice_ready_candidates: int
    candidates_with_identical_nb_iot_lte_m_cost_family_within_binding: int


def _d(v: Any) -> Decimal:
    return Decimal(str(v))


def _ceil_div_positive(numer: int, denom: int) -> int:
    if numer <= 0:
        return 0
    return (numer + denom - 1) // denom


def _round_up(value: int, unit: int) -> int:
    if value <= 0:
        return 0
    return _ceil_div_positive(value, unit) * unit


def source_evidence_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(x) for x in policy["source_updates"]]


def billing_anchor_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for x in policy["billing_session_anchors"]:
        r = dict(x)
        r["probability_interpretation"] = False
        rows.append(r)
    return rows


def procurement_anchor_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for x in policy["procurement_anchors"]:
        r = dict(x)
        r["probability_interpretation"] = False
        rows.append(r)
    return rows


def _preferred_keys(subset_rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> set[tuple[str, str]]:
    expected_scenario = str(policy["scientific_policy"]["scenario_id"])
    keys = {(str(r["scenario_id"]), str(r["stack_id"])) for r in subset_rows}
    if len(keys) != int(policy["expected"]["preferred_subset_candidates"]):
        raise ValueError(f"Expected four preferred subset candidates, got {len(keys)}")
    if {s for s, _ in keys} != {expected_scenario}:
        raise ValueError("Stage-6C preferred subset scenario drift detected.")
    return keys


def select_stage5n_rows(
    stage5n_rows: Iterable[dict[str, Any]],
    subset_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    keys = _preferred_keys(subset_rows, policy)
    selected = [dict(r) for r in stage5n_rows if (str(r["scenario_id"]), str(r["stack_id"])) in keys]
    selected.sort(key=lambda r: str(r["session_control_row_id"]))
    expected = int(policy["expected"]["source_stage5n_rows"])
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} Stage-5N rows for preferred subset, got {len(selected)}")
    return selected


def build_cost_family_rows(
    stage5n_rows: Iterable[dict[str, Any]],
    subset_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    selected = select_stage5n_rows(stage5n_rows, subset_rows, policy)
    billing = billing_anchor_rows(policy)
    procurement = procurement_anchor_rows(policy)
    fixed = policy["fixed_cash_components"]
    included = int(fixed["included_data_bytes"])
    topup_bytes = int(fixed["topup_increment_bytes"])
    topup_price = _d(fixed["topup_price_eur"])
    sim = _d(fixed["standard_sim_eur"])
    base = _d(fixed["base_connectivity_prepaid_eur"])

    out: list[dict[str, Any]] = []
    for src in selected:
        per_report = int(src["session_control_augmented_transport_bytes_per_report"])
        report_count = int(src["five_year_report_count"])
        raw_total = int(src["five_year_session_control_augmented_transport_bytes"])
        for b in billing:
            unit = int(b["rounding_unit_bytes"])
            if b["session_count_rule"] == "one_session_for_horizon":
                billed = _round_up(raw_total, unit)
                session_count = 1
            elif b["session_count_rule"] == "one_session_per_report":
                billed = _round_up(per_report, unit) * report_count
                session_count = report_count
            else:
                raise ValueError(f"Unknown billing session-count rule: {b['session_count_rule']}")
            topups = _ceil_div_positive(billed - included, topup_bytes)
            for p in procurement:
                module = _d(p["module_unit_price_eur"])
                cost = module + sim + base + _d(topups) * topup_price
                out.append({
                    "cost_family_row_id": f"{src['session_control_row_id']}__{b['billing_anchor_id']}__{p['procurement_anchor_id']}",
                    "scenario_id": src["scenario_id"],
                    "stack_id": src["stack_id"],
                    "access_technology": src["access_technology"],
                    "binding_family": src["binding_family"],
                    "anchor_id": src["anchor_id"],
                    "shape_id": src["shape_id"],
                    "session_control_envelope_id": src["envelope_id"],
                    "billing_anchor_id": b["billing_anchor_id"],
                    "procurement_anchor_id": p["procurement_anchor_id"],
                    "probability_interpretation": False,
                    "raw_transport_bytes_per_report": per_report,
                    "raw_transport_bytes_5y": raw_total,
                    "pdp_session_count_5y": session_count,
                    "billing_rounding_unit_bytes": unit,
                    "billed_transport_bytes_5y": billed,
                    "billed_transport_mb_5y": billed / 1_000_000.0,
                    "topup_count": topups,
                    "module_price_eur": float(module),
                    "standard_sim_eur": float(sim),
                    "base_connectivity_prepaid_eur": float(base),
                    "topup_cost_eur": float(_d(topups) * topup_price),
                    "lifecycle_cost_eur": float(cost),
                    "decision_use_status": "READY_ROBUSTNESS_FAMILY",
                    "score_authorised_when_energy_ready": True,
                    "publication_score_authorised_now": False,
                })
    out.sort(key=lambda r: str(r["cost_family_row_id"]))
    return out


def build_candidate_cost_summary_rows(family_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in family_rows:
        grouped[(str(r["scenario_id"]), str(r["stack_id"]))].append(r)
    out: list[dict[str, Any]] = []
    for (scenario_id, stack_id), rows in sorted(grouped.items()):
        costs = sorted({float(r["lifecycle_cost_eur"]) for r in rows})
        topups = sorted({int(r["topup_count"]) for r in rows})
        billed = [float(r["billed_transport_mb_5y"]) for r in rows]
        out.append({
            "scenario_id": scenario_id,
            "stack_id": stack_id,
            "binding_family": rows[0]["binding_family"],
            "access_technology": rows[0]["access_technology"],
            "family_member_rows": len(rows),
            "unique_lifecycle_cost_levels": len(costs),
            "lifecycle_cost_min_eur": min(costs),
            "lifecycle_cost_max_eur": max(costs),
            "topup_count_min": min(topups),
            "topup_count_max": max(topups),
            "billed_transport_min_mb_5y": min(billed),
            "billed_transport_max_mb_5y": max(billed),
            "cost_decision_use_status": "READY_ROBUSTNESS_FAMILY",
            "probability_interpretation": False,
            "energy_decision_use_status": "BLOCKED",
            "first_slice_candidate_ready": False,
            "publication_score_authorised": False,
        })
    return out


def _cost_signature(rows: list[dict[str, Any]]) -> tuple[tuple[str, str, str, str, float], ...]:
    return tuple(sorted((
        str(r["anchor_id"]), str(r["shape_id"]), str(r["session_control_envelope_id"]),
        f"{r['billing_anchor_id']}|{r['procurement_anchor_id']}", float(r["lifecycle_cost_eur"])
    ) for r in rows))


def count_candidates_with_identical_rat_cost_family_within_binding(family_rows: Iterable[dict[str, Any]]) -> int:
    data = list(family_rows)
    by_stack: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in data:
        by_stack[str(r["stack_id"])].append(r)
    pairs = [
        ("nbiot_ip_coap_dtls_lwm2m", "ltem_ip_coap_dtls_lwm2m"),
        ("nbiot_ip_mqtt_tls_lwm2m", "ltem_ip_mqtt_tls_lwm2m"),
    ]
    identical_candidates = 0
    for a, b in pairs:
        if a not in by_stack or b not in by_stack:
            continue
        if _cost_signature(by_stack[a]) == _cost_signature(by_stack[b]):
            identical_candidates += 2
    return identical_candidates


def audit_summary(
    family_rows: Iterable[dict[str, Any]],
    candidate_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> CostRobustnessSummary:
    family = list(family_rows)
    candidates = list(candidate_rows)
    result = CostRobustnessSummary(
        preferred_subset_candidates=len(candidates),
        source_stage5n_rows=len(family) // (len(policy["billing_session_anchors"]) * len(policy["procurement_anchors"])),
        billing_anchors=len(policy["billing_session_anchors"]),
        procurement_anchors=len(policy["procurement_anchors"]),
        cost_family_rows=len(family),
        cost_ready_candidates=sum(r["cost_decision_use_status"] == "READY_ROBUSTNESS_FAMILY" for r in candidates),
        energy_ready_candidates=sum(r["energy_decision_use_status"].startswith("READY") for r in candidates),
        first_slice_ready_candidates=sum(bool(r["first_slice_candidate_ready"]) for r in candidates),
        candidates_with_identical_nb_iot_lte_m_cost_family_within_binding=count_candidates_with_identical_rat_cost_family_within_binding(family),
    )
    expected = policy["expected"]
    for key, actual in result.__dict__.items():
        if key in expected and actual != int(expected[key]):
            raise ValueError(f"Stage-6C expected {key}={expected[key]}, observed {actual}")
    return result
