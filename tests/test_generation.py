import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest, verified_author_model
from rcwh.generation.records import append_bytes, binding, run_task, store, verify_record
from rcwh.generation.render import PromptRenderer, request_for
from rcwh.generation.runner import AnthropicRunner, Budget, DEFAULT_MODEL, ReplayRunner
from rcwh.generation.writing import diff_report, feedback_report, generate, load_draft, revision_prompt

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path, monkeypatch):
    shutil.copytree(ROOT / 'schemas', tmp_path / 'schemas')
    shutil.copytree(ROOT / 'data/writing/prompts', tmp_path / 'data/writing/prompts')
    (tmp_path / 'input.json').write_text('{}\n')
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    return tmp_path


def response(text='甲说道：“不知。”\n\n乙退了。', stop='end_turn', identity='msg1'):
    return {'id': identity, 'model': DEFAULT_MODEL, 'content': [{'type': 'thinking', 'thinking': ''},
            {'type': 'text', 'text': text}], 'usage': {'input_tokens': 12, 'output_tokens': 8}, 'stop_reason': stop}


def rendered(root):
    return PromptRenderer(root).render('author-v1', {'chapter': 89, 'scenes': [], 'package': {}}, [binding(root, 'input.json')])


def test_replay_draft_feedback_revise_diff_and_author_verification(root, monkeypatch):
    monkeypatch.setattr('rcwh.generation.writing.CharacterKnowledgeRuntime.from_repo', lambda root: None)
    monkeypatch.setattr('rcwh.generation.writing.continuity_report', lambda root, chapter: {'status': 'PENDING'})
    first = generate(root, ReplayRunner([response()]), rendered(root), Budget(), chapter=89)
    draft_path = first['draft']['path']
    draft, text = load_draft(root, draft_path)
    assert verified_author_model(root, draft['authors'][0], text.encode())['name'] == DEFAULT_MODEL
    feedback = feedback_report(root, draft_path)
    assert feedback['qualification'] == 'FEEDBACK_ONLY' and feedback['formal_eligibility'] is False
    assert not (root / 'data/scene_readings.json').exists()
    ref = store(root, 'data/writing/feedback', feedback)
    revised = revision_prompt(root, draft_path, ref['path'])
    second = generate(root, ReplayRunner([response('甲只摇头。\n\n乙退了。', identity='msg2')]), revised,
                      Budget(), chapter=89, parent=first['draft'], feedback=ref)
    packet = diff_report(root, draft_path, second['draft']['path'])
    assert packet['paragraph_change_reading_packet']
    assert 'entire revised candidate' in packet['formal_review_requirement']
    assert load_draft(root, second['draft']['path'])[0]['parent'] == first['draft']
    feedback['candidate']['sha256'] = '0' * 64
    bad = store(root, 'data/writing/feedback', feedback)
    with pytest.raises(ValueError, match='stale'):
        revision_prompt(root, draft_path, bad['path'])


@pytest.mark.parametrize('stop', ['max_tokens', 'refusal', 'tool_use', 'pause_turn', None])
def test_incomplete_responses_recorded_but_not_candidates(root, stop):
    item = rendered(root)
    with pytest.raises(ValueError, match='model run failed'):
        run_task(root, ReplayRunner([response(stop=stop)]), request_for(item, Budget()),
                 inputs=item['inputs'], template=item['template'], budget=Budget())
    paths = list((root / 'artifacts/runs').glob('*.json'))
    assert len(paths) == 1 and json.loads(paths[0].read_text())['status'] == 'FAIL'
    assert not (root / 'artifacts/candidates').exists()


def test_raw_response_and_input_tampering_rejected(root):
    result = generate(root, ReplayRunner([response()]), rendered(root), Budget(), chapter=89)
    record = json.loads((root / result['raw_run']['path']).read_text())
    changed = deepcopy(record)
    changed['response']['content'][1]['text'] = 'tampered'
    with pytest.raises(ValueError, match='identity'):
        verify_record(changed)
    (root / 'input.json').write_text('{"changed": true}')
    assert load_draft(root, result['draft']['path'])[1] == response()['content'][1]['text']
    from rcwh.generation.snapshots import InputSnapshot
    snapshot = InputSnapshot(root, record['input_snapshot'])
    assert snapshot.read(record['inputs'][0]) == b'{}\n'
    blob = snapshot.entries[('input.json', record['inputs'][0]['sha256'])]
    (root / blob['path']).write_bytes(b'tampered historical bytes')
    with pytest.raises(ValueError, match='stale'):
        load_draft(root, result['draft']['path'])


