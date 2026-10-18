from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetError
from rcwh.workflow.admission import chapter_scope
from test_agent_release import edition, packet, peers, write

ROOT = Path(__file__).resolve().parents[1]


def test_stable_default_scope_remains_exact():
    expected = json.loads((ROOT / 'tests/fixtures/baseline-ch89-scope.json').read_bytes())
    assert chapter_scope(ROOT, 'data/writing/packages/ch89-production-v5.json') == expected


def test_actual_ch81_advisory_scope_is_explicit_and_not_semantic_pass():
    path = 'data/writing/packages/ch81-agent-research-v2.json'
    default = chapter_scope(ROOT, path)
    assert 'CHAPTER_SCENE_SCOPE_MISSING' in default['findings']
    assert 'advisory_contract_paths' not in default
    selected = chapter_scope(ROOT, path, plan_contracts=True)
    assert 'CHAPTER_SCENE_SCOPE_MISSING' not in selected['findings']
    assert len(selected['advisory_contract_paths']) == 3
    assert all(report['prose_supported_semantic_replay']['status'] == 'NOT_CHECKED'
               for report in selected['advisory_contract_reports'])


@pytest.mark.parametrize('fault,expected', [('stale', 'STALE_AGENT_PLAN_CONTRACT'),
                                           ('chapter', 'CHAPTER_MISMATCH'),
                                           ('generated', 'NOT_EDITED'),
                                           ('outside', 'OUTSIDE_DECLARED_DIRECTORY')])
def test_bad_advisory_bindings_cannot_enter_scope(tmp_path, monkeypatch, fault, expected):
    from types import SimpleNamespace
    contract = json.loads((ROOT / 'data/planning/contracts/agent-final-v1/81-S1.v2.json').read_bytes())
    if fault == 'chapter':
        contract['chapter'] = 82
    elif fault == 'generated':
        contract['status'] = 'DRAFT_GENERATED'
    relative = 'data/planning/contracts/test.json' if fault != 'outside' else 'unselected/test.json'
    binding = write(tmp_path, relative, contract)
    if fault == 'stale':
        binding['sha256'] = '0' * 64
    exemplar = write(tmp_path, 'exemplars.json', {'dataset_ref': 'test'})
    write(tmp_path, 'package.json', {'chapter': 81, 'sources': [], 'exemplar_set': exemplar, 'plan': [binding]})
    monkeypatch.setattr('rcwh.workflow.admission.ProvenanceGraph.from_repo', lambda _: SimpleNamespace(
        sources={}, claims={}, implementations={}))
    monkeypatch.setattr('rcwh.workflow.admission.validate', lambda *args: None)
    with pytest.raises(AssetError, match=expected):
        chapter_scope(tmp_path, 'package.json', plan_contracts=True)


@pytest.mark.parametrize('replay,expected', [('PENDING', 'PASS'), ('FAIL', 'FAIL')])
def test_unchecked_contract_tiers_are_info_but_replay_failure_blocks(edition, monkeypatch, replay, expected):
    e = edition
    exemplar = write(e.root, 'exemplars.json', {'dataset_ref': 'test', 'segments': []})
    package_binding = write(e.root, 'new-package.json', {'chapter': 86, 'exemplar_set': exemplar})
    advisory = write(e.root, 'data/planning/contracts/agent-final-v2/test.json', {'fixture': 'advisory'})
    e.request['chapters'][0]['writing_package'] = package_binding
    e.request['chapters'][0]['panel']['packet'] = packet(e.root, 'advisory', [
        {'id': 'candidate', 'scope': 'CANDIDATE', 'binding': e.candidate},
        {'id': 'package', 'scope': 'PACKAGE', 'binding': package_binding},
        {'id': 'legacy', 'scope': 'CONTRACT', 'binding': e.contract},
        {'id': 'advisory', 'scope': 'CONTRACT', 'binding': advisory}])
    peers(e.root, e.request['chapters'][0]['panel']['packet'])
    scope = {'chapter': 86, 'paths': [e.contract['path'], advisory['path']], 'used_source_ids': [],
             'dataset_refs': ['test'], 'findings': [], 'advisory_contract_paths': [advisory['path']],
             'advisory_contract_reports': [{'declared_compatibility': {'status': 'PENDING'},
                 'deterministic_world_state_replay': {'status': replay},
                 'prose_supported_semantic_replay': {'status': 'NOT_CHECKED'}}]}
    calls = []
    def selected(root, path, **kwargs):
        calls.append(kwargs)
        return deepcopy(scope)
    monkeypatch.setattr('rcwh.workflow.admission.chapter_scope', selected)
    gates, reports = e.runtime._inputs(e.request['chapters'][0])
    assert calls == [{'plan_contracts': True}]
    assert gates['CONTRACT_PEERS'] == expected
    assert e.contract in reports['contract_peer_bindings']
    assert advisory in reports['contract_peer_bindings']


