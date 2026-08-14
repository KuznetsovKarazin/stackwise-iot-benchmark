from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io import load_yaml
from .quality import evidence_score
from .registry import DatasetRegistry


def build_registry_audit(registry: DatasetRegistry) -> pd.DataFrame:
    rows = []
    for record in registry.records:
        data = record.data
        computed_score, computed_grade = evidence_score(data)
        rows.append({
            "dataset_id": record.id,
            "title": data.get("title"),
            "provider": data.get("provider"),
            "status": data.get("status"),
            "year": data.get("year"),
            "technologies": "; ".join(data.get("technologies", [])),
            "metrics": "; ".join(data.get("metrics", [])),
            "boundaries": "; ".join(data.get("measurement_boundaries", [])),
            "declared_grade": data.get("evidence_grade"),
            "computed_score": computed_score,
            "computed_grade": computed_grade,
            "raw_available": bool(data.get("raw_available")),
            "code_available": bool(data.get("code_available")),
            "licence_id": data.get("licence", {}).get("id"),
            "licence_status": data.get("licence", {}).get("status"),
            "redistribution": data.get("licence", {}).get("redistribution"),
            "doi": data.get("doi"),
            "landing_url": data.get("landing_url"),
        })
    return pd.DataFrame(rows)


def build_coverage_matrix(registry: DatasetRegistry) -> pd.DataFrame:
    rows = []
    for record in registry.records:
        for technology in record.data.get("technologies", []):
            for metric in record.data.get("metrics", []):
                rows.append({
                    "dataset_id": record.id,
                    "technology": technology,
                    "metric": metric,
                    "grade": record.data.get("evidence_grade"),
                    "status": record.data.get("status"),
                })
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    return pd.crosstab(long["technology"], long["metric"], values=long["dataset_id"], aggfunc="count").fillna(0).astype(int)


def write_audit(
    registry_path: str | Path = "datasets/registry.yml",
    excluded_path: str | Path = "datasets/excluded.yml",
    output_dir: str | Path = "results/audit",
) -> dict[str, Path]:
    registry = DatasetRegistry(registry_path)
    registry.validate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    audit = build_registry_audit(registry)
    matrix = build_coverage_matrix(registry)
    audit_path = output / "dataset_audit.csv"
    matrix_path = output / "coverage_matrix.csv"
    audit.to_csv(audit_path, index=False)
    matrix.to_csv(matrix_path)

    excluded = load_yaml(excluded_path).get("excluded", [])
    markdown = [
        "# STACKWISE evidence audit",
        "",
        f"Active empirical datasets: **{len(audit)}**",
        f"Core datasets: **{int((audit['status'] == 'core').sum())}**",
        f"Datasets with verified licences: **{int((audit['licence_status'] == 'verified').sum())}**",
        f"Explicitly excluded candidates: **{len(excluded)}**",
        "",
        "## Active registry",
        "",
        audit[["dataset_id", "status", "declared_grade", "licence_status", "technologies", "metrics"]].to_markdown(index=False),
        "",
        "## Excluded records",
        "",
    ]
    for item in excluded:
        markdown.append(f"- `{item.get('id')}` — {item.get('reason')}")
    markdown_path = output / "audit_report.md"
    markdown_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return {"audit": audit_path, "matrix": matrix_path, "report": markdown_path}
