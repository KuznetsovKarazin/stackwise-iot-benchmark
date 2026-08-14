from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


READY_STATUSES = {"READY_DIRECT", "READY_BRIDGED"}
ALLOWED_RELATIONS = {"DIRECT", "BRIDGEABLE", "CONDITIONAL_INPUT_ONLY", "MISSING", "INCOMPATIBLE"}


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class DecisionReadinessSummary:
    audited_candidate_rows: int
    audited_target_rows: int
    ready_target_rows: int
    feasible_candidate_rows: int
    feasible_first_slice_fully_ready_rows: int
    feasible_cellular_ip_rows: int
    cellular_ip_energy_unlock_scenarios: int


def expand_evidence_rules(policy: dict[str, Any], stack_ids: set[str]) -> dict[tuple[str, str], dict[str, Any]]:
    target_ids = {str(x["target_metric_id"]) for x in policy["decision_targets"]}
    expanded: dict[tuple[str, str], dict[str, Any]] = {}
    for rule in policy["evidence_rules"]:
        relation = str(rule["evidence_relation"])
        if relation not in ALLOWED_RELATIONS:
            raise ValueError(f"Unsupported evidence relation {relation!r} in {rule['rule_id']}")
        target = str(rule["target_metric_id"])
        if target not in target_ids:
            raise ValueError(f"Unknown target {target!r} in {rule['rule_id']}")
        for stack_id in rule["stack_ids"]:
            stack_id = str(stack_id)
            if stack_id not in stack_ids:
                raise ValueError(f"Unknown stack {stack_id!r} in {rule['rule_id']}")
            key = (stack_id, target)
            if key in expanded:
                raise ValueError(f"Duplicate readiness rule for {stack_id}/{target}")
            expanded[key] = dict(rule)
    expected = {(s, t) for s in stack_ids for t in target_ids}
    missing = sorted(expected - set(expanded))
    extra = sorted(set(expanded) - expected)
    if missing or extra:
        raise ValueError(f"Readiness rules do not cover the complete stack x target grid. missing={missing}, extra={extra}")
    return expanded


