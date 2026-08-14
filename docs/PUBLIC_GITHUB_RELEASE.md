# Public GitHub release checklist

This repository is prepared for a public scientific-software release. Before the first push:

1. On a fresh public clone, run the self-contained suite: `python scripts/run_public_ci.py`.
   In a complete research workspace, also run the full local regression suite: `pytest -q`.
2. Run `python scripts/audit_public_repository.py --working-tree`.
3. Initialise Git only after `.gitignore` is present.
4. Stage with `git add .`.
5. Run `python scripts/audit_public_repository.py --staged`.
6. Inspect `git status --short` manually.
7. Confirm that no raw data, generated results, backup directories, patch ZIPs, credentials or local manuscript files are staged.
8. Commit and push to an empty GitHub repository.
9. Create the immutable tag `v0.1.61` and a GitHub Release from that tag.

The public repository intentionally excludes local `data/`, `results/`, `release/`, `dist/`, `backups/`, `.stackwise_backups/`, `payload/`, root-level ZIP diagnostics and the manuscript workspace. The benchmark itself is already archived at https://doi.org/10.5281/zenodo.21937093.
