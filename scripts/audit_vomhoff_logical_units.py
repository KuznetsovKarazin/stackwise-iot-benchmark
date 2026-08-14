from __future__ import annotations

import argparse
from pathlib import Path

from stackwise.io import dump_json, read_table, write_table
from stackwise.provenance import write_run_manifest
from stackwise.vomhoff_audit import audit_vomhoff_logical_units


DEFAULT_INPUT = Path("data/processed/vomhoff_nbiot_ltem_energy_2023/observations.parquet")
DEFAULT_OUTPUT = Path("results/validation/vomhoff_logical_unit_audit")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Vomhoff source-segment multiplicity before defining Stage-2 logical run/phase aggregation."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Validated harmonised Vomhoff table not found: {args.input}. "
            "Run 'stackwise harmonize vomhoff_nbiot_ltem_energy_2023 --strict' first."
        )

    frame = read_table(args.input)
    summary, groups, multi_segments, non_target, fig5_standby = audit_vomhoff_logical_units(frame)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = dump_json(summary, args.output_dir / "summary.json")
    groups_path = write_table(groups, args.output_dir / "candidate_target_phase_groups.csv")
    multi_path = write_table(multi_segments, args.output_dir / "multi_segment_target_segments.csv")
    non_target_path = write_table(non_target, args.output_dir / "non_target_event_counts.csv")
    standby_path = write_table(fig5_standby, args.output_dir / "figure5_standby_audit.csv")

    manifest_path = write_run_manifest(
        args.output_dir / "run_manifest.json",
        command="python scripts/audit_vomhoff_logical_units.py",
        inputs=[args.input],
        outputs=[summary_path, groups_path, multi_path, non_target_path, standby_path],
        parameters={
            "aggregation_authorised": False,
            "purpose": "identify Stage-2 logical run/phase unit without pseudo-replication",
        },
    )

    print(f"Input rows: {summary['input_rows']}")
    print(f"Target-phase rows: {summary['target_phase_rows']}")
    print(f"Candidate logical phase groups: {summary['candidate_logical_phase_groups']}")
    print(f"Multi-segment target groups: {summary['multi_segment_target_groups']}")
    print(f"Maximum segments in one candidate group: {summary['max_segments_per_candidate_group']}")
    print(f"Metadata-inconsistent candidate groups: {summary['metadata_inconsistent_candidate_groups']}")
    standby = summary["figure5_standby_source_discrepancy_audit"]
    print(
        "Figure 5 Standby audit: "
        f"rows={standby['rows']}, duration_s={standby['duration_s']}"
    )
    print("Aggregation authorised: NO (audit only)")
    print(f"Summary: {summary_path}")
    print(f"Multi-segment details: {multi_path}")
    print(f"Run manifest: {manifest_path}")


if __name__ == "__main__":
    main()
