from copy import deepcopy
import json
from pathlib import Path

import pytest

from rcwh.generation.local_scenario import compile_scenario, verify_material, checkpoint_view

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = 'data/writing/local-scenarios/ch86-v1/scenario.json'


@pytest.fixture
def scenario():
    return json.loads((ROOT / SCENARIO).read_bytes())


def event(scenario, name):
    return next(e for e in scenario['events'] if e['id'] == name)


def test_actual_model_keeps_arrival_knowledge_and_cold_medicine_distinct(scenario):
    checkpoints = compile_scenario(scenario)['checkpoints']
    key = 'actor.baoyu.knowledge.death_exact_moment'
    assert checkpoints['baoyu_arrives']['values'][key] == 'NOT_KNOWN'
    assert checkpoints['baoyu_asks_rewarm']['values'][key] == 'NOT_KNOWN'
    assert checkpoints['baoyu_learns_death_time']['values'][key] == 'KNOWS'
    assert checkpoints['ENTRY']['values']['object.OBJ-MEDICINE-BOWL-86.temperature'] == 'warm'
    assert checkpoints['baoyu_asks_rewarm']['values']['object.OBJ-MEDICINE-BOWL-86.temperature'] == 'UNKNOWN'
    terminal = checkpoints['terminal_cold_unfinished_medicine']['values']
    assert terminal['object.OBJ-MEDICINE-BOWL-86.temperature'] == 'cold'
    assert terminal['object.OBJ-MEDICINE-BOWL-86.status'] == 'CONTAINS_UNFINISHED_MEDICINE'
    assert terminal['object.medicine_bowl_86.temperature'] == 'UNKNOWN'
    assert terminal['actor.daiyu.body_action_capacity'] == 'UNKNOWN'
    assert all(c['execution'] == 'NOT_OBSERVED' for c in checkpoints.values())


def test_incomparable_branches_never_leak_knowledge(scenario):
    c = compile_scenario(scenario)['checkpoints']
    assert 'death_witnessed' not in c['baoyu_receives_critical_message']['events']
    assert 'baoyu_receives_critical_message' not in c['body_care_started']['events']
    assert c['body_care_started']['values']['actor.baoyu.knowledge.critical_decline'] == 'UNKNOWN_AT_UNORDERED_CUT'
    assert c['baoyu_receives_critical_message']['values']['actor.daiyu.life_state'] == 'UNKNOWN_AT_UNORDERED_CUT'
    assert c['baoyu_receives_critical_message']['scope'] == 'EDITORIAL_MODEL_ONLY_NOT_OBSERVED'


def test_transport_reconstructs_every_checkpoint_value_exactly(scenario):
    compiled = compile_scenario(scenario)
    view = checkpoint_view(compiled)
    for name, cp in compiled['checkpoints'].items():
        assert {**view['entry_values'], **view['checkpoints'][name]['overrides']} == cp['values']


@pytest.mark.parametrize('case', ['cycle', 'duplicate_event', 'unknown_actor', 'unknown_target',
                                  'future_message', 'unknown_sender_fact', 'unwitnessed_fact',
                                  'unordered_writes', 'false_from', 'request_reheats', 'fill_g01',
                                  'merge_bowls', 'invent_global_id', 'boolean_version', 'authority',
                                  'delivery_without_update', 'force_unordered_pair', 'fake_observed_execution',
                                  'unknown_field', 'claim_semantic_pass'])