def _profile_lookup(profile_rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in profile_rows:
        key = (str(row["scenario_id"]), str(row["stack_id"]))
        if key in out:
            raise ValueError(f"Duplicate operating profile for {key}")
        out[key] = row
    return out


def _profile_state(*, rule: dict[str, Any], scenario_id: str, stack_id: str, profiles: dict[tuple[str, str], dict[str, Any]]) -> str:
    if not _bool(rule.get("profile_required", False)):
        return "NOT_REQUIRED"
    row = profiles.get((scenario_id, stack_id))
    if row is None:
        return "NOT_MATERIALISED"
    unresolved = int(row.get("unresolved_required_field_count") or 0)
    return "COMPLETE" if unresolved == 0 else "PARTIAL"


def _readiness_status(*, relation: str, profile_state: str, bridge_materialised: bool) -> str:
    if relation == "DIRECT":
        return "READY_DIRECT"
    if relation == "BRIDGEABLE":
        if bridge_materialised and profile_state in {"COMPLETE", "NOT_REQUIRED"}:
            return "READY_BRIDGED"
        if profile_state in {"PARTIAL", "NOT_MATERIALISED"}:
            return "PROFILE_UNRESOLVED"
        return "BRIDGEABLE"
    if relation == "CONDITIONAL_INPUT_ONLY":
        return "ROBUSTNESS_ONLY"
    if relation == "INCOMPATIBLE":
        return "INCOMPATIBLE"
    return "MISSING"


def build_candidate_target_readiness(
    *,
    feasibility_rows: Iterable[dict[str, Any]],
    candidate_rows: Iterable[dict[str, Any]],
    profile_rows: Iterable[dict[str, Any]],
    bridge_rows: Iterable[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    feasibility = list(feasibility_rows)
    candidates = list(candidate_rows)
    stack_ids = {str(r["stack_id"]) for r in candidates}
    if len(stack_ids) != len(candidates):
        raise ValueError("Candidate stack catalogue contains duplicate stack IDs.")
    rules = expand_evidence_rules(policy, stack_ids)
    profiles = _profile_lookup(profile_rows)
    target_meta = {str(x["target_metric_id"]): x for x in policy["decision_targets"]}

    bridge_lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in bridge_rows:
        key = (str(row["scenario_id"]), str(row["stack_id"]), str(row["target_metric_id"]))
        bridge_lookup[key] = row

    rows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for frow in feasibility:
        status = str(frow["status"])
        if status == "infeasible":
            continue
        scenario_id = str(frow["scenario_id"])
        stack_id = str(frow["stack_id"])
        pair = (scenario_id, stack_id)
        if pair in seen_pairs:
            raise ValueError(f"Duplicate non-infeasible scenario/stack pair {pair}")
        seen_pairs.add(pair)
        if stack_id not in stack_ids:
            raise ValueError(f"Feasibility matrix references unknown stack {stack_id!r}")

        for target_id, meta in target_meta.items():
            rule = rules[(stack_id, target_id)]
            profile_state = _profile_state(rule=rule, scenario_id=scenario_id, stack_id=stack_id, profiles=profiles)
            bridge = bridge_lookup.get((scenario_id, stack_id, target_id))
            bridge_materialised = False
            bridge_state = "NO_CONTRACT"
            if bridge is not None:
                bridge_state = str(bridge.get("scientific_status") or "CONTRACT_PRESENT")
                bridge_materialised = _bool(bridge.get("numeric_output_materialised", False)) or "materialised" in bridge_state.lower() and "blocked" not in bridge_state.lower()
            relation = str(rule["evidence_relation"])
            readiness = _readiness_status(relation=relation, profile_state=profile_state, bridge_materialised=bridge_materialised)
            rows.append({
                "scenario_id": scenario_id,
                "stack_id": stack_id,
                "feasibility_status": status,
                "target_metric_id": target_id,
                "target_role": str(meta["role"]),
                "first_slice_required": bool(meta["first_slice_required"]),
                "rule_id": str(rule["rule_id"]),
                "evidence_relation": relation,
                "source_dataset_ids": "|".join(map(str, rule.get("source_dataset_ids", []))),
                "source_metric_ids": "|".join(map(str, rule.get("source_metric_ids", []))),
                "profile_state": profile_state,
                "bridge_state": bridge_state,
                "uncertainty_state": str(rule["uncertainty_state"]),
                "readiness_status": readiness,
                "gap_id": str(rule["gap_id"]),
                "blocking_reasons": "|".join(map(str, rule.get("blocking_reasons", []))),
                "closure_action": str(rule["closure_action"]),
            })
    return rows


def build_gap_priority_rows(readiness_rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(readiness_rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["gap_id"])].append(row)

    out: list[dict[str, Any]] = []
    for gap_id, grows in grouped.items():
        feasible = [r for r in grows if r["feasibility_status"] == "feasible"]
        first_slice = any(_bool(r["first_slice_required"]) for r in grows)
        relations = sorted({str(r["evidence_relation"]) for r in grows})
        relation_class = "mixed" if len(relations) != 1 else relations[0]
        scenarios = sorted({str(r["scenario_id"]) for r in feasible})
        stacks = sorted({str(r["stack_id"]) for r in feasible})
        closure_action = str(grows[0]["closure_action"])
        out.append({
            "gap_id": gap_id,
            "first_slice_required": first_slice,
            "evidence_relation": relation_class,
            "affected_feasible_candidate_rows": len(feasible),
            "affected_feasible_scenarios": len(scenarios),
            "feasible_scenario_ids": "|".join(scenarios),
            "feasible_stack_ids": "|".join(stacks),
            "closure_action": closure_action,
        })

    preferred = str(policy["priority_policy"]["preferred_next_existing_evidence_bridge"])
    mandatory_parallel = str(policy["priority_policy"].get("mandatory_parallel_contract", ""))
    relation_order = {"BRIDGEABLE": 0, "CONDITIONAL_INPUT_ONLY": 1, "MISSING": 2, "INCOMPATIBLE": 3, "mixed": 4}
    def priority_bucket(row: dict[str, Any]) -> int:
        if row["gap_id"] == preferred:
            return 0
        if row["gap_id"] == mandatory_parallel:
            return 1
        return 2
    out.sort(key=lambda r: (
        priority_bucket(r),
        0 if _bool(r["first_slice_required"]) else 1,
        relation_order.get(str(r["evidence_relation"]), 9),
        -int(r["affected_feasible_candidate_rows"]),
        str(r["gap_id"]),
    ))
    for idx, row in enumerate(out, start=1):
        row["audit_priority_order"] = idx
        row["preferred_next_existing_evidence_bridge"] = row["gap_id"] == preferred
        row["mandatory_parallel_contract"] = row["gap_id"] == mandatory_parallel
    return out


def scenario_readiness_rows(readiness_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(readiness_rows)
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["feasibility_status"] == "feasible":
            by_scenario[str(row["scenario_id"])].append(row)

    out: list[dict[str, Any]] = []
    for scenario_id, srows in sorted(by_scenario.items()):
        by_stack: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in srows:
            by_stack[str(row["stack_id"])].append(row)
        first_slice_ready_stacks: list[str] = []
        energy_relation_bridgeable_stacks: list[str] = []
        for stack_id, trows in by_stack.items():
            required = [r for r in trows if _bool(r["first_slice_required"])]
            if required and all(str(r["readiness_status"]) in READY_STATUSES for r in required):
                first_slice_ready_stacks.append(stack_id)
            energy = next(r for r in trows if r["target_metric_id"] == "expected_device_energy_per_application_report_j")
            if energy["evidence_relation"] == "BRIDGEABLE":
                energy_relation_bridgeable_stacks.append(stack_id)
        out.append({
            "scenario_id": scenario_id,
            "feasible_candidate_count": len(by_stack),
            "first_slice_ready_candidate_count": len(first_slice_ready_stacks),
            "first_slice_comparison_ready": len(first_slice_ready_stacks) >= 2,
            "first_slice_ready_stack_ids": "|".join(sorted(first_slice_ready_stacks)),
            "energy_bridgeable_candidate_count": len(energy_relation_bridgeable_stacks),
            "energy_bridgeable_stack_ids": "|".join(sorted(energy_relation_bridgeable_stacks)),
        })
    return out


def audit_summary(readiness_rows: Iterable[dict[str, Any]], scenario_rows: Iterable[dict[str, Any]], policy: dict[str, Any]) -> DecisionReadinessSummary:
    rows = list(readiness_rows)
    scenarios = list(scenario_rows)
    candidate_pairs = {(str(r["scenario_id"]), str(r["stack_id"])) for r in rows}
    feasible_pairs = {(str(r["scenario_id"]), str(r["stack_id"])) for r in rows if r["feasibility_status"] == "feasible"}
    ready = sum(str(r["readiness_status"]) in READY_STATUSES for r in rows)

    first_slice_ready_pairs = set()
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["feasibility_status"] == "feasible":
            by_pair[(str(r["scenario_id"]), str(r["stack_id"]))].append(r)
    for pair, prows in by_pair.items():
        required = [r for r in prows if _bool(r["first_slice_required"])]
        if required and all(str(r["readiness_status"]) in READY_STATUSES for r in required):
            first_slice_ready_pairs.add(pair)

    cellular_ip = {
        "nbiot_ip_coap_dtls_lwm2m", "ltem_ip_coap_dtls_lwm2m",
        "nbiot_ip_mqtt_tls_lwm2m", "ltem_ip_mqtt_tls_lwm2m",
    }
    feasible_cellular_ip_rows = sum(1 for pair in feasible_pairs if pair[1] in cellular_ip)
    unlock_scenarios = sum(1 for s in scenarios if int(s["energy_bridgeable_candidate_count"]) >= 2)

    result = DecisionReadinessSummary(
        audited_candidate_rows=len(candidate_pairs),
        audited_target_rows=len(rows),
        ready_target_rows=ready,
        feasible_candidate_rows=len(feasible_pairs),
        feasible_first_slice_fully_ready_rows=len(first_slice_ready_pairs),
        feasible_cellular_ip_rows=feasible_cellular_ip_rows,
        cellular_ip_energy_unlock_scenarios=unlock_scenarios,
    )
    expected = policy["expected"]
    checks = {
        "audited_candidate_rows": result.audited_candidate_rows,
        "audited_target_rows": result.audited_target_rows,
        "ready_target_rows": result.ready_target_rows,
        "feasible_candidate_rows": result.feasible_candidate_rows,
        "feasible_first_slice_fully_ready_rows": result.feasible_first_slice_fully_ready_rows,
        "feasible_cellular_ip_rows": result.feasible_cellular_ip_rows,
        "cellular_ip_energy_unlock_scenarios": result.cellular_ip_energy_unlock_scenarios,
    }
    for key, actual in checks.items():
        if key in expected and actual != int(expected[key]):
            raise ValueError(f"Stage-5E expected {key}={expected[key]}, observed {actual}.")
    return result


def feasibility_counts(feasibility_rows: Iterable[dict[str, Any]]) -> Counter[str]:
    return Counter(str(r["status"]) for r in feasibility_rows)
