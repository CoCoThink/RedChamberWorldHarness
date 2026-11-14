"""Version the two prose-supported care-order refinements after original follow-up."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from rcwh.generation.local_scenario import compile_scenario, verify_material
from rcwh.generation.records import binding, bound_bytes
from prepare_ch86_knowledge_split import write
from prepare_ch86_knowledge_amendment import verify_replay_refinement
import verify_ch86_knowledge_followup as followup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'artifacts/local-scenario-ch86-knowledge-split/amendment-v2'
SCENARIO = 'data/writing/local-scenarios/ch86-v5/scenario.json'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v5.json'
EDGES = [['body_care_started', 'runner_observes_death'],
         ['liwan_takes_care', 'baoyu_arrives']]
EVIDENCE = [
    {'edge': EDGES[0], 'paragraphs': [25, 26, 28],
     'quote': '请医的跑腿还在候着动静，听见叫水便来问。',
     'interpretation': '初次料理和叫热水已经开始，非全部照护完成；跑腿因叫水而来。'},
    {'edge': EDGES[1], 'paragraphs': [32, 35],
     'quote': '李纨自己也流泪，将她手旁压着的衣领抽平，向外道：“干净衣裳拿近些，水有人接着，别都挤进来。”',
     'interpretation': '李纨已参与第一轮衣物和热水料理；宝玉到场时李纨已在，帕子衣裳亦已不同。不约束她与远端启程的顺序。'}]


def amend(previous):
    model = deepcopy(previous)
    model['before'].extend(deepcopy(EDGES))
    return model


def build(root=ROOT):
    followup.verify(root)
    previous_ref = binding(root, 'data/writing/local-scenarios/ch86-v4/scenario.json')
    previous = json.loads(bound_bytes(root, previous_ref))
    model = amend(previous)
    scenario_ref = write(root, SCENARIO, model)
    package = json.loads((root / 'data/writing/packages/ch86-local-scenario-v4.json').read_bytes())
    package.update(id='writing-package:ch86:local-scenario:v5', world=[scenario_ref],
                   purpose='第86回照护先后关系保守补边；语义复核前仍PENDING，不授予production或stable。')
    package_ref = write(root, PACKAGE, package)
    _, compiled, _ = verify_material(root, package)
    verify_replay_refinement(compile_scenario(previous), compiled)
    execution_ref = binding(root, followup.REVIEW + '/execution.json')
    execution = json.loads(bound_bytes(root, execution_ref))
    write(root, OUTPUT + '/manifest.json', {
        'kind': 'CH86_CARE_ORDER_AMENDMENT', 'status': 'PENDING_INDEPENDENT_FOLLOWUP',
        'previous_scenario': previous_ref, 'scenario': scenario_ref, 'package': package_ref,
        'checkpoints': write(root, OUTPUT + '/checkpoints.json', compiled),
        'original_review_execution': execution_ref,
        'original_opinions': [a['raw_opinion'] for a in execution['attempts']],
        'candidate': binding(root, 'artifacts/candidates/ch86/2319feaac4b3f3824b185520cb0eae9d3968ab24e01e491be17547d3013b67c2.txt'),
        'added_edges': EDGES, 'causal_edge_evidence': EVIDENCE,
        'state_replay_change': 'PRESERVE_DETERMINED_VALUES; REFINE_UNORDERED_CUTS; NO_EFFECT_CHANGES',
        'contracts': model['contracts'], 'old_fact_mapping': 'NO_EQUIVALENT_LOCAL_VALUE',
        'unmodeled_boundary': '雪雁旁听后知识未更新；UNKNOWN不得解释为未获告。未声称全人物知识或全文事件覆盖。',
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
    assert manifest['added_edges'] == EDGES and manifest['causal_edge_evidence'] == EVIDENCE
    candidate = bound_bytes(root, manifest['candidate']).decode().strip().split('\n\n')
    for evidence in EVIDENCE:
        assert evidence['quote'] in '\n'.join(candidate[n - 1] for n in evidence['paragraphs'])
    package = json.loads(bound_bytes(root, manifest['package']))
    actual, compiled, _ = verify_material(root, package)
    assert actual == new and compiled == json.loads(bound_bytes(root, manifest['checkpoints']))
    verify_replay_refinement(compile_scenario(old), compiled)
    for before, after in EDGES:
        assert before in compiled['checkpoints'][after]['events']
    assert manifest['contracts'] == old['contracts'] == new['contracts']
    assert manifest['status'] == 'PENDING_INDEPENDENT_FOLLOWUP'
    assert manifest['old_fact_mapping'] == 'NO_EQUIVALENT_LOCAL_VALUE'
    assert manifest['production_admission'] == 'NOT_GRANTED' and manifest['authority_effect'] == 'NONE'
    return {'status': 'PASS', 'scope': 'CARE_ORDER_REFINEMENT_ONLY',
            'semantic_status': 'PENDING', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    else:
        build()