def test_model_rejects_causal_identity_and_authority_mutations(scenario, case):
    if case == 'cycle': scenario['before'].append(['baoyu_arrives', 'ordinary_care'])
    elif case == 'duplicate_event': scenario['events'].append(deepcopy(scenario['events'][0]))
    elif case == 'unknown_actor': event(scenario, 'baoyu_arrives')['participants'].append('unregistered')
    elif case == 'unknown_target': event(scenario, 'baoyu_arrives')['effects'][0]['target'] = 'actor.unregistered.location'
    elif case == 'future_message': scenario['messages'][-1]['received_at'] = 'baoyu_arrives'
    elif case == 'unknown_sender_fact': scenario['messages'][1]['facts'] = ['death_exact_moment']
    elif case == 'unwitnessed_fact': event(scenario, 'death_witnessed')['observed_facts'] = []
    elif case == 'unordered_writes':
        event(scenario, 'body_care_started')['effects'].append({'target': 'object.OBJ-MEDICINE-BOWL-86.temperature',
            'from': 'warm', 'to': 'cold', 'reason': 'mutation'})
    elif case == 'false_from': event(scenario, 'medicine_cools')['effects'][0]['from'] = 'cold'
    elif case == 'request_reheats':
        event(scenario, 'baoyu_asks_rewarm')['effects'].append({'target': 'object.OBJ-MEDICINE-BOWL-86.temperature',
            'from': 'UNKNOWN', 'to': 'hot', 'reason': 'mutation'})
    elif case == 'fill_g01':
        event(scenario, 'unfinished_revision')['effects'].append({'target': 'object.local:ch86:pages.gap',
            'from': 'UNFILLED', 'to': 'FILLED', 'reason': 'mutation'})
    elif case == 'merge_bowls': scenario['objects'][1]['id'] = scenario['objects'][0]['id']
    elif case == 'invent_global_id': next(a for a in scenario['actors'] if a['name'] == '雪雁')['id'] = 'xueyan'
    elif case == 'boolean_version': scenario['version'] = True
    elif case == 'authority': scenario['production_admission'] = 'GRANTED'
    elif case == 'force_unordered_pair': scenario['before'].append(['body_care_started', 'baoyu_receives_critical_message'])
    elif case == 'fake_observed_execution': event(scenario, 'baoyu_arrives')['execution'] = 'OBSERVED'
    elif case == 'unknown_field': scenario['global_truth_override'] = True
    elif case == 'claim_semantic_pass': scenario['semantic_replay'] = 'PASS'
    else: event(scenario, 'liwan_notified')['effects'] = []
    with pytest.raises((ValueError, KeyError)):
        compile_scenario(scenario)


def test_real_contracts_preserve_every_original_unknown_and_obligation():
    package = json.loads((ROOT / 'data/writing/packages/ch86-local-scenario-v1.json').read_bytes())
    _, _, contracts = verify_material(ROOT, package)
    for _, contract in contracts:
        old = json.loads((ROOT / f'data/planning/contracts/agent-final-v1/{contract["id"]}.v2.json').read_bytes())
        for name, value in contract['original_declarations'].items():
            assert value == old[name]
        for name in ('required_beats', 'forbidden_beats'):
            assert [b['description'] for b in contract[name]] == [b['description'] for b in old[name]]


def test_contract_set_cannot_omit_seed():
    package = json.loads((ROOT / 'data/writing/packages/ch86-local-scenario-v1.json').read_bytes())
    package['plan'].pop()
    with pytest.raises(ValueError, match='contract set'):
        verify_material(ROOT, package)


# Session transport integration uses small corpus/source fixtures; the separate
# pilot verifier exercises the real registered package and corpus.
from test_session_generation import session_root
from test_generation import root


