import json

from rcwh.generation.records import binding
from rcwh.generation.render import PromptRenderer
from rcwh.generation.runner import Budget, ReplayRunner
from rcwh.generation.writing import feedback_report, generate
from test_generation import DEFAULT_MODEL, response, root


def test_semantic_replay_never_registers_official_reading(root, monkeypatch):
    monkeypatch.setattr('rcwh.generation.writing.CharacterKnowledgeRuntime.from_repo', lambda root: None)
    monkeypatch.setattr('rcwh.generation.writing.continuity_report', lambda root, chapter: {'status': 'PENDING'})
    task = {'chapter': 89, 'package': {}, 'scenes': [{'contract': {'id': 'scene', 'chapter': 89,
            'participants': [], 'required_beats': [], 'forbidden_beats': [], 'exit_state': []},
            'entry': {'values': {}, 'origins': {}, 'knowledge': None}}]}
    rendered = PromptRenderer(root).render('author-v1', task, [binding(root, 'input.json')])
    first = generate(root, ReplayRunner([response()]), rendered, Budget(), chapter=89)
    report = feedback_report(root, first['draft']['path'], runner=ReplayRunner([response('{}', identity='feedback')]))
    assert report['semantic_runs'] and report['semantic_requests']
    assert report['formal_eligibility'] is False
    assert all(check['qualification'] == 'FEEDBACK_ONLY' for check in report['checks'])
    paths = list((root / 'artifacts/runs').glob('*.json'))
    assert len(paths) == 2
    assert not (root / 'data/evaluation/scene_readings.json').exists()
    assert all(json.loads(path.read_text())['provider'] == 'replay' for path in paths)
    assert next(check for check in report['checks'] if check['evaluator'] == 'scene_semantics')['status'] == 'FAIL'


def test_unrequested_semantic_feedback_is_pending_not_malformed_reading(root, monkeypatch):
    monkeypatch.setattr('rcwh.generation.writing.CharacterKnowledgeRuntime.from_repo', lambda root: None)
    monkeypatch.setattr('rcwh.generation.writing.continuity_report', lambda root, chapter: {'status': 'PENDING'})
    task = {'chapter': 89, 'package': {}, 'scenes': [{'contract': {'id': 'scene', 'chapter': 89,
            'participants': [], 'required_beats': [], 'forbidden_beats': [], 'exit_state': []},
            'entry': {'values': {}, 'origins': {}, 'knowledge': None}}]}
    rendered = PromptRenderer(root).render('author-v1', task, [binding(root, 'input.json')])
    first = generate(root, ReplayRunner([response()]), rendered, Budget(), chapter=89)
    monkeypatch.setattr('rcwh.evaluation.semantics.registered_reading',
                        lambda *args: (_ for _ in ()).throw(AssertionError('official reading registry consulted')))
    report = feedback_report(root, first['draft']['path'])
    reading = next(check for check in report['checks'] if check['evaluator'] == 'scene_semantics')
    assert reading['status'] == 'PENDING'
    assert reading['findings'] == ['MODEL_SEMANTIC_FEEDBACK_NOT_REQUESTED']
    assert report['semantic_requests'] and report['semantic_runs'] == []
    assert report['formal_eligibility'] is False
    assert not (root / 'data/evaluation/scene_readings.json').exists()
