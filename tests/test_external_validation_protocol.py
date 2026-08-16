from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_external_validation_registries_exist_and_are_versioned():
    for rel in [
        "datasets/external_validation_campaign.yml",
        "datasets/external_validation_use_cases.yml",
        "datasets/external_validation_evidence_sources.yml",
        "datasets/external_validation_admissibility_policy.yml",
    ]:
        p = ROOT / rel
        assert p.exists(), rel
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1


def test_exactly_five_primary_external_use_cases_are_preselected():
    data = yaml.safe_load((ROOT / "datasets/external_validation_use_cases.yml").read_text(encoding="utf-8"))
    assert len(data["use_cases"]) == 5
    assert len({x["source_case_id"] for x in data["use_cases"]}) == 5


def test_three_held_out_sources_include_negative_control():
    data = yaml.safe_load((ROOT / "datasets/external_validation_evidence_sources.yml").read_text(encoding="utf-8"))
    assert len(data["sources"]) == 3
    ids = {x["external_source_id"] for x in data["sources"]}
    assert "EV_E2_POVALAC_LORAWAN_TRAFFIC_2023" in ids
    p = next(x for x in data["sources"] if x["external_source_id"] == "EV_E2_POVALAC_LORAWAN_TRAFFIC_2023")
    assert "delivery_probability" in p["pre_registered_prohibited_direct_targets"]


def test_frozen_comparison_classes_are_complete():
    data = yaml.safe_load((ROOT / "datasets/external_validation_admissibility_policy.yml").read_text(encoding="utf-8"))
    assert set(data["frozen_comparison_classes"]) == {"C0_DIRECT", "C1_BRIDGEABLE", "C2_CONDITIONAL", "E0_MISSING"}
    assert data["external_schema_policy"]["new_canonical_field_allowed_after_freeze"] is False


def test_outcome_runner_manifest_state_is_consistent():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'external_validation/protocol_manifest.json').read_text(encoding='utf-8'))
    if manifest['freeze_state'] == 'PRE_DATA_FROZEN':
        assert manifest['outcome_analysis_permitted'] is True
        assert len(manifest.get('held_out_inputs', [])) == 3
    else:
        assert manifest['outcome_analysis_permitted'] is False


def test_vannieuwenborg_predata_extraction_is_materialised():
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    cases = yaml.safe_load((root / 'datasets/external_validation_use_cases.yml').read_text(encoding='utf-8'))['use_cases']
    selected = {c['source_case_id']: c for c in cases if c['source_case_id'].startswith('VANNIEUWENBORG')}
    assert len(selected) == 2
    assert all(c['requirements_status'] == 'EXTRACTED_AND_REVIEWED' for c in selected.values())
    assert all(c['requirements'] for c in selected.values())


def test_external_portfolio_requires_two_publication_families():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    text = (root / 'docs/PAPER_B_EXTERNAL_VALIDATION_PROTOCOL.md').read_text(encoding='utf-8')
    assert 'at least two independent publication families' in text


def test_design_manifest_hashes_frozen_method_inputs():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'external_validation/protocol_manifest.json').read_text(encoding='utf-8'))
    assert len(manifest.get('frozen_method_inputs', [])) >= 5
    assert all('sha256' in item for item in manifest['frozen_method_inputs'])
    if manifest['freeze_state'] == 'PRE_DATA_FROZEN':
        assert manifest['outcome_analysis_permitted'] is True
    else:
        assert manifest['outcome_analysis_permitted'] is False


def test_all_external_cases_are_transcribed_before_predata_freeze():
    import yaml
    root = Path(__file__).resolve().parents[1]
    cases = yaml.safe_load((root / 'datasets/external_validation_use_cases.yml').read_text(encoding='utf-8'))['use_cases']
    assert len(cases) == 5
    assert all(c['requirements_status'] == 'EXTRACTED_AND_REVIEWED' for c in cases)
    assert all(c['requirements'] for c in cases)
    assert (root / 'external_validation/annotations/hints_source_discrepancies_predata.csv').exists()


def test_hints_conflicts_are_not_exact_mappings():
    import yaml
    root = Path(__file__).resolve().parents[1]
    cases = yaml.safe_load((root / 'datasets/external_validation_use_cases.yml').read_text(encoding='utf-8'))['use_cases']
    for case in [c for c in cases if c['source_family'] == 'HINTS']:
        for req in case['requirements']:
            if req.get('source_conflict'):
                assert req['mapping_status'] == 'unavailable'
