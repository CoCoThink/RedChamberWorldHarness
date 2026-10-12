from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.backtest.session import SessionBacktest, anonymous_export
from rcwh.backtest.study import HOLDOUT_PATH
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import binding, store
from rcwh.workflow.agent_panel import register, verify_packet
from test_backtest import study, write


@pytest.fixture
def session(study):
    backtest, state = study
    return SessionBacktest(backtest.root), state


def setup(session, *, revise_direct=False):
    backtest, _ = session
    prepared = backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')
    finals, originals = [], []
    for row in prepared['author_packets']:
        identity = row['workflow'] + '-' + row['sample_id']
        path = identity + '.txt'
        (backtest.root / path).write_bytes(('甲笑道：“尚不知。”\r\n\r\n乙只摇头。' + identity).encode())
        first = backtest.register(path, row['packet']['path'], session_id='author-' + identity, session_model_label='declared-writer')
        originals.append(first['round'])
        if row['workflow'] == 'HARNESS' or revise_direct:
            feedback = write(backtest.root, identity + '-feedback.json', {
                'qualification': 'FEEDBACK_ONLY', 'parent': first['round'], 'candidate_sha256': first['candidate']['sha256'],
                'text': '删去空言，仍循给定事件。', 'authority_effect': 'NONE'})
            revision = backtest.prepare_revision('work/revisions', first['round']['path'], feedback['path'])
            (backtest.root / (identity + '-revised.txt')).write_text('甲不再言语。\n\n乙仍摇头。' + identity)
            final = backtest.register(identity + '-revised.txt', revision['packet']['path'], session_id='author-' + identity,
                                      session_model_label='declared-writer')
        else:
            final = first
        finals.append(final['round']['path'])
    registry = backtest.registry('work/registry', finals)['registry']
    return prepared, registry, originals


def test_prepare_exact_equal_shared_targets_no_holdout_leak(session):
    backtest, state = session
    result = backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')
    assert len(result['author_packets']) == 4
    packets = [json.loads((backtest.root / row['packet']['path']).read_bytes()) for row in result['author_packets']]
    assert all(packet['request_sha256'] == digest(canonical_bytes(packet['request'])) for packet in packets)
    tasks = [json.loads(packet['request']['messages'][0]['content']) for packet in packets]
    assert tasks[0]['shared'] == tasks[2]['shared'] and tasks[0]['shared']['target_characters'] == 100
    assert tasks[0]['workflow_support'] is None and tasks[2]['workflow_support']['style_reference']['chapter_count'] == 78
    assert '原文秘密不入提示' not in json.dumps(packets, ensure_ascii=False)
    assert tasks[2]['workflow_support']['style_reference']['reference_scope']['excluded_chapters'] == [79, 80]
    preparation = json.loads((backtest.root / result['preparation']['path']).read_bytes())
    assert binding(backtest.root, HOLDOUT_PATH) in preparation['inputs']
    assert preparation['resource_parity'] == 'NOT_VERIFIED' and preparation['model_pretraining_exposure'] == 'UNKNOWN'
    assert not any(state['calls'])
    with pytest.raises(FileExistsError):
        backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')


@pytest.mark.parametrize('ids', [['one'], ['one', 'one']])
def test_prepare_requires_at_least_two_distinct_pairs(session, ids):
    backtest, _ = session
    with pytest.raises(ValueError, match='paired sample'):
        backtest.prepare('work/prepared', characters=100, sample_ids=ids, coordinator_session_id='coordinator-session')


def test_session_lineage_full_pairs_export_observations_and_no_provider_proof(session):
    backtest, _ = session
    prepared, registry, originals = setup(session, revise_direct=True)
    report = backtest.summary(registry['path'])
    assert report['paired_sample_count'] == 2 and len(report['samples']) == 4
    assert all(sample['declared_rounds'] == 2 for sample in report['samples'])
    assert report['controlled_workflow_effect'] == report['outcome'] == 'NOT_ESTIMABLE'
    assert report['resource_parity'] == report['actual_token_usage'] == 'NOT_VERIFIED'
    assert report['model_pretraining_exposure'] == 'UNKNOWN'
    assert all(sample['overlap']['verdict'] is None and sample['style'] for sample in report['samples'])
    assert report['automatic_winner'] is None and report['independent_human_admission'] is False
    records = json.loads((backtest.root / registry['path']).read_bytes())
    assert not any(key in json.dumps(records) for key in ('raw_run', 'sdk_version', 'request_id', 'billed_tokens'))
    exported = backtest.export('work/export', registry['path'], coordinator_session_id='coordinator-session')
    packet = verify_packet(backtest.root, exported['packet'])
    assert len(packet['subjects']) == 5 and all(s['scope'] == 'CANDIDATE' for s in packet['subjects'])
    metadata = json.dumps(packet)
    assert all(word not in metadata for word in ('DIRECT', 'HARNESS', 'ORIGINAL_REFERENCE', 'author-DIRECT', registry['path']))
    public = backtest.root / exported['public_directory']
    assert len(list(public.glob('*.txt'))) == 5 and not list(public.glob('*template*'))
    assert '原文秘密不入提示' in ''.join(path.read_text() for path in public.glob('*.txt'))
    mapping = json.loads((backtest.root / exported['mapping']['path']).read_bytes())
    assert sum(row['kind'] == 'ORIGINAL_REFERENCE' for row in mapping['mapping']) == 1
    assert mapping['context'] == registry
    report = backtest.summary(registry['path'], exported['mapping']['path'])
    assert report['agent_reading']['status'] == 'PENDING' and report['outcome'] == 'NOT_ESTIMABLE'


