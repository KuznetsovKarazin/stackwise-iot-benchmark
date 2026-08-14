from __future__ import annotations

import csv
import io
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd
import requests


ZENODO_SEARCH_API = "https://zenodo.org/api/records"

POSITIVE_TERMS = {
    "measurement": 3,
    "measurements": 3,
    "measured": 3,
    "experimental": 3,
    "raw": 2,
    "trace": 2,
    "traces": 2,
    "current": 2,
    "power": 2,
    "energy": 2,
    "rssi": 2,
    "snr": 2,
    "latency": 2,
    "coverage": 2,
    "testbed": 2,
    "real network": 3,
    "field campaign": 3,
}
NEGATIVE_TERMS = {
    "simulation": -5,
    "simulated": -5,
    "synthetic": -5,
    "intrusion detection": -3,
    "cyber attack": -3,
    "forecasting": -2,
    "electricity consumption": -3,
    "smart light": -3,
}


@dataclass
class Candidate:
    provider: str
    identifier: str
    title: str
    landing_url: str
    description: str
    licence: str | None
    empirical_score: int
    recommendation: str


def empirical_candidate_score(title: str, description: str = "") -> tuple[int, str]:
    text = f"{title} {description}".casefold()
    score = sum(weight for term, weight in POSITIVE_TERMS.items() if term in text)
    score += sum(weight for term, weight in NEGATIVE_TERMS.items() if term in text)
    if score >= 5:
        label = "high_priority_review"
    elif score >= 1:
        label = "manual_review"
    else:
        label = "likely_unsuitable"
    return score, label


def search_zenodo(query: str, size: int = 25, timeout: int = 60) -> list[Candidate]:
    response = requests.get(
        ZENODO_SEARCH_API,
        params={"q": query, "size": size, "sort": "mostrecent"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    candidates: list[Candidate] = []
    for hit in payload.get("hits", {}).get("hits", []):
        metadata = hit.get("metadata", {})
        title = str(metadata.get("title", ""))
        description = str(metadata.get("description", ""))
        score, recommendation = empirical_candidate_score(title, description)
        record_id = str(hit.get("id", ""))
        licence = metadata.get("license")
        if isinstance(licence, dict):
            licence = licence.get("id") or licence.get("title")
        candidates.append(
            Candidate(
                provider="zenodo",
                identifier=record_id,
                title=title,
                landing_url=f"https://zenodo.org/records/{record_id}",
                description=description,
                licence=str(licence) if licence else None,
                empirical_score=score,
                recommendation=recommendation,
            )
        )
    return candidates


def search_kaggle(query: str) -> list[Candidate]:
    if shutil.which("kaggle") is None:
        raise RuntimeError("Kaggle CLI is not installed. Run: pip install kaggle")
    completed = subprocess.run(
        ["kaggle", "datasets", "list", "-s", query, "--csv"],
        check=True,
        capture_output=True,
        text=True,
    )
    frame = pd.read_csv(io.StringIO(completed.stdout))
    candidates: list[Candidate] = []
    for _, row in frame.iterrows():
        ref = str(row.get("ref", ""))
        title = str(row.get("title", ref))
        description = str(row.get("subtitle", ""))
        score, recommendation = empirical_candidate_score(title, description)
        candidates.append(
            Candidate(
                provider="kaggle",
                identifier=ref,
                title=title,
                landing_url=f"https://www.kaggle.com/datasets/{ref}",
                description=description,
                licence=str(row.get("licenseName", "")) or None,
                empirical_score=score,
                recommendation=recommendation,
            )
        )
    return candidates


def write_candidates(candidates: list[Candidate], output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(candidate) for candidate in candidates]).sort_values(
        ["empirical_score", "provider"], ascending=[False, True]
    ).to_csv(path, index=False)
    return path
