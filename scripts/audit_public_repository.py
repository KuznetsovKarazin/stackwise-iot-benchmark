from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_PUBLIC_FILE_BYTES = 20 * 1024 * 1024

BLOCKED_PREFIXES = (
    "backups/",
    "payload/",
    "results/",
    "release/",
    "dist/",
    ".venv/",
    "venv/",
    ".pytest_cache/",
    "paper/",
    "data/raw/",
    "data/interim/",
    "data/processed/",
    "data/analysis_ready/",
)
BLOCKED_BASENAMES = {
    "PATCH_APPLY.txt",
    "PROJECT_INVENTORY.txt",
    "kaggle.json",
    ".env",
}
BLOCKED_SUFFIXES = {".zip", ".7z", ".rar", ".pkl", ".pickle", ".parquet", ".feather"}

SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"']?(?!<|YOUR_|EXAMPLE|dummy|test)[^\s\"']{8,}"
        ),
    ),
]

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".cff",
    ".ini", ".cfg", ".csv", ".tsv", ".sh", ".ps1", ".dockerfile", "",
}


def _normalise(path: Path) -> str:
    return path.as_posix().lstrip("./")


def _git_staged_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("No usable Git index found. Run `git init -b main` and `git add .` first.")
    return [ROOT / line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _working_tree_candidates() -> list[Path]:
    excluded_roots = {
        ".git", ".venv", "venv", ".pytest_cache", ".ruff_cache", ".mypy_cache",
        "backups", "payload", "results", "release", "dist", "paper",
    }
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT)
        if rel_dir.parts and rel_dir.parts[0] in excluded_roots:
            dirnames[:] = []
            continue
        if rel_dir.parts[:1] == ("data",) and len(rel_dir.parts) > 1 and rel_dir.parts[1] != "examples":
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in excluded_roots and d != "__pycache__"]
        for filename in filenames:
            path = Path(dirpath) / filename
            rel = path.relative_to(ROOT)
            if rel.name in BLOCKED_BASENAMES or rel.suffix.lower() in BLOCKED_SUFFIXES:
                continue
            candidates.append(path)
    return candidates


def audit(files: list[Path], staged: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for path in files:
        if not path.exists() or not path.is_file():
            continue
        rel = _normalise(path.relative_to(ROOT))
        if rel in seen:
            continue
        seen.add(rel)

        if staged:
            if any(rel.startswith(prefix) for prefix in BLOCKED_PREFIXES):
                errors.append(f"blocked path staged: {rel}")
            if path.name in BLOCKED_BASENAMES:
                errors.append(f"blocked file staged: {rel}")
            if path.suffix.lower() in BLOCKED_SUFFIXES:
                errors.append(f"binary/archive file staged: {rel}")

        size = path.stat().st_size
        if size > MAX_PUBLIC_FILE_BYTES:
            errors.append(f"file exceeds 20 MiB public-repo limit: {rel} ({size} bytes)")

        suffix = path.suffix.lower()
        if suffix not in TEXT_SUFFIXES and path.name not in {"Dockerfile", "Makefile"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible {label} in {rel}")

        if re.search(r"\b[A-Za-z]:\\", text):
            warnings.append(f"local Windows path found in {rel}; review before publication")

    return sorted(set(errors)), sorted(set(warnings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit STACKWISE before a public GitHub push.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--working-tree", action="store_true", help="Scan public-source candidates before Git init.")
    mode.add_argument("--staged", action="store_true", help="Audit exactly the files currently staged in Git.")
    args = parser.parse_args()

    files = _git_staged_files() if args.staged else _working_tree_candidates()
    errors, warnings = audit(files, staged=args.staged)

    print(f"STACKWISE public-repository audit: {'FAILED' if errors else 'OK'}")
    print(f"Files inspected: {len(files)}")
    print(f"Errors / warnings: {len(errors)} / {len(warnings)}")
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings[:20]:
        print(f"WARNING: {item}")
    if len(warnings) > 20:
        print(f"WARNING: {len(warnings) - 20} additional warnings omitted")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
