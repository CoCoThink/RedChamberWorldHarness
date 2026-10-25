"""Apply root-approved editorial proposals; immutable revisions, no peer credit."""
from copy import deepcopy
from pathlib import Path
import difflib
import json
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding, bound_bytes
from rcwh.generation.session import prepare_request, import_draft
from rcwh.generation.writing import feedback_report
from rcwh.workflow.attribution import release_attribution

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def write(relative, value):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    if target.exists():
        assert target.read_bytes() == raw, f'resume would replace retained bytes: {relative}'
    else:
        target.write_bytes(raw)
    return binding(ROOT, relative)

def run():
    design = json.loads((OUT / 'design-decisions.json').read_bytes())
    bound_bytes(ROOT, design['basis_request'])
    selection = json.loads((ROOT / 'data/agent_release/selection-81-100-v3.json').read_bytes())
    assert not (ROOT / 'data/agent_release/selection-81-100-v4.json').exists()
    texts = {}
    for row in selection['chapters']:
        text = bound_bytes(ROOT, row['candidate']).decode()
        for e in (e for e in design['edits'] if e['chapter'] == row['chapter']):
            assert text.count(e['before']) == 1, (row['chapter'], e['issue_id'])
            text = text.replace(e['before'], e['after'])
        texts[row['chapter']] = text
    summary = []
    for row in selection['chapters']:
        ch = row['chapter']
        if ch not in design['changed_chapters']:
            continue
        previous = deepcopy(row)
        old = bound_bytes(ROOT, row['candidate']).decode()
        new = texts[ch]
        base = f'{OUT.relative_to(ROOT).as_posix()}/revisions/ch{ch}'
        feedback = write(base + '-feedback.json', feedback_report(ROOT, row['draft']['path']))
        choices = [d for d in design['decisions'] if any(e['chapter'] == ch and e['issue_id'] == d['issue_id'] for e in design['edits'])]
        notes = {'kind': 'ROOT_ACTUAL_EDITORIAL_REVISION', 'chapter': ch,
                 'declaration': '原生设计协作者提供逐段建议；根协调者核对、选择、调整并实际应用。不是由新写作提示词从头生成；不把设计建议记为同行意见。原作者、父稿及纯重绑保管链保留。',
                 'editor': f'session:coordinator-edit-20261025:ch{ch}',
                 'assisting_designs': choices,
                 'edits': [e for e in design['edits'] if e['chapter'] == ch],
                 'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
        note_ref = write(base + '-editorial-notes.json', notes)
        prepared = prepare_request(ROOT, parent_path=row['draft']['path'], feedback_path=feedback['path'],
                                   notes_path=note_ref['path'], revision_template='revise-v2', renderer_version=2)
        request = write(base + '-request.json', prepared)
        text = write(base + '-edited.txt', new.encode())
        result = import_draft(ROOT, text['path'], request['path'], session_id=f'coordinator-edit-20261025:ch{ch}',
                              session_model_label='current agent environment (declared); root actual editor using disclosed design assistance',
                              parent_path=row['draft']['path'], feedback_path=feedback['path'])
        row.update(candidate=result['candidate'], draft=result['draft'])
        attribution = release_attribution(ROOT, row)
        assert attribution['contributors'][-1]['principal_id'] == f'session:coordinator-edit-20261025:ch{ch}'
        record = {'chapter': ch, 'previous': previous, 'current': deepcopy(row), 'import': result,
                  'editorial_notes': note_ref, 'diff': '\n'.join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile='v2', tofile='v3', lineterm='')),
                  'attribution': attribution, 'peer_review': 'PENDING_NEW_CONTEXT'}
        write(base + '-result.json', record)
        summary.append(record)
        print(f'ch{ch}: imported actual revision', flush=True)
    selection['id'] = 'selection:81-100:v4'
    write('data/agent_release/selection-81-100-v4.json', selection)
    write(f'{OUT.relative_to(ROOT).as_posix()}/revisions/summary.json', summary)
    print(json.dumps({'status': 'PASS', 'revised': design['changed_chapters'], 'review': 'PENDING'}, ensure_ascii=False))

if __name__ == '__main__':
    with rebuild_scope():
        run()
