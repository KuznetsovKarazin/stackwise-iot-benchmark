from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_rank_acceptability(frame: pd.DataFrame, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ax = frame.plot(kind="bar", stacked=True, figsize=(10, 5))
    ax.set_ylabel("Rank acceptability")
    ax.set_xlabel("Alternative")
    ax.set_ylim(0, 1)
    ax.legend(title="Rank", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    return path


def write_solution_markdown(solution, output: str | Path, title: str = "Fleet solution") -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"Total cost: **${solution.total_cost_usd:,.2f}**", "", "## Assignment", ""]
    for group, tech in solution.assignment.items():
        lines.append(f"- {group}: {tech}")
    lines.extend(["", "## Cost breakdown", ""])
    for item, value in solution.breakdown.items():
        lines.append(f"- {item}: ${value:,.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