def test_selected_plan_contracts_supply_scope_for_any_chapter(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from test_agent_contracts import fixture_repo, edited
    fixture_repo(tmp_path)
    contract = edited(tmp_path)
    contract['chapter'] = 86
    plan = json.loads((tmp_path / contract['chapter_plan_ref']).read_bytes())
    plan['chapter'] = 86
    plan_binding = write(tmp_path, contract['chapter_plan_ref'], plan)
    contract['bindings']['chapter_plan'] = plan_binding
    selected = write(tmp_path, 'data/planning/contracts/test-v1/s.v1.json', contract)
    exemplar = write(tmp_path, 'exemplars.json', {'dataset_ref': 'test'})
    write(tmp_path, 'package.json', {'chapter': 86, 'sources': [], 'exemplar_set': exemplar, 'plan': [plan_binding, selected]})
    monkeypatch.setattr('rcwh.workflow.admission.ProvenanceGraph.from_repo', lambda _: SimpleNamespace(
        sources={}, claims={}, implementations={}))
    monkeypatch.setattr('rcwh.planning.contracts.inspect_contract', lambda *args, **kwargs: {
        'declared_compatibility': {'status': 'PENDING', 'checks': []},
        'deterministic_world_state_replay': {'status': 'PENDING'},
        'prose_supported_semantic_replay': {'status': 'NOT_CHECKED'}})
    scope = chapter_scope(tmp_path, 'package.json', plan_contracts=True)
    assert scope['advisory_contract_paths'] == [selected['path']]
    # No chapter number is special-cased: selected plan contracts are scope.
    assert 'CHAPTER_SCENE_SCOPE_MISSING' not in scope['findings']


def test_real_seed_pointing_to_unselected_plan_cannot_enter_scope(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from test_agent_contracts import fixture_repo, edited, SEED, PLAN
    from rcwh.generation.records import binding
    fixture_repo(tmp_path)
    seed = json.loads((tmp_path / SEED).read_bytes())
    seed['chapter_plan_ref'] = 'data/planning/chapters/unselected.json'
    write(tmp_path, SEED, seed)
    write(tmp_path, seed['chapter_plan_ref'], {'chapter': 82, 'scenes': []})
    contract = edited(tmp_path)
    contract['chapter_plan_ref'] = PLAN
    contract['bindings']['chapter_plan'] = binding(tmp_path, PLAN)
    selected = write(tmp_path, 'data/planning/contracts/test-v1/s.v1.json', contract)
    exemplar = write(tmp_path, 'exemplars.json', {'dataset_ref': 'test'})
    write(tmp_path, 'package.json', {'chapter': 81, 'sources': [], 'exemplar_set': exemplar,
                                   'plan': [binding(tmp_path, PLAN), selected]})
    monkeypatch.setattr('rcwh.workflow.admission.ProvenanceGraph.from_repo', lambda _: SimpleNamespace(
        sources={}, claims={}, implementations={}))
    with pytest.raises(AssetError, match='AGENT_CONTRACT_SEED_PLAN_MISMATCH'):
        chapter_scope(tmp_path, 'package.json', plan_contracts=True)


def test_wrong_contract_internal_reference_is_rejected(monkeypatch):
    from rcwh.planning.contracts import inspect_contract
    original = inspect_contract
    def broken(*args, **kwargs):
        report = original(*args, **kwargs)
        report['declared_compatibility'] = {'status': 'FAIL', 'checks': [
            {'status': 'FAIL', 'code': 'CONTRACT_REFERENCE_INVALID'}]}
        return report
    monkeypatch.setattr('rcwh.planning.contracts.inspect_contract', broken)
    with pytest.raises(AssetError, match='CONTRACT_REFERENCE_INVALID'):
        chapter_scope(ROOT, 'data/writing/packages/ch81-agent-research-v2.json', plan_contracts=True)


def test_project_documents_cited_by_adapters_are_context_not_missing_sources(monkeypatch):
    path = 'data/writing/packages/ch86-agent-research-v3.json'
    scope = chapter_scope(ROOT, path, plan_contracts=True)
    assert not [f for f in scope['findings'] if f.startswith('UNRESOLVED_DEPENDENT_SOURCE_ASSET')]
    assert {'asset:sha256:3735d2b2d82d70aac061f2cf7f5ccee84370064d6935364aa587402dccb7ff96',
            'asset:sha256:98d9c0a13e692043b440941fe50cdcb719ab9cb4f1623f061f894cb6d6a3155c',
            'asset:sha256:e9b9b54f25c6c2419433b9b3da040e936d0f4d1bad4945817c5cad1643161f97'} <= set(scope['project_reference_context'])
    # An asset that is not a catalogued project document stays a missing input.
    from types import SimpleNamespace
    monkeypatch.setattr('rcwh.workflow.admission.AssetCatalog.from_repo', lambda root: SimpleNamespace(assets={}))
    scope = chapter_scope(ROOT, path, plan_contracts=True)
    assert [f for f in scope['findings'] if f.startswith('UNRESOLVED_DEPENDENT_SOURCE_ASSET')]
