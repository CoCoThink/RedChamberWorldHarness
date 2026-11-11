from copy import deepcopy
import pytest
from rcwh.generation.writing import revision_task, feedback_report, load_draft
from rcwh.generation.session import prepare_request, import_draft, verify_prepared_request
from rcwh.generation.records import store
from test_generation import root
from test_session_generation import session_root, saved
from test_revision_templates import parent_and_feedback


def test_projection_preserves_constraints_current_negative_findings_and_legacy():
    base = {'scenes': [{'unknown': 'UNKNOWN', 'forbidden': ['fill G01']}], 'sources': ['complete']}
    prior = {'writing_task': base, 'original': 'old prose', 'feedback': {'FAIL': 'old'}, 'editorial_notes': 'old notes'}
    feedback = {'findings': [{'assessment': 'FAIL', 'reason': 'repeat'}, {'assessment': 'PENDING'}]}
    result = revision_task(prior, 'immediate full prose', feedback, 'complete notes', 'revise-v3')
    assert result['writing_task'] == base
    assert result['feedback'] == feedback and result['original'] == 'immediate full prose'
    assert result['history_selection']['removed_wrapper_depth'] == 1
    assert revision_task(prior, 'text', feedback, None, 'revise-v2')['writing_task'] == prior
    again = revision_task(result, 'next full prose', feedback, None, 'revise-v3')
    assert again['writing_task'] == base and again['history_selection']['removed_wrapper_depth'] == 1
    changed = deepcopy(prior); changed['additional_obligations'] = ['do not discard']
    with pytest.raises(ValueError, match='unknown constraints'):
        revision_task(changed, 'text', feedback, None, 'revise-v3')


def test_v3_revision_import_keeps_exact_immediate_parent_and_new_template(session_root):
    root = session_root
    first, feedback = parent_and_feedback(root)
    second_request = prepare_request(root, parent_path=first['draft']['path'], feedback_path=feedback['path'], revision_template='revise-v2')
    saved(root, 'second.json', second_request); (root/'second.txt').write_text('甲把旧信放回抽屉，转身问乙。\n')
    second = import_draft(root,'second.txt','second.json',session_id='session-test',session_model_label='unverified')
    f = feedback_report(root, second['draft']['path']); f['checks'].append({'status':'FAIL','reason':'keep this negative finding'})
    fref = store(root,'data/writing/feedback',f)
    packet = prepare_request(root,parent_path=second['draft']['path'],feedback_path=fref['path'],revision_template='revise-v3')
    assert packet['parent'] == second['draft']
    assert packet['task']['writing_task'] == second_request['task']['writing_task']
    assert packet['task']['original'] == (root/'second.txt').read_text()
    assert packet['task']['feedback'] == f
    assert verify_prepared_request(root, packet)['template']['path'].endswith('revise-v3.md')
    saved(root,'third.json',packet);(root/'third.txt').write_text('乙看着抽屉，没有接话。\n')
    third = import_draft(root,'third.txt','third.json',session_id='session-test',session_model_label='unverified')
    d,_ = load_draft(root,third['draft']['path']);assert d['parent']==second['draft']
    packet['task']['feedback']['checks'][-1]['status']='PASS'
    with pytest.raises(ValueError):verify_prepared_request(root, packet)


def test_many_revisions_keep_base_constraints_without_recursive_prose_growth():
    from rcwh.candidate_reviews import canonical_bytes
    base = {'chapter':86,'required':['do not fill gap'],'unknown':'UNKNOWN'}
    task=base
    sizes=[]
    for _ in range(40):
        task=revision_task(task,'the immediate text',{'finding':'PENDING'},'notes','revise-v3')
        sizes.append(len(canonical_bytes(task)))
        assert task['writing_task']==base
    assert len(set(sizes[1:]))==1


def test_cli_v3_custody_and_template_change_are_checked(session_root, capsys):
    import argparse,json
    from rcwh.application.write import add_commands,command
    root=session_root;first,feedback=parent_and_feedback(root)
    parser=argparse.ArgumentParser();parser.add_argument('--root');add_commands(parser.add_subparsers())
    args=parser.parse_args(['--root',str(root),'write','revise',first['draft']['path'],'--feedback',feedback['path'],'--revision-template','revise-v3','--dry-run'])
    assert command(args)==0
    packet=json.loads(capsys.readouterr().out)
    assert verify_prepared_request(root,packet)['template']['path'].endswith('revise-v3.md')
    (root/'data/writing/prompts/revise-v3.md').write_text('changed template')
    with pytest.raises(ValueError):verify_prepared_request(root,packet)
