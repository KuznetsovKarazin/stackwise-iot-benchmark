from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from stackwise.provenance import write_run_manifest
from stackwise.uncertainty_treatment import (
    cost_point_vs_robustness_family,
    loed_point_vs_model_robustness,
    summarise_experiment3,
    vomhoff_point_vs_bootstrap,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/experiment3_uncertainty_treatment.yml"


def _write_figures(vomhoff: pd.DataFrame, loed: pd.DataFrame, cost_pairs: pd.DataFrame, out_dir: Path) -> list[Path]:
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 5.4))
    x = range(len(vomhoff))
    y = vomhoff["point_estimate_j"].to_numpy(float)
    lower = y - vomhoff["q025_j"].to_numpy(float)
    upper = vomhoff["q975_j"].to_numpy(float) - y
    ax.errorbar(x, y, yerr=[lower, upper], fmt="o", capsize=5)
    labels = [f"{r.technology}\n{r.source_application_protocol}" for r in vomhoff.itertuples(index=False)]
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Source-aligned active transaction energy (J)")
    ax.set_title("Vomhoff point estimates and dependence-preserving bootstrap intervals")
    fig.tight_layout()
    p = out_dir / "figure1_vomhoff_point_vs_bootstrap.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.4))
    labels = [f"{r.campaign_id}/{r.metric}" for r in loed.itertuples(index=False)]
    ax.bar(range(len(loed)), loed["sd_max_to_min_ratio_median"])
    ax.axhline(1.0, linewidth=1)
    ax.set_xticks(range(len(loed)), labels, rotation=20, ha="right")
    ax.set_ylabel("max SD / min SD across 3/7/14-day block models")
    ax.set_title("LoED uncertainty scale changes while the point estimate is fixed")
    fig.tight_layout()
    p = out_dir / "figure2_loed_block_model_sensitivity.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(9, 5.4))
    x = range(len(cost_pairs))
    refs = cost_pairs["deterministic_reference_mqtt_minus_coap_eur"].to_numpy(float)
    mins = cost_pairs["aligned_difference_min_eur"].to_numpy(float)
    maxs = cost_pairs["aligned_difference_max_eur"].to_numpy(float)
    ax.errorbar(x, refs, yerr=[refs - mins, maxs - refs], fmt="o", capsize=5)
    ax.axhline(0.0, linewidth=1)
    ax.set_xticks(list(x), cost_pairs["access_technology"].tolist())
    ax.set_ylabel("MQTT minus CoAP lifecycle cost (EUR / 5 y)")
    ax.set_title("A single cost point hides the width and ties of the aligned robustness family")
    fig.tight_layout()
    p = out_dir / "figure3_cost_point_vs_aligned_family.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths.append(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    paths = {name: ROOT / rel for name, rel in policy["inputs"].items()}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Experiment-3 input missing ({name}): {path}. Re-run the validated upstream stage on the full local data tree."
            )

    vomhoff_input = pd.read_csv(paths["vomhoff_source_active_summary"])
    loed_input = pd.read_csv(paths["loed_robustness_summary"])
    cost_input = pd.read_csv(paths["stage6c_cost_family"])

    vomhoff, vomhoff_pairs = vomhoff_point_vs_bootstrap(vomhoff_input)
    loed = loed_point_vs_model_robustness(loed_input)
    cost_summary, cost_pairs, cost_detail = cost_point_vs_robustness_family(
        cost_input,
        reference_state={str(k): str(v) for k, v in policy["reference_cost_state"].items()},
    )
    summary = summarise_experiment3(vomhoff, vomhoff_pairs, loed, cost_summary, cost_pairs)

    out_dir = ROOT / policy["outputs"]["directory"]
    out_dir.mkdir(parents=True, exist_ok=True)
    vomhoff.to_csv(out_dir / "vomhoff_point_vs_bootstrap.csv", index=False)
    vomhoff_pairs.to_csv(out_dir / "vomhoff_pairwise_interval_robustness.csv", index=False)
    loed.to_csv(out_dir / "loed_point_vs_model_robustness.csv", index=False)
    cost_summary.to_csv(out_dir / "cost_point_vs_family_summary.csv", index=False)
    cost_pairs.to_csv(out_dir / "cost_pairwise_robustness.csv", index=False)
    cost_detail.to_csv(out_dir / "cost_aligned_state_differences.csv", index=False)

    relative_widths = vomhoff["relative_interval_width_pct"].astype(float)
    loed_ratios = loed["sd_max_to_min_ratio_median"].astype(float)
    payload = {
        "stage": "Experiment 3 — deterministic point treatment vs uncertainty-/robustness-aware treatment",
        "benchmark_version": policy["benchmark"]["benchmark_version"],
        **asdict(summary),
        "vomhoff_relative_interval_width_pct_min": float(relative_widths.min()),
        "vomhoff_relative_interval_width_pct_median": float(relative_widths.median()),
        "vomhoff_relative_interval_width_pct_max": float(relative_widths.max()),
        "loed_sd_max_to_min_ratio_median_min": float(loed_ratios.min()),
        "loed_sd_max_to_min_ratio_median_max": float(loed_ratios.max()),
        "cost_naive_marginal_range_overlap_for_both_rats": bool(cost_pairs["naive_marginal_ranges_overlap"].all()),
        "cost_aligned_state_reversals": int(cost_pairs["aligned_states_mqtt_cheaper"].sum()),
        "cost_reference_gap_eur": sorted(set(cost_pairs["deterministic_reference_mqtt_minus_coap_eur"].astype(float).round(12))),
        "cost_aligned_gap_min_eur": float(cost_pairs["aligned_difference_min_eur"].min()),
        "cost_aligned_gap_max_eur": float(cost_pairs["aligned_difference_max_eur"].max()),
        "point_treatment_probability_interpretation": False,
        "epistemic_robustness_probability_interpretation": False,
        "global_candidate_ranking_performed": False,
        "publication_mcda_authorised": False,
        "publication_interpretation": (
            "The same deterministic point treatment has different consequences under the three validated uncertainty semantics. "
            "For the source-aligned Vomhoff diagnostic, marginal nonparametric intervals preserve the point ordering while quantifying unequal precision; "
            "no cross-block probability of superiority is asserted. For LoED, the campaign point estimate is fixed but the uncertainty scale changes materially "
            "across the retained 3/7/14-day temporal models, so a single deterministic or single-block treatment hides model-form sensitivity. For lifecycle cost, "
            "a single reference state suggests a fixed CoAP-vs-MQTT gap, whereas the aligned finite robustness family shows a wider 0-to-70 EUR gap and many exact ties. "
            "Although marginal cost ranges overlap, paired-state analysis shows no MQTT-cheaper reversal, demonstrating why dependence/state alignment must be preserved."
        ),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    figures: list[Path] = []
    if not args.no_figures:
        figures = _write_figures(vomhoff, loed, cost_pairs, out_dir)

    write_run_manifest(
        out_dir / "run_manifest.json",
        command="python scripts/run_experiment3_uncertainty_treatment.py",
        inputs=[POLICY, *paths.values()],
        outputs=[
            out_dir / "vomhoff_point_vs_bootstrap.csv",
            out_dir / "vomhoff_pairwise_interval_robustness.csv",
            out_dir / "loed_point_vs_model_robustness.csv",
            out_dir / "cost_point_vs_family_summary.csv",
            out_dir / "cost_pairwise_robustness.csv",
            out_dir / "cost_aligned_state_differences.csv",
            summary_path,
            *figures,
        ],
        parameters={
            "benchmark_version": policy["benchmark"]["benchmark_version"],
            "reference_cost_state": policy["reference_cost_state"],
            "probability_pooling_across_epistemic_states": False,
            "global_candidate_ranking": False,
        },
    )

    print("Experiment-3 deterministic vs uncertainty-/robustness-aware treatment: OK")
    print(
        "Vomhoff source contexts / pairwise comparisons / marginal-interval-separated pairs: "
        f"{summary.vomhoff_contexts} / {summary.vomhoff_pairwise_comparisons} / {summary.vomhoff_marginal_interval_separated_pairs}"
    )
    print(
        "LoED campaign×metric rows / SD-ratio >1.25 / >1.50: "
        f"{summary.loed_campaign_metric_rows} / {summary.loed_rows_with_sd_ratio_gt_1_25} / {summary.loed_rows_with_sd_ratio_gt_1_50}"
    )
    print(
        "Cost candidates / aligned states per RAT / CoAP-cheaper / tied / MQTT-cheaper aligned rows: "
        f"{summary.cost_candidates} / {summary.cost_aligned_states_per_rat} / {summary.cost_strict_coap_cheaper_rows_total} / "
        f"{summary.cost_tie_rows_total} / {summary.cost_mqtt_cheaper_rows_total}"
    )
    print("Cross-block/epistemic pooled probability interpretation: no")
    print("Global candidate ranking / publication MCDA authorised: no / no")


if __name__ == "__main__":
    main()
