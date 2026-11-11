"""Verify revision custody and exact scope delta, never certify literary quality."""
import hashlib
import json
from pathlib import Path
import runpy
from rcwh.generation.records import bound_bytes
from rcwh.generation.writing import load_draft, revision_task
from rcwh.generation.local_scenario import verify_material
from rcwh.generation.lineage import current_compatibility
from rcwh.corpus.dataset import rebuild_scope

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('artifacts/local-trial-revision-ch86-20261111')

def read(p):return json.loads((ROOT/p).read_bytes())

def verify():
    imported=read(BASE/'import.json'); old=read('artifacts/local-trial-ch86-20261110/import-v3.json')
    delta=read(BASE/'scope-delta.json'); package=json.loads(bound_bytes(ROOT,delta['selected_package']))
    scenario,_,contracts=verify_material(ROOT,package)
    expected=json.loads(bound_bytes(ROOT,delta['parent_scenario']))
    expected['contracts']=[c['selected'] for c in delta['contracts']]
    expected['extra_editorial_choices'].append(delta['scenario_append_choice'])
    assert scenario==expected==json.loads(bound_bytes(ROOT,delta['selected_scenario']))
    for change,(_,contract) in zip(delta['contracts'],contracts,strict=True):
        before=json.loads(bound_bytes(ROOT,change['parent']))
        assert before['participants']==change['old_participants']
        before.update(participants=change['participants'],participant_scope=delta['participant_scope'])
        assert before==contract==json.loads(bound_bytes(ROOT,change['selected']))
    with rebuild_scope():
        draft,text=load_draft(ROOT,imported['draft']['path'])
        parent,parent_text=load_draft(ROOT,old['draft']['path'])
        assert draft['parent']==old['draft'] and draft['package']==parent['package']
        assert {a['principal_id'] for a in draft['authors']}=={a['principal_id'] for a in parent['authors']}=={'session:main-agent:ch86-local-trial:20261110'}
        compatibility=current_compatibility(ROOT,imported['draft']['path'])
        assert compatibility['status']=='PASS',compatibility
    assert text.encode()==(ROOT/BASE/'ch86-authored-v4.txt').read_bytes()
    request=json.loads(bound_bytes(ROOT,draft['prepared_request']))
    feedback=json.loads(bound_bytes(ROOT,draft['feedback']))
    notes=(ROOT/BASE/'revision-notes.md').read_text()
    assert json.dumps(delta,ensure_ascii=False,indent=2) in notes
    assert request['task']==revision_task(parent['task'],parent_text,feedback,notes,'revise-v3')
    assert request['context']['revision_template']=='revise-v3'
    assert request['byte_admission']['status']=='PASS'
    assert read(BASE/'budget-rejection.json')['admission']['status']=='FAIL'
    assert len(text.encode())<=request['context']['context_limits']['output_reserve_bytes']
    checks=feedback['checks'][:4];findings=[]
    for check in checks:
        opinion=json.loads(bound_bytes(ROOT,check['details']['original_opinion']))
        assert check['details']['findings']==opinion['findings']
        assert check['status']==opinion['overall_assessment']
        assert check['details']['nonpass_obligations']==[o for o in opinion['obligation_findings'] if o['assessment']!='PASS']
        findings.extend(opinion['findings'])
    assert len(findings)==21 and sum(f['assessment']=='FAIL' for f in findings)==1
    assert sum(f['assessment']=='PENDING' for f in findings)==7
    assert feedback['checks'][4]['details']['scope_delta']=={'path':str(BASE/'scope-delta.json'),'sha256':hashlib.sha256((ROOT/BASE/'scope-delta.json').read_bytes()).hexdigest()}
    audit=read(BASE/'author-selfcheck.json')
    assert audit['candidate']==draft['candidate'] and audit['independent_opinions']==0
    assert not audit['formal_eligibility'] and audit['independence']=='SAME_AUTHOR_NOT_INDEPENDENT'
    ledger=json.loads(bound_bytes(ROOT,audit['paragraph_ledger']))
    assert ledger['candidate']==draft['candidate']
    assert '\n\n'.join(r['quote'] for r in ledger['paragraphs'])+'\n'==text
    for row in ledger['paragraphs']:
        a,b=row['byte_range'];raw=text.encode()[a:b]
        assert raw.decode()==row['quote'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    ids={r['id'] for r in ledger['paragraphs']}
    assert {r['event'] for r in audit['events']}=={e['id'] for e in scenario['events']}
    assert {r['id'] for r in audit['messages']}=={m['id'] for m in scenario['messages']}
    expected_oblig={(ref['path'],key,n) for ref,c in contracts for key in ['required_beats','forbidden_beats'] for n in range(1,len(c[key])+1)}
    assert {(r['contract'],r['type'],r['ordinal']) for r in audit['obligations']}==expected_oblig
    for row in audit['events']+audit['messages']+audit['obligations']:
        assert row['paragraph_refs'] and set(row['paragraph_refs'])<=ids
        assert row['assessment']=='AUTHOR_PROPOSED_MAPPING_NOT_SEMANTIC_PASS'
    views=read(BASE/'reading-views.json')
    for pair in views['files']:
        assert json.loads(bound_bytes(ROOT,pair['source']))==json.loads(bound_bytes(ROOT,pair['complete_reading_view']))
    assert len(views['files'])==7 and not views['omitted_fields']
    packet=runpy.run_path(str(ROOT/BASE/'prepare.py'))['prepare'](check=True)
    manifest=read(BASE/'review/manifest.json')
    assert manifest['candidate']['sha256']==draft['candidate']['sha256']
    assert manifest['independent_opinions']==0 and all(t['status']=='NOT_STARTED' for t in manifest['tasks'])
    for task in manifest['tasks']:
        if task['role']=='LOCAL_CONTRACT_AND_STATE':
            assert str(BASE/'reading-inputs/scenario.json') in {r['path'] for r in task['read_inputs']}
    return {'status':'PASS','scope':'CUSTODY_SCOPE_DELTA_AND_BUDGET_ONLY','draft':imported['draft'],'candidate':draft['candidate'],'current_compatibility':compatibility,'packets':packet,'paragraphs':len(ids),'historical_findings_retained':len(findings),'independent_opinions_on_new_candidate':0,'semantic_status':'PENDING','literary_status':'PENDING','source_and_corpus_review':'NOT_CHECKED','production_admission':'NOT_GRANTED','authority_effect':'NONE'}

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
