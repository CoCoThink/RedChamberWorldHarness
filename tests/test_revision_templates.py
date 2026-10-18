import json

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import store
from rcwh.generation.render import PromptRenderer, request_for
from rcwh.generation.runner import Budget
from rcwh.generation.session import import_draft, prepare_request, verify_prepared_request
from rcwh.generation.writing import feedback_report, load_draft, revision_prompt
from test_generation import root
from test_session_generation import session_root, prepare, imported, saved


def parent_and_feedback(root):
    prepare(root)
    first = imported(root)
    feedback = store(root, 'data/writing/feedback', feedback_report(root, first['draft']['path']))
    return first, feedback


def test_explicit_v2_selection_binds_template_and_actual_revision_parent(session_root):
    root = session_root
    first, feedback = parent_and_feedback(root)
    default = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'])
    explicit_legacy = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'],
                                      revision_template='revise-v1')
    assert canonical_bytes(default) == canonical_bytes(explicit_legacy)
    assert 'revision_template' not in default['context']
    revised = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'],
                              revision_template='revise-v2')
    assert revised['context']['revision_template'] == 'revise-v2'
    assert revised['template']['path'] == 'data/writing/prompts/revise-v2.md'
    assert revised['package'] == default['package']
    assert revised['parent'] == first['draft']
    assert revised['task'] == default['task']
    assert revised['request_sha256'] != default['request_sha256']
    assert verify_prepared_request(root, revised)['template'] == revised['template']
    saved(root, 'revision.json', revised)
    (root / 'revised.txt').write_text('甲放下灯，乙才开口。\n')
    second = import_draft(root, 'revised.txt', 'revision.json', session_id='session-test',
                          session_model_label='unverified writer')
    record, _ = load_draft(root, second['draft']['path'])
    assert record['template'] == revised['template'] and record['parent'] == first['draft']


@pytest.mark.parametrize('tamper', ['context_removed', 'context_v1', 'template_changed', 'template_stale'])
def test_v2_template_custody_cannot_be_rebound(session_root, tamper):
    root = session_root
    first, feedback = parent_and_feedback(root)
    packet = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'],
                             revision_template='revise-v2')
    if tamper == 'context_removed':
        del packet['context']['revision_template']
    elif tamper == 'context_v1':
        packet['context']['revision_template'] = 'revise-v1'
    elif tamper == 'template_stale':
        (root / packet['template']['path']).write_text('Changed system instructions.')
    else:
        rendered = PromptRenderer(root).render('revise-v1', packet['task'], packet['inputs'])
        packet['template'] = rendered['template']
        packet['prompt_sha256'] = rendered['prompt_sha256']
        packet['request'] = request_for(rendered, Budget(**packet['budget']))
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
    with pytest.raises(ValueError):
        verify_prepared_request(root, packet)


def test_v2_not_available_as_draft_selection_or_arbitrary_template(session_root):
    root = session_root
    with pytest.raises(ValueError, match='requires a revision parent'):
        prepare_request(root, package_path='package.json', chapter=89, revision_template='revise-v2')
    first, feedback = parent_and_feedback(root)
    for name in ['author-v1', '../revise-v2', 'revise-v3']:
        with pytest.raises(ValueError, match='unknown revision template'):
            revision_prompt(root, first['draft']['path'], feedback['path'], revision_template=name)
    packet = prepare_request(root, package_path='package.json', chapter=89)
    packet['context']['revision_template'] = 'revise-v2'
    with pytest.raises(ValueError, match='invalid session prepared'):
        verify_prepared_request(root, packet)


def test_cli_explicit_v2_dry_run_is_reproducible(session_root, capsys):
    import argparse
    from rcwh.application.write import add_commands, command
    root = session_root
    first, feedback = parent_and_feedback(root)
    parser = argparse.ArgumentParser()
    parser.add_argument('--root')
    add_commands(parser.add_subparsers())
    args = parser.parse_args(['--root', str(root), 'write', 'revise', first['draft']['path'],
                              '--feedback', feedback['path'], '--revision-template', 'revise-v2', '--dry-run'])
    assert command(args) == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet['context']['revision_template'] == 'revise-v2'
    assert verify_prepared_request(root, packet)['template'] == packet['template']
