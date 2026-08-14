from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.publication_consolidation import consolidate_publication_results

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/publication_result_consolidation.yml"


def main() -> None:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    paths = {k: ROOT / v for k, v in policy["inputs"].items()}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Publication consolidation input missing ({name}): {path}")
    summaries = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in paths.items()}
    headlines, claims, figures, tables, summary = consolidate_publication_results(
        summaries["experiment1_summary"],
        summaries["experiment2_summary"],
        summaries["experiment3_summary"],
        summaries["experiment4_summary"],
    )
    out = ROOT / policy["outputs"]["directory"]
    out.mkdir(parents=True, exist_ok=True)
    headlines.to_csv(out / "headline_results.csv", index=False)
    claims.to_csv(out / "claim_evidence_matrix.csv", index=False)
    figures.to_csv(out / "figure_plan.csv", index=False)
    tables.to_csv(out / "table_plan.csv", index=False)
    payload = {
        "stage": "Publication result consolidation — Experiments 1–4",
        "benchmark_version": policy["benchmark_version"],
        **asdict(summary),
        "benchmark_content_frozen": True,
        "experiments_1_to_4_closed": True,
        "narrow_article_ready_without_fleet_claim": True,
        "broad_original_article_ready": False,
        "recommended_next_step": "Experiment 5 — fleet portfolio feasibility and simplification penalty using frozen hard-feasibility evidence only.",
        "scope_recommendation": (
            "Do not claim a publication-grade global stochastic MCDA ranking because canonical energy+cost completeness is absent. "
            "Keep uncertainty-aware treatment as a methodological contribution. If the paper retains the original heterogeneous-fleet claim, "
            "add one final fleet portfolio feasibility experiment; otherwise explicitly narrow the scope and drop that claim."
        ),
    }
    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_run_manifest(
        out / "run_manifest.json",
        command="python scripts/consolidate_publication_results.py",
        inputs=[POLICY, *paths.values()],
        outputs=[out / "headline_results.csv", out / "claim_evidence_matrix.csv", out / "figure_plan.csv", out / "table_plan.csv", summary_path],
        parameters={
            "benchmark_version": policy["benchmark_version"],
            "benchmark_content_frozen": True,
            "global_candidate_ranking_authorised": False,
            "fleet_claim_requires_additional_result": True,
        },
    )
    print("Publication-result consolidation (Experiments 1–4): OK")
    print(f"Closed experiments / headline results: {summary.experiments_closed} / {summary.headline_result_rows}")
    print(f"Strong / partial / open claims: {summary.strong_claims} / {summary.partial_claims} / {summary.open_claims}")
    print(f"Recommended main figures / main tables: {summary.main_figures_recommended} / {summary.main_tables_recommended}")
    print("Narrow article ready without fleet claim: yes")
    print("Broad original article ready / global MCDA authorised: no / no")
    print("Final fleet portfolio experiment recommended: yes")


if __name__ == "__main__":
    main()
