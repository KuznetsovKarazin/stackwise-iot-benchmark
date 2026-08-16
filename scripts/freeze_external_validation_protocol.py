from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_FILES = [
    ROOT / "docs/PAPER_B_EXTERNAL_VALIDATION_PROTOCOL.md",
    ROOT / "datasets/external_validation_campaign.yml",
    ROOT / "datasets/external_validation_use_cases.yml",
    ROOT / "datasets/external_validation_evidence_sources.yml",
    ROOT / "datasets/external_validation_admissibility_policy.yml",
    ROOT / "external_validation/source_document_manifest.json",
    ROOT / "external_validation/annotations/hints_source_discrepancies_predata.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_method_files() -> list[Path]:
    campaign = yaml.safe_load((ROOT / 'datasets/external_validation_campaign.yml').read_text(encoding='utf-8'))
    return [ROOT / rel for rel in campaign['frozen_method_inputs'].values()]


def validate_ready() -> list[str]:
    errors: list[str] = []
    use_cases = yaml.safe_load((ROOT / "datasets/external_validation_use_cases.yml").read_text(encoding="utf-8"))
    for case in use_cases["use_cases"]:
        if case.get("requirements_status") != "EXTRACTED_AND_REVIEWED":
            errors.append(f"{case['source_case_id']}: requirements_status is not EXTRACTED_AND_REVIEWED")
        if not case.get("requirements"):
            errors.append(f"{case['source_case_id']}: no extracted requirements")
        for req in case.get("requirements", []):
            for key in ("requirement_id", "source_reference", "stackwise_field", "mapping_status", "hard_or_preference"):
                if not req.get(key):
                    errors.append(f"{case['source_case_id']}: requirement missing {key}")

    source_registry = yaml.safe_load((ROOT / 'datasets/external_validation_evidence_sources.yml').read_text(encoding='utf-8'))
    src_dir = ROOT / 'external_validation/sources'
    for src in source_registry['sources']:
        local = src_dir / src['local_validation_filename']
        if not local.exists():
            errors.append(f"{src['external_source_id']}: held-out file not materialised locally: {local.relative_to(ROOT)}")
            continue
        got = md5(local)
        if got.lower() != src['selected_file_md5'].lower():
            errors.append(f"{src['external_source_id']}: MD5 mismatch expected={src['selected_file_md5']} actual={got}")

    for p in frozen_method_files():
        if not p.exists():
            errors.append(f"frozen method input missing: {p.relative_to(ROOT)}")
    return errors


def file_entry(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def held_out_entries() -> list[dict[str, object]]:
    source_registry = yaml.safe_load((ROOT / 'datasets/external_validation_evidence_sources.yml').read_text(encoding='utf-8'))
    src_dir = ROOT / 'external_validation/sources'
    entries=[]
    for src in source_registry['sources']:
        path = src_dir / src['local_validation_filename']
        entries.append({
            'source_id': src['external_source_id'],
            'path': str(path.relative_to(ROOT)),
            'bytes': path.stat().st_size,
            'md5': md5(path),
            'sha256': sha256(path),
        })
    return entries


def source_document_entries() -> list[dict[str, object]]:
    manifest = json.loads((ROOT / 'external_validation/source_document_manifest.json').read_text(encoding='utf-8'))
    return manifest['documents']


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true", help="Require all pre-data inputs and held-out files to be complete.")
    args = parser.parse_args()

    all_required = PROTOCOL_FILES + frozen_method_files()
    missing = [str(p) for p in all_required if not p.exists()]
    if missing:
        raise SystemExit("Missing protocol/frozen method files: " + ", ".join(missing))

    errors = validate_ready() if args.freeze else []
    if errors:
        print("PRE-DATA freeze refused:")
        for error in errors:
            print(" -", error)
        raise SystemExit(2)

    campaign = yaml.safe_load((ROOT / 'datasets/external_validation_campaign.yml').read_text(encoding='utf-8'))
    manifest = {
        "campaign_id": campaign['campaign_id'],
        "freeze_state": "PRE_DATA_FROZEN" if args.freeze else campaign.get('status','DESIGN_FREEZE_PRE_DATA'),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_files": [file_entry(p) for p in PROTOCOL_FILES],
        "frozen_method_inputs": [file_entry(p) for p in frozen_method_files()],
        "held_out_inputs": held_out_entries() if args.freeze else [],
        "source_documents": source_document_entries(),
        "benchmark_version": campaign['benchmark']['version'],
        "rules_changed_after_outcome_inspection": False,
        "outcome_analysis_permitted": bool(args.freeze),
    }
    out = ROOT / "external_validation/protocol_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Protocol manifest written: {out}")
    if args.freeze:
        print("PRE-DATA protocol freeze: OK")
    else:
        print(f"Design-freeze manifest only ({manifest['freeze_state']}); outcome analysis remains prohibited.")


if __name__ == "__main__":
    main()
