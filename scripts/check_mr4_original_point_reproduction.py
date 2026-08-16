from __future__ import annotations

"""Reproduce the original Experiment-4 accounting point with the generalized MR4 engine.

This is a non-outcome-changing diagnostic. It checks that the generalized factorial
accounting implementation reproduces the frozen original 64-byte / 60-s / 5-y,
500-MB allowance / 500-MB increment accounting ladder exactly for all 288
standards/billing states.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from stackwise.lwm2m_serialization import serialized_payload_bytes
from stackwise.wire_accounting import strict_transport_floor_bytes, anchor_known_component_bytes
from stackwise.session_control_envelope import build_session_control_envelope_rows

OUT = ROOT / "results/external_validation/paper_b_external_validation_v1"


def generalized_original_point() -> pd.DataFrame:
    payload = 64
    interval = 60
    horizon = 5
    allowance_mb = 500
    increment_mb = 500
    rounding = 1000

    variants = pd.read_csv(ROOT / "results/validation/stage5k_protocol_envelope_variants/protocol_envelope_variants.csv")
    variants = variants[variants.scenario_id.eq("asset_tracking_periodic_cross_cell")].copy()
    ser_policy = yaml.safe_load((ROOT / "datasets/stage5m_lwm2m_serialization_envelope.yml").read_text())
    sess_policy = yaml.safe_load((ROOT / "datasets/stage5n_security_session_control_envelope.yml").read_text())
    shapes = [s["shape_id"] for s in ser_policy["serialization_surrogates"]]

    mod, serrows = [], []
    for _, vr in variants.iterrows():
        v = vr.to_dict()
        v["application_payload_bytes"] = payload
        v["reporting_interval_s"] = interval
        v["variant_id"] = f"{vr['variant_id']}__P{payload}__I{interval}"
        mod.append(v)
        for shape in shapes:
            enc = str(v["lwm2m_payload_encoding"])
            encoded = serialized_payload_bytes(
                payload,
                enc,
                shape,
                object_id=int(ser_policy["scientific_policy"]["synthetic_test_object_id"]),
            )
            strict0 = strict_transport_floor_bytes(v, 0)
            l1 = strict0 + payload
            l2 = strict_transport_floor_bytes(v, encoded)
            anchor = anchor_known_component_bytes(v, encoded, include_ip=False)
            serrows.append(
                {
                    "serialization_row_id": f"{v['variant_id']}__{shape}",
                    "variant_id": v["variant_id"],
                    "profile_id": v["profile_id"],
                    "scenario_id": v["scenario_id"],
                    "stack_id": v["stack_id"],
                    "binding_family": v["binding_family"],
                    "access_technology": v["access_technology"],
                    "anchor_id": v["anchor_id"],
                    "shape_id": shape,
                    "lwm2m_payload_encoding": enc,
                    "serialized_lwm2m_payload_bytes": encoded,
                    "anchor_transport_bytes_per_report_with_surrogate": anchor,
                    "five_year_report_count": 1,
                    "included_data_bytes": 10**18,
                    "_L0": payload,
                    "_L1": l1,
                    "_L2": l2,
                }
            )

    env = build_session_control_envelope_rows(serrows, mod, sess_policy)
    sr = {r["serialization_row_id"]: r for r in serrows}
    base = []
    for e in env:
        s = sr[e["serialization_row_id"]]
        for billing in ["B0_persistent_pdp", "B1_pdp_per_report"]:
            base.append(
                {
                    "stack_id": e["stack_id"],
                    "anchor_id": e["anchor_id"],
                    "shape_id": e["shape_id"],
                    "session_control_envelope_id": e["envelope_id"],
                    "billing_anchor_id": billing,
                    "L0_bytes_per_report": float(s["_L0"]),
                    "L1_bytes_per_report": float(s["_L1"]),
                    "L2_bytes_per_report": float(s["_L2"]),
                    "L3_bytes_per_report": float(e["session_control_augmented_transport_bytes_per_report"]),
                }
            )
    d = pd.DataFrame(base)
    report_count = int(np.ceil(horizon * 365.25 * 86400 / interval))
    d["report_count"] = report_count
    for level in range(4):
        d[f"L{level}_bytes_5y_recomputed"] = d[f"L{level}_bytes_per_report"] * report_count
    raw = d["L3_bytes_5y_recomputed"].to_numpy(float)
    per = d["L3_bytes_per_report"].to_numpy(float)
    b0 = np.ceil(raw / rounding) * rounding
    b1 = np.ceil(per / rounding) * rounding * report_count
    d["L4_bytes_5y_recomputed"] = np.where(d.billing_anchor_id.eq("B0_persistent_pdp"), b0, b1)
    d["allowance_bytes"] = allowance_mb * 1_000_000
    d["billing_increment_bytes"] = increment_mb * 1_000_000
    return d


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    original = pd.read_csv(ROOT / "results/experiments/experiment4_accounting_simplification/aligned_state_accounting_ablation.csv")
    recomputed = generalized_original_point()
    keys = ["stack_id", "anchor_id", "shape_id", "session_control_envelope_id", "billing_anchor_id"]
    orig = original[keys + ["L0_bytes_5y", "L1_bytes_5y", "L2_bytes_5y", "L3_bytes_5y", "L4_bytes_5y"]].copy()
    merged = orig.merge(recomputed, on=keys, how="outer", validate="one_to_one", indicator=True)
    for level in range(5):
        merged[f"L{level}_absolute_difference_bytes"] = (
            merged[f"L{level}_bytes_5y_recomputed"] - merged[f"L{level}_bytes_5y"]
        ).abs()
    diff_cols = [f"L{i}_absolute_difference_bytes" for i in range(5)]
    merged["all_levels_exact"] = merged[diff_cols].max(axis=1).eq(0)

    detail_path = OUT / "mr4_original_point_reproduction.csv"
    merged.to_csv(detail_path, index=False)
    summary = {
        "diagnostic": "generalized_MR4_reproduces_frozen_Experiment4_original_point",
        "payload_bytes": 64,
        "reporting_interval_s": 60,
        "horizon_years": 5,
        "allowance_mb": 500,
        "billing_increment_mb": 500,
        "expected_state_rows": 288,
        "merged_state_rows": int(len(merged)),
        "all_keys_matched": bool((merged["_merge"] == "both").all()),
        "exact_rows_all_levels": int(merged["all_levels_exact"].sum()),
        "all_rows_exact_all_levels": bool(merged["all_levels_exact"].all()),
        "max_abs_difference_bytes_by_level": {
            f"L{i}": float(merged[f"L{i}_absolute_difference_bytes"].max()) for i in range(5)
        },
        "interpretation": "The factorial MR4 generalization changes the workload/tariff grid only; at the frozen original point it reproduces every L0-L4 byte total exactly for all 288 protocol/billing states.",
    }
    (OUT / "mr4_original_point_reproduction.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if not summary["all_keys_matched"] or not summary["all_rows_exact_all_levels"] or len(merged) != 288:
        raise SystemExit(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
