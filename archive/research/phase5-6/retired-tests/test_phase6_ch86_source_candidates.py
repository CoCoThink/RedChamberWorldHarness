"""Exact novel excerpts do not qualify project summaries or historical claims."""
import json
from pathlib import Path

from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/provenance'


def test_unregistered_novel_candidates_are_exact_spans_not_carrier_qualification():
    proposal = json.loads((BASE / 'ch86-narrow-text-evidence-v1.json').read_bytes())
    observation = json.loads((BASE / 'ch86-narrow-locator-observation-v1.json').read_bytes())
    assert json.loads(bound_bytes(ROOT, observation['proposal'])) == proposal
    assert proposal['status'] == 'UNREGISTERED_RESEARCH_CANDIDATES'
    assert proposal['authority_effect'] == observation['authority_effect'] == 'NONE'
    assert observation['locator_status'] == 'PASS'
    assert observation['source_registration'] == 'NOT_PERFORMED'
    assert observation['ch86_project_carrier_closure'] == 'NOT_GRANTED'
    assert observation['human_qualification'] is False
    units = {row['unit_ref']: row for line in bound_bytes(ROOT, proposal['extraction_units']).splitlines()
             if (row := json.loads(line))}
    for key in ('adapter', 'scene', 'carrier', 'extraction_manifest'):
        bound_bytes(ROOT, proposal[key])
    assert [row['chapter'] for row in proposal['records']] == [51, 56, 58, 45]
    for row, checked in zip(proposal['records'], observation['records'], strict=True):
        source = row['source_proposal']
        assert source['type'] == 'NOVEL_TEXT'
        assert source['tier'] == 'EDITORIAL'
        assert source['locator_verification']['status'] == 'UNVERIFIED'
        assert not validate_instance(source, ROOT / 'schemas/source.schema.json')
        locator = source['locator']
        actual = locator['joiner'].join(units[span['unit_ref']]['text'][span['start']:span['end']]
                                        for span in locator['spans'])
        assert actual == source['text']
        assert digest(actual.encode()) == source['text_sha256'] == locator['raw_text_sha256']
        assert checked['id'] == row['id']
        assert checked['verification']['status'] == 'PASS'
        assert checked['verification']['raw_excerpt'] == actual
        assert checked['verification']['findings'] == []
    medical = proposal['records'][0]
    assert medical['omitted_inline_commentary'] is True
    assert '庚夹' not in medical['source_proposal']['text']
    assert len(medical['source_proposal']['locator']['spans']) == 2
    assert '宝钗' in proposal['records'][3]['narrow_supported_proposition']


def test_three_carrier_audit_keeps_project_documents_distinct_from_primary_evidence():
    report = json.loads((BASE / 'ch86-three-carrier-origin-audit-v1.json').read_bytes())
    assert report['authority_effect'] == 'NONE'
    assert 'none is currently a closed qualified provenance source' in report['overall_conclusion']
    assert 'not original historical evidence' in report['overall_conclusion']
    count = 0

    def check(value):
        nonlocal count
        if isinstance(value, dict):
            if {'path', 'sha256'} <= value.keys() and isinstance(value['path'], str):
                path = ROOT / value['path']
                assert path.resolve().is_relative_to(ROOT)
                if path.is_file():
                    assert digest(path.read_bytes()) == value['sha256']
                    count += 1
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(report)
    assert count >= 32
