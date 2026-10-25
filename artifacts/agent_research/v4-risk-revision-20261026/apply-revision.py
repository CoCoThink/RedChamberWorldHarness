"""Actual root revision following retained negative opinions; no peer credit."""
from pathlib import Path
from copy import deepcopy
import difflib
import json
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding, bound_bytes
from rcwh.generation.session import prepare_request, import_draft
from rcwh.generation.writing import feedback_report
from rcwh.workflow.attribution import release_attribution

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def write(relative, value):
    target = R / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    assert not target.exists(), relative
    target.write_bytes(raw)
    return binding(R, relative)


def main():
    design = json.loads((O / 'design-decisions.json').read_bytes())
    bound_bytes(R, design['basis_request'])
    selection = json.loads((R / 'data/agent_release/selection-81-100-v7.json').read_bytes())
    row = next(r for r in selection['chapters'] if r['chapter'] == 87)
    previous = deepcopy(row)
    old = bound_bytes(R, row['candidate']).decode()
    new = old
    for e in design['edits']:
        assert e['chapter'] == 87 and new.count(e['before']) == 1
        new = new.replace(e['before'], e['after'])
    assert new != old and new.endswith('\n')
    base = O.relative_to(R).as_posix() + '/revisions/ch87'
    feedback = write(base + '-feedback.json', feedback_report(R, row['draft']['path']))
    notes = write(base + '-editorial-notes.json', {
        'kind': 'ROOT_ACTUAL_EDITORIAL_REVISION', 'chapter': 87,
        'editor': design['editor'], 'design': binding(R, (O / 'design-decisions.json').relative_to(R).as_posix()),
        'declaration': 'Root actual revision after reading two fresh negative opinions. No design delegation or peer credit. Original prose authors, earlier editors, custodians and old negatives remain.',
        'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'})
    prepared = prepare_request(R, parent_path=row['draft']['path'], feedback_path=feedback['path'],
                               notes_path=notes['path'], revision_template='revise-v2', renderer_version=2)
    request = write(base + '-request.json', prepared)
    text = write(base + '-edited.txt', new.encode())
    result = import_draft(R, text['path'], request['path'],
                          session_id='coordinator-risk-edit-20261026:ch87',
                          session_model_label='current agent environment (declared); root actual risk revision',
                          parent_path=row['draft']['path'], feedback_path=feedback['path'])
    row.update(candidate=result['candidate'], draft=result['draft'])
    attribution = release_attribution(R, row)
    assert attribution['contributors'][-1]['principal_id'] == design['editor']
    record = {'chapter': 87, 'previous': previous, 'current': deepcopy(row), 'import': result,
              'editorial_notes': notes, 'attribution': attribution,
              'diff': '\n'.join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile='v4-r2', tofile='v4-r3', lineterm='')),
              'peer_review': 'PENDING_NEW_CONTEXT_AFTER_NEW_INPUT_CI'}
    write(base + '-result.json', record)
    selection['id'] = 'selection:81-100:v8'
    write('data/agent_release/selection-81-100-v8.json', selection)
    print(json.dumps({'status': 'PASS', 'revised': [87], 'candidate': row['candidate'], 'review': 'PENDING'}, ensure_ascii=False))


if __name__ == '__main__':
    with rebuild_scope():
        main()
