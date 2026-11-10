"""Check real selected local material and session custody, never prose qualification."""
import argparse
import json
from pathlib import Path

from rcwh.assets import AssetCatalog
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.local_scenario import verify_material, checkpoint_view
from rcwh.generation.records import bound_bytes, binding
from rcwh.generation.session import verify_prepared_request, _verify_payload_export
from rcwh.literary_inputs import LiteraryInputs

DIRECTORY = 'artifacts/local-scenario-ch86-20261110'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v1.json'


def dispositions(root, scenario, compiled, contracts):
    rows, unresolved = [], []
    aliases = {'daiyu_death_exact_moment': 'death_exact_moment', 'daiyu_illness_severe': 'illness_severe'}
    for _, contract in contracts:
        old_path = f'data/planning/contracts/agent-final-v1/{contract["id"]}.v2.json'
        old = json.loads((root / old_path).read_bytes())
        for key, value in contract['original_declarations'].items():
            if value != old[key]:
                raise ValueError('original declarations differ: ' + contract['id'])
        for kind in ('required_beats', 'forbidden_beats'):
            expected = [{k: item[k] for k in ('description', 'citations', 'epistemic')} for item in old[kind]]
            if contract[kind] != expected:
                raise ValueError('original obligation changed: ' + contract['id'])
        for group in ('entry_state', 'exit_state', 'preconditions'):
            checkpoint = contract['entry_checkpoint'] if group != 'exit_state' else contract['checkpoints'][-1]
            for i, declaration in enumerate(old[group]):
                original_target = declaration['equals']
                target = original_target.replace('character.', 'actor.', 1)
                for old_fact, new_fact in aliases.items():
                    target = target.replace('.knowledge.' + old_fact, '.knowledge.' + new_fact)
                model = compiled['checkpoints'][checkpoint]['values']
                rows.append({'seed': contract['id'], 'group': group, 'index': i,
                             'original_declaration': declaration, 'original_binding': binding(root, old_path),
                             'disposition': 'PRESERVED_ORIGINAL_UNKNOWN' if declaration['status'] == 'UNKNOWN' else 'PRESERVED_ORIGINAL_DECLARATION',
                             'separate_editorial_checkpoint': checkpoint,
                             'separate_editorial_target': target if target in model else None,
                             'separate_editorial_value': model.get(target),
                             'local_mapping': 'EXPLICIT_PLAN_ONLY' if target in model else 'NO_EQUIVALENT_LOCAL_VALUE',
                             'evidence_resolution': 'NONE', 'observed_execution': 'NOT_ESTABLISHED'})
        for i, issue in enumerate(old['unresolved']):
            unresolved.append({'seed': contract['id'], 'index': i, 'original_issue': issue,
                               'disposition': 'PRESERVED_NOT_DISCHARGED_BY_EDITORIAL_MODEL',
                               'evidence_resolution': 'NONE'})
    return {'kind': 'LOCAL_SCENARIO_ORIGINAL_DECLARATION_DISPOSITIONS', 'version': 1,
            'declarations': rows, 'unresolved': unresolved, 'authority_effect': 'NONE'}