def test_local_session_import_and_historical_load_do_not_claim_model_execution(session_root, monkeypatch, capsys):
    import shutil
    from rcwh.candidate_reviews import canonical_bytes
    from rcwh.generation import render
    from rcwh.generation.records import binding
    from rcwh.generation.session import prepare_request, verify_prepared_request, import_draft
    from rcwh.generation.writing import load_draft, feedback_report
    from rcwh.generation.lineage import current_compatibility
    for relative in ('data/writing/local-scenarios/ch86-v1', 'data/world/m3_core.json',
                     'data/objects/m4.json', 'data/objects/medicine_bowl.yaml', 'data/planning/chapters/ch86.json'):
        source, target = ROOT / relative, session_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir(): shutil.copytree(source, target, dirs_exist_ok=True)
        else: shutil.copyfile(source, target)
    report = render.LiteraryInputs(None).package('package.json')
    package = report['package']
    scenario = json.loads((session_root / SCENARIO).read_bytes())
    package.update(chapter=86, operation_scope='RESEARCH', assets=[],
                   world=[binding(session_root, SCENARIO)],
                   plan=[binding(session_root, 'data/planning/chapters/ch86.json'), *scenario['contracts']])
    (session_root / 'package.json').write_bytes(canonical_bytes(package))
    monkeypatch.setattr('rcwh.literary_inputs.LiteraryInputs', lambda catalog: type('Inputs', (), {
        'package': lambda self, path: deepcopy(report)})())
    packet = prepare_request(session_root, package_path='package.json', chapter=86)
    verify_prepared_request(session_root, packet)
    import argparse
    from rcwh.application.write import add_commands, command
    parser = argparse.ArgumentParser()
    parser.add_argument('--root')
    add_commands(parser.add_subparsers())
    args = parser.parse_args(['--root', str(session_root), 'write', 'draft', 'package.json',
                              '--chapter', '86', '--dry-run'])
    assert command(args) == 0
    cli_packet = json.loads(capsys.readouterr().out)
    assert cli_packet['task'] == packet['task']
    verify_prepared_request(session_root, cli_packet)
    # Even an available runner is outside the local pilot execution protocol.
    args.execute = True
    args.dry_run = False
    assert command(args) == 1
    assert 'session DRY_RUN/import only' in capsys.readouterr().out
    # Governance and unselected world state cannot invalidate this selected model.
    (session_root / 'data/project').mkdir(parents=True, exist_ok=True)
    (session_root / 'data/project/closure_roots.json').write_text('{"changed":true}')
    core_path = session_root / 'data/world/m3_core.json'
    core_bytes = core_path.read_bytes()
    core = json.loads(core_bytes)
    core['baseline']['characters']['daiyu']['life_state'] = 'UNRELATED_GLOBAL_BASELINE_CHANGE'
    core_path.write_bytes(canonical_bytes(core))
    verify_prepared_request(session_root, packet)
    # The selected identity is fresh-checked as a record, independently of its carrier.
    next(a for a in core['characters'] if a['id'] == 'daiyu')['name'] = 'changed selected identity'
    core_path.write_bytes(canonical_bytes(core))
    with pytest.raises(ValueError, match='identity changed'):
        verify_prepared_request(session_root, packet)
    core_path.write_bytes(core_bytes)
    assert len(packet['task']['scenes']) == 6
    assert packet['task']['threads'] is None
    assert not any(ref['path'].startswith(('data/world/', 'data/objects/', 'data/knowledge/', 'data/scenes/'))
                   for ref in packet['inputs'])
    (session_root / 'request.json').write_bytes(canonical_bytes(packet))
    (session_root / 'authored.txt').write_text('紫鹃低头看那碗药，手却没有再伸过去。\n')
    imported = import_draft(session_root, 'authored.txt', 'request.json', session_id='local-fixture',
                           session_model_label='fixture configured writer, not provider verified')
    draft_path = imported['draft']['path']
    before = load_draft(session_root, draft_path)
    feedback = feedback_report(session_root, draft_path)
    assert len([c for c in feedback['checks'] if c.get('evaluator') == 'scene_state' and c['status'] == 'PENDING']) == 6
    assert feedback['semantic_requests'] == []
    # A later edit of the local scenario invalidates current compatibility but
    # cannot rewrite imported historical input or fabricate observed events.
    mutated = deepcopy(scenario)
    mutated['events'][0]['description'] += ' changed'
    (session_root / SCENARIO).write_bytes(canonical_bytes(mutated))
    with pytest.raises(ValueError): verify_prepared_request(session_root, packet)
    assert current_compatibility(session_root, draft_path)['compatibility'] == 'STALE'
    assert load_draft(session_root, draft_path) == before


def test_local_editorial_package_is_explicitly_rejected_for_production():
    from rcwh.literary_inputs import LiteraryInputs
    inputs = LiteraryInputs(type('Catalog', (), {'root': ROOT})())
    with pytest.raises(ValueError, match='LOCAL_EDITORIAL_MODEL_NOT_PRODUCTION_INPUT'):
        inputs.package('data/writing/packages/ch86-local-scenario-v1.json', production=True)
