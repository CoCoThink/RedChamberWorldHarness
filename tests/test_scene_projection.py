from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.scene_projection import project, verify_projection, frozen_knowledge, create_projection
from rcwh.io import load_data
from test_generation import root
from test_session_generation import session_root

ROOT = Path(__file__).resolve().parents[1]
QUERY = {'version': 1, 'chapter': 86, 'characters': ['baoyu', 'daiyu', 'zijuan'],
         'scenes': [{'path': 'data/scenes/ch86_last_night.yaml', 'objects': ['OBJ-MEDICINE-BOWL-86'],
                     'object_checkpoint': 'ENTRY',
                     'knowledge_checkpoints': ['ENTRY', 'K86-ZIJUAN-SEES-RAPID-DECLINE']}]}


def write(root, path, data):
    p = root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(canonical_bytes(data))


def mutate(root, path, fn):
    data = load_data(root / path); fn(data); write(root, path, data)


@pytest.fixture
def scene_root(tmp_path):
    for folder in ('world', 'objects', 'knowledge', 'scenes'):
        shutil.copytree(ROOT / 'data' / folder, tmp_path / 'data' / folder)
    return tmp_path


def test_scene_entry_keeps_independent_truth_layers_and_no_future_knowledge(scene_root):
    p = project(scene_root, QUERY); scene = p['scenes'][0]
    assert scene['entry']['values']['object.medicine_bowl_86.temperature'] == 'warm'
    assert scene['entry']['values']['object.OBJ-MEDICINE-BOWL-86.location'] == 's02'
    assert scene['entry']['values']['object.medicine_bowl_86.location'] == 'xiaoxiang_room'
    assert scene['entry']['origins']['character.daiyu.resources.physical_strength'] == 'SCENE_LOCAL_RECONSTRUCTION_INPUT'
    assert scene['entry']['knowledge']['states']['zijuan']['suspects'] == []
    assert scene['knowledge_checkpoints']['K86-ZIJUAN-SEES-RAPID-DECLINE']['states']['zijuan']['suspects'] == ['daiyu_may_die_tonight']
    assert 'daiyu_death_exact_moment' in scene['entry']['knowledge']['states']['baoyu']['does_not_know']
    assert p['semantic_replay'] == 'NOT_CHECKED' and p['authority_effect'] == 'NONE'


@pytest.mark.parametrize('case', ['unrelated_object', 'future_transition', 'unrelated_knowledge', 'later_knowledge'])
def test_unconsumed_changes_preserve_exact_scene_material(scene_root, case):
    before = project(scene_root, QUERY)
    if case == 'unrelated_object':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['objects'][0].update(name='unrelated'))
    elif case == 'future_transition':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['transitions'].append({
            'id': 'NEW', 'object_id': 'OBJ-MEDICINE-BOWL-86', 'chapter': 87, 'sequence': 999,
            'from': {}, 'to': {'temperature': 'UNKNOWN'}}))
    else:
        sid = 'ch89_confiscation_message' if case == 'unrelated_knowledge' else 'ch86_last_night'
        def change(d):
            s = next(s for s in d['scenes'] if s['id'] == sid)
            s['events'][-1]['updates'] = []
        mutate(scene_root, 'data/knowledge/v03_slice2.json', change)
    verify_projection(scene_root, before)
    assert project(scene_root, QUERY) == before


@pytest.mark.parametrize('case', ['baseline', 'legacy', 'new_transition', 'new_knowledge', 'fact', 'new_scene', 'edge', 'rules'])
def test_relevant_changes_and_new_dependencies_invalidate(scene_root, case):
    before = project(scene_root, QUERY)
    if case == 'baseline':
        mutate(scene_root, 'data/objects/m4.json', lambda d: next(o for o in d['objects'] if o['id']=='OBJ-MEDICINE-BOWL-86')['baseline'].update(temperature='cold'))
    elif case == 'legacy':
        mutate(scene_root, 'data/objects/medicine_bowl.yaml', lambda d: d['state'].update(temperature='cold'))
    elif case == 'new_transition':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['transitions'].append({'id':'NEW','object_id':'OBJ-MEDICINE-BOWL-86','chapter':85,'sequence':900,'from':{},'to':{'temperature':'UNKNOWN'}}))
    elif case == 'new_knowledge':
        mutate(scene_root, 'data/knowledge/v03_slice2.json', lambda d: d['scenes'][0]['events'].append({'id':'NEW','sequence':5,'updates':[]}))
    elif case == 'fact':
        mutate(scene_root, 'data/knowledge/v03_slice2.json', lambda d: d['facts'][0].update(label='changed'))
    elif case == 'new_scene':
        write(scene_root, 'data/scenes/new.json', {'id':'new','chapter':86,'participants':['baoyu']})
    elif case == 'edge':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['identity_edges'].append({'id':'NEW','from':'OBJ-MEDICINE-BOWL-86','to':'OBJ-TONGLING-JADE','status':'OPEN'}))
    else:
        before['rules']['src/rcwh/generation/scene_projection.py'] = '0'*64
    with pytest.raises((ValueError, KeyError)):
        verify_projection(scene_root, before)