def test_append_only_safe_paths(root):
    ref = append_bytes(root, 'artifacts/test.txt', b'first')
    with pytest.raises(FileExistsError):
        append_bytes(root, ref['path'], b'second')
    with pytest.raises(ValueError):
        append_bytes(root, '../escape', b'bad')
    (root / 'link').symlink_to(root / 'artifacts', target_is_directory=True)
    with pytest.raises(ValueError):
        append_bytes(root, 'link/new.txt', b'bad')
    assert not list((root / 'artifacts').glob('.generation-*'))


def test_dry_request_stable_no_unsupported_params_or_key(root, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    a, b = rendered(root), rendered(root)
    assert a['prompt_sha256'] == b['prompt_sha256']
    request = request_for(a, Budget())
    assert set(request) == {'model', 'max_tokens', 'system', 'messages'}
    assert request['model'] == DEFAULT_MODEL
    with pytest.raises(ValueError, match='requires --execute'):
        AnthropicRunner().run(request, Budget())
    with pytest.raises(ValueError, match='ANTHROPIC_API_KEY'):
        AnthropicRunner(execute=True, network_consent=True).run(request, Budget())


def test_replay_exact_request_and_budgets(root):
    item = rendered(root)
    request = request_for(item, Budget())
    result = run_task(root, ReplayRunner([response()]), request, inputs=item['inputs'], template=item['template'], budget=Budget())
    bad = {**request, 'system': 'changed'}
    with pytest.raises(ValueError, match='request identity'):
        ReplayRunner([result['record']]).run(bad, Budget())
    with pytest.raises(ValueError, match='budget'):
        Budget(max_retries=1).validate()
    with pytest.raises(ValueError, match='input byte'):
        run_task(root, ReplayRunner([response()]), request, inputs=item['inputs'], template=item['template'],
                 budget=Budget(max_input_bytes=1))


def test_application_draft_dry_run_and_replay(root, monkeypatch, capsys):
    from rcwh.application.write import add_commands, command
    parser = argparse.ArgumentParser()
    parser.add_argument('--root')
    add_commands(parser.add_subparsers())
    monkeypatch.setattr('rcwh.application.write.PromptRenderer.draft', lambda self, *a, **kw: rendered(root))
    args = parser.parse_args(['--root', str(root), 'write', 'draft', 'input.json', '--chapter', '89'])
    assert command(args) == 0
    assert json.loads(capsys.readouterr().out)['mode'] == 'DRY_RUN'
    assert not (root / 'artifacts').exists()
    (root / 'replay.json').write_bytes(canonical_bytes([response()]))
    args = parser.parse_args(['--root', str(root), 'write', 'draft', 'input.json', '--chapter', '89', '--replay', 'replay.json'])
    assert command(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['drafts'][0]['qualification'] == 'RESEARCH_ONLY'
    draft_path = result['drafts'][0]['draft']['path']
    monkeypatch.setattr('rcwh.generation.writing.CharacterKnowledgeRuntime.from_repo', lambda root: None)
    monkeypatch.setattr('rcwh.generation.writing.continuity_report', lambda root, chapter: {'status': 'PENDING'})
    args = parser.parse_args(['--root', str(root), 'write', 'feedback', draft_path, '--dry-run'])
    assert command(args) == 0
    assert json.loads(capsys.readouterr().out)['mode'] == 'DRY_RUN'
    assert not (root / 'data/writing/feedback').exists()
    args = parser.parse_args(['--root', str(root), 'write', 'feedback', draft_path])
    assert command(args) == 0
    feedback = json.loads(capsys.readouterr().out)['feedback']['path']
    args = parser.parse_args(['--root', str(root), 'write', 'revise', draft_path, '--feedback', feedback])
    assert command(args) == 0
    assert json.loads(capsys.readouterr().out)['mode'] == 'DRY_RUN'
    (root / 'revise-replay.json').write_bytes(canonical_bytes([response('改稿。', identity='msg2')]))
    args = parser.parse_args(['--root', str(root), 'write', 'revise', draft_path, '--feedback', feedback,
                             '--replay', 'revise-replay.json'])
    assert command(args) == 0
    revised_path = json.loads(capsys.readouterr().out)['draft']['path']
    args = parser.parse_args(['--root', str(root), 'write', 'diff', draft_path, revised_path])
    assert command(args) == 0
    assert json.loads(capsys.readouterr().out)['paragraph_change_reading_packet']
