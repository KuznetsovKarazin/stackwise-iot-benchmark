from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These tests are intentionally self-contained: they exercise the installable package,
# schemas, registry contracts, MCDA/optimizer primitives, evidence contracts and
# publication packaging without requiring local upstream archives or generated results/.
PUBLIC_CI_TEST_FILES = [
    "tests/test_smoke.py",
    "tests/test_registry.py",
    "tests/test_schema.py",
    "tests/test_metrics.py",
    "tests/test_optimizer.py",
    "tests/test_mcda.py",
    "tests/test_evidence_contract.py",
    "tests/test_publication_packaging.py",
]


def main() -> None:
    cmd = [sys.executable, "-m", "pytest", "-q", *PUBLIC_CI_TEST_FILES]
    print("Running STACKWISE public self-contained CI suite")
    print(" ".join(cmd))
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
