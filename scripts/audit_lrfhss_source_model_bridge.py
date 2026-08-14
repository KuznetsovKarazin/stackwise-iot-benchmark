from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from stackwise.lrfhss_source_model import (
    TX_CURRENT_A,
    airtime_breakdown,
    model_incremental_radio_energy_j,
)
from stackwise.provenance import write_run_manifest


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _b(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _f(value: Any) -> float:
    return float(value)


def _i(value: Any) -> int:
    return int(float(value))


def _table6_rows() -> list[dict[str, Any]]:
    # Published Table-6 values, represented at the precision shown in the paper.
    source_rows = [
        {"dr_family": "DR8_DR10", "representative_dr": 8, "frm_payload_bytes": 1, "source_header_ms": 700.4, "source_payload_ms": 870.4, "source_hops_ms": 2.475, "source_tx_total_ms": 1573.3},
        {"dr_family": "DR8_DR10", "representative_dr": 8, "frm_payload_bytes": 50, "source_header_ms": 700.4, "source_payload_ms": 3379.2, "source_hops_ms": 7.875, "source_tx_total_ms": 4087.5},
        {"dr_family": "DR9_DR11", "representative_dr": 9, "frm_payload_bytes": 1, "source_header_ms": 466.9, "source_payload_ms": 435.2, "source_hops_ms": 1.350, "source_tx_total_ms": 903.5},
        {"dr_family": "DR9_DR11", "representative_dr": 9, "frm_payload_bytes": 115, "source_header_ms": 466.9, "source_payload_ms": 3353.6, "source_hops_ms": 7.650, "source_tx_total_ms": 3828.2},
    ]
    rows: list[dict[str, Any]] = []
    for src in source_rows:
        air = airtime_breakdown(src["frm_payload_bytes"], src["representative_dr"])
        model = {
            "model_header_ms": air.header_duration_s * 1000,
            "model_payload_ms": air.payload_duration_s * 1000,
            "model_hops_ms": air.hop_duration_s * 1000,
            "model_tx_total_ms": air.tx_total_duration_s * 1000,
            "rendered_eq6_payload_ms": air.rendered_eq6_payload_duration_s * 1000,
        }
        row = {**src, **model}
        row["header_error_ms"] = round(row["model_header_ms"], 1) - row["source_header_ms"]
        row["payload_error_ms"] = round(row["model_payload_ms"], 1) - row["source_payload_ms"]
        row["hops_error_ms"] = round(row["model_hops_ms"], 3) - row["source_hops_ms"]
        row["tx_total_error_ms"] = round(row["model_tx_total_ms"], 1) - row["source_tx_total_ms"]
        row["table6_numeric_reproduced"] = all(abs(row[k]) < 1e-12 for k in ["header_error_ms", "payload_error_ms", "hops_error_ms", "tx_total_error_ms"])
        row["eq6_rendered_vs_table_payload_delta_ms"] = row["model_payload_ms"] - row["rendered_eq6_payload_ms"]
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the LR-FHSS published source model before any Stage-5 whole-device bridge activation.")
    ap.add_argument("--policy", type=Path, default=Path("datasets/stage5b_lrfhss_source_model_policy.yml"))
    ap.add_argument("--stage5a-summary", type=Path, default=Path("results/validation/stage5_operating_profiles/summary.json"))
    ap.add_argument("--stage5a-profiles", type=Path, default=Path("results/validation/stage5_operating_profiles/operating_profile_fields.csv"))
    ap.add_argument("--transaction-derivation", type=Path, default=Path("data/analysis_ready/lorawan_lrfhss_energy_2024/transaction_derivation.csv"))
    ap.add_argument("--trace-validation", type=Path, default=Path("results/validation/lrfhss/trace_validation.csv"))
    ap.add_argument("--stage3-state", type=Path, default=Path("data/analysis_ready/core_four_uncertainty/stage3_uncertainty_state.csv"))
    ap.add_argument("--output", type=Path, default=Path("results/validation/stage5_lrfhss_bridge_audit"))
    args = ap.parse_args()

    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8")) or {}
    expected = policy["expected"]
    scientific = policy["scientific_policy"]
    validation_policy = policy["validation_policy"]
    benchmark = policy["benchmark_refinement"]
    stage5a = json.loads(args.stage5a_summary.read_text(encoding="utf-8"))
    profiles = _read_csv(args.stage5a_profiles)
    tx_rows = _read_csv(args.transaction_derivation)
    trace_rows = _read_csv(args.trace_validation)
    stage3 = _read_csv(args.stage3_state)

    if (stage5a["stage4_feasible_rows"], stage5a["stage4_infeasible_rows"], stage5a["stage4_unresolved_rows"]) != (21, 39, 3):
        raise SystemExit("Stage-5B refuses to alter the frozen Stage-4 matrix.")
    if stage5a["numeric_bridge_outputs"] != 0 or stage5a["bridges_ready_for_numeric_evaluation"] != 0:
        raise SystemExit("Stage-5B expects all Stage-5A bridges to remain blocked before this audit.")

    lrfhss_unc = [r for r in stage3 if r.get("dataset_id") == "lorawan_lrfhss_energy_2024" and r.get("metric_id") == "radio_incremental_transaction_energy_j"]
    if len(lrfhss_unc) != 1 or lrfhss_unc[0].get("resolution_class") != "explicit_epistemic_gap":
        raise SystemExit("LR-FHSS Stage-3 single-trace epistemic-gap semantics were not preserved.")

    profile_rows = [r for r in profiles if r.get("profile_id") == "profile_lorawan_lrfhss_agriculture_energy"]
    payload = [r for r in profile_rows if r.get("field_id") == "application_payload_bytes"]
    if len(payload) != 1 or payload[0].get("status") != "known" or _i(payload[0]["value"]) != int(benchmark["frm_payload_bytes"]):
        raise SystemExit("Expected the 16-byte LR-FHSS benchmark payload to be scenario-derived in Stage-5A.")

    table_rows = _table6_rows()
    table_csv = args.output / "publication_table6_reproduction.csv"
    _write_csv(table_csv, table_rows, [
        "dr_family","representative_dr","frm_payload_bytes","source_header_ms","model_header_ms","header_error_ms",
        "source_payload_ms","model_payload_ms","rendered_eq6_payload_ms","eq6_rendered_vs_table_payload_delta_ms","payload_error_ms",
        "source_hops_ms","model_hops_ms","hops_error_ms","source_tx_total_ms","model_tx_total_ms","tx_total_error_ms","table6_numeric_reproduced"
    ])

    tx_map = {(r["confirmation_mode"], _i(r["source_dr_index"])): r for r in tx_rows}
    trace_map = {(r["confirmation_mode"], _i(r["source_dr_index"])): r for r in trace_rows}
    keys = sorted(tx_map, key=lambda x: (x[0], x[1]))
    if keys != sorted(trace_map, key=lambda x: (x[0], x[1])) or len(keys) != 8:
        raise SystemExit("Expected the same eight confirmation-mode x DR source configurations in transaction and trace artifacts.")

    tolerance = float(validation_policy["close_reproduction_abs_relative_error_pct"])
    source_payload = int(validation_policy["source_trace_payload_bytes"])
    reproduction: list[dict[str, Any]] = []
    plateau: list[dict[str, Any]] = []
    for mode, dr in keys:
        tx = tx_map[(mode, dr)]
        tr = trace_map[(mode, dr)]
        if _i(tr["payload_bytes"]) != source_payload or _i(tr["tx_power_dbm"]) != int(validation_policy["source_trace_tx_power_dbm"]):
            raise SystemExit(f"Unexpected source profile for {mode} DR{dr}.")
        observed = _f(tx["incremental_transaction_energy_j"])
        modeled = model_incremental_radio_energy_j(source_payload, dr, mode)
        rel = (modeled / observed - 1.0) * 100.0
        close = abs(rel) <= tolerance
        reproduction.append({
            "confirmation_mode": mode,
            "source_dr_index": dr,
            "frm_payload_bytes": source_payload,
            "tx_power_dbm": _f(tr["tx_power_dbm"]),
            "observed_incremental_radio_energy_j": observed,
            "source_model_incremental_radio_energy_j": modeled,
            "relative_error_pct": rel,
            "abs_relative_error_pct": abs(rel),
            "audit_tolerance_pct": tolerance,
            "close_source_trace_reproduction": close,
            "payload_extrapolation_authorised": bool(close and mode == "unconfirmed"),
            "population_uncertainty_identified": False,
        })
        measured_plateau = _f(tr["tx_plateau_mean_current_a"])
        plateau.append({
            "confirmation_mode": mode,
            "source_dr_index": dr,
            "measured_tx_plateau_current_a": measured_plateau,
            "published_model_tx_current_a": TX_CURRENT_A,
            "measured_to_model_ratio": measured_plateau / TX_CURRENT_A,
            "relative_difference_pct": (measured_plateau / TX_CURRENT_A - 1.0) * 100.0,
            "causal_explanation_identified": False,
        })

    reproduction_csv = args.output / "source_trace_reproduction_4byte.csv"
    _write_csv(reproduction_csv, reproduction, [
        "confirmation_mode","source_dr_index","frm_payload_bytes","tx_power_dbm","observed_incremental_radio_energy_j",
        "source_model_incremental_radio_energy_j","relative_error_pct","abs_relative_error_pct","audit_tolerance_pct",
        "close_source_trace_reproduction","payload_extrapolation_authorised","population_uncertainty_identified"
    ])
    plateau_csv = args.output / "confirmed_tx_plateau_diagnostic.csv"
    _write_csv(plateau_csv, plateau, [
        "confirmation_mode","source_dr_index","measured_tx_plateau_current_a","published_model_tx_current_a",
        "measured_to_model_ratio","relative_difference_pct","causal_explanation_identified"
    ])

    unconfirmed_pass = {(r["source_dr_index"]): bool(r["close_source_trace_reproduction"]) for r in reproduction if r["confirmation_mode"] == "unconfirmed"}
    confirmed_pass = {(r["source_dr_index"]): bool(r["close_source_trace_reproduction"]) for r in reproduction if r["confirmation_mode"] == "confirmed"}
    variants: list[dict[str, Any]] = []
    screen: list[dict[str, Any]] = []
    budget = float(benchmark["energy_budget_j"])
    benchmark_payload = int(benchmark["frm_payload_bytes"])
    for mode in ("unconfirmed", "confirmed"):
        for dr in (8, 9, 10, 11):
            energy = model_incremental_radio_energy_j(benchmark_payload, dr, mode)
            source_gate = unconfirmed_pass[dr] if mode == "unconfirmed" else confirmed_pass[dr]
            extrap_authorised = bool(source_gate and mode == "unconfirmed")
            above = bool(energy > budget) if extrap_authorised else None
            if not extrap_authorised:
                status = "model_not_authorised_for_payload_extrapolation"
            elif above:
                status = "matched_variant_infeasible_by_radio_component_lower_bound"
            else:
                status = "whole_device_unresolved_radio_component_below_or_equal_budget"
            variants.append({
                "confirmation_mode": mode,
                "source_dr_index": dr,
                "frm_payload_bytes": benchmark_payload,
                "tx_power_dbm": int(benchmark["source_aligned_tx_power_dbm"]),
                "source_4byte_reproduction_gate_passed": source_gate,
                "payload_extrapolation_authorised": extrap_authorised,
                "modeled_incremental_radio_energy_j": energy,
                "whole_device_budget_j": budget,
                "radio_component_exceeds_whole_device_budget": above,
                "numeric_quantity_semantics": "radio_module_incremental_class_a_transaction_model_diagnostic",
                "whole_device_energy_estimate": False,
                "population_distribution": False,
            })
            screen.append({
                "confirmation_mode": mode,
                "source_dr_index": dr,
                "frm_payload_bytes": benchmark_payload,
                "tx_power_dbm": int(benchmark["source_aligned_tx_power_dbm"]),
                "modeled_incremental_radio_energy_j": energy,
                "whole_device_budget_j": budget,
                "source_model_valid_for_payload_extrapolation": extrap_authorised,
                "one_sided_budget_screen_status": status,
                "exact_profile_variant_required_before_feasibility_update": True,
                "generic_candidate_feasibility_resolved": False,
            })

    variants_csv = args.output / "benchmark_radio_model_variants_16byte.csv"
    _write_csv(variants_csv, variants, [
        "confirmation_mode","source_dr_index","frm_payload_bytes","tx_power_dbm","source_4byte_reproduction_gate_passed",
        "payload_extrapolation_authorised","modeled_incremental_radio_energy_j","whole_device_budget_j",
        "radio_component_exceeds_whole_device_budget","numeric_quantity_semantics","whole_device_energy_estimate","population_distribution"
    ])
    screen_csv = args.output / "one_sided_budget_screen.csv"
    _write_csv(screen_csv, screen, [
        "confirmation_mode","source_dr_index","frm_payload_bytes","tx_power_dbm","modeled_incremental_radio_energy_j","whole_device_budget_j",
        "source_model_valid_for_payload_extrapolation","one_sided_budget_screen_status","exact_profile_variant_required_before_feasibility_update","generic_candidate_feasibility_resolved"
    ])

    handoff_rows = [
        {"rule_id":"freeze_stage4_matrix","policy_state":"required","rule":"Preserve the frozen Stage-4 result 21 feasible / 39 infeasible / 3 unresolved; Stage-5B does not select an LR-FHSS DR or confirmation mode."},
        {"rule_id":"explicit_profile_variant","policy_state":"required","rule":"Any feasibility use of a component lower bound requires an explicitly versioned operating-profile variant matching DR, confirmation mode, TX power, retry policy, receive-window policy and accounting boundary."},
        {"rule_id":"unconfirmed_component_extrapolation","policy_state":"conditional","rule":"Payload extrapolation is authorised only for the unconfirmed radio-component source model after close 4-byte reproduction; it is not a whole-device bridge."},
        {"rule_id":"confirmed_extrapolation","policy_state":"prohibited","rule":"Confirmed payload extrapolation is blocked because the published source-state model does not reproduce the confirmed 4-byte traces and the TX-plateau mismatch is unexplained."},
        {"rule_id":"radio_lower_bound","policy_state":"conditional","rule":"For an exactly matched variant, validated radio-component energy above the whole-device budget is sufficient for one-sided infeasibility; radio energy below the budget is not sufficient for whole-device feasibility."},
        {"rule_id":"best_dr_post_hoc","policy_state":"prohibited","rule":"Do not choose DR or confirmation mode post hoc to minimise modeled energy."},
        {"rule_id":"single_trace_population_sampling","policy_state":"prohibited","rule":"The Stage-3 LR-FHSS single-trace epistemic gap remains; deterministic model reproduction does not create a population uncertainty distribution."},
        {"rule_id":"whole_device_numeric_bridge","policy_state":"prohibited","rule":"No whole-device/report numeric estimate is materialised at Stage-5B."},
        {"rule_id":"preference_scoring","policy_state":"prohibited","rule":"Preference scoring remains blocked."},
        {"rule_id":"publication_mcda","policy_state":"prohibited","rule":"Publication MCDA/ranking remains blocked."},
    ]
    handoff_csv = args.output / "stage5c_handoff_rules.csv"
    _write_csv(handoff_csv, handoff_rows, ["rule_id","policy_state","rule"])

    unconf = [r for r in reproduction if r["confirmation_mode"] == "unconfirmed"]
    conf = [r for r in reproduction if r["confirmation_mode"] == "confirmed"]
    unconf_above = [r for r in screen if r["confirmation_mode"] == "unconfirmed" and r["one_sided_budget_screen_status"] == "matched_variant_infeasible_by_radio_component_lower_bound"]
    unconf_below = [r for r in screen if r["confirmation_mode"] == "unconfirmed" and r["one_sided_budget_screen_status"] == "whole_device_unresolved_radio_component_below_or_equal_budget"]
    conf_blocked = [r for r in screen if r["confirmation_mode"] == "confirmed" and r["one_sided_budget_screen_status"] == "model_not_authorised_for_payload_extrapolation"]

    checkpoint = {
        "publication_table6_reproduction_rows": len(table_rows),
        "publication_table6_rows_reproduced": sum(_b(r["table6_numeric_reproduced"]) for r in table_rows),
        "source_trace_reproduction_rows": len(reproduction),
        "unconfirmed_trace_rows": len(unconf),
        "unconfirmed_close_reproduction_rows": sum(_b(r["close_source_trace_reproduction"]) for r in unconf),
        "unconfirmed_max_abs_relative_error_pct": max(_f(r["abs_relative_error_pct"]) for r in unconf),
        "confirmed_trace_rows": len(conf),
        "confirmed_close_reproduction_rows": sum(_b(r["close_source_trace_reproduction"]) for r in conf),
        "confirmed_min_abs_relative_error_pct": min(_f(r["abs_relative_error_pct"]) for r in conf),
        "confirmed_max_abs_relative_error_pct": max(_f(r["abs_relative_error_pct"]) for r in conf),
        "tx_plateau_diagnostic_rows": len(plateau),
        "confirmed_tx_plateau_current_a_min": min(_f(r["measured_tx_plateau_current_a"]) for r in plateau if r["confirmation_mode"] == "confirmed"),
        "confirmed_tx_plateau_current_a_max": max(_f(r["measured_tx_plateau_current_a"]) for r in plateau if r["confirmation_mode"] == "confirmed"),
        "published_model_tx_current_a": TX_CURRENT_A,
        "benchmark_variant_rows": len(variants),
        "one_sided_budget_screen_rows": len(screen),
        "unconfirmed_variants_above_budget": len(unconf_above),
        "unconfirmed_variants_below_or_equal_budget": len(unconf_below),
        "confirmed_variants_extrapolation_blocked": len(conf_blocked),
        "stage4_feasible_rows": 21,
        "stage4_infeasible_rows": 39,
        "stage4_unresolved_rows": 3,
    }
    for key, value in expected.items():
        if key in checkpoint and checkpoint[key] != value:
            raise SystemExit(f"Checkpoint mismatch {key}: {checkpoint[key]} != {value}")

    summary = {
        "stage": policy["stage"],
        "stage5_status": policy["stage5_status"],
        **checkpoint,
        "source_model_publication_doi": policy["sources"]["source_model_publication"]["doi"],
        "source_dataset_doi": policy["sources"]["measurement_dataset"]["doi"],
        "source_internal_equation_table_discrepancy_causally_resolved": False,
        "payload_duration_operationalisation": policy["source_model"]["payload_duration_operationalisation"],
        "audit_tolerance_pct": tolerance,
        "audit_tolerance_is_statistical_confidence_bound": False,
        "unconfirmed_payload_extrapolation_authorised_for_radio_component_only": True,
        "confirmed_payload_extrapolation_authorised": False,
        "confirmed_tx_plateau_mismatch_causal_explanation_identified": False,
        "generic_lrfhss_candidate_feasibility_resolved": False,
        "whole_device_energy_estimate_materialised": False,
        "numeric_target_bridge_output_authorised": False,
        "lrfhss_single_trace_uncertainty_preserved": True,
        "stage4_matrix_preserved": True,
        "preference_scoring_authorised": False,
        "publication_mcda_authorised": False,
        "interpretation": (
            "The published LR-FHSS radio-state model closely reproduces all four unconfirmed 4-byte source traces under the explicit Table-6 numerical operationalisation, but it does not reproduce the confirmed traces. "
            "The confirmed captures also exhibit an approximately 50 mA TX plateau versus the 25.7 mA published state-model current; the cause is not identified. Stage 5B therefore authorises payload extrapolation only for unconfirmed radio-component variants. "
            "At 16 bytes, DR8/DR10 radio-component energy alone exceeds the 0.2 J whole-device budget, yielding a one-sided exclusion only for an exactly matched profile variant; DR9/DR11 remain whole-device unresolved. The generic frozen candidate remains unresolved because DR/confirmation/profile fields are not selected."
        ),
        "next_scientific_step": (
            "Stage 5C: version explicit LR-FHSS operating-profile variants from scenario/deployment evidence rather than selecting the lowest-energy DR post hoc. Only an explicitly matched unconfirmed DR8/DR10 variant may inherit the one-sided component lower-bound exclusion; DR9/DR11 still require a whole-device residual-energy bridge, and confirmed variants require new evidence/model reconciliation."
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = args.output / "run_manifest.json"
    write_run_manifest(
        manifest,
        command="python scripts/audit_lrfhss_source_model_bridge.py",
        inputs=[args.policy,args.stage5a_summary,args.stage5a_profiles,args.transaction_derivation,args.trace_validation,args.stage3_state],
        outputs=[summary_path,table_csv,reproduction_csv,plateau_csv,variants_csv,screen_csv,handoff_csv],
        parameters={
            "source_trace_reproduction_tolerance_pct": tolerance,
            "confirmed_payload_extrapolation_authorised": False,
            "whole_device_energy_estimate_materialised": False,
            "numeric_target_bridge_output_authorised": False,
            "preference_scoring_authorised": False,
            "publication_mcda_authorised": False,
        },
    )

    print("Stage-5B LR-FHSS source-model bridge audit: OK")
    print(f"Table-6 reproduction: {checkpoint['publication_table6_rows_reproduced']} / {checkpoint['publication_table6_reproduction_rows']}")
    print(f"Unconfirmed close reproduction: {checkpoint['unconfirmed_close_reproduction_rows']} / {checkpoint['unconfirmed_trace_rows']} (max abs error {checkpoint['unconfirmed_max_abs_relative_error_pct']:.3f}%)")
    print(f"Confirmed close reproduction: {checkpoint['confirmed_close_reproduction_rows']} / {checkpoint['confirmed_trace_rows']} (abs error {checkpoint['confirmed_min_abs_relative_error_pct']:.1f}-{checkpoint['confirmed_max_abs_relative_error_pct']:.1f}%)")
    print(f"16-byte unconfirmed radio variants above / <= budget: {len(unconf_above)} / {len(unconf_below)}")
    print("Generic LR-FHSS candidate feasibility resolved: NO")
    print("Whole-device target bridge / preference scoring / publication MCDA: NO / NO / NO")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
