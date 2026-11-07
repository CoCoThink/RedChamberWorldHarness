from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.world_projection import create_projection, project, verify_projection
from rcwh.generation.snapshots import freeze_inputs, InputSnapshot
from rcwh.generation.records import binding

ROOT = Path(__file__).resolve().parents[1]
QUERY = {'version': 1, 'chapter': 87, 'characters': ['baochai', 'baoyu', 'fengjie']}

@pytest.fixture
def world(tmp_path):
    shutil.copytree(ROOT / 'data/world', tmp_path / 'data/world')
    shutil.copytree(ROOT / 'schemas', tmp_path / 'schemas')
    return tmp_path


def change(root, name, fn):
    path = root / f'data/world/m3_{name}.json'
    doc = json.loads(path.read_bytes()); fn(doc); path.write_bytes(canonical_bytes(doc))


def test_entry_is_prior_chapter_and_does_not_assert_prose_or_source_authority(world):
    p = project(world, QUERY)
    assert p['material']['entry']['chapter'] == 86
    assert p['material']['entry']['characters']['baoyu']['marital_status'] == 'UNMARRIED'
    assert set(p['material']['core']['baseline']['characters']) == set(QUERY['characters'])
    assert p['semantic_replay'] == 'NOT_CHECKED' and p['authority_effect'] == 'NONE'


@pytest.mark.parametrize('mutation', ['unrelated_character', 'unrelated_event', 'future_event', 'governance'])
def test_unconsumed_mutations_preserve_exact_material(world, mutation):
    before = project(world, QUERY)
    if mutation == 'unrelated_character':
        change(world, 'core', lambda d: next(c for c in d['characters'] if c['id']=='xiangling').update(name='unrelated name'))
    elif mutation == 'governance':
        (world / 'data/project').mkdir(); (world / 'data/project/closure_roots.json').write_text('{}')
    else:
        chapter, person = (88, 'baoyu') if mutation == 'future_event' else (85, 'xiangling')
        change(world, 'core', lambda d: d['events'].append({'id':'NEW','chapter':chapter,'sequence':999,
            'effects':[{'set':f'characters.{person}.body_state','value':'new'}]}))
    assert project(world, QUERY) == before
    verify_projection(world, before)


@pytest.mark.parametrize('mutation', ['selected_definition','baseline','added_event','removed_entity','new_field','rule','query','changed_group'])
def test_consumed_or_unknown_changes_invalidate_even_without_a_previously_bound_event(world, mutation):
    before = project(world, QUERY)
    if mutation == 'selected_definition':
        change(world,'core',lambda d: next(c for c in d['characters'] if c['id']=='baoyu').update(name='changed'))
    elif mutation == 'baseline':
        change(world,'core',lambda d: d['baseline']['characters']['baoyu'].update(body_state='UNKNOWN'))
    elif mutation == 'changed_group':
        change(world,'core',lambda d: next(c for c in d['characters'] if c['id']=='baoyu').update(groups=['new']))
    elif mutation == 'added_event':
        change(world,'core',lambda d: d['events'].append({'id':'NEW','chapter':86,'sequence':999,
            'effects':[{'set':'characters.baoyu.body_state','value':'new'}]}))
    elif mutation == 'removed_entity':
        change(world,'core',lambda d: d['characters'].__setitem__(slice(None),[c for c in d['characters'] if c['id']!='baoyu']))
    elif mutation == 'new_field':
        change(world,'core',lambda d: d.update(unknown_constraints=[]))
    elif mutation == 'query':
        before['query']['version']=2
    else:
        before['rule_sha256']='0'*64
    with pytest.raises((ValueError, KeyError)):
        verify_projection(world,before)


def test_material_snapshot_survives_carrier_retirement(world):
    refs=create_projection(world,87,QUERY['characters'])
    snapshot=InputSnapshot(world,freeze_inputs(world,[refs['projection']]))
    frozen=snapshot.read(refs['projection'])
    shutil.rmtree(world/'data/world')
    assert snapshot.read(refs['projection'])==frozen
    with pytest.raises(OSError):
        verify_projection(world,json.loads(frozen))
    assert not any('m3_' in ref['original']['path'] for ref in snapshot.document['entries'])


