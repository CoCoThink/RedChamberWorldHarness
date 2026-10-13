import argparse
from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest, verified_author_model
from rcwh.generation.records import binding, store
from rcwh.generation.render import PromptRenderer, request_for
from rcwh.generation.runner import Budget, ReplayRunner
from rcwh.generation.session import (
    EXECUTION_BASIS, import_draft, prepare_request, prepared_request_integrity_report, verify_prepared_request,
)
from rcwh.generation.writing import diff_report, feedback_report, generate, load_draft, revision_prompt
from test_generation import response, root


@pytest.fixture
def session_root(root, monkeypatch):
    package = {'chapter': 89, 'exemplar_set': None, 'world': [], 'plan': [], 'sources': []}
    for path, value in {
        'examples.json': {}, 'manifest.json': {}, 'data/world/version.json': {'id': 'world'},
        'data/planning/chapters/ch89.json': {'chapter': 89, 'scenes': [{'ref': 'data/planning/scenes/s.json'}]},
        'data/planning/scenes/s.json': {'id': 's', 'chapter': 89, 'kind': 'SCENE_SKELETON'},
    }.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(canonical_bytes(value))
    package['exemplar_set'] = binding(root, 'examples.json')
    package['world'] = [binding(root, 'data/world/version.json')]
    (root / 'package.json').write_bytes(canonical_bytes(package))
    report = {'status': 'PASS', 'findings': [], 'scope': 'FROZEN_RESEARCH_WRITING_INPUTS',
              'production_blockers': ['CORPUS_HUMAN_LAYER_AUDIT_PENDING'], 'package': package, 'sources': [],
              'exemplars': {'spec': {'manifest_ref': 'asset:sha256:' + 'a'*64, 'dataset_ref': 'dataset'}, 'segments': []}}
    monkeypatch.setattr('rcwh.generation.render.AssetCatalog.from_repo', lambda root: type('Catalog', (), {
        'resolve': lambda self, ref: type('Asset', (), {'path': root / 'manifest.json'})()})())
    monkeypatch.setattr('rcwh.generation.render.LiteraryInputs', lambda catalog: type('Inputs', (), {
        'package': lambda self, path: deepcopy(report)})())
    monkeypatch.setattr('rcwh.graph.ProvenanceGraph.from_repo', lambda root: type('Graph', (), {'sources': {}})())
    monkeypatch.setattr('rcwh.generation.writing.CharacterKnowledgeRuntime.from_repo', lambda root: None)
    monkeypatch.setattr('rcwh.generation.writing.continuity_report', lambda root, chapter: {'status': 'PENDING'})
    return root


def saved(root, path, value):
    (root / path).write_bytes(canonical_bytes(value))
    return path


def prepare(root, **kwargs):
    packet = prepare_request(root, package_path='package.json', chapter=89, **kwargs)
    saved(root, 'request.json', packet)
    (root / 'authored.txt').write_bytes('甲说道：“不知。”\r\n\r\n乙退了。\r\n'.encode())
    return packet


def imported(root, **kwargs):
    return import_draft(root, 'authored.txt', 'request.json', session_id='session-test',
                        session_model_label='configured writer (unverified)', **kwargs)


