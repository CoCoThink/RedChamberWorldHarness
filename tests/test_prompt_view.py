from copy import deepcopy
import json

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.prompt_view import admission, encode, expand, frozen_prompt
from rcwh.generation.session import prepare_request, verify_frozen_request, verify_prepared_request
from test_generation import root
from test_session_generation import session_root, observed_session, saved, imported, set_observer_python

LIMITS = {'version':1, 'max_context_bytes':500000, 'overhead_reserve_bytes':32768, 'output_reserve_bytes':24000}
OPTIONS = {'renderer_version':2, 'prompt_view_version':1, 'context_limits':LIMITS}


def test_lossless_shared_values_preserve_null_literals_arrays_and_all_constraints():
    contract = {'must':['约束不得删除']*200, 'unknown':None, 'literal':{'$shared':'not-a-reference'}}
    task = {'plan':{'a/b~c':contract}, 'contracts':[contract], 'unknown':None,
            'list':[{'data':[1,2,3]}, None], 'negative':['FAIL','PENDING']}
    before = deepcopy(task); payload = encode(task)
    assert len(payload['shared']) == 1 and len(payload['bindings']) == 2
    assert expand(payload) == before == task
    assert len(canonical_bytes(payload)) < len(canonical_bytes(task))
    assert payload['task']['unknown'] is None


def test_small_or_single_values_are_retained_without_pointless_indirection():
    task = {'a':{'small':'text'}, 'b':{'small':'text'}, 'one':{'large':'文'*2000}}
    payload = encode(task)
    assert payload['shared'] == {} and payload['bindings'] == []
    assert expand(payload) == task


@pytest.mark.parametrize('size,shared',[(1023,False),(1024,True)])
def test_sharing_threshold_uses_exact_canonical_utf8_bytes(size,shared):
    value={'v':''}; value['v']='x'*(size-len(canonical_bytes(value)))
    assert len(canonical_bytes(value))==size
    payload=encode({'a':value,'b':value})
    assert bool(payload['shared']) is shared
    assert expand(payload)=={'a':value,'b':value}


@pytest.mark.parametrize('fault', ['missing_value','unused_value','changed_value','duplicate_path','overlap',
                                  'non_placeholder','bad_index','boolean_version','invalid_payload','invalid_binding'])
def test_shared_view_rejects_forged_or_ambiguous_bindings(fault):
    obj = {'contents':'文'*1200, 'unknown':None}; task = {'a':obj,'b':obj}
    payload = encode(task); identity = next(iter(payload['shared']))
    if fault == 'missing_value': payload['shared'].pop(identity)
    elif fault == 'unused_value':
        extra = {'contents':'另'*1200}; payload['shared'][digest(canonical_bytes(extra))] = extra
    elif fault == 'changed_value': payload['shared'][identity]['contents'] = 'changed'
    elif fault == 'duplicate_path': payload['bindings'].append(deepcopy(payload['bindings'][0]))
    elif fault == 'overlap': payload['bindings'].append({'path':['a','unknown'],'value':identity})
    elif fault == 'non_placeholder': payload['task']['a'] = 'not-null'
    elif fault == 'bad_index': payload['bindings'][0]['path'] = ['missing',0]
    elif fault == 'invalid_payload': payload = None
    elif fault == 'invalid_binding': payload['bindings'][0] = {'path':['a'],'value':[]}
    else: payload['version'] = True
    with pytest.raises(ValueError): expand(payload)


@pytest.fixture
def view_root(session_root, monkeypatch):
    monkeypatch.setattr('rcwh.generation.render.DEFAULT_RENDERER_VERSION', 2)
    return session_root


def prepared(root, **changes):
    options = {**OPTIONS, **changes}
    return prepare_request(root, package_path='package.json', chapter=89, **options)


def test_context_reservations_admit_exact_boundary_and_reject_one_byte_less(view_root):
    packet = prepared(view_root)
    total = packet['byte_admission']['reserved_total_bytes']
    limits = {**LIMITS, 'max_context_bytes':total}
    exact = prepared(view_root, context_limits=limits)
    assert exact['byte_admission']['status']=='PASS'
    assert exact['byte_admission']['token_capacity_status']=='NOT_MEASURED'
    assert exact['request']==packet['request']
    with pytest.raises(ValueError, match='context byte budget'):
        prepared(view_root, context_limits={**limits,'max_context_bytes':total-1})
    assert not (view_root/'artifacts').exists()


@pytest.mark.parametrize('field,value', [('version',True), ('max_context_bytes',True),
                                      ('overhead_reserve_bytes',-1), ('output_reserve_bytes',0)])
def test_context_limits_use_valid_byte_values_without_boolean_integer_coercion(view_root,field,value):
    with pytest.raises(ValueError): prepared(view_root, context_limits={**LIMITS,field:value})


