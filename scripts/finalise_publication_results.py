from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import yaml

from stackwise.provenance import write_run_manifest
from stackwise.publication_finalisation import finalise_publication_results

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "datasets/publication_finalisation.yml"


def main() -> None:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    paths = {k: ROOT / v for k, v in policy["inputs"].items()}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Final publication input missing ({name}): {path}")
    summaries = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in paths.items()}
    headlines, claims, split, figures, tables, summary = finalise_publication_results(
        summaries["experiment1_summary"],
        summaries["experiment2_summary"],
        summaries["experiment3_summary"],
        summaries["experiment4_summary"],
        summaries["experiment5_summary"],
    )
    out = ROOT / policy["outputs"]["directory"]
    out.mkdir(parents=True, exist_ok=True)
    headlines.to_csv(out / "headline_results.csv", index=False)
    claims.to_csv(out / "claim_evidence_matrix.csv", index=False)
    split.to_csv(out / "two_paper_split_matrix.csv", index=False)
    figures.to_csv(out / "figure_plan.csv", index=False)
    tables.to_csv(out / "table_plan.csv", index=False)
    payload = {
        "stage": "Final publication consolidation — Experiments 1–5",
        "benchmark_version": policy["benchmark_version"],
        **asdict(summary),
        "benchmark_content_frozen": True,
        "experiments_1_to_5_closed": True,
        "experimental_programme_closed": True,
        "recommended_publication_strategy": "TWO_PAPERS",
        "data_paper_scope": "Benchmark construction, provenance, harmonisation, schemas, boundaries, uncertainty metadata, technical validation and release QA; exclude Experiments 1–5.",
        "method_paper_scope": "STACKWISE decision framework plus Experiments 1–5; cite Benchmark v1.0.0 as the frozen input artifact; exclude claims of global stochastic ranking and matched whole-device cellular energy.",
        "remaining_research_blockers_for_submission": [],
        "remaining_scope_limitations": [
            "No publication-grade global stochastic ranking across all candidate stacks.",
            "No matched whole-device energy/report comparison across the four cellular IP candidates.",
        ],
        "recommended_next_step": "Freeze experiment outputs, deposit/cite Benchmark v1.0.0, then draft the data paper and the STACKWISE methodology/results paper as distinct manuscripts.",
    }
    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_run_manifest(
        out / "run_manifest.json",
        command="python scripts/finalise_publication_results.py",
        inputs=[POLICY, *paths.values()],
        outputs=[out / "headline_results.csv", out / "claim_evidence_matrix.csv", out / "two_paper_split_matrix.csv", out / "figure_plan.csv", out / "table_plan.csv", summary_path],
        parameters={
            "benchmark_version": policy["benchmark_version"],
            "benchmark_content_frozen": True,
            "experiments_1_to_5_closed": True,
            "two_paper_split_recommended": True,
            "global_candidate_ranking_authorised": False,
        },
    )
    print("Final publication consolidation (Experiments 1–5): OK")
    print(f"Closed experiments / headline results: {summary.experiments_closed} / {summary.headline_result_rows}")
    print(f"Strong / open claims: {summary.strong_claims} / {summary.open_claims}")
    print(f"Method-paper main figures / main tables: {summary.methodology_main_figures} / {summary.methodology_main_tables}")
    print("Broad methodology article ready / global MCDA authorised: yes / no")
    print("Two-paper split recommended / experimental programme closed: yes / yes")


if __name__ == "__main__":
    main()