def test_exact_session_import_research_pending_package_no_provider_or_human_claims(session_root):
    root = session_root
    packet = prepare(root)
    result = imported(root)
    draft, text = load_draft(root, result['draft']['path'])
    run = json.loads((root / result['run']['path']).read_bytes())
    assert packet['task']['input_readiness']['blockers'] == ['CORPUS_HUMAN_LAYER_AUDIT_PENDING']
    assert text.encode() == (root / 'authored.txt').read_bytes()
    assert draft['execution_basis'] == result['execution_basis'] == run['execution_basis'] == EXECUTION_BASIS
    assert result['qualification'] == 'RESEARCH_ONLY' and result['formal_eligibility'] is False
    assert result['human_qualification'] is False and draft['authors'][0]['kind'] == 'MODEL'
    assert draft['authors'][0]['principal_id'] == 'session:session-test'
    assert run['session_configured_model'] == {'label': 'configured writer (unverified)', 'basis': 'UNVERIFIED_DECLARATION'}
    assert run['session_configured_model']['label'] != packet['request']['model']
    forbidden = {'raw_run', 'provider', 'sdk_version', 'usage', 'request_id', 'response', 'model', 'billed_tokens'}
    assert not forbidden.intersection(run) and not forbidden.intersection(draft)
    assert not (root / 'artifacts/runs').exists()
    assert run['package'] == packet['package'] == binding(root, 'package.json')
    assert (root / run['prepared_request']['path']).read_bytes() == (root / 'request.json').read_bytes()
    assert run['request_sha256'] == digest(canonical_bytes(packet['request']))
    for ref in (result['draft'], result['run'], result['prepared_request'], result['candidate']):
        assert Path(ref['path']).stem == ref['sha256'] == digest((root / ref['path']).read_bytes())
    with pytest.raises(ValueError, match='invalid model run'):
        verified_author_model(root, draft['authors'][0], text.encode())


@pytest.mark.parametrize('text', [
    "正文\n\nexpanded=[]\nfor i,p in enumerate(paras):\n expanded.append(p)",
    "\n\n".join(f"平儿将钥匙重新系紧，绳结太短，拆开一次便要重新打。这是第{i}次清点后的细小阻滞，仍需下一只手来接。" for i in range(20)),
])
def test_failed_prose_integrity_rejected_before_session_files_are_written(session_root, text):
    root = session_root
    prepare(root)
    (root / 'authored.txt').write_text(text)
    with pytest.raises(ValueError, match='session prose integrity failed'):
        imported(root)
    assert not (root / 'data/writing/drafts').exists()
    assert not (root / 'artifacts/candidates').exists()


def test_session_feedback_revision_lineage_and_diff_are_offline(session_root):
    root = session_root
    prepare(root, route='direct')
    first = imported(root)
    report = feedback_report(root, first['draft']['path'])
    assert report['formal_eligibility'] is False and report['semantic_runs'] == []
    assert report['checks'][0]['qualification'] == 'FEEDBACK_ONLY'
    feedback = store(root, 'data/writing/feedback', report)
    (root / 'notes.txt').write_text('只改第一段。')
    revision = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'], notes_path='notes.txt')
    saved(root, 'revision.json', revision)
    (root / 'revised.txt').write_bytes('甲只摇头。\r\n\r\n乙退了。\r\n'.encode())
    second = import_draft(root, 'revised.txt', 'revision.json', session_id='session-test',
                          session_model_label='configured writer', parent_path=first['draft']['path'], feedback_path=feedback['path'])
    draft, _ = load_draft(root, second['draft']['path'])
    assert draft['parent'] == first['draft'] and draft['feedback'] == feedback and draft['route'] == 'direct'
    assert draft['authors'][0]['principal_id'] == load_draft(root, first['draft']['path'])[0]['authors'][0]['principal_id']
    assert binding(root, 'notes.txt') in draft['inputs']
    assert revision['package'] == binding(root, 'package.json')
    diff = diff_report(root, first['draft']['path'], second['draft']['path'])
    assert diff['paragraph_change_reading_packet'] and '甲只摇头' in diff['unified_diff']
    assert diff['qualification'] == 'FEEDBACK_ONLY'
    report2 = feedback_report(root, second['draft']['path'])
    assert report2['candidate'] == second['candidate']
    # Existing provider/replay revision remains compatible with a session parent.
    third = generate(root, ReplayRunner([response('乙独自去了。', identity='msg3')]),
                     revision_prompt(root, second['draft']['path'], store(root, 'data/writing/feedback', report2)['path']),
                     Budget(), chapter=89, parent=second['draft'])
    assert load_draft(root, third['draft']['path'])[0]['parent'] == second['draft']


