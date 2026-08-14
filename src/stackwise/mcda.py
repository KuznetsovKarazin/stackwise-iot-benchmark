"""Prototype/smoke MCDA helpers. Fallback uncertainty is not a validated STACKWISE Stage-3 model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .io import load_yaml


@dataclass
class SmaaResult:
    rank_acceptability: pd.DataFrame
    mean_utility: pd.Series
    weight_samples: pd.DataFrame
    utility_samples: pd.DataFrame


def feasibility_filter(capabilities: pd.DataFrame, requirements: dict[str, object]) -> pd.Series:
    feasible = pd.Series(True, index=capabilities.index)
    for key, requirement in requirements.items():
        if key.startswith("min_"):
            column = key[4:]
            feasible &= pd.to_numeric(capabilities[column], errors="coerce") >= float(requirement)
        elif key.startswith("max_"):
            column = key[4:]
            feasible &= pd.to_numeric(capabilities[column], errors="coerce") <= float(requirement)
        else:
            feasible &= capabilities[key] == requirement
    return feasible


def normalise_scores(raw: pd.DataFrame, directions: dict[str, str]) -> pd.DataFrame:
    result = pd.DataFrame(index=raw.index)
    for criterion in raw.columns:
        values = pd.to_numeric(raw[criterion], errors="coerce")
        low, high = values.min(), values.max()
        if not np.isfinite(low) or not np.isfinite(high) or high == low:
            result[criterion] = 0.5
            continue
        scaled = (values - low) / (high - low)
        if directions.get(criterion, "maximize") == "minimize":
            scaled = 1.0 - scaled
        result[criterion] = scaled.clip(0, 1)
    return result


def run_smaa(
    score_means: pd.DataFrame,
    *,
    score_stds: pd.DataFrame | None = None,
    baseline_weights: pd.Series | None = None,
    samples: int = 20000,
    weight_concentration: float = 30.0,
    common_factor_loading: float = 0.0,
    seed: int = 26,
) -> SmaaResult:
    alternatives = list(score_means.index)
    criteria = list(score_means.columns)
    means = score_means.to_numpy(dtype=float)
    stds = (
        score_stds.reindex(index=alternatives, columns=criteria).to_numpy(dtype=float)
        if score_stds is not None
        else np.full_like(means, 0.08)
    )
    if baseline_weights is None:
        baseline = np.full(len(criteria), 1 / len(criteria))
    else:
        baseline = baseline_weights.reindex(criteria).to_numpy(dtype=float)
        baseline = baseline / baseline.sum()

    rng = np.random.default_rng(seed)
    weights = rng.dirichlet(np.maximum(baseline * weight_concentration, 1e-6), size=samples)
    common = rng.normal(size=(samples, 1, 1))
    idiosyncratic = rng.normal(size=(samples, len(alternatives), len(criteria)))
    loading = float(np.clip(common_factor_loading, 0, 0.999))
    noise = loading * common + np.sqrt(1 - loading**2) * idiosyncratic
    sampled_scores = np.clip(means[None, :, :] + stds[None, :, :] * noise, 0, 1)
    utilities = np.einsum("sac,sc->sa", sampled_scores, weights)
    order = np.argsort(-utilities, axis=1)
    ranks = np.empty_like(order)
    ranks[np.arange(samples)[:, None], order] = np.arange(1, len(alternatives) + 1)

    acceptability = pd.DataFrame(index=alternatives)
    for rank in range(1, len(alternatives) + 1):
        acceptability[f"rank_{rank}"] = (ranks == rank).mean(axis=0)
    return SmaaResult(
        rank_acceptability=acceptability,
        mean_utility=pd.Series(utilities.mean(axis=0), index=alternatives, name="mean_utility"),
        weight_samples=pd.DataFrame(weights, columns=criteria),
        utility_samples=pd.DataFrame(utilities, columns=alternatives),
    )


def load_mcda_config(path: str | Path = "configs/mcda.yml") -> dict:
    return load_yaml(path)