def test_shared_view_is_opt_in_and_refuses_legacy_renderer(view_root):
    legacy = prepare_request(view_root,package_path='package.json',chapter=89,renderer_version=2)
    assert 'prompt_view' not in legacy and 'context_limits' not in legacy['context']
    assert 'byte_admission' not in legacy
    with pytest.raises(ValueError,match='renderer v2'):
        prepared(view_root,renderer_version=1)


@pytest.mark.parametrize('fault', ['missing_report','missing_context','forged_admission','payload','rehashed_task'])
def test_prepared_view_rejects_tampering_even_when_provider_hashes_are_recomputed(view_root,fault):
    packet = prepared(view_root)
    if fault == 'missing_report': packet.pop('byte_admission')
    elif fault == 'missing_context': packet['context'].pop('context_limits')
    elif fault == 'forged_admission': packet['byte_admission']['request_bytes'] = 0
    elif fault == 'payload': packet['prompt_view']['payload']['task']['chapter'] = 1
    else:
        packet['task']['guidance'] = 'injected replacement guidance'
        packet['prompt_view']['payload'] = encode(packet['task'])
        packet['prompt_view']['task_sha256'] = digest(canonical_bytes(packet['task']))
        rebuilt = frozen_prompt(view_root,packet,packet['task'])
        packet['prompt_sha256'] = rebuilt['prompt_sha256']
        packet['request'].update(system=rebuilt['system'],messages=rebuilt['messages'])
        packet['request_sha256'] = digest(canonical_bytes(packet['request']))
        packet['byte_admission'] = admission(packet['request'],LIMITS)
    with pytest.raises(ValueError): verify_prepared_request(view_root,packet)


def test_session_import_checks_actual_output_bytes_before_any_publication(view_root):
    packet = prepared(view_root,context_limits={**LIMITS,'output_reserve_bytes':1})
    saved(view_root,'request.json',packet); (view_root/'authored.txt').write_text('甲说道：“不知。”\n')
    with pytest.raises(ValueError, match='reserved UTF-8 bytes'): imported(view_root)
    assert not (view_root/'artifacts').exists()
    assert not (view_root/'data/writing/drafts').exists()


def test_export_contains_exact_admitted_payload_and_preserves_separate_custody(view_root):
    from rcwh.generation.session import export_request
    packet=prepared(view_root);saved(view_root,'request.json',packet)
    result=export_request(view_root,'request.json')
    raw=(view_root/result['payload']['path']).read_bytes()
    assert raw==canonical_bytes(packet['request'])
    assert len(raw)==packet['byte_admission']['request_bytes']
    assert set(json.loads(raw))=={'system','messages','model','max_tokens'}
    assert result['consumption_proof'] is False
    assert result['prepared_request']['sha256']==digest((view_root/'request.json').read_bytes())
    assert export_request(view_root,'request.json')==result


def test_export_rejects_stale_or_forged_requests_before_publication(view_root):
    from rcwh.generation.session import export_request
    packet=prepared(view_root);packet['byte_admission']['request_bytes']=0
    saved(view_root,'request.json',packet)
    with pytest.raises(ValueError): export_request(view_root,'request.json')
    assert not (view_root/'artifacts').exists()


def test_shared_import_requires_export_receipt_before_publication(view_root):
    saved(view_root,'request.json',prepared(view_root))
    (view_root/'authored.txt').write_text('甲说道：“不知。”\n')
    with pytest.raises(ValueError,match='requires a payload export receipt'): imported(view_root)
    assert not (view_root/'artifacts').exists()


@pytest.mark.parametrize('fault',['source','payload','consumption','missing_binding'])
def test_shared_import_rejects_invalid_export_custody_before_publication(view_root,fault):
    from rcwh.generation.session import export_request
    saved(view_root,'request.json',prepared(view_root))
    (view_root/'authored.txt').write_text('甲说道：“不知。”\n')
    result=export_request(view_root,'request.json')
    receipt=json.loads((view_root/result['receipt']['path']).read_bytes())
    if fault=='source': receipt['prepared_request']['sha256']='0'*64
    elif fault=='consumption': receipt['consumption_proof']=True
    elif fault=='missing_binding': receipt.pop('payload')
    else:
        (view_root/'wrong.json').write_bytes(b'{}')
        receipt['payload']={'path':'wrong.json','sha256':digest(b'{}')}
    saved(view_root,'forged-receipt.json',receipt)
    before={str(p) for p in (view_root/'artifacts').rglob('*')}
    with pytest.raises(ValueError): imported(view_root,payload_export_path='forged-receipt.json')
    assert {str(p) for p in (view_root/'artifacts').rglob('*')}==before
    assert not (view_root/'data/writing/drafts').exists()