def test_session_revision_accepts_verified_raw_run_parent(session_root):
    root = session_root
    rendered = PromptRenderer(root).draft('package.json', 89)
    first = generate(root, ReplayRunner([response()]), rendered, Budget(), chapter=89)
    feedback = store(root, 'data/writing/feedback', feedback_report(root, first['draft']['path']))
    request = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    saved(root, 'request.json', request)
    (root / 'authored.txt').write_text('另写一段。')
    second = imported(root)
    assert load_draft(root, second['draft']['path'])[0]['parent'] == first['draft']


@pytest.mark.parametrize('tamper', ['request', 'task', 'missing_input', 'template', 'prompt_hash', 'chapter', 'raw_run', 'provider'])
def test_rehashed_prepared_request_forgery_is_rejected_before_publication(session_root, tamper):
    root = session_root
    packet = prepare(root)
    if tamper == 'request':
        packet['request']['system'] += '\nForged instruction'
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
    elif tamper == 'task':
        packet['task']['target_characters'] = 3
        packet['request']['messages'][0]['content'] = canonical_bytes(packet['task']).decode()
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
    elif tamper == 'missing_input':
        packet['inputs'].pop()
    elif tamper == 'template':
        packet['template'] = binding(root, 'input.json')
    elif tamper == 'prompt_hash':
        packet['prompt_sha256'] = '0' * 64
    elif tamper == 'chapter':
        packet['chapter'] = 88
    else:
        packet[tamper] = binding(root, 'input.json') if tamper == 'raw_run' else 'anthropic'
    saved(root, 'request.json', packet)
    with pytest.raises(ValueError, match='prepared request'):
        imported(root)
    assert not (root / 'artifacts').exists()


@pytest.mark.parametrize('path', ['data/world/version.json', 'package.json', 'data/writing/prompts/author-v1.md'])
def test_stale_inputs_and_templates_are_rejected(session_root, path):
    root = session_root
    prepare(root)
    (root / path).write_bytes(b'changed')
    with pytest.raises(ValueError, match='stale'):
        imported(root)
    assert not (root / 'artifacts').exists()


def test_new_renderer_dependency_is_not_silently_missing_from_manifest(session_root):
    root = session_root
    prepare(root)
    path = root / 'data/world/new.json'
    path.write_bytes(b'{}')
    with pytest.raises(ValueError, match='current renderer'):
        imported(root)


@pytest.mark.parametrize('field', ['raw_run', 'provider', 'sdk_version', 'usage', 'billed_tokens', 'request_id', 'model'])
def test_session_run_rejects_provider_provenance_even_when_rehashed(session_root, field):
    root = session_root
    prepare(root)
    result = imported(root)
    draft, _ = load_draft(root, result['draft']['path'])
    run = json.loads((root / result['run']['path']).read_bytes())
    run[field] = {} if field in {'usage', 'raw_run', 'model'} else 'fabricated'
    draft['run'] = store(root, 'artifacts/author-runs', run)
    forged = store(root, 'data/writing/drafts/ch89', draft)
    with pytest.raises(ValueError, match='invalid session author run'):
        load_draft(root, forged['path'])


@pytest.mark.parametrize('field', ['task', 'prompt_sha256', 'authors', 'raw_run', 'human_qualification'])
def test_session_draft_rejects_rehashed_record_tampering(session_root, field):
    root = session_root
    prepare(root)
    first = imported(root)
    draft, _ = load_draft(root, first['draft']['path'])
    if field == 'task':
        draft['task']['target_characters'] = 1
    elif field == 'authors':
        draft['authors'][0]['principal_id'] = 'session:someone-else'
    elif field == 'raw_run':
        draft['raw_run'] = binding(root, 'input.json')
    elif field == 'human_qualification':
        draft[field] = True
    else:
        draft[field] = '0' * 64
    forged = store(root, 'data/writing/drafts/ch89', draft)
    with pytest.raises(ValueError):
        load_draft(root, forged['path'])


@pytest.mark.parametrize('path', ['authored.txt', 'request.json', 'data/world/version.json'])
def test_loaded_session_draft_rejects_stale_source_and_context(session_root, path):
    root = session_root
    prepare(root)
    first = imported(root)
    (root / path).write_bytes(b'changed')
    with pytest.raises(ValueError, match='stale'):
        load_draft(root, first['draft']['path'])


