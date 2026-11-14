"""Resolve active instruction and medical-knowledge ambiguity without rewriting originals."""
import json
from copy import deepcopy
from pathlib import Path

from rcwh.generation.local_scenario import compile_scenario, verify_material
from rcwh.generation.records import binding, bound_bytes
from prepare_ch86_knowledge_split import write

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/local-scenario-ch86-knowledge-split'
OUTPUT = BASE + '/amendment-v1'
SCENARIO = 'data/writing/local-scenarios/ch86-v4/scenario.json'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v4.json'
DUTY = '迟获病危消息才赶来，到场问药后获告死亡发生及相对经过；精确死时、医学判定的生理过程和医学死因仍未知，不赶上最后一息。'
CLOCK = '选定请医反馈早于改字、改字早于最后突变、病危报信启程早于死亡、宝玉到达晚于死亡，并在到场先问药后获告死亡发生及相对经过。精确死时、医学判定的生理过程和医学死因仍未知；只是待实现偏序，不映射旧场事件、不设置时辰、房间或路线。'
PHYSIOLOGY = '经医学测量或专业判定的死亡生理机制或过程；不含现场无应答、失去支撑力或照护者所称气没了等普通观察；医学死因另列death_medical_cause。'
CAUSE = '经证据确定的医学死因或死亡因果链；不得由长期病程、候医或未饮药自动推出。'
EDGES = [['liwan_notified', 'wangfuren_notified'], ['liwan_arrives', 'baoyu_arrives']]


def amend(old):
    model = deepcopy(old)
    next(a for a in model['actors'] if a['id'] == 'baoyu')['duty'] = DUTY
    next(c for c in model['source_conflicts'] if c['id'] == 'CLOCK')['decision'] = CLOCK
    next(f for f in model['facts'] if f['id'] == 'death_physiological_detail')['meaning'] = PHYSIOLOGY
    next(f for f in model['facts'] if f['id'] == 'death_relative_account')['meaning'] += ' 包含照护者普通观察的陈述，不把呼吸观察提升为医学判定。'
    model['facts'].append({'id': 'death_medical_cause', 'meaning': CAUSE})
    for actor in model['actors']:
        model['initial'][f'actor.{actor["id"]}.knowledge.death_medical_cause'] = 'UNKNOWN'
    for actor in ('zijuan', 'baoyu'):
        model['invariants'].append({'kind': 'CONSTANT', 'target': f'actor.{actor}.knowledge.death_medical_cause', 'value': 'UNKNOWN'})
    model['before'].extend(deepcopy(EDGES))
    return model


def verify_replay_refinement(previous, compiled):
    """Add supported ordering, retaining every previously determined value."""
    assert set(previous['checkpoints']) == set(compiled['checkpoints'])
    for name, old in previous['checkpoints'].items():
        new = compiled['checkpoints'][name]
        assert set(old['events']) <= set(new['events'])
        for key, value in old['values'].items():
            if value != 'UNKNOWN_AT_UNORDERED_CUT':
                assert new['values'][key] == value


def build(root=ROOT):
    from verify_ch86_knowledge_review import verify
    verify(root)
    previous = json.loads((root / 'data/writing/local-scenarios/ch86-v3/scenario.json').read_bytes())
    model = amend(previous)
    scenario_ref = write(root, SCENARIO, model)
    package = json.loads((root / 'data/writing/packages/ch86-local-scenario-v3.json').read_bytes())
    package.update(id='writing-package:ch86:local-scenario:v4', world=[scenario_ref],
                   purpose='第86回死亡知识拆分文案勘误；复核前仍PENDING，不授予production或stable。')
    package_ref = write(root, PACKAGE, package)
    _, compiled, _ = verify_material(root, package)
    previous_replay = compile_scenario(previous)
    verify_replay_refinement(previous_replay, compiled)
    checkpoints_ref = write(root, OUTPUT + '/checkpoints.json', compiled)
    execution = json.loads((root / BASE / 'review/execution.json').read_bytes())
    write(root, OUTPUT + '/manifest.json', {
        'kind': 'CH86_KNOWLEDGE_AMENDMENT', 'status': 'PENDING_INDEPENDENT_FOLLOWUP',
        'previous_scenario': binding(root, 'data/writing/local-scenarios/ch86-v3/scenario.json'),
        'scenario': scenario_ref, 'package': package_ref, 'checkpoints': checkpoints_ref,
        'original_review_execution': binding(root, BASE + '/review/execution.json'),
        'original_opinions': [a['raw_opinion'] for a in execution['attempts']],
        'candidate': binding(root, 'artifacts/candidates/ch86/2319feaac4b3f3824b185520cb0eae9d3968ab24e01e491be17547d3013b67c2.txt'),
        'changes': ['actors[id=baoyu].duty', 'source_conflicts[id=CLOCK].decision',
                    'facts[id=death_relative_account].meaning', 'facts[id=death_physiological_detail].meaning',
                    'facts[id=death_medical_cause] (NEW)', 'initial: per-actor medical cause UNKNOWN',
                    'invariants: zijuan/baoyu medical cause CONSTANT UNKNOWN',
                    'before: liwan_notified < wangfuren_notified; liwan_arrives < baoyu_arrives'],
        'state_replay_change': 'PRESERVE_DETERMINED_VALUES; REFINE_UNORDERED_CUTS; NEW_MEDICAL_CAUSE_UNKNOWN',
        'causal_edge_evidence': [{'edge': EDGES[0], 'paragraphs': [29], 'quote': '他答应着还要去报。'},
                                 {'edge': EDGES[1], 'paragraphs': [35], 'quote': '他进来，只见紫鹃在床边，李纨也在'}],
        'contracts': model['contracts'], 'old_fact_mapping': 'NO_EQUIVALENT_LOCAL_VALUE',
        'source_and_corpus_review': 'NOT_CHECKED', 'authority_effect': 'NONE',
        'production_admission': 'NOT_GRANTED'})


def verify(root=ROOT):
    manifest = json.loads((root / OUTPUT / 'manifest.json').read_bytes())
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                bound_bytes(root, ref)
    old = json.loads(bound_bytes(root, manifest['previous_scenario']))
    new = json.loads(bound_bytes(root, manifest['scenario']))
    assert new == amend(old)
    package = json.loads(bound_bytes(root, manifest['package']))
    actual, compiled, _ = verify_material(root, package)
    assert actual == new and compiled == json.loads(bound_bytes(root, manifest['checkpoints']))
    old_compiled = compile_scenario(old)
    verify_replay_refinement(old_compiled, compiled)
    assert all(cp['values'][f'actor.{actor["id"]}.knowledge.death_medical_cause'] == 'UNKNOWN'
               for cp in compiled['checkpoints'].values() for actor in new['actors'])
    assert manifest['old_fact_mapping'] == 'NO_EQUIVALENT_LOCAL_VALUE'
    assert manifest['production_admission'] == 'NOT_GRANTED'
    return {'status': 'PASS', 'scope': 'EXACT_DECLARED_AMENDMENT_AND_CONSERVATIVE_REPLAY_REFINEMENT', 'semantic_status': 'PENDING', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    else:
        build()