def test_frozen_history_does_not_recompile_and_revisions_keep_full_parent(view_root,monkeypatch):
    from rcwh.generation.records import store
    from rcwh.generation.writing import load_draft,feedback_report
    from rcwh.generation import prompt_view
    from rcwh.generation.session import export_request
    packet = prepared(view_root)
    saved(view_root,'request.json',packet); (view_root/'authored.txt').write_text('甲说道：“不知。”\n\n乙退了。')
    first_export=export_request(view_root,'request.json')
    first = imported(view_root,payload_export_path=first_export['receipt']['path'])
    run=json.loads((view_root/first['run']['path']).read_bytes())
    assert run['payload_export']==first_export['receipt'] and run['exported_payload']==first_export['payload']
    before = load_draft(view_root,first['draft']['path'])
    with monkeypatch.context() as scoped:
        def refuse(*args): raise AssertionError('history must not use current compactor')
        scoped.setattr(prompt_view,'encode',refuse)
        assert load_draft(view_root,first['draft']['path'])==before
        verify_frozen_request(view_root,packet)
        feedback = feedback_report(view_root,first['draft']['path'])
    ref = store(view_root,'data/writing/feedback',feedback)
    revision = prepare_request(view_root,parent_path=first['draft']['path'],feedback_path=ref['path'],**OPTIONS)
    assert revision['task']['writing_task']==packet['task']
    assert expand(revision['prompt_view']['payload'])==revision['task']
    saved(view_root,'request.json',revision);(view_root/'authored.txt').write_text('甲只摇头。\n\n乙退了。')
    second_export=export_request(view_root,'request.json')
    second = imported(view_root,payload_export_path=second_export['receipt']['path'])
    assert load_draft(view_root,second['draft']['path'])[0]['parent']==first['draft']
    # The extra view instruction is also frozen, so current path retirement is safe.
    (view_root/'data/writing/prompts/shared-values-v1.md').unlink()
    for exported in (first_export,second_export):
        for field in ('payload','receipt'): (view_root/exported[field]['path']).unlink()
    assert load_draft(view_root,second['draft']['path'])[0]['parent']==first['draft']


@pytest.mark.parametrize('tamper',[False,True])
def test_shared_view_preserves_narrow_runtime_observation_normalization(observed_session,monkeypatch,tamper):
    from rcwh.generation.render import PromptRenderer
    root,source = observed_session
    monkeypatch.setattr('rcwh.generation.render.DEFAULT_RENDERER_VERSION',2)
    original = PromptRenderer.draft
    def with_metadata(self,*args,**kwargs):
        value=original(self,*args,**kwargs)
        return {**value,'renderer_version':2,'dependency_records':[],'readiness':{'scope':'TEST_OBSERVATION'}}
    monkeypatch.setattr(PromptRenderer,'draft',with_metadata)
    packet=prepared(root); before=deepcopy(packet)
    set_observer_python(source,'CPython 3.12.13')
    if tamper:
        source['record']['excerpt']='changed source text'
        with pytest.raises(ValueError): verify_prepared_request(root,packet)
    else:
        fresh=verify_prepared_request(root,packet)
        assert fresh['task']!=packet['task']
        assert expand(fresh['prompt_view']['payload'])==fresh['task']
    assert packet==before


def test_runtime_observation_drift_cannot_hide_a_changed_shared_encoder(observed_session,monkeypatch):
    from rcwh.generation.render import PromptRenderer
    from rcwh.generation import prompt_view
    root,source=observed_session
    monkeypatch.setattr('rcwh.generation.render.DEFAULT_RENDERER_VERSION',2)
    original_draft=PromptRenderer.draft
    def with_repeated_material(self,*args,**kwargs):
        value=original_draft(self,*args,**kwargs)
        value['task']['repeated_context']=[{'constraint':'不得改动'*400}]*2
        return {**value,'renderer_version':2,'dependency_records':[],'readiness':{'scope':'TEST_OBSERVATION'}}
    monkeypatch.setattr(PromptRenderer,'draft',with_repeated_material)
    packet=prepared(root)
    assert len(packet['prompt_view']['payload']['bindings'])>=2
    set_observer_python(source,'CPython 3.12.13')
    original_encode=prompt_view.encode
    def reversed_bindings(task):
        value=original_encode(task);value['bindings'].reverse();return value
    monkeypatch.setattr(prompt_view,'encode',reversed_bindings)
    with pytest.raises(ValueError,match='algorithm drift'):
        verify_prepared_request(root,packet)


def test_cli_shared_view_requires_reservations_and_blocks_provider_execution(view_root,capsys):
    import argparse
    from rcwh.application.write import add_commands,command
    parser=argparse.ArgumentParser();parser.add_argument('--root');add_commands(parser.add_subparsers())
    base=['--root',str(view_root),'write','draft','package.json','--chapter','89','--shared-view']
    assert command(parser.parse_args(base))==1
    assert json.loads(capsys.readouterr().out)['status']=='FAIL'
    flags=['--context-bytes','500000','--context-overhead-bytes','32768','--context-output-bytes','24000']
    assert command(parser.parse_args(base+flags))==0
    packet=json.loads(capsys.readouterr().out)
    assert packet['byte_admission']['status']=='PASS'
    assert command(parser.parse_args(base+flags+['--execute','--network-consent']))==1
    assert 'DRY_RUN/import only' in json.loads(capsys.readouterr().out)['findings'][0]