@pytest.mark.parametrize('text_path,request_path', [('../outside.txt', 'request.json'), ('authored.txt', '../outside.json'),
                                                    ('/tmp/prose', 'request.json'), ('linked.txt', 'request.json')])
def test_import_rejects_external_and_symlink_paths(session_root, text_path, request_path):
    root = session_root
    prepare(root)
    (root / 'linked.txt').symlink_to(root / 'authored.txt')
    with pytest.raises(ValueError):
        import_draft(root, text_path, request_path, session_id='session-test', session_model_label='configured')
    assert not (root / 'artifacts').exists()


def test_content_addressed_duplicate_is_reused_without_overwrite_and_conflicts_fail(session_root):
    root = session_root
    prepare(root)
    first = imported(root)
    assert imported(root) == first
    (root / first['candidate']['path']).write_bytes(b'corrupted existing file')
    with pytest.raises(ValueError, match='stale|conflict'):
        imported(root)
    assert (root / first['candidate']['path']).read_bytes() == b'corrupted existing file'
    assert not list(root.rglob('.generation-*'))


@pytest.fixture
def observed_session(session_root, monkeypatch):
    """Synthetic source report with the same custody/diff shape as the ch95 report."""
    extractor = {'name': 'rcwh-extraction', 'version': 1, 'code_sha256': 'a' * 64,
                 'package_version': None, 'python': 'CPython 3.14.6'}
    registered = {**extractor, 'code_sha256': 'b' * 64, 'python': 'CPython 3.12.13'}
    lock = {'path': 'requirements/extraction.lock.json', 'sha256': 'c' * 64}
    source = {'record': {'id': 'src:observed', 'excerpt': 'unchanged carrier excerpt', 'locator': 'unit:1'},
              'verification': {'status': 'PASS', 'verification_report': {
                  'status': 'VERIFIED', 'rebuild': {
                      'status': 'PASS', 'scope': 'EXTRACTION_CONTENT_REBUILD', 'manifest_ref': 'asset:sha256:' + 'd' * 64,
                      'output_sha256': 'e' * 64, 'unit_count': 1,
                      'registered_toolchain': {'extractor': deepcopy(registered), 'dependency_lock': deepcopy(lock)},
                      'current_toolchain': {'extractor': deepcopy(extractor), 'dependency_lock': deepcopy(lock)},
                      'toolchain_diff': {'extractor': {'registered': deepcopy(registered), 'current': deepcopy(extractor)}}}}}}
    original = PromptRenderer.draft
    def draft(renderer, *args, **kwargs):
        rendered = original(renderer, *args, **kwargs)
        task = deepcopy(rendered['task'])
        task['sources'] = [deepcopy(source)]
        return renderer.render('author-v1', task, rendered['inputs'])
    monkeypatch.setattr(PromptRenderer, 'draft', draft)
    return session_root, source


def observer_parents(source):
    rebuild = source['verification']['verification_report']['rebuild']
    return rebuild['current_toolchain']['extractor'], rebuild['toolchain_diff']['extractor']['current']


def set_observer_python(source, version):
    for parent in observer_parents(source):
        parent['python'] = version


def rehash_frozen_packet(root, packet):
    template = Path(packet['template']['path']).stem
    rendered = PromptRenderer(root).render(template, packet['task'], packet['inputs'])
    packet['prompt_sha256'] = rendered['prompt_sha256']
    packet['request'] = request_for(rendered, Budget(**packet['budget']), packet['request']['model'])
    packet['request_sha256'] = digest(canonical_bytes(packet['request']))