def test_harness_requires_revision_and_full_pair_ids(session):
    backtest, _ = session
    prepared = backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')
    finals = []
    for i, row in enumerate(prepared['author_packets']):
        (backtest.root / f'text-{i}.txt').write_text('甲只摇头。' + str(i))
        first = backtest.register(f'text-{i}.txt', row['packet']['path'], session_id='session-' + str(i), session_model_label='declared')
        finals.append(first['round']['path'])
    with pytest.raises(ValueError, match='HARNESS_REVISION_REQUIRED'):
        backtest.registry('work/registry', finals)
    with pytest.raises(ValueError):
        backtest.registry('work/registry', finals[:2])


@pytest.mark.parametrize('change', ['config', 'task', 'corpus', 'new-source'])
def test_preparation_stale_source_dependencies_fail_closed(session, change):
    backtest, state = session
    prepared = backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')
    if change == 'config':
        config = json.loads((backtest.root / HOLDOUT_PATH).read_bytes())
        config['limitations'].append('changed')
        write(backtest.root, HOLDOUT_PATH, config)
        backtest = SessionBacktest(backtest.root)
    elif change == 'task':
        path = backtest.study.data['shared_task']['path']
        value = json.loads((backtest.root / path).read_bytes())
        value['plan_summary'] = 'changed'
        write(backtest.root, path, value)
    elif change == 'corpus':
        state['rows'][0]['text'] = '变更正文'
        state['rows'][0]['text_sha256'] = digest(state['rows'][0]['text'].encode())
    else:
        write(backtest.root, 'data/provenance/sources/new.json', {})
    (backtest.root / 'new.txt').write_text('甲只摇头。')
    with pytest.raises(ValueError):
        backtest.register('new.txt', prepared['author_packets'][0]['packet']['path'], session_id='declared', session_model_label='declared')


@pytest.mark.parametrize('change', ['request', 'parent', 'feedback'])
def test_exact_revision_parent_and_advisory_feedback_binding(session, change):
    backtest, _ = session
    prepared = backtest.prepare('work/prepared', characters=100, coordinator_session_id='coordinator-session')
    row = prepared['author_packets'][2]
    (backtest.root / 'original.txt').write_text('甲只摇头。')
    first = backtest.register('original.txt', row['packet']['path'], session_id='author-session', session_model_label='declared')
    feedback = {'qualification': 'FEEDBACK_ONLY', 'parent': first['round'], 'candidate_sha256': first['candidate']['sha256'],
                'text': '调整章法。', 'authority_effect': 'NONE'}
    if change == 'parent':
        feedback['parent'] = binding(backtest.root, HOLDOUT_PATH)
    if change == 'feedback':
        feedback['qualification'] = 'FORMAL'
    ref = write(backtest.root, 'feedback.json', feedback)
    if change != 'request':
        with pytest.raises(ValueError):
            backtest.prepare_revision('work/revisions', first['round']['path'], ref['path'])
    else:
        revision = backtest.prepare_revision('work/revisions', first['round']['path'], ref['path'])
        packet = json.loads((backtest.root / revision['packet']['path']).read_bytes())
        assert packet['request']['messages'][1]['content'] == '甲只摇头。'
        packet['request']['messages'][1]['content'] = 'fake prior text'
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
        forged = write(backtest.root, 'forged.json', packet)
        (backtest.root / 'revised.txt').write_text('甲不言语。')
        with pytest.raises(ValueError, match='exact prepared request'):
            backtest.register('revised.txt', forged['path'], session_id='author-session', session_model_label='declared')


