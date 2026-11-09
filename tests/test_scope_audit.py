from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.scope_audit import assess, bundle, reconstruct


@pytest.fixture
def packet():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root/'artifacts/prompt-view-pilot-20261108/prepared-request.json').read_bytes())


def test_real_scope_coverage_does_not_upgrade_unmapped_scenes_or_unknowns(packet):
    before=deepcopy(packet); report=assess(packet['task'])
    assert report['status']=='PENDING' and report['explicit_id_coverage']=='PASS'
    assert len(report['contracts'])==6
    codes=[f['code'] for f in report['findings']]
    assert codes.count('NO_EXECUTABLE_SCENE_ID_MATCH')==6
    assert codes.count('NO_LOCAL_KNOWLEDGE_BINDING')==6
    assert {f['detail'] for f in report['findings'] if f['code']=='NO_SCENE_KNOWLEDGE_ENTRY'}=={'liwan','wangfuren'}
    assert all(not s['local_state_proven'] for c in report['contracts'] for s in c['states'])
    for original, row in zip(packet['task']['agent_contracts'], report['contracts'],strict=True):
        assert row['unresolved']==original['unresolved']
        assert [s['declaration'] for s in row['states']]==[x for key in ('entry_state','preconditions','exit_state') for x in original[key]]
    assert 'xueyan' not in report['selected']['characters']
    assert {'medicine_bowl_86','OBJ-MEDICINE-BOWL-86'} <= set(report['selected']['objects'])
    assert packet==before


@pytest.mark.parametrize('fault,code', [('participant','MISSING_PARTICIPANT'),('object','MISSING_REQUIRED_OBJECT'),
                                     ('fact','MISSING_FACT_ID'),('state','NO_PROJECTED_STATE_FIELD')])
def test_missing_explicit_scope_fails_instead_of_disappearing_in_pending(packet,fault,code):
    task=packet['task']; c=task['agent_contracts'][0]
    if fault=='participant': c['participants'].append('missing_actor')
    elif fault=='object': c['required_objects'].append('missing_object')
    elif fault=='fact': c['references']['knowledge'][0]['value']['id']='missing_fact'
    else: c['entry_state'][0]['equals']='character.daiyu.missing_field'
    report=assess(task)
    assert report['status']==report['explicit_id_coverage']=='FAIL'
    assert any(f['status']=='FAIL' and f['code']==code for f in report['findings'])


def test_full_partition_reconstructs_export_exactly_and_assigns_every_fragment(packet):
    raw=canonical_bytes(packet['request']); manifest,files=bundle(packet,raw)
    assert reconstruct(manifest,files)==raw
    assert all(len(raw)<=65536 for raw in files.values())
    assert max(t['reserved_total_bytes'] for t in manifest['assignments'])<=131072
    assert set(files)=={f for t in manifest['assignments'] for f in t['files']}
    assert len(manifest['assignments'])==8  # Six contracts, projection, packed residual context.
    assert all(t['status']=='NOT_STARTED' for t in manifest['assignments'])
    view=packet['prompt_view']['payload']
    for identity,value in view['shared'].items():
        assert files[manifest['shared_fragments'][identity]]==canonical_bytes(value)
    assert all(t['input_bytes']==sum(len(files[p]) for p in t['files']) for t in manifest['assignments'])


@pytest.mark.parametrize('limits',[{'max_file_bytes':1024},{'max_task_bytes':1024},{'overhead_bytes':True}])
def test_partition_refuses_actual_limits(limits,packet):
    with pytest.raises(ValueError): bundle(packet,canonical_bytes(packet['request']),**limits)


@pytest.mark.parametrize('fault',['fragment','unassigned','budget','negative','no_instructions','future_entry'])
def test_delivered_partition_cannot_hide_material_or_forge_admission(packet,fault):
    manifest,files=bundle(packet,canonical_bytes(packet['request']))
    if fault=='fragment': files[next(iter(files))]=b'{}'
    elif fault=='unassigned':
        manifest['assignments']=[t for t in manifest['assignments'] if 'task-00.json' not in t['files']]
    elif fault=='budget': manifest['assignments'][0]['input_bytes']-=1
    elif fault=='negative': manifest['limits']['overhead_bytes']=-1
    elif fault=='no_instructions': manifest['assignments'][0]['files'].remove('instructions.txt')
    else:
        # Even recomputed fragment hashes cannot change the original author input.
        path=manifest['task_fragments']['world'];value=json.loads(files[path]);doc=next(iter(value.values()))
        doc['knowledge_runtime']['scenes'][0]['entry']['baoyu']['knows'].append('daiyu_death_exact_moment')
        files[path]=canonical_bytes(value);manifest['files'][path]={'sha256':digest(files[path]),'bytes':len(files[path])}
        for task in manifest['assignments']:
            task['input_bytes']=sum(len(files[p]) for p in task['files'])
            task['reserved_total_bytes']=task['input_bytes']+manifest['limits']['overhead_bytes']+manifest['limits']['output_bytes']
    with pytest.raises(ValueError): reconstruct(manifest,files)


def test_oversize_preparation_publishes_nothing(tmp_path,packet,monkeypatch):
    import importlib.util
    spec=importlib.util.spec_from_file_location('scope_review_tool',Path(__file__).resolve().parents[1]/'tools/prepare_scope_review.py')
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    from rcwh.generation.records import binding
    monkeypatch.setattr(tool,'verify_prepared_request',lambda *args:None)
    monkeypatch.setattr(tool,'verify_frozen_request',lambda *args:None)
    (tmp_path/'packet.json').write_bytes(canonical_bytes(packet))
    raw=canonical_bytes(packet['request']);(tmp_path/'payload.json').write_bytes(raw)
    from rcwh.generation.session import EXECUTION_BASIS
    receipt={'kind':'SESSION_PAYLOAD_EXPORT','version':1,'prepared_request':binding(tmp_path,'packet.json'),
             'payload':binding(tmp_path,'payload.json'),'byte_admission':packet['byte_admission'],
             'execution_basis':EXECUTION_BASIS,'consumption_proof':False,'authority_effect':'NONE'}
    (tmp_path/'receipt.json').write_bytes(canonical_bytes(receipt))
    with pytest.raises(ValueError,match='byte ceiling'):
        tool.prepare(tmp_path,'packet.json','receipt.json','review',max_task_bytes=1)
    assert not (tmp_path/'review').exists()
    result=tool.prepare(tmp_path,'packet.json','receipt.json','review')
    assert result['status']=='PASS' and result['scope_status']=='PENDING'
    assert tool.check(tmp_path,'review')['exact_request_reconstructed'] is True
    before={p.name:p.read_bytes() for p in (tmp_path/'review').iterdir()}
    with pytest.raises(ValueError,match='already exists'):
        tool.prepare(tmp_path,'packet.json','receipt.json','review')
    assert before=={p.name:p.read_bytes() for p in (tmp_path/'review').iterdir()}
    report=tmp_path/'review/scope-report.json'; doc=json.loads(report.read_bytes());doc['status']='PASS'
    report.write_bytes(canonical_bytes(doc))
    with pytest.raises(ValueError,match='scope report differs'): tool.check(tmp_path,'review')