@pytest.mark.parametrize('case', ['unknown_object', 'missing_object', 'duplicate_order', 'duplicate_event',
                                  'unknown_fact', 'missing_checkpoint', 'missing_character', 'unknown_field',
                                  'boolean_version', 'deleted_object', 'deleted_legacy', 'missing_knowledge_scene',
                                  'unknown_edge_shape'])
def test_unsupported_or_incomplete_scene_scope_fails_closed(scene_root, case):
    query = deepcopy(QUERY)
    if case == 'unknown_object': query['scenes'][0]['objects'] = ['MISSING']
    elif case == 'missing_object': query['scenes'][0]['objects'] = []
    elif case == 'missing_checkpoint': query['scenes'][0]['knowledge_checkpoints'] = ['K86-ZIJUAN-SEES-RAPID-DECLINE']
    elif case == 'missing_character': query['characters'].remove('zijuan')
    elif case == 'boolean_version': query['version'] = True
    elif case == 'deleted_object':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d.update(objects=[o for o in d['objects'] if o['id']!='OBJ-MEDICINE-BOWL-86']))
    elif case == 'deleted_legacy':
        (scene_root/'data/objects/medicine_bowl.yaml').unlink()
    elif case == 'missing_knowledge_scene':
        mutate(scene_root, 'data/knowledge/v03_slice2.json', lambda d: d.update(scenes=[s for s in d['scenes'] if s['chapter']!=86]))
    elif case == 'unknown_edge_shape':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['identity_edges'].append({'id':'NEW','from':'OBJ-MEDICINE-BOWL-86','new_target':'UNKNOWN'}))
    elif case == 'unknown_field':
        mutate(scene_root, 'data/objects/m4.json', lambda d: d.update(new_rules=[]))
    elif case == 'unknown_fact':
        mutate(scene_root, 'data/knowledge/v03_slice2.json', lambda d: d['scenes'][0]['entry']['baoyu']['knows'].append('MISSING'))
    elif case == 'duplicate_event':
        mutate(scene_root, 'data/knowledge/v03_slice2.json', lambda d: d['scenes'][0]['events'].append(deepcopy(d['scenes'][0]['events'][0])))
    else:
        mutate(scene_root, 'data/objects/m4.json', lambda d: d['transitions'].append({**d['transitions'][0], 'id':'NEW'}))
    with pytest.raises((ValueError, KeyError, OSError)):
        project(scene_root, query)


def test_object_relationship_closure_preserves_distinct_identity_nodes(scene_root):
    mutate(scene_root, 'data/objects/m4.json', lambda d: d['identity_edges'].append({
        'id':'NEW','from':'OBJ-MEDICINE-BOWL-86','to':'OBJ-TONGLING-JADE','status':'OPEN'}))
    objects = project(scene_root, QUERY)['scenes'][0]['objects']
    assert set(objects['states']) == {'OBJ-MEDICINE-BOWL-86','OBJ-TONGLING-JADE',
                                     'OBJ-SNOW-JADE-91','OBJ-ZHEN-PACKAGE-98'}
    assert objects['states']['OBJ-TONGLING-JADE']['holder'] == 'baoyu'
    assert objects['states']['OBJ-SNOW-JADE-91']['holder'] is None
    assert any(e['id']=='OID-01' for e in objects['edges'])


