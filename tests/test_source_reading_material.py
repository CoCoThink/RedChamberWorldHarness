"""An old source handout must not masquerade as the currently selected audit."""
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow.review_intake import source_reading_material
from rcwh.workflow import review_intake

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = 'artifacts/reviews/source-independent-v2-20261009/human-review-template.json'


def save(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(value))
    return {'path': path, 'sha256': digest(target.read_bytes())}


def test_real_handout_reports_old_protocol_and_four_missing_sources():
    report = source_reading_material(ROOT)
    assert report['reading_material_status'] == 'BINDING_MATCHES'
    assert report['legacy_reading_material_status'] == 'STALE_PROTOCOL'
    assert report['reading_material_scope'] == 'PROTOCOL_AND_TEMPLATE_BINDING_ONLY'
    assert report['required_source_count'] == 16
    assert len(report['legacy_template_missing_sources']) == 4
    assert 'src:jimao:ch18:daiyu-death' in report['legacy_template_missing_sources']
    assert sum(s.endswith(':npm005664') for s in report['legacy_template_missing_sources']) == 3


def test_status_does_not_recommend_an_old_handout_as_current(monkeypatch):
    monkeypatch.setattr(review_intake, 'LANES', ('source',))
    monkeypatch.setattr(review_intake, 'lane_summary', lambda *_: {'status': 'PENDING', 'review_count': 0})
    report = review_intake.status(ROOT)
    lane = report['lanes'][0]
    assert lane['reading_material_status'] == 'BINDING_MATCHES'
    assert lane['legacy_reading_material_status'] == 'STALE_PROTOCOL'
    assert lane['reading_material'] != lane['legacy_reading_material']
    assert lane['current_protocol']['path'].endswith('protocol-v4.json')
    assert lane['status'] == report['status'] == 'PENDING'
    assert lane['review_count'] == 0 and report['authority_effect'] == 'NONE'


@pytest.mark.parametrize('fault,expected', [
    ('none', 'BINDING_MATCHES'), ('missing_template', 'NOT_PREPARED'),
    ('old_protocol', 'STALE_PROTOCOL'), ('missing_source', 'SCOPE_MISMATCH'),
    ('duplicate_source', 'SCOPE_MISMATCH'), ('extra_source', 'SCOPE_MISMATCH')])
def test_material_status_uses_selected_bytes_and_exact_scope(tmp_path, fault, expected):
    ref = save(tmp_path, 'protocol.json', {'sources': [{'source_ref': 'fixture:one'}]})
    save(tmp_path, 'data/provenance/audits/selection.json', {'protocol': ref})
    template = {'protocol_sha256': ref['sha256'], 'results': [{'source_ref': 'fixture:one'}]}
    if fault == 'old_protocol': template['protocol_sha256'] = '0' * 64
    elif fault == 'missing_source': template['results'] = []
    elif fault == 'duplicate_source': template['results'] *= 2
    elif fault == 'extra_source': template['results'].append({'source_ref': 'fixture:extra'})
    if fault != 'missing_template': save(tmp_path, TEMPLATE, template)
    assert source_reading_material(tmp_path)['reading_material_status'] == expected
    (tmp_path / 'protocol.json').write_text('{}')
    with pytest.raises(ValueError):
        source_reading_material(tmp_path)


@pytest.mark.parametrize('fault,expected', [
    ('none', 'BINDING_MATCHES'), ('old_plan', 'STALE_PROTOCOL'),
    ('old_template', 'STALE_PROTOCOL'), ('missing_subject', 'SCOPE_MISMATCH'),
    ('changed_subject', 'SCOPE_MISMATCH'), ('duplicate_subject', 'SCOPE_MISMATCH')])
def test_current_plan_checks_template_and_exact_subject_bindings(tmp_path, fault, expected):
    subject = {'source_ref': 'fixture:one', 'source_record_sha256': '1' * 64}
    ref = save(tmp_path, 'protocol.json', {'sources': [subject]})
    save(tmp_path, 'data/provenance/audits/selection.json', {'protocol': ref, 'reviews': []})
    template = {'protocol_sha256': ref['sha256'], 'results': [{'source_ref': 'fixture:one'}]}
    if fault == 'old_template': template['protocol_sha256'] = '0' * 64
    template_ref = save(tmp_path, 'current-template.json', template)
    plan = {'protocol': ref, 'template': template_ref, 'subjects': [dict(subject)]}
    if fault == 'old_plan': plan['protocol'] = {**ref, 'sha256': '0' * 64}
    elif fault == 'missing_subject': plan['subjects'] = []
    elif fault == 'changed_subject': plan['subjects'][0]['source_record_sha256'] = '2' * 64
    elif fault == 'duplicate_subject': plan['subjects'] *= 2
    save(tmp_path, 'data/writing/source-review-next/plan.json', plan)
    report = source_reading_material(tmp_path)
    assert report['reading_material_status'] == expected
    assert report['legacy_reading_material_status'] == 'NOT_PREPARED'
    # Intake ledger changes cannot stale fixed reading materials.
    save(tmp_path, 'data/provenance/audits/selection.json', {'protocol': ref, 'reviews': [{'fixture': True}]})
    assert source_reading_material(tmp_path)['reading_material_status'] == expected
    if fault != 'old_plan':
        (tmp_path / template_ref['path']).write_text('{}')
        with pytest.raises(ValueError):
            source_reading_material(tmp_path)