@pytest.mark.parametrize('stored,current', [('CPython 3.14.6', 'CPython 3.12.13'), ('CPython 3.12.13', 'CPython 3.14.6')])
def test_only_two_runtime_python_observations_vary_and_frozen_bytes_are_retained(observed_session, stored, current):
    root, source = observed_session
    set_observer_python(source, stored)
    packet = prepare(root)
    frozen_bytes = (root / 'request.json').read_bytes()
    frozen_packet = deepcopy(packet)
    assert prepared_request_integrity_report(root, packet)['runtime_observation_variations'] == []
    set_observer_python(source, current)
    fresh = verify_prepared_request(root, packet)
    report = prepared_request_integrity_report(root, packet)
    prefix = 'task.sources[0].verification.verification_report.rebuild.'
    assert report['runtime_observation_variations'] == [
        {'path': prefix + 'current_toolchain.extractor.python', 'stored': stored, 'current': current},
        {'path': prefix + 'toolchain_diff.extractor.current.python', 'stored': stored, 'current': current}]
    assert report['stored_prompt_sha256'] == packet['prompt_sha256'] != report['fresh_prompt_sha256']
    assert report['stored_request_sha256'] == packet['request_sha256'] != report['fresh_request_sha256']
    assert fresh == PromptRenderer(root).draft('package.json', 89)
    assert prepare_request(root, package_path='package.json', chapter=89)['task'] == fresh['task']
    assert packet == frozen_packet and (root / 'request.json').read_bytes() == frozen_bytes
    result = imported(root)
    draft, _ = load_draft(root, result['draft']['path'])
    run = json.loads((root / result['run']['path']).read_bytes())
    assert (root / result['prepared_request']['path']).read_bytes() == frozen_bytes
    assert draft['task'] == packet['task'] and run['request_sha256'] == packet['request_sha256']
    assert draft['prompt_sha256'] == run['prompt_sha256'] == packet['prompt_sha256']
    assert not {'usage', 'request_id', 'elapsed', 'consumed', 'response'}.intersection(report)


@pytest.mark.parametrize('tamper', ['prompt_hash', 'fresh_prompt_hash', 'request_hash', 'task', 'request',
                                   'task_body_rehashed', 'system_rehashed', 'messages_rehashed', 'params_rehashed'])
def test_runtime_drift_does_not_waive_frozen_envelope_or_hash_forgery(observed_session, tamper):
    root, source = observed_session
    packet = prepare(root)
    set_observer_python(source, 'CPython 3.12.13')
    if tamper == 'prompt_hash':
        packet['prompt_sha256'] = '0' * 64
    elif tamper == 'fresh_prompt_hash':
        packet['prompt_sha256'] = PromptRenderer(root).draft('package.json', 89)['prompt_sha256']
    elif tamper == 'request_hash':
        packet['request_sha256'] = '0' * 64
    elif tamper == 'task':
        set_observer_python(packet['task']['sources'][0], 'CPython 3.13.1')
    elif tamper == 'request':
        packet['request']['system'] += '\nForged instruction'
    elif tamper == 'task_body_rehashed':
        packet['task']['target_characters'] = 1
        rehash_frozen_packet(root, packet)
    else:
        if tamper == 'system_rehashed':
            packet['request']['system'] += '\nForged instruction'
        elif tamper == 'messages_rehashed':
            packet['request']['messages'][0]['content'] += ' '
        else:
            packet['request']['max_tokens'] -= 1
        packet['prompt_sha256'] = digest(canonical_bytes({key: packet['request'][key] for key in ('system', 'messages')}))
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
    saved(root, 'request.json', packet)
    with pytest.raises(ValueError, match='prepared request'):
        imported(root)
    assert not (root / 'artifacts').exists()


@pytest.mark.parametrize('version', ['PyPy 3.12.13', 'CPython 2.7.18', 'CPython 3.12', 'CPython 3.12.13rc1',
                                    'CPython 3.12.13\n', 'CPython 3.12.13 arbitrary', 31213, None])
@pytest.mark.parametrize('field', [0, 1])
@pytest.mark.parametrize('side', ['stored', 'fresh'])
def test_runtime_python_allowance_rejects_non_version_values(observed_session, version, field, side):
    root, source = observed_session
    packet = prepare(root)
    set_observer_python(source, 'CPython 3.12.13')
    selected = packet['task']['sources'][0] if side == 'stored' else source
    observer_parents(selected)[field]['python'] = version
    if side == 'stored':
        rehash_frozen_packet(root, packet)
    with pytest.raises(ValueError, match='prepared request'):
        verify_prepared_request(root, packet)


