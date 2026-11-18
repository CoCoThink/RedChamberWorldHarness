"""Source handouts bind current evidence without manufacturing review coverage."""
import json
from pathlib import Path
import runpy
import socket
import subprocess
import sys

from rcwh.assets import AssetError
from rcwh.assets.ingest import AssetIntake
from rcwh.candidate_reviews import canonical_bytes
from test_source_extraction import extraction_repo, write_source  # noqa: F401
from test_source_audit import audit_source_repo, submit_fixture  # noqa: F401

import pytest

from rcwh.candidate_reviews import digest
from rcwh.workflow.review_intake import prepare_registration

import rcwh.workflow.source_audit_preparation as prep

ROOT = Path(__file__).resolve().parents[1]


def test_cli_forwards_check_to_core(monkeypatch, capsys):
    calls = []

    def run(root, check=False):
        calls.append((root, check))
        return {'status': 'PASS'}

    monkeypatch.setattr(prep, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['prepare_source_audit_review.py', '--check'])
    runpy.run_path(str(ROOT / 'tools/prepare_source_audit_review.py'), run_name='__main__')

    assert calls == [(ROOT, True)]
    assert json.loads(capsys.readouterr().out) == {'status': 'PASS'}


@pytest.fixture(scope='module')
def prepared():
    # Fail if preparation starts any network/DNS use, including through adapters.
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo
    def forbidden(*args, **kwargs):
        raise AssertionError('source preparation must be offline')
    socket.socket.connect = socket.getaddrinfo = forbidden
    try:
        return prep.documents(ROOT)
    finally:
        socket.socket.connect, socket.getaddrinfo = original_connect, original_lookup


def test_current_campaign_exact_scope_context_and_dependency_bindings(prepared):
    plan = json.loads(prepared[f'{prep.BASE}/plan.json'])
    protocol = json.loads((ROOT / plan['protocol']['path']).read_bytes())
    assert plan['protocol']['sha256'] == digest((ROOT / plan['protocol']['path']).read_bytes())
    assert len(plan['subjects']) == 16
    assert [{k: subject[k] for k in ('source_ref', 'source_record_sha256')} for subject in plan['subjects']] == protocol['sources']
    for subject in plan['subjects']:
        trace = json.loads(prepared[subject['context']['path']])['trace']
        assert trace['source']['id'] == subject['source_ref']
        assert sorted(c['id'] for c in trace['claims']) == subject['claim_ids']
    for ref in plan['tracked_inputs']:
        assert digest((ROOT / ref['path']).read_bytes()) == ref['sha256']
    assert len(plan['asset_records']) > 15
    assert not {'selection', 'review_status', 'selected_review_count'} & plan.keys()
    paths = {ref['path'] for ref in plan['tracked_inputs']}
    assert 'data/provenance/audits/selection.json' not in paths
    assert not any(path.startswith('data/catalog/') for path in paths)
    v3 = json.loads((ROOT / 'data/provenance/audits/protocol-v3.json').read_bytes())
    assert all(row in protocol['sources'] for row in v3['sources'])
    from rcwh.workflow.admission import chapter_scope
    scope = chapter_scope(ROOT, 'data/writing/packages/ch86-local-scenario-v6.json')
    assert set(scope['used_source_ids']) == {
        'src:history:beijing:1774:rental-contract',
        'src:history:cao:1728:pawn-tickets:npm005664', 'src:jimao:ch18:daiyu-death'}
    assert set(scope['used_source_ids']) <= {s['source_ref'] for s in plan['subjects']}
    assert plan['authority_effect'] == 'NONE' and plan['production_admission'] == 'NOT_GRANTED'
    # Fresh reconstruction must exactly match every retained reading file.
    for path, raw in prepared.items():
        assert (ROOT / path).read_bytes() == raw


def test_unfilled_template_cannot_be_registered(prepared, tmp_path):
    raw = prepared[f'{prep.BASE}/human-review-template.json']
    template = json.loads(raw)
    assert all(row[key] is None for row in template['results'] for key in prep.CHECKS)
    path = tmp_path / 'unfilled.json'
    path.write_bytes(raw)
    with pytest.raises(ValueError, match='未填写字段'):
        prepare_registration(ROOT, 'source', path, origin='test:unfilled-preparation')


