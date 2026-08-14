from __future__ import annotations

from pathlib import Path

from stackwise.publication_packaging import build_deterministic_deposit_archive

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    release_dir = ROOT / "release/stackwise_benchmark_v1.0.0"
    qa_summary = ROOT / "results/validation/benchmark_release_final_qa/summary.json"
    output_dir = ROOT / "dist/stackwise_benchmark_v1.0.0"
    result = build_deterministic_deposit_archive(release_dir, qa_summary, output_dir)
    mib = result.archive_bytes / (1024 * 1024)
    print("STACKWISE Benchmark v1.0.0 deposit package: OK")
    print(f"Packaged release files / archive size MiB: {result.packaged_files} / {mib:.3f}")
    print(f"Archive SHA-256: {result.archive_sha256}")
    print("Benchmark licence / raw upstream archives absent: CC-BY-4.0 / yes")
    print("Release QA / Zenodo finalisation ready: passed / yes")
    print("Deterministic archive / publication MCDA authorised: yes / no")
    print(f"Deposit archive: {result.archive_path}")


if __name__ == "__main__":
    main()