@pytest.mark.parametrize('side', ['stored', 'fresh'])
@pytest.mark.parametrize('path,value', [
    (('record', 'excerpt'), 'changed excerpt'), (('record', 'locator'), 'unit:2'),
    (('record', 'python'), 'CPython 3.12.13'), (('verification', 'status'), 'FAIL'),
    (('verification', 'verification_report', 'status'), 'UNVERIFIED'),
    (('verification', 'verification_report', 'rebuild', 'status'), 'FAIL'),
    (('verification', 'verification_report', 'rebuild', 'scope'), 'OTHER_REBUILD'),
    (('verification', 'verification_report', 'rebuild', 'output_sha256'), 'f' * 64),
    (('verification', 'verification_report', 'rebuild', 'unit_count'), 2),
    (('verification', 'verification_report', 'rebuild', 'python'), 'CPython 3.12.13'),
    (('verification', 'verification_report', 'rebuild', 'current_toolchain', 'extractor', 'code_sha256'), 'f' * 64),
    (('verification', 'verification_report', 'rebuild', 'current_toolchain', 'extractor', 'version'), 2),
    (('verification', 'verification_report', 'rebuild', 'current_toolchain', 'dependency_lock', 'sha256'), 'f' * 64),
    (('verification', 'verification_report', 'rebuild', 'registered_toolchain', 'extractor', 'python'), 'CPython 3.13.1'),
    (('verification', 'verification_report', 'rebuild', 'toolchain_diff', 'extractor', 'registered', 'python'), 'CPython 3.13.1'),
    (('verification', 'verification_report', 'rebuild', 'toolchain_diff', 'extractor', 'current', 'code_sha256'), 'f' * 64),
    (('verification', 'verification_report', 'rebuild', 'toolchain_diff', 'status'), 'PASS'),
])
def test_runtime_allowance_keeps_every_other_source_and_rebuild_field_exact(observed_session, side, path, value):
    root, source = observed_session
    packet = prepare(root)
    set_observer_python(source, 'CPython 3.12.13')
    selected = packet['task']['sources'][0] if side == 'stored' else source
    for key in path[:-1]:
        selected = selected[key]
    selected[path[-1]] = value
    if side == 'stored':
        rehash_frozen_packet(root, packet)
    with pytest.raises(ValueError, match='prepared request'):
        verify_prepared_request(root, packet)


@pytest.mark.parametrize('side', ['stored', 'fresh'])
@pytest.mark.parametrize('path', [
    ('verification', 'verification_report', 'rebuild', 'current_toolchain', 'extractor', 'python'),
    ('verification', 'verification_report', 'rebuild', 'toolchain_diff', 'extractor'),
])
def test_runtime_allowance_never_waives_missing_observers_or_diff_shape(observed_session, side, path):
    root, source = observed_session
    packet = prepare(root)
    set_observer_python(source, 'CPython 3.12.13')
    selected = packet['task']['sources'][0] if side == 'stored' else source
    for key in path[:-1]:
        selected = selected[key]
    del selected[path[-1]]
    if side == 'stored':
        rehash_frozen_packet(root, packet)
    with pytest.raises(ValueError, match='prepared request'):
        verify_prepared_request(root, packet)


def test_runtime_drift_preserves_real_revision_preparation_and_import(observed_session):
    root, source = observed_session
    prepare(root)
    first = imported(root)
    feedback = store(root, 'data/writing/feedback', feedback_report(root, first['draft']['path']))
    revision = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    saved(root, 'revision.json', revision)
    revision_bytes = (root / 'revision.json').read_bytes()
    set_observer_python(source, 'CPython 3.12.13')
    assert verify_prepared_request(root, revision)['task'] == revision['task']
    result = import_draft(root, 'authored.txt', 'revision.json', session_id='session-test',
                          session_model_label='configured writer (unverified)')
    draft, _ = load_draft(root, result['draft']['path'])
    assert draft['parent'] == first['draft'] and draft['task'] == revision['task']
    assert (root / result['prepared_request']['path']).read_bytes() == revision_bytes