def test_write_preflights_entire_set_and_never_overwrites(tmp_path, monkeypatch):
    docs = {'new.json': b'new\n', 'existing.json': b'expected\n'}
    monkeypatch.setattr(prep, 'documents', lambda root: docs)
    (tmp_path / 'existing.json').write_bytes(b'altered\n')
    with pytest.raises(ValueError, match='refusing to replace'):
        prep.run(tmp_path)
    assert not (tmp_path / 'new.json').exists()
    assert (tmp_path / 'existing.json').read_bytes() == b'altered\n'


def test_check_does_not_fill_missing_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(prep, 'documents', lambda root: {'missing.json': b'expected\n'})
    with pytest.raises(ValueError, match='missing reading material'):
        prep.run(tmp_path, check=True)
    assert not (tmp_path / 'missing.json').exists()


@pytest.fixture
def frozen_source_plan(audit_source_repo):
    root, source, protocol, selected = audit_source_repo
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', 'add', '.'], cwd=root, check=True)
    result = prep.run(root)
    assert result['audit_summary']['status'] == 'PENDING'
    return root, source, protocol, selected, prep.documents(root)


def test_selected_positive_and_adverse_reviews_leave_frozen_plan_valid(frozen_source_plan):
    root, source, _, selected, frozen = frozen_source_plan
    # Synthetic submissions live only in a temporary repository. Exercise the real
    # audit ledger and raw-review asset validation, rather than mocking verdicts.
    submit_fixture(root, selected, source)
    positive = prep.run(root, check=True)
    assert positive['review_status'] == 'PASS' and positive['review_count'] == 1
    assert prep.documents(root) == frozen
    submit_fixture(root, selected, source, rejected_check='excerpt_valid', reviewer_id='fixture:adverse-reader')
    adverse = prep.run(root, check=True)
    assert adverse['audit_summary']['status'] == 'FAIL' and adverse['review_count'] == 2
    assert adverse['audit_summary']['findings'][0]['rejected_checks'] == ['excerpt_valid']
    assert prep.documents(root) == frozen


def test_unrelated_catalog_addition_does_not_stale_frozen_plan(frozen_source_plan):
    root, _, _, _, frozen = frozen_source_plan
    unrelated = root.parent / 'unrelated.txt'
    unrelated.write_bytes(b'Unrelated catalog content, not evidence for this source')
    AssetIntake(root).ingest(unrelated, origin='test:unrelated', kind='PROJECT_REFERENCE')
    assert prep.run(root, check=True)['status'] == 'PASS'
    assert prep.documents(root) == frozen


@pytest.mark.parametrize('target', ['protocol', 'source', 'carrier'])
def test_frozen_plan_rejects_changed_bound_evidence(frozen_source_plan, target):
    root, source, protocol, selected, _ = frozen_source_plan
    if target == 'protocol':
        path = root / selected['protocol']['path']
        protocol['id'] = 'source-audit:changed-protocol'
        path.write_bytes(canonical_bytes(protocol))
        with pytest.raises(AssetError, match='STALE_SOURCE_AUDIT_RECORD'):
            prep.run(root, check=True)
        # Even a correctly rebound active protocol cannot reuse the frozen plan.
        selected['protocol']['sha256'] = digest(path.read_bytes())
        (root / 'data/provenance/audits/selection.json').write_bytes(canonical_bytes(selected))
        with pytest.raises(ValueError, match='refusing to replace'):
            prep.run(root, check=True)
    elif target == 'source':
        source['title'] = 'Changed source identity context'
        write_source(root, source)
        with pytest.raises(AssetError, match='STALE_SOURCE_AUDIT_SOURCE'):
            prep.run(root, check=True)
    else:
        from rcwh.assets import AssetCatalog
        carrier = AssetCatalog.from_repo(root).resolve(source['container']['ref'])
        carrier.path.write_bytes(b'Changed original carrier bytes')
        with pytest.raises((ValueError, AssetError)):
            prep.run(root, check=True)
