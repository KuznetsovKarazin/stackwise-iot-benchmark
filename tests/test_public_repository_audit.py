from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_public_repository.py"
spec = importlib.util.spec_from_file_location("audit_public_repository", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_public_audit_blocks_local_artifacts(tmp_path: Path) -> None:
    root = module.ROOT
    original = module.ROOT
    try:
        module.ROOT = tmp_path
        blocked = tmp_path / "backups" / "snapshot.txt"
        blocked.parent.mkdir(parents=True)
        blocked.write_text("safe", encoding="utf-8")
        errors, _ = module.audit([blocked], staged=True)
        assert any("blocked path staged" in item for item in errors)
    finally:
        module.ROOT = original


def test_public_audit_detects_secret_pattern(tmp_path: Path) -> None:
    original = module.ROOT
    try:
        module.ROOT = tmp_path
        source = tmp_path / "example.py"
        source.write_text("api_" + "key=" + "'abcdefghijk12345'\n", encoding="utf-8")
        errors, _ = module.audit([source], staged=True)
        assert any("credential assignment" in item for item in errors)
    finally:
        module.ROOT = original


def test_public_audit_accepts_normal_source(tmp_path: Path) -> None:
    original = module.ROOT
    try:
        module.ROOT = tmp_path
        source = tmp_path / "module.py"
        source.write_text("VALUE = 42\n", encoding="utf-8")
        errors, warnings = module.audit([source], staged=True)
        assert errors == []
        assert warnings == []
    finally:
        module.ROOT = original
