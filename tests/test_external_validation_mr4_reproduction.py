from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mr4_generalization_reproduces_original_frozen_point_exactly():
    p = ROOT / "external_validation/results_public/mr4_original_point_reproduction.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["merged_state_rows"] == 288
    assert d["all_keys_matched"] is True
    assert d["exact_rows_all_levels"] == 288
    assert d["all_rows_exact_all_levels"] is True
    assert all(float(v) == 0.0 for v in d["max_abs_difference_bytes_by_level"].values())
