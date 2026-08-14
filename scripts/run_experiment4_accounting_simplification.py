from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from stackwise.accounting_simplification import LEVELS, build_accounting_ablation
from stackwise.provenance import write_run_manifest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/experiment4_accounting_simplification.yml"


def _figures(levels: pd.DataFrame, cost_summary: pd.DataFrame, out_dir: Path) -> list[Path]:
    labels = ["Payload\nonly", "Transport\naware", "Serialization\naware", "Session/control\naware", "Billing\naware"]
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.plot(range(5), levels["exceeds_nominal_allowance_rows"].to_numpy(int), marker="o")
    ax.set_xticks(range(5), labels)
    ax.set_ylabel("States exceeding nominal 500 MB")
    ax.set_title("Accounting detail changes the tariff-volume classification")
    fig.tight_layout()
    p = out_dir / "figure1_exceedance_by_accounting_level.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.4))
    vals = 100.0 * levels["misclassification_fraction_vs_billing_aware"].to_numpy(float)
    ax.bar(range(5), vals)
    ax.set_xticks(range(5), labels)
    ax.set_ylabel("Misclassified state-space coverage vs billing-aware (%)")
    ax.set_title("Cost of simplification: false tariff classifications shrink with stack-aware accounting")
    fig.tight_layout()
    p = out_dir / "figure2_misclassification_vs_billing_aware.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.plot(range(5), cost_summary["median_cost_underestimation_eur"].to_numpy(float), marker="o", label="median")
    ax.plot(range(5), cost_summary["max_cost_underestimation_eur"].to_numpy(float), marker="o", label="maximum")
    ax.set_xticks(range(5), labels)
    ax.set_ylabel("Lifecycle-cost underestimation vs billing-aware (EUR / 5 y)")
    ax.set_title("Simplified traffic accounting can materially understate connectivity cost")
    ax.legend()
    fig.tight_layout()
    p = out_dir / "figure3_cost_underestimation_by_accounting_level.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    paths = {k: ROOT / v for k, v in policy["inputs"].items()}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Experiment-4 input missing ({name}): {path}")

    traffic, level_summary, cost_summary, summary = build_accounting_ablation(
        pd.read_csv(paths["stage5l_wire_accounting"]),
        pd.read_csv(paths["stage5m_serialization"]),
        pd.read_csv(paths["stage5n_session_control"]),
        pd.read_csv(paths["stage6c_cost_family"]),
        scenario_id=str(policy["benchmark"]["scenario_id"]),
        nominal_allowance_bytes=int(policy["benchmark"]["nominal_allowance_bytes"]),
        topup_increment_bytes=int(policy["benchmark"]["topup_increment_bytes"]),
        topup_price_eur=float(policy["benchmark"]["topup_price_eur"]),
    )

    out_dir = ROOT / policy["outputs"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    traffic.to_csv(out_dir / "aligned_state_accounting_ablation.csv", index=False)
    level_summary.to_csv(out_dir / "accounting_level_summary.csv", index=False)
    cost_summary.to_csv(out_dir / "cost_underestimation_summary.csv", index=False)

    # Binding-specific decomposition is useful for publication interpretation.
    binding_rows = []
    for binding, grp in traffic.groupby("binding_family", sort=True):
        for idx, level in enumerate(LEVELS):
            cur = grp[f"L{idx}_exceeds_nominal_allowance"]
            binding_rows.append({
                "binding_family": binding,
                "level_index": idx,
                "level_id": level,
                "states": len(grp),
                "exceed_rows": int(cur.sum()),
                "within_rows": int((~cur).sum()),
                "exceed_state_space_fraction": float(cur.mean()),
                "probability_interpretation": False,
            })
    binding_summary = pd.DataFrame(binding_rows)
    binding_summary.to_csv(out_dir / "binding_level_summary.csv", index=False)

    payload = {
        "stage": "Experiment 4 — accounting/cost simplification ablation",
        "benchmark_version": policy["benchmark"]["benchmark_version"],
        "scenario_id": policy["benchmark"]["scenario_id"],
        **asdict(summary),
        "level_exceedance_rows": level_summary.set_index("level_id")["exceeds_nominal_allowance_rows"].astype(int).to_dict(),
        "misclassification_fraction_vs_billing_aware": level_summary.set_index("level_id")["misclassification_fraction_vs_billing_aware"].astype(float).to_dict(),
        "median_cost_underestimation_eur": cost_summary.set_index("level_id")["median_cost_underestimation_eur"].astype(float).to_dict(),
        "max_cost_underestimation_eur": cost_summary.set_index("level_id")["max_cost_underestimation_eur"].astype(float).to_dict(),
        "state_space_probability_interpretation": False,
        "real_candidate_mcda_performed": False,
        "publication_mcda_authorised": False,
        "publication_interpretation": (
            "On the same 288 aligned traffic/billing states, application-payload-only accounting classifies every state as within the nominal 500-MB allowance, "
            "whereas billing-aware accounting classifies 252 states as exceeding it. Adding known transport structure resolves the MQTT/TLS risk but still misses "
            "108 billing-aware exceedances; explicit LwM2M serialization reduces this to 100, session/control accounting to 36, and PDP-session billing resolves the remainder. "
            "Across 576 procurement-expanded cost rows, the payload-only simplification understates the final five-year connectivity cost in 504 rows, with a median "
            "underestimate of 50 EUR and maximum of 100 EUR. These are deterministic sensitivity-state coverage results, not probabilities of deployment configurations."
        ),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    figures: list[Path] = []
    if not args.no_figures:
        figures = _figures(level_summary, cost_summary, out_dir)

    write_run_manifest(
        out_dir / "run_manifest.json",
        command="python scripts/run_experiment4_accounting_simplification.py",
        inputs=[POLICY, *paths.values()],
        outputs=[
            out_dir / "aligned_state_accounting_ablation.csv",
            out_dir / "accounting_level_summary.csv",
            out_dir / "cost_underestimation_summary.csv",
            out_dir / "binding_level_summary.csv",
            summary_path,
            *figures,
        ],
        parameters={
            "benchmark_version": policy["benchmark"]["benchmark_version"],
            "scenario_id": policy["benchmark"]["scenario_id"],
            "nominal_allowance_bytes": int(policy["benchmark"]["nominal_allowance_bytes"]),
            "state_space_probability_interpretation": False,
            "real_candidate_mcda": False,
        },
    )

    print("Experiment-4 accounting/cost simplification ablation: OK")
    print(
        "Aligned traffic states / procurement-expanded cost rows: "
        f"{summary.aligned_traffic_states} / {summary.procurement_expanded_cost_rows}"
    )
    print(
        "Nominal-allowance exceed rows L0/L1/L2/L3/L4: "
        f"{summary.level0_exceed_rows} / {summary.level1_exceed_rows} / {summary.level2_exceed_rows} / {summary.level3_exceed_rows} / {summary.level4_exceed_rows}"
    )
    print(
        "False-within rows vs billing-aware L0/L1/L2/L3: "
        f"{summary.level0_false_within_vs_final} / {summary.level1_false_within_vs_final} / {summary.level2_false_within_vs_final} / {summary.level3_false_within_vs_final}"
    )
    print(
        "New exceed rows from transport / serialization / session-control / billing: "
        f"{summary.level0_to_level1_new_exceed_rows} / {summary.level1_to_level2_new_exceed_rows} / "
        f"{summary.level2_to_level3_new_exceed_rows} / {summary.level3_to_level4_new_exceed_rows}"
    )
    c0 = cost_summary.iloc[0]
    c3 = cost_summary.iloc[3]
    print(
        "Payload-only median/max cost underestimate vs billing-aware (EUR): "
        f"{c0.median_cost_underestimation_eur:.1f} / {c0.max_cost_underestimation_eur:.1f}"
    )
    print(
        "Session/control-aware median/max cost underestimate before billing (EUR): "
        f"{c3.median_cost_underestimation_eur:.1f} / {c3.max_cost_underestimation_eur:.1f}"
    )
    print("State-space probability interpretation / publication MCDA authorised: no / no")


if __name__ == "__main__":
    main()
