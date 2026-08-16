from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    issues: list[str] = []
    warnings: list[str] = []

    use_cases = yaml.safe_load((ROOT / 'datasets/external_validation_use_cases.yml').read_text(encoding='utf-8'))
    sources = yaml.safe_load((ROOT / 'datasets/external_validation_evidence_sources.yml').read_text(encoding='utf-8'))

    # Use-case source transcription checks
    for case in use_cases['use_cases']:
        status = case.get('requirements_status')
        reqs = case.get('requirements') or []
        if status == 'EXTRACTED_AND_REVIEWED':
            if not reqs:
                issues.append(f"{case['source_case_id']}: extracted status but no requirements")
            for req in reqs:
                for key in ('requirement_id','source_reference','source_text_or_faithful_paraphrase','stackwise_field','mapping_status','hard_or_preference'):
                    if key not in req or req[key] in ('', None):
                        issues.append(f"{case['source_case_id']}/{req.get('requirement_id','?')}: missing {key}")
                if req.get('mapping_status') not in {'exact','interpretable','unavailable'}:
                    issues.append(f"{case['source_case_id']}/{req.get('requirement_id','?')}: invalid mapping_status")
        else:
            warnings.append(f"{case['source_case_id']}: exact requirement extraction pending")

    # Pre-data source-document audit checks
    source_doc_manifest = ROOT / 'external_validation/source_document_manifest.json'
    discrepancy_audit = ROOT / 'external_validation/annotations/hints_source_discrepancies_predata.csv'
    if not source_doc_manifest.exists():
        issues.append('source-document manifest missing')
    if not discrepancy_audit.exists():
        issues.append('HINTS pre-data discrepancy audit missing')

    # Local held-out file checks. Absence is a pre-freeze blocker, not a protocol design error.
    src_dir = ROOT / 'external_validation/sources'
    file_checks=[]
    for src in sources['sources']:
        local = src_dir / src['local_validation_filename']
        rec={'source_id':src['external_source_id'],'path':str(local.relative_to(ROOT)),'exists':local.exists(),'expected_md5':src['selected_file_md5']}
        if local.exists():
            got=md5(local); rec['actual_md5']=got; rec['md5_match']=got.lower()==src['selected_file_md5'].lower()
            if not rec['md5_match']:
                issues.append(f"{src['external_source_id']}: local MD5 mismatch")
        else:
            rec['actual_md5']=None; rec['md5_match']=False
            warnings.append(f"{src['external_source_id']}: held-out file not yet materialised locally")
        file_checks.append(rec)

    report={
        'ready_for_pre_data_freeze': not issues and all(c['exists'] and c['md5_match'] for c in file_checks) and all(c.get('requirements_status')=='EXTRACTED_AND_REVIEWED' for c in use_cases['use_cases']),
        'issues':issues,
        'warnings':warnings,
        'held_out_file_checks':file_checks,
    }
    out=ROOT/'external_validation/input_validation_report.json'
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 1 if issues else 0

if __name__=='__main__':
    raise SystemExit(main())
