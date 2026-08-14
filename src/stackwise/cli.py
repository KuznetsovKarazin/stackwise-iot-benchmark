from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from .audit import write_audit
from .download import download_dataset
from .discovery import search_kaggle, search_zenodo, write_candidates
from .harmonize import combine_processed, harmonize_dataset
from .io import read_table
from .models import fit_energy_model, save_energy_model
from .optimizer import load_fleet_config, optimise_fleet
from .registry import DatasetRegistry
from .reproduce import reproduce_smoke


app = typer.Typer(no_args_is_help=True, help="STACKWISE research pipeline")
console = Console()


@app.command("registry-validate")
def registry_validate(registry: Path = Path("datasets/registry.yml")) -> None:
    obj = DatasetRegistry(registry)
    obj.validate()
    console.print(f"[green]Valid registry:[/green] {len(obj.records)} empirical datasets")


@app.command("registry-list")
def registry_list(
    registry: Path = Path("datasets/registry.yml"),
    status: str | None = None,
    technology: str | None = None,
    provider: str | None = None,
) -> None:
    obj = DatasetRegistry(registry)
    rows = obj.select(status=status, technology=technology, provider=provider)
    table = Table("ID", "Status", "Grade", "Provider", "Technologies", "Licence")
    for record in rows:
        data = record.data
        table.add_row(
            record.id,
            str(data.get("status")),
            str(data.get("evidence_grade")),
            record.provider,
            ", ".join(data.get("technologies", [])),
            f"{data.get('licence', {}).get('id')} / {record.licence_status}",
        )
    console.print(table)


@app.command()
def discover(
    query: str,
    provider: str = typer.Option("both", help="zenodo, kaggle, or both"),
    output: Path = Path("results/discovery/candidates.csv"),
    size: int = 25,
) -> None:
    candidates = []
    if provider in {"zenodo", "both"}:
        candidates.extend(search_zenodo(query, size=size))
    if provider in {"kaggle", "both"}:
        candidates.extend(search_kaggle(query))
    path = write_candidates(candidates, output)
    console.print(f"[green]Candidate catalogue:[/green] {path}")


@app.command()
def download(
    dataset_id: str,
    registry: Path = Path("datasets/registry.yml"),
    root: Path = Path("data/raw"),
    accept_license: bool = typer.Option(False, help="Confirm that the live dataset licence was reviewed"),
    accept_unverified_license: bool = typer.Option(False, help="Permit a registry record whose licence is not verified"),
    file_glob: list[str] | None = typer.Option(
        None,
        "--file-glob",
        help="Override registry file globs; repeat to request specific provider files",
    ),
) -> None:
    record = DatasetRegistry(registry).get(dataset_id)
    files = download_dataset(
        record,
        root=root,
        accept_license=accept_license,
        accept_unverified_license=accept_unverified_license,
        file_globs_override=file_glob,
    )
    console.print(f"[green]Downloaded {len(files)} files[/green] to {root / dataset_id}")


@app.command()
def harmonize(
    dataset_id: str,
    registry: Path = Path("datasets/registry.yml"),
    strict: bool = False,
) -> None:
    output, messages = harmonize_dataset(dataset_id, registry_path=registry, strict=strict)
    console.print(f"[green]Harmonised:[/green] {output}")
    for message in messages[:20]:
        console.print(f"[yellow]- {message}[/yellow]")


@app.command()
def combine(output: Path = Path("data/processed/canonical_observations.parquet")) -> None:
    path = combine_processed(output=output)
    console.print(f"[green]Combined observations:[/green] {path}")


@app.command()
def audit(
    registry: Path = Path("datasets/registry.yml"),
    excluded: Path = Path("datasets/excluded.yml"),
    output: Path = Path("results/audit"),
) -> None:
    paths = write_audit(registry, excluded, output)
    for name, path in paths.items():
        console.print(f"[green]{name}:[/green] {path}")


@app.command("fit-energy")
def fit_energy(
    observations: Path,
    output: Path = Path("results/models/energy"),
) -> None:
    frame = read_table(observations)
    model = fit_energy_model(frame)
    paths = save_energy_model(model, output)
    console.print(f"[green]Fitted {model.model_type} on {model.rows_used} rows[/green]")
    for name, path in paths.items():
        console.print(f"{name}: {path}")


@app.command()
def optimize(
    config: Path = Path("configs/fleet.yml"),
    max_technologies: int | None = None,
    ownership: str | None = None,
    complexity_penalty: float | None = None,
) -> None:
    solution = optimise_fleet(
        load_fleet_config(config),
        max_technologies=max_technologies,
        ownership=ownership,
        technology_complexity_penalty_usd=complexity_penalty,
    )
    console.print(f"[green]TCO: ${solution.total_cost_usd:,.2f}[/green]")
    for group, tech in solution.assignment.items():
        console.print(f"{group}: {tech}")


@app.command()
def reproduce(
    smoke: bool = typer.Option(False, help="Run the self-contained smoke pipeline"),
    output: Path = Path("results/smoke"),
) -> None:
    if not smoke:
        raise typer.BadParameter("Only --smoke is implemented for a no-download run")
    paths = reproduce_smoke(output)
    console.print(f"[green]Smoke pipeline completed:[/green] {len(paths)} outputs")
    for name, path in paths.items():
        console.print(f"{name}: {path}")


if __name__ == "__main__":
    app()