def verify(root):
    receipt = json.loads((root / DIRECTORY / 'preparation.json').read_bytes())
    bound_bytes(root, receipt['source_decision'])
    for ref in receipt['original_contracts']:
        bound_bytes(root, ref)
    package = json.loads(bound_bytes(root, receipt['package']))
    scenario, compiled, contracts = verify_material(root, package)
    if canonical_bytes(compiled) != (root / DIRECTORY / 'checkpoints.json').read_bytes():
        raise ValueError('stored local checkpoints differ from fresh causal model')
    decision = json.loads(bound_bytes(root, receipt['source_decision']))
    if not {tuple(edge) for edge in decision['proposed_local_order']['before']} <= {tuple(edge) for edge in scenario['before']}:
        raise ValueError('coordinator causal constraints were dropped')
    for name in ('unconstrained_pairs', 'unresolved'):
        if scenario[name] != decision['proposed_local_order'][name]:
            raise ValueError('coordinator limits changed')
    if scenario['pressure_phases'] != decision['pressure_phases']:
        raise ValueError('pressure-phase mapping changed')
    selected_roles = {r['name']: r for r in decision['roles']
                      if r['selected_representation'] != 'NARRATIVE_LABOR_ROLES'}
    if {r['name'] for r in scenario['actors']} != set(selected_roles):
        raise ValueError('coordinator role coverage changed')
    for actor in scenario['actors']:
        selected = selected_roles[actor['name']]
        if actor['duty'] != selected['selected_duty'] or (selected['existing_entity_id'] is not None
                                                       and actor['id'] != selected['existing_entity_id']):
            raise ValueError('coordinator actor identity or duty changed')
    narrative = [r for r in decision['roles'] if r['selected_representation'] == 'NARRATIVE_LABOR_ROLES'] + [
                 r for r in decision['objects'] if r['selected_representation'].startswith('NARRATIVE_')]
    if scenario['narrative_roles_and_props'] != narrative:
        raise ValueError('narrative labor or care props were silently omitted')
    dispositions_report = dispositions(root, scenario, compiled, contracts)
    if canonical_bytes(dispositions_report) != (root / DIRECTORY / 'dispositions.json').read_bytes():
        raise ValueError('original unknown dispositions differ')
    packet = json.loads(bound_bytes(root, receipt['request']))
    if packet['context']['package_path'] != PACKAGE or packet['package'] != receipt['package']:
        raise ValueError('prepared request selected a different package')
    with rebuild_scope():
        verify_prepared_request(root, packet)
    _verify_payload_export(packet, receipt['request'], receipt['export']['receipt'], receipt['export']['payload'],
                           lambda ref: bound_bytes(root, ref))
    raw_carriers = [r['path'] for r in packet['inputs'] if r['path'].startswith(
        ('data/world/', 'data/objects/', 'data/knowledge/', 'data/scenes/', 'data/project/closure_roots'))]
    if raw_carriers or packet['task']['threads'] is not None or len(packet['task']['scenes']) != 6:
        raise ValueError('local request accidentally inherited global/legacy material')
    if packet['task']['local_checkpoints'] != checkpoint_view(compiled):
        raise ValueError('request checkpoint view differs from model')
    try:
        LiteraryInputs(AssetCatalog.from_repo(root)).package(PACKAGE, production=True)
    except ValueError as exc:
        if 'LOCAL_EDITORIAL_MODEL_NOT_PRODUCTION_INPUT' not in str(exc):
            raise
    else:
        raise ValueError('local model entered production')
    states = compiled['checkpoints']
    target = 'actor.baoyu.knowledge.death_exact_moment'
    if (states['baoyu_arrives']['values'][target] != 'NOT_KNOWN'
            or states['baoyu_asks_rewarm']['values'][target] != 'NOT_KNOWN'
            or states['baoyu_learns_death_time']['values'][target] != 'KNOWS'
            or states['terminal_cold_unfinished_medicine']['values']['object.OBJ-MEDICINE-BOWL-86.temperature'] != 'cold'):
        raise ValueError('local arrival or medicine boundary failed')
    return {'status': 'PASS', 'scope': 'EDITORIAL_MODEL_AND_REQUEST_CUSTODY_ONLY',
            'package': receipt['package'], 'request': receipt['request'],
            'request_bytes': packet['byte_admission']['request_bytes'],
            'reserved_total_bytes': packet['byte_admission']['reserved_total_bytes'],
            'token_capacity': 'NOT_MEASURED', 'events': len(scenario['events']), 'messages': len(scenario['messages']),
            'declarations_preserved': len(dispositions_report['declarations']),
            'unknown_preserved': sum(r['original_declaration']['status'] == 'UNKNOWN' for r in dispositions_report['declarations']),
            'unresolved_preserved': len(dispositions_report['unresolved']),
            'scope_status': 'PENDING', 'prose_realization': 'NOT_STARTED',
            'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    print(json.dumps(verify(parser.parse_args().root.resolve()), ensure_ascii=False, indent=2))