def test_session_history_and_revision_keep_frozen_projection_but_live_admission_stales(session_root, monkeypatch):
    from test_session_generation import session_root as unused, imported, saved
    from rcwh.generation import render as renderer
    from rcwh.generation.session import prepare_request, verify_prepared_request
    from rcwh.generation.lineage import current_compatibility
    from rcwh.generation.writing import load_draft, revision_prompt, feedback_report
    from copy import deepcopy
    root=session_root
    shutil.copytree(ROOT/'data/world',root/'data/world',dirs_exist_ok=True)
    ref=create_projection(root,89,QUERY['characters'])['projection']
    report=renderer.LiteraryInputs(None).package('package.json')
    report['package']['world']=[ref]
    saved(root,'package.json',report['package'])
    monkeypatch.setattr(renderer,'LiteraryInputs',lambda catalog:type('Inputs',(),{'package':lambda self,path:deepcopy(report)})())
    packet=prepare_request(root,package_path='package.json',chapter=89,renderer_version=2)
    saved(root,'request.json',packet);(root/'authored.txt').write_text('甲说：“未必。”\n')
    draft=imported(root)
    before=load_draft(root,draft['draft']['path'])
    assert current_compatibility(root,draft['draft']['path'])['compatibility']=='CURRENT'
    change(root,'core',lambda d:next(c for c in d['characters'] if c['id']=='xiangling').update(name='unrelated'))
    assert verify_prepared_request(root,packet)['task']==packet['task']
    change(root,'core',lambda d:d['baseline']['characters']['baoyu'].update(body_state='UNKNOWN'))
    assert current_compatibility(root,draft['draft']['path'])['compatibility']=='STALE'
    with pytest.raises(ValueError,match='STALE_WORLD_PROJECTION'):
        verify_prepared_request(root,packet)
    assert load_draft(root,draft['draft']['path'])==before
    feedback=feedback_report(root,draft['draft']['path'])
    saved(root,'feedback.json',feedback)
    revision=revision_prompt(root,draft['draft']['path'],'feedback.json',renderer_version=2)
    assert revision['task']['writing_task']==packet['task']

# Import existing fixtures only; their generated prose and reviews stay in tmp_path.
from test_generation import root
from test_session_generation import session_root


@pytest.mark.parametrize('fault', ['executable', 'missing_participant', 'mixed', 'legacy'])
def test_renderer_refuses_unscoped_or_incompatible_consumers(session_root, monkeypatch, fault):
    from test_session_generation import saved
    from rcwh.generation import render as renderer
    root=session_root
    shutil.copytree(ROOT/'data/world',root/'data/world',dirs_exist_ok=True)
    report=renderer.LiteraryInputs(None).package('package.json')
    report['package']['world']=[create_projection(root,89,QUERY['characters'])['projection']]
    if fault=='mixed':
        report['package']['world'].append(binding(root,'data/world/version.json'))
    if fault=='executable':
        (root/'data/scenes').mkdir(exist_ok=True)
        saved(root,'data/scenes/executable.json',{'id':'exec','chapter':89})
    if fault=='missing_participant':
        saved(root,'data/planning/scenes/s.json',{'id':'s','chapter':89,'participants':['xiren']})
    saved(root,'package.json',report['package'])
    monkeypatch.setattr(renderer,'LiteraryInputs',lambda catalog:type('Inputs',(),{'package':lambda self,path:deepcopy(report)})())
    with pytest.raises(ValueError,match='world projection'):
        renderer.PromptRenderer(root,version=1 if fault=='legacy' else 2).draft('package.json',89)


def test_new_group_knowledge_is_found_by_fresh_query(world):
    p=project(world,QUERY)
    char=next(c for c in p['material']['core']['characters'] if c['id']=='baoyu')
    target=char['groups'][0]
    change(world,'knowledge',lambda d:d['knowledge_rules'].append({'chapter':86,'targets':[target],'fact':'new fact','kind':'UNKNOWN'}))
    with pytest.raises(ValueError,match='STALE_WORLD_PROJECTION'):
        verify_projection(world,p)


@pytest.mark.parametrize('field', ['protocol_version','query'])
def test_boolean_cannot_impersonate_protocol_version(world,field):
    p=project(world,QUERY)
    if field=='query':p['query']['version']=True
    else:p['protocol_version']=True
    with pytest.raises(ValueError):verify_projection(world,p)
