"""Writing v2 custody survives governance; live admission is a separate decision."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation import render as render_module
from rcwh.generation.dependencies import WritingDependencies
from rcwh.generation.lineage import current_compatibility, freeze_history, historical_artifact_paths, receipt_path
from rcwh.generation.records import binding, store
from rcwh.generation.render import PromptRenderer
from rcwh.generation.runner import Budget, ReplayRunner
from rcwh.generation.session import import_draft, prepare_request, verify_prepared_request
from rcwh.generation.snapshots import InputSnapshot, freeze_inputs
from rcwh.generation.writing import diff_report, feedback_report, generate, load_draft, revision_prompt
from test_generation import response, root
from test_session_generation import session_root, prepare, imported, saved


@pytest.fixture
def writing_root(session_root, monkeypatch):
    monkeypatch.setattr('rcwh.generation.render.DEFAULT_RENDERER_VERSION', 2)
    return session_root


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def test_new_default_does_not_bind_governance_or_unselected_domain_files(writing_root):
    root = writing_root
    write(root, 'data/project/closure_roots.json', {'selected': []})
    write(root, 'data/project/implementation.json', {'progress': 1})
    write(root, 'data/world/unselected.json', {'unselected': 1})
    packet = prepare(root)
    assert packet['schema_version'] == packet['renderer_version'] == 2
    assert 'input_readiness' not in packet['task']
    assert packet['readiness']['blockers'] == ['CORPUS_HUMAN_LAYER_AUDIT_PENDING']
    assert not any(ref['path'].startswith('data/project/') for ref in packet['inputs'])
    first = imported(root)
    before = load_draft(root, first['draft']['path'])
    write(root, 'data/project/closure_roots.json', {'selected': ['new audit']})
    write(root, 'data/project/new-governance.json', {'new': True})
    write(root, 'data/world/unselected.json', {'unselected': 2})
    assert verify_prepared_request(root, packet)['task'] == packet['task']
    assert load_draft(root, first['draft']['path']) == before
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'CURRENT'


@pytest.mark.parametrize('path', ['authored.txt', 'request.json', 'data/world/version.json', 'package.json',
                                 'data/writing/prompts/author-v1.md'])
def test_historical_snapshot_survives_mutable_input_retirement(writing_root, path):
    root = writing_root
    prepare(root)
    first = imported(root)
    before = load_draft(root, first['draft']['path'])
    (root / path).unlink()
    assert load_draft(root, first['draft']['path']) == before
    report = current_compatibility(root, first['draft']['path'])
    if path in {'authored.txt', 'request.json'}:
        assert report['compatibility'] == 'CURRENT'
    else:
        assert report['compatibility'] == 'STALE'


def test_relevant_edit_separates_history_from_current_and_blocks_new_import(writing_root):
    root = writing_root
    packet = prepare(root)
    first = imported(root)
    write(root, 'data/world/version.json', {'id': 'world-v2'})
    assert load_draft(root, first['draft']['path'])[0]['schema_version'] == 2
    report = current_compatibility(root, first['draft']['path'])
    assert report['status'] == 'FAIL' and report['compatibility'] == 'STALE'
    assert report['changed_inputs'] == ['data/world/version.json']
    with pytest.raises(ValueError, match='stale'):
        verify_prepared_request(root, packet)


def test_new_selected_scene_dependency_is_detected_without_a_directory_binding(writing_root):
    root = writing_root
    packet = prepare(root)
    first = imported(root)
    write(root, 'data/planning/scenes/new.json', {'id': 'new', 'chapter': 89, 'kind': 'SCENE_SKELETON'})
    write(root, 'data/planning/chapters/ch89.json', {'chapter': 89, 'scenes': [
        {'ref': 'data/planning/scenes/s.json'}, {'ref': 'data/planning/scenes/new.json'}]})
    with pytest.raises(ValueError, match='stale'):
        verify_prepared_request(root, packet)
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'STALE'
    assert load_draft(root, first['draft']['path'])[0]['task'] == packet['task']


@pytest.mark.parametrize('target', ['candidate', 'prepared_request', 'run', 'snapshot', 'blob'])
def test_archived_custody_tampering_still_fails(writing_root, target):
    root = writing_root
    prepare(root)
    first = imported(root)
    if target == 'snapshot':
        ref = first['input_snapshot']
    elif target == 'blob':
        frozen = InputSnapshot(root, first['input_snapshot'])
        ref = next(iter(frozen.entries.values()))
    else:
        ref = first[target]
    (root / ref['path']).write_bytes(b'corrupted historical object')
    with pytest.raises(ValueError, match='stale'):
        load_draft(root, first['draft']['path'])


def test_rehashed_snapshot_cannot_omit_a_declared_dependency(writing_root):
    root = writing_root
    prepare(root)
    first = imported(root)
    draft, _ = load_draft(root, first['draft']['path'])
    run = json.loads((root / draft['run']['path']).read_bytes())
    value = json.loads((root / first['input_snapshot']['path']).read_bytes())
    value['entries'].pop()
    ref = store(root, 'artifacts/writing-inputs/manifests', value)
    draft['input_snapshot'] = run['input_snapshot'] = ref
    draft['run'] = store(root, 'artifacts/author-runs', run)
    draft['authors'][0]['run'] = draft['run']
    forged = store(root, 'data/writing/drafts/ch89', draft)
    with pytest.raises(ValueError, match='manifest mismatch|missing historical'):
        load_draft(root, forged['path'])


def test_revision_uses_frozen_parent_and_does_not_flatten_legacy_inputs(writing_root):
    root = writing_root
    prepare(root)
    first = imported(root)
    original, text = load_draft(root, first['draft']['path'])
    report = feedback_report(root, first['draft']['path'])
    feedback = store(root, 'data/writing/feedback', report)
    (root / 'package.json').unlink()
    (root / 'data/world/version.json').unlink()
    packet = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    assert packet['schema_version'] == 2
    assert not {ref['path'] for ref in packet['inputs']} & {ref['path'] for ref in original['inputs']}
    saved(root, 'revision.json', packet)
    (root / 'revised.txt').write_text('甲摇头。\n\n乙独自退了。')
    second = import_draft(root, 'revised.txt', 'revision.json', session_id='revision', session_model_label='declared')
    (root / feedback['path']).unlink()
    assert load_draft(root, second['draft']['path'])[0]['parent'] == first['draft']
    assert diff_report(root, first['draft']['path'], second['draft']['path'])['paragraph_change_reading_packet']
    assert current_compatibility(root, second['draft']['path'])['compatibility'] == 'STALE'


def test_legacy_migration_preserves_originals_and_then_ignores_governance_drift(session_root, monkeypatch):
    root = session_root
    write(root, 'data/project/closure_roots.json', {'records': []})
    prepare(root)
    first = imported(root)
    originals = {field: (root / first[field]['path']).read_bytes() for field in ['draft', 'candidate', 'run', 'prepared_request']}
    monkeypatch.setattr('rcwh.generation.render.DEFAULT_RENDERER_VERSION', 2)
    frozen = freeze_history(root, first['draft']['path'])
    assert frozen['migration'] == 'FROZEN_WITHOUT_REWRITING'
    assert freeze_history(root, first['draft']['path'])['migration'] == 'ALREADY_FROZEN'
    for field, raw in originals.items():
        assert (root / first[field]['path']).read_bytes() == raw
    write(root, 'data/project/closure_roots.json', {'records': ['new admission']})
    write(root, 'data/project/implementation.json', {'progress': 'changed'})
    assert load_draft(root, first['draft']['path'])[0]['schema_version'] == 1
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'CURRENT'
    feedback = store(root, 'data/writing/feedback', feedback_report(root, first['draft']['path']))
    revision = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    assert revision['schema_version'] == 2
    assert all(not r['path'].startswith('data/project/') for r in revision['inputs'])


def test_migration_never_waives_stale_legacy_bindings(session_root):
    root = session_root
    write(root, 'data/project/closure_roots.json', {'records': []})
    prepare(root)
    first = imported(root)
    write(root, 'data/project/closure_roots.json', {'records': ['changed']})
    with pytest.raises(ValueError, match='stale'):
        freeze_history(root, first['draft']['path'])
    draft = json.loads((root / first['draft']['path']).read_bytes())
    assert not (root / receipt_path(draft)).exists()


def test_selected_records_do_not_bind_other_records_in_the_same_file(root):
    source = {'id': 'source:selected', 'text': 'selected'}
    unrelated = {'id': 'source:other', 'text': 'other'}
    graph = type('Graph', (), {'sources': {source['id']: source, unrelated['id']: unrelated}})()
    catalog = type('Catalog', (), {'assets': {}})()
    package = {'assets': [], 'sources': [{'source_ref': source['id']}]}
    first = WritingDependencies(root, catalog, graph)
    first.selected(package, {})
    unrelated['text'] = 'changed independently'
    second = WritingDependencies(root, catalog, graph)
    second.selected(package, {})
    assert first.manifest_records() == second.manifest_records()
    assert first.files == second.files == set()


def test_snapshot_blobs_are_deduplicated_and_never_overwritten(root):
    (root / 'same.json').write_bytes((root / 'input.json').read_bytes())
    refs = [binding(root, 'input.json'), binding(root, 'same.json')]
    first = freeze_inputs(root, refs)
    assert freeze_inputs(root, refs) == first
    frozen = InputSnapshot(root, first)
    frozen.verify(refs)
    assert len(set(ref['path'] for ref in frozen.entries.values())) == 1
    blob = next(iter(frozen.entries.values()))
    (root / blob['path']).write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='stale'):
        freeze_inputs(root, refs)


def test_provider_path_also_preserves_history_and_reports_current_inputs(writing_root):
    root = writing_root
    first = generate(root, ReplayRunner([response()]), PromptRenderer(root).draft('package.json', 89), Budget(), chapter=89)
    write(root, 'data/world/version.json', {'changed': True})
    assert load_draft(root, first['draft']['path'])[1]
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'STALE'


def test_producer_observations_are_archived_instead_of_rebound_to_current_paths(root):
    (root / 'parent.txt').write_bytes(b'original carrier')
    parent_id, manifest_id = 'asset:fixture:parent', 'asset:fixture:manifest'
    write(root, 'manifest.json', {'dependency_lock': {'path': 'retired.lock.json', 'sha256': '0' * 64},
                                 'input': {'asset_ref': parent_id}})
    files = {parent_id: 'parent.txt', manifest_id: 'manifest.json'}
    class Catalog:
        assets = {parent_id: {'derived_from': []}, manifest_id: {'derived_from': [parent_id], 'roles': ['REFERENCE']}}
        def resolve(self, ref):
            path = root / files[ref]
            return type('Asset', (), {'path': path, 'sha256': digest(path.read_bytes())})()
    catalog = Catalog()
    before = WritingDependencies(root, catalog, None)
    before.asset(manifest_id)
    assert before.files == {'parent.txt', 'manifest.json'}
    catalog.assets[manifest_id]['roles'].append('NEW_CATALOG_TAG')
    after = WritingDependencies(root, catalog, None)
    after.asset(manifest_id)
    assert before.manifest_records() == after.manifest_records()


def test_readiness_is_reported_without_changing_author_context(writing_root, monkeypatch):
    root = writing_root
    packet = prepare(root)
    original = render_module.LiteraryInputs
    class ChangedReadiness:
        def __init__(self, catalog): self.inputs = original(catalog)
        def package(self, path):
            report = self.inputs.package(path)
            report['production_blockers'] = ['DIFFERENT_CURRENT_ADMISSION']
            return report
    monkeypatch.setattr('rcwh.generation.render.LiteraryInputs', ChangedReadiness)
    assert verify_prepared_request(root, packet)['task'] == packet['task']


def test_current_renderer_changes_do_not_reinterpret_historical_requests(writing_root, monkeypatch):
    root = writing_root
    prepare(root)
    first = imported(root)
    def changed(*args, **kwargs):
        raise ValueError('renderer behavior changed')
    monkeypatch.setattr(PromptRenderer, 'draft', changed)
    assert load_draft(root, first['draft']['path'])[1]
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'STALE'


def test_current_symlink_cannot_replace_a_frozen_blob_but_can_retire_a_logical_path(writing_root):
    root = writing_root
    prepare(root)
    first = imported(root)
    original = root / 'data/world/version.json'
    original.unlink()
    original.symlink_to(root / 'input.json')
    assert load_draft(root, first['draft']['path'])[1]
    assert current_compatibility(root, first['draft']['path'])['compatibility'] == 'STALE'
    frozen = InputSnapshot(root, first['input_snapshot'])
    blob = root / next(iter(frozen.entries.values()))['path']
    blob.unlink()
    blob.symlink_to(root / 'input.json')
    with pytest.raises(ValueError, match='symlink'):
        load_draft(root, first['draft']['path'])


def test_check_cli_reports_history_and_current_separately(writing_root, capsys):
    import argparse
    from rcwh.application.write import add_commands, command

    root = writing_root
    prepare(root)
    first = imported(root)
    write(root, 'data/world/version.json', {'changed': True})
    parser = argparse.ArgumentParser()
    parser.add_argument('--root')
    add_commands(parser.add_subparsers())
    args = parser.parse_args(['--root', str(root), 'write', 'check', first['draft']['path'], '--current'])
    assert command(args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['historical_integrity']['status'] == 'PASS'
    assert report['current_compatibility']['compatibility'] == 'STALE'


def test_provider_revision_preserves_notes_and_frozen_parent_after_retirement(writing_root):
    root = writing_root
    first = generate(root, ReplayRunner([response()]), PromptRenderer(root).draft('package.json', 89), Budget(), chapter=89)
    feedback = store(root, 'feedback', feedback_report(root, first['draft']['path']))
    (root / 'notes.txt').write_text('Keep the original causal sequence.', encoding='utf-8')
    (root / 'data/world/version.json').unlink()
    rendered = revision_prompt(root, first['draft']['path'], feedback['path'], 'notes.txt')
    revised = generate(root, ReplayRunner([response('甲只摇头。乙退了。', identity='msg-revised')]), rendered, Budget(), chapter=89,
                       parent=first['draft'], feedback=feedback)
    (root / 'notes.txt').unlink()
    draft, text = load_draft(root, revised['draft']['path'])
    assert text and draft['task']['editorial_notes'] == 'Keep the original causal sequence.'
    assert current_compatibility(root, revised['draft']['path'])['compatibility'] == 'STALE'


def test_provider_prompt_digest_is_verified(writing_root):
    root = writing_root
    first = generate(root, ReplayRunner([response()]), PromptRenderer(root).draft('package.json', 89), Budget(), chapter=89)
    draft = json.loads((root / first['draft']['path']).read_bytes())
    draft['prompt_sha256'] = '0' * 64
    write(root, first['draft']['path'], draft)
    with pytest.raises(ValueError, match='prompt digest'):
        load_draft(root, first['draft']['path'])


def test_prompt_template_change_preserves_history_but_changes_current_basis(writing_root):
    root = writing_root
    prepare(root)
    first = imported(root)
    template = root / 'data/writing/prompts/author-v1.md'
    template.write_text(template.read_text() + '\nNew writing instruction.\n')
    assert load_draft(root, first['draft']['path'])[1]
    report = current_compatibility(root, first['draft']['path'])
    assert report['compatibility'] == 'STALE'
    assert report['changed_inputs'] == ['data/writing/prompts/author-v1.md']


def test_physical_closure_follows_frozen_objects_after_logical_input_retirement(writing_root):
    root = writing_root
    prepare(root)
    first = imported(root)
    (root / 'data/world/version.json').unlink()
    draft, _ = load_draft(root, first['draft']['path'])
    paths = historical_artifact_paths(root, draft)
    assert 'data/world/version.json' not in paths
    assert first['input_snapshot']['path'] in paths
    assert any(path.startswith('artifacts/writing-inputs/blobs/') for path in paths)
    assert all((root / path).is_file() for path in paths)


def test_migrated_legacy_revision_still_checks_its_historical_parent(session_root):
    root = session_root
    write(root, 'data/project/closure_roots.json', {'records': []})
    prepare(root)
    first = imported(root)
    feedback = store(root, 'feedback', feedback_report(root, first['draft']['path']))
    packet = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    assert packet['schema_version'] == 1
    saved(root, 'revision.json', packet)
    (root / 'revised.txt').write_text('甲摇头。乙独自退了。')
    second = import_draft(root, 'revised.txt', 'revision.json', session_id='revision', session_model_label='declared')
    freeze_history(root, second['draft']['path'])
    write(root, 'data/project/closure_roots.json', {'records': ['new governance']})
    assert load_draft(root, second['draft']['path'])[1]
    (root / first['draft']['path']).write_bytes(b'corrupt parent')
    with pytest.raises(ValueError):
        load_draft(root, second['draft']['path'])