def test_runtime_allowance_traverses_only_named_nested_writing_tasks(observed_session, monkeypatch):
    root, source = observed_session
    original = PromptRenderer.draft
    def nested(renderer, *args, **kwargs):
        rendered = original(renderer, *args, **kwargs)
        task = {'writing_task': {'writing_task': rendered['task']}, 'other': {'sources': [deepcopy(source)]}}
        return renderer.render('author-v1', task, rendered['inputs'])
    monkeypatch.setattr(PromptRenderer, 'draft', nested)
    packet = prepare(root)
    old_source = deepcopy(source)
    set_observer_python(source, 'CPython 3.12.13')
    # Only named writing_task nesting is eligible, not identical containers elsewhere.
    with pytest.raises(ValueError, match='prepared request'):
        verify_prepared_request(root, packet)
    def bounded(renderer, *args, **kwargs):
        rendered = nested(renderer, *args, **kwargs)
        rendered['task']['other']['sources'] = [deepcopy(old_source)]
        return renderer.render('author-v1', rendered['task'], rendered['inputs'])
    monkeypatch.setattr(PromptRenderer, 'draft', bounded)
    report = prepared_request_integrity_report(root, packet)
    assert len(report['runtime_observation_variations']) == 2
    assert all(row['path'].startswith('task.writing_task.writing_task.sources[0].')
               for row in report['runtime_observation_variations'])


def test_prepared_parent_assertions_empty_labels_and_empty_output_rejected(session_root):
    root = session_root
    prepare(root)
    with pytest.raises(ValueError, match='parent differs'):
        imported(root, parent_path='input.json')
    for identity, model in [('', 'configured'), ('session-test', '  ')]:
        with pytest.raises(ValueError, match='invalid session author run'):
            import_draft(root, 'authored.txt', 'request.json', session_id=identity, session_model_label=model)
    (root / 'authored.txt').write_bytes(b' \r\n')
    with pytest.raises(ValueError, match='empty'):
        imported(root)
    assert not (root / 'artifacts').exists()


def test_cli_prepare_import_feedback_revise_import_diff(session_root, capsys):
    from rcwh.application.write import add_commands, command
    root = session_root
    parser = argparse.ArgumentParser()
    parser.add_argument('--root')
    add_commands(parser.add_subparsers())
    def call(words):
        args = parser.parse_args(['--root', str(root), 'write'] + words)
        assert command(args) == 0
        return json.loads(capsys.readouterr().out)
    preview = call(['draft', 'package.json', '--chapter', '89', '--dry-run'])
    assert preview['samples'] == 1 and preview['kind'] == 'WRITING_PREPARED_REQUEST'
    assert verify_prepared_request(root, preview)['task'] == preview['task']
    saved(root, 'request.json', preview)
    (root / 'authored.txt').write_text('甲说道：“不知。”\n\n乙退了。')
    first = call(['import-draft', 'authored.txt', '--request', 'request.json', '--session-id', 'cli-session',
                  '--session-model-label', 'unverified configuration'])
    feedback = call(['feedback', first['draft']['path']])['feedback']
    preview = call(['revise', first['draft']['path'], '--feedback', feedback['path'], '--dry-run'])
    saved(root, 'revision.json', preview)
    (root / 'revised.txt').write_text('甲只摇头。\n\n乙退了。')
    second = call(['import-draft', 'revised.txt', '--request', 'revision.json', '--session-id', 'cli-session',
                   '--session-model-label', 'unverified configuration', '--parent', first['draft']['path'],
                   '--feedback', feedback['path']])
    assert call(['diff', first['draft']['path'], second['draft']['path']])['paragraph_change_reading_packet']
    assert second['execution_basis'] == EXECUTION_BASIS
    assert not (root / 'artifacts/runs').exists()