def test_named_object_checkpoint_replays_prefix_without_global_alias_or_clock_inference(scene_root):
    query = deepcopy(QUERY)
    mutate(scene_root, 'data/objects/m4.json', lambda d: next(o for o in d['objects'] if o['id']=='OBJ-MEDICINE-BOWL-86').pop('legacy_ref'))
    contract = load_data(scene_root / query['scenes'][0]['path'])
    contract['required_objects'] = ['OBJ-MEDICINE-BOWL-86']
    contract['preconditions'] = []
    contract['exit_state'] = []
    write(scene_root, query['scenes'][0]['path'], contract)
    query['scenes'][0]['object_checkpoint'] = 'OT86-01'
    p = project(scene_root, query)
    assert p['scenes'][0]['entry']['values']['object.OBJ-MEDICINE-BOWL-86.temperature'] == 'cold'
    assert p['scenes'][0]['entry']['knowledge']['checkpoint'] == 'ENTRY'
    assert p['scenes'][0]['entry']['temporal_alignment'] == 'NOT_INFERRED'
    mutate(scene_root, 'data/objects/m4.json', lambda d: d['transitions'].append({'id':'NEW','object_id':'OBJ-MEDICINE-BOWL-86','chapter':86,'sequence':50,'from':{},'to':{'temperature':'warm'}}))
    with pytest.raises(ValueError): verify_projection(scene_root, p)


def test_legacy_has_no_within_scene_clock_and_cannot_overwrite_network_checkpoint(scene_root):
    query = deepcopy(QUERY); query['scenes'][0]['object_checkpoint'] = 'OT86-01'
    with pytest.raises(ValueError, match='legacy object'):
        project(scene_root, query)


def test_boolean_cannot_impersonate_scene_material_protocol(scene_root):
    p = project(scene_root, QUERY); p['protocol_version'] = True
    with pytest.raises(ValueError): verify_projection(scene_root, p)


def test_history_and_feedback_use_frozen_scene_material_after_live_knowledge_changes(scene_root, session_root, monkeypatch):
    from test_session_generation import imported, saved
    from rcwh.generation import render
    from rcwh.generation.lineage import current_compatibility
    from rcwh.generation.session import prepare_request, verify_prepared_request
    from rcwh.generation.writing import feedback_report, load_draft
    if scene_root != session_root:
        for folder in ('world', 'objects', 'knowledge', 'scenes'):
            shutil.copytree(scene_root/'data'/folder, session_root/'data'/folder, dirs_exist_ok=True)
    # Existing fixture uses chapter 89; explicitly select its real executable scene.
    q = {'version':1,'chapter':89,'characters':['baochai','qianxue','xiaohong'],
         'scenes':[{'path':'data/scenes/ch89_confiscation_message.yaml','objects':[],
                    'object_checkpoint':'ENTRY','knowledge_checkpoints':['ENTRY','K89-OFFICIAL-MESSAGE-HEARD']}]}
    # qianxue/xiaohong have optional world bindings in the source runtime. This
    # fixture deliberately registers explicit unknown states, never infers them.
    def register(d):
        for cid in ['qianxue','xiaohong']:
            if not any(c['id']==cid for c in d['characters']):
                d['characters'].append({'id':cid,'name':cid,'groups':[]})
                d['baseline']['characters'][cid]={'life_state':'UNKNOWN'}
    mutate(session_root,'data/world/m3_core.json',register)
    ref = create_projection(session_root, q)['projection']
    report = render.LiteraryInputs(None).package('package.json')
    report['package']['world'] = [ref]; saved(session_root,'package.json',report['package'])
    monkeypatch.setattr(render,'LiteraryInputs',lambda catalog:type('Inputs',(),{'package':lambda self,path:deepcopy(report)})())
    def refuse_global(*args, **kwargs):
        raise AssertionError('projected rendering must not use the global state adapter')
    monkeypatch.setattr(render, 'SceneStateAdapter', refuse_global)
    packet = prepare_request(session_root,package_path='package.json',chapter=89,renderer_version=2)
    assert not any(r['path'].startswith(('data/world/m3_','data/knowledge/','data/objects/')) for r in packet['inputs'])
    saved(session_root,'request.json',packet); (session_root/'authored.txt').write_text('甲说：“未必。”\n')
    draft = imported(session_root); path = draft['draft']['path']
    before = load_draft(session_root,path)
    frozen = feedback_report(session_root,path)
    mutate(session_root,'data/knowledge/v03_slice2.json',lambda d:next(s for s in d['scenes'] if s['chapter']==89)['entry']['baochai']['knows'].append('official_confiscation_exact_scope'))
    assert current_compatibility(session_root,path)['compatibility']=='STALE'
    with pytest.raises(ValueError): verify_prepared_request(session_root,packet)
    assert load_draft(session_root,path)==before
    # Removing the live knowledge carrier proves feedback cannot secretly use it.
    (session_root/'data/knowledge/v03_slice2.json').unlink()
    after = feedback_report(session_root,path)
    assert after['semantic_requests'] == frozen['semantic_requests']
    assert after['checks'] == frozen['checks']
