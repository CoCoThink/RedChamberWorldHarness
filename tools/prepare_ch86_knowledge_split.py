"""Create an immutable research-only successor to the chapter 86 local model."""
import json
from copy import deepcopy
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.local_scenario import compile_scenario, verify_material
from rcwh.generation.records import binding

ROOT = Path(__file__).resolve().parents[1]
OLD = 'data/writing/local-scenarios/ch86-v2'
NEW = 'data/writing/local-scenarios/ch86-v3'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v3.json'
OUTPUT = 'artifacts/local-scenario-ch86-knowledge-split'
RENAMES = {'death_time_notice_sent': 'death_account_notice_sent',
           'baoyu_learns_death_time': 'baoyu_learns_death_account',
           'death-time-notice': 'death-account-notice'}


def write(root, path, value):
    target = root / path
    raw = canonical_bytes(value)
    if target.exists() and target.read_bytes() != raw:
        raise ValueError('refusing to overwrite: ' + path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return binding(root, path)


def rename(value):
    if isinstance(value, str):
        return RENAMES.get(value, value)
    if isinstance(value, list):
        return [rename(v) for v in value]
    if isinstance(value, dict):
        return {k: rename(v) for k, v in value.items()}
    return value


def build(root=ROOT):
    scenario = json.loads((root / OLD / 'scenario.json').read_bytes())
    contracts = []
    for i in range(1, 7):
        contract = json.loads((root / OLD / f'contracts/86-S{i}.v3.json').read_bytes())
        # Preserve the historic declarations and obligations verbatim.
        contract['entry_checkpoint'] = rename(contract['entry_checkpoint'])
        contract['checkpoints'] = rename(contract['checkpoints'])
        contracts.append(write(root, f'{NEW}/contracts/86-S{i}.v3.json', contract))
    preserved = deepcopy(scenario['original_declarations'])
    scenario = rename(scenario)
    scenario['original_declarations'] = preserved
    scenario['contracts'] = contracts
    for fact in scenario['facts']:
        if fact['id'] == 'death_exact_moment':
            fact.update(id='death_relative_account', meaning='死亡发生的相对经过：雪雁出去以后、紫鹃托着黛玉时气没了；不含精确死时或医学因果')
    scenario['facts'].extend([{'id': 'death_precise_time', 'meaning': '可确定的精确死亡钟点或可测量瞬间'},
                              {'id': 'death_physiological_detail', 'meaning': '可确定的生理死时细节或医学因果'}])
    for key in list(scenario['initial']):
        if key.endswith('.knowledge.death_exact_moment'):
            value = scenario['initial'].pop(key)
            prefix = key.rsplit('.', 1)[0]
            scenario['initial'][prefix + '.death_relative_account'] = value
            scenario['initial'][prefix + '.death_precise_time'] = 'UNKNOWN'
            scenario['initial'][prefix + '.death_physiological_detail'] = 'UNKNOWN'
    for event in scenario['events']:
        event['observed_facts'] = ['death_relative_account' if f == 'death_exact_moment' else f for f in event['observed_facts']]
        for effect in event['effects']:
            effect['target'] = effect['target'].replace('.death_exact_moment', '.death_relative_account')
        if event['id'] == 'death_account_notice_sent':
            event['description'] = '问药后紫鹃讲述她亲历的死亡相对经过；不传达精确死时或医学因果。'
        if event['id'] == 'baoyu_learns_death_account':
            event['description'] = '到场并问药后宝玉获告死亡发生及相对经过；精确死时和医学因果仍未知。'
    for message in scenario['messages']:
        message['facts'] = ['death_relative_account' if f == 'death_exact_moment' else f for f in message['facts']]
    for rule in scenario['invariants']:
        if 'target' in rule:
            rule['target'] = rule['target'].replace('.death_exact_moment', '.death_relative_account')
    for actor in ('zijuan', 'baoyu'):
        for fact in ('death_precise_time', 'death_physiological_detail'):
            scenario['invariants'].append({'kind': 'CONSTANT', 'target': f'actor.{actor}.knowledge.{fact}', 'value': 'UNKNOWN'})
    scenario['extra_editorial_choices'].append('旧 death_exact_moment 无等值映射；相对经过不证明精确死时或医学因果，旧合同声明保持原样。')
    compiled = compile_scenario(scenario)
    scenario_ref = write(root, f'{NEW}/scenario.json', scenario)
    package = json.loads((root / 'data/writing/packages/ch86-local-scenario-v2.json').read_bytes())
    package.update(id='writing-package:ch86:local-scenario:v3', world=[scenario_ref],
                   plan=package['plan'][:2] + contracts,
                   purpose='第86回死亡知识命题拆分的研究模型；未经独立语义审读，不授予production或stable。')
    package_ref = write(root, PACKAGE, package)
    verify_material(root, package)
    write(root, f'{OUTPUT}/checkpoints.json', compiled)
    write(root, f'{OUTPUT}/manifest.json', {
        'kind': 'CH86_KNOWLEDGE_SPLIT_REVIEW', 'version': 1, 'status': 'NOT_STARTED',
        'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED',
        'old_fact_mapping': 'NO_EQUIVALENT_LOCAL_VALUE',
        'scenario': scenario_ref, 'package': package_ref, 'contracts': contracts,
        'candidate_import': binding(root, 'artifacts/local-trial-revision-ch86-20261111/import.json'),
        'semantic_boundary': binding(root, 'artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md'),
        'previous_scenario': binding(root, f'{OLD}/scenario.json'),
        'checkpoints': binding(root, f'{OUTPUT}/checkpoints.json')})


if __name__ == '__main__':
    build()
