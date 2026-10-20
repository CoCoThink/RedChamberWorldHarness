from copy import deepcopy
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import binding
from rcwh.generation.render import PromptRenderer
from rcwh.literary_inputs import LiteraryInputs
from test_literary_inputs import writing_repo
from test_corpus_dataset import corpus_repo, ROOT
from test_source_extraction import extraction_repo


def select_set(root, package_path, package):
    path = root / 'supplement.json'
    path.write_bytes(canonical_bytes({'kind': 'test-fixture'}))
    package['operation_scope'] = 'RESEARCH'
    package['research_source_sets'] = [binding(root, 'supplement.json')]
    (root / package_path).write_bytes(canonical_bytes(package))


def fake_report(root):
    return {'status': 'PENDING', 'integrity_status': 'PASS', 'evidence_readiness': 'PENDING',
            'records': {'sources': [], 'claims': []}, 'paths': ['supplement.json'], 'findings': [],
            'authority_effect': 'NONE', 'qualification': 'MODEL'}


def test_only_explicit_research_selection_adds_pending_bound_data(writing_repo, monkeypatch):
    root, _, path, _, package = writing_repo
    catalog = AssetCatalog.from_repo(root)
    before = LiteraryInputs(catalog).package(path)
    assert 'supplemental_source_sets' not in before
    select_set(root, path, package)
    calls = []
    def inspect(self, selected, **kwargs):
        calls.append((selected, kwargs))
        return fake_report(root)
    monkeypatch.setattr('rcwh.provenance.research_inputs.ResearchSourceInputs.report', inspect)
    report = LiteraryInputs(catalog).package(path)
    assert report['status'] == 'PASS'
    assert 'SUPPLEMENTAL_RESEARCH_EVIDENCE_PENDING' in report['production_blockers']
    assert report['supplemental_source_sets'][0]['status'] == 'PENDING'
    assert calls == [(package['research_source_sets'][0], {'chapter': 89, 'mode': 'RESEARCH'})]
    shutil.copytree(ROOT / 'data/writing/prompts', root / 'data/writing/prompts')
    scene = root / 'data/planning/scenes/scene.json'
    scene.parent.mkdir(parents=True)
    scene.write_bytes(canonical_bytes({'kind': 'SCENE_SKELETON', 'chapter': 89, 'id': 'scene'}))
    plan = root / 'data/planning/chapters/ch89.json'
    plan.parent.mkdir(parents=True)
    plan.write_bytes(canonical_bytes({'chapter': 89, 'scenes': [{'ref': 'data/planning/scenes/scene.json'}]}))
    rendered = PromptRenderer(root).draft(path, 89)
    assert binding(root, 'supplement.json') in rendered['inputs']
    expected = deepcopy(report['supplemental_source_sets'])
    for selected in expected:
        selected.pop('paths')
    assert rendered['task']['supplemental_source_sets'] == expected


@pytest.mark.parametrize('scope', [None, 'BACKTEST', 'PRODUCTION'])
def test_new_sets_cannot_leak_into_production_or_backtest(writing_repo, scope):
    root, _, path, _, package = writing_repo
    select_set(root, path, package)
    if scope is None:
        del package['operation_scope']
    else:
        package['operation_scope'] = scope
    (root / path).write_bytes(canonical_bytes(package))
    with pytest.raises(AssetError):
        LiteraryInputs(AssetCatalog.from_repo(root)).package(path)
    with pytest.raises(AssetError, match='NOT_PRODUCTION'):
        LiteraryInputs(AssetCatalog.from_repo(root)).package(path, production=True)


def test_bad_integrity_is_rejected_not_downranked_to_pending(writing_repo, monkeypatch):
    root, _, path, _, package = writing_repo
    select_set(root, path, package)
    report = fake_report(root)
    report.update(integrity_status='FAIL', findings=['STALE_RESEARCH_BINDING'])
    monkeypatch.setattr('rcwh.provenance.research_inputs.ResearchSourceInputs.report', lambda *args, **kwargs: report)
    with pytest.raises(AssetError, match='STALE_RESEARCH_BINDING'):
        LiteraryInputs(AssetCatalog.from_repo(root)).package(path)


def test_duplicate_records_across_sets_are_rejected(writing_repo, monkeypatch):
    root, _, path, _, package = writing_repo
    select_set(root, path, package)
    (root / 'supplement2.json').write_bytes(b'{}')
    package['research_source_sets'].append(binding(root, 'supplement2.json'))
    (root / path).write_bytes(canonical_bytes(package))
    report = fake_report(root)
    report['records']['sources'] = [{'id': 'new-source'}]
    monkeypatch.setattr('rcwh.provenance.research_inputs.ResearchSourceInputs.report', lambda *args, **kwargs: deepcopy(report))
    with pytest.raises(AssetError, match='DUPLICATE_SUPPLEMENTAL_RECORD'):
        LiteraryInputs(AssetCatalog.from_repo(root)).package(path)