@pytest.mark.parametrize('fake', ['raw_run', 'provider', 'sdk_version', 'request_id', 'actual_tokens', 'billed_tokens'])
def test_session_round_rejects_fake_execution_metadata(session, fake):
    backtest, _ = session
    _, registry, originals = setup(session)
    records = json.loads((backtest.root / registry['path']).read_bytes())
    final = records['samples'][0]['final_round']
    round_record = json.loads((backtest.root / final['path']).read_bytes())
    round_record[fake] = 'fabricated'
    forged_round = store(backtest.root, 'work/forged', round_record)
    records['samples'][0]['final_round'] = forged_round
    forged = store(backtest.root, 'work/forged', records)
    with pytest.raises(ValueError, match='invalid session backtest round'):
        backtest.summary(forged['path'])


def test_export_registry_cannot_be_swapped_and_public_tampering_rejected(session):
    backtest, _ = session
    _, registry, _ = setup(session)
    export = backtest.export('work/export', registry['path'], coordinator_session_id='coordinator-session')
    records = json.loads((backtest.root / registry['path']).read_bytes())
    records['samples'].reverse()
    replacement = store(backtest.root, 'work/replacement', records)
    with pytest.raises(ValueError, match='STALE_EXPORT_REGISTRY'):
        backtest.summary(replacement['path'], export['mapping']['path'])
    packet = json.loads((backtest.root / export['packet']['path']).read_bytes())
    (backtest.root / packet['subjects'][0]['binding']['path']).write_text('changed')
    with pytest.raises(ValueError):
        backtest.summary(registry['path'], export['mapping']['path'])


def test_original_text_and_parent_source_lineage_are_bound(session):
    backtest, _ = session
    _, registry, originals = setup(session)
    record = json.loads((backtest.root / originals[2]['path']).read_bytes())
    (backtest.root / record['text_source']['path']).write_text('tampered parent')
    with pytest.raises(ValueError, match='stale'):
        backtest.summary(registry['path'])


def test_generic_export_no_reference_and_rejects_unsafe_path(session):
    backtest, _ = session
    context = binding(backtest.root, HOLDOUT_PATH)
    (backtest.root / 'candidate.txt').write_text('甲只摇头。')
    candidates = [{'id': 'candidate-ch89', 'text': binding(backtest.root, 'candidate.txt'), 'author_session_ids': ['writer-session']}]
    result = anonymous_export(backtest.root, 'other/export', candidates, context=context, coordinator_session_id='coordinator-session')
    assert len(verify_packet(backtest.root, result['packet'])['subjects']) == 1
    with pytest.raises(FileExistsError):
        anonymous_export(backtest.root, 'other/export', candidates, context=context, coordinator_session_id='coordinator-session')
    with pytest.raises(ValueError):
        anonymous_export(backtest.root, '../escape', candidates, context=context, coordinator_session_id='coordinator-session')


@pytest.mark.parametrize('author_alias', [False, True])
def test_two_declared_peer_readings_only_enable_descriptive_outcome(session, author_alias):
    backtest, _ = session
    _, registry, _ = setup(session)
    exported = backtest.export('work/export', registry['path'], coordinator_session_id='coordinator-session')
    packet = verify_packet(backtest.root, exported['packet'])
    for identity in ('reader-one', 'reader-two'):
        opinion = {'schema_version': 1, 'report_kind': 'AGENT_REVIEW_OPINION', 'packet': exported['packet'],
                   'reviewer': {'id': identity, 'kind': 'MODEL_SUBAGENT', 'session_id': identity + '-session',
                                'model': {'label': 'configured peer', 'verification': 'DECLARED_NOT_VERIFIED'},
                                'context_isolation': {'asserted': True, 'verification': 'NOT_PROVEN'}},
                   'results': [{'subject_id': row['id'], 'subject_sha256': row['binding']['sha256'], 'verdict': 'PASS',
                                'notes': 'Synthetic research fixture; not human qualification.', 'sample_checks': []} for row in packet['subjects']],
                   'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY', 'independent_human_admission': False}
        if author_alias and identity == 'reader-one':
            opinion['reviewer']['session_id'] = 'author-DIRECT-one'
        source = write(backtest.root, identity + '.json', opinion)
        register(backtest.root, backtest.root / source['path'], origin='test fixture')
    report = backtest.summary(registry['path'], exported['mapping']['path'])
    assert report['outcome'] == ('NOT_ESTIMABLE' if author_alias else 'DESCRIPTIVE_AGENT_READING_ONLY')
    assert bool(report['excluded_author_readings']) is author_alias
    assert report['controlled_workflow_effect'] == 'NOT_ESTIMABLE' and report['resource_parity'] == 'NOT_VERIFIED'
    assert report['independent_human_admission'] is False and report['automatic_winner'] is None
