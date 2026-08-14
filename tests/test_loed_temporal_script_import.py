from __future__ import annotations

import importlib.util
from pathlib import Path


def test_loed_temporal_audit_script_imports_cleanly():
    script = Path(__file__).resolve().parents[1] / "scripts" / "audit_loed_temporal_structure.py"
    spec = importlib.util.spec_from_file_location("stackwise_test_audit_loed_temporal_structure", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
    assert module.write_run_manifest.__module__ == "stackwise.provenance"
