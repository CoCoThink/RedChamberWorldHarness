"""Version the coordinator's explicit care-before-departure order decision."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from rcwh.generation.local_scenario import compile_scenario, verify_material
from rcwh.generation.records import binding, bound_bytes
from prepare_ch86_knowledge_split import write
from prepare_ch86_knowledge_amendment import verify_replay_refinement
import verify_ch86_care_order_review as v5_review

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'artifacts/local-scenario-ch86-knowledge-split/amendment-v3'
SCENARIO = 'data/writing/local-scenarios/ch86-v6/scenario.json'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v6.json'
EDGE = ['liwan_takes_care', 'baoyu_departs']
UNCONSTRAINED = ['liwan_takes_care', 'baoyu_departs']
CANDIDATE = 'artifacts/candidates/ch86/2319feaac4b3f3824b185520cb0eae9d3968ab24e01e491be17547d3013b67c2.txt'
EVIDENCE = {
    'edge': EDGE,
    'paragraphs': [31, 33],
    'quotes': [
        '李纨自己也流泪，将她手旁压着的衣领抽平，向外道：“干净衣裳拿近些，水有人接着，别都挤进来。”',
        '宝玉听了便走，雪雁跟上来。'
    ],
    'interpretation': '正文第31段李纨开始安排衣物和热水的第一轮照护；第33段宝玉听到雪雁报病危后便走。段号不计回目。仅约束照护开始先于启程，不推断具体时刻、路线或行程。'
}


def amend(previous):
    model = deepcopy(previous)
    model['before'].append(deepcopy(EDGE))
    model['unconstrained_pairs'] = [pair for pair in model['unconstrained_pairs'] if pair != UNCONSTRAINED]
    return model


def build(root=ROOT):
    v5_review.verify(root)
    previous_ref = binding(root, 'data/writing/local-scenarios/ch86-v5/scenario.json')
    previous = json.loads(bound_bytes(root, previous_ref))
    disposition_ref = binding(root, v5_review.REVIEW + '/disposition.json')
    disposition = json.loads(bound_bytes(root, disposition_ref))
    if disposition['decision'] != 'CONTINUE_TO_VERSIONED_CARE_ORDER_V6; HOLD_PRODUCTION':
        raise ValueError('v6 requires the recorded coordinator decision')
    model = amend(previous)
    scenario_ref = write(root, SCENARIO, model)
    package = json.loads((root / 'data/writing/packages/ch86-local-scenario-v5.json').read_bytes())
    package.update(id='writing-package:ch86:local-scenario:v6', world=[scenario_ref],
                   purpose='按v5复核处置补入正文明确的李纨开始照护先于宝玉启程；语义复核前仍PENDING。')
    package_ref = write(root, PACKAGE, package)
    _, compiled, _ = verify_material(root, package)
    verify_replay_refinement(compile_scenario(previous), compiled)
    candidate_ref = binding(root, CANDIDATE)
    review_execution_ref = binding(root, v5_review.REVIEW + '/execution.json')
    write(root, OUTPUT + '/manifest.json', {
        'kind': 'CH86_CARE_ORDER_AMENDMENT', 'status': 'PENDING_INDEPENDENT_FOLLOWUP',
        'previous_scenario': previous_ref, 'scenario': scenario_ref, 'package': package_ref,
        'checkpoints': write(root, OUTPUT + '/checkpoints.json', compiled),
        'previous_review_disposition': disposition_ref,
        'previous_review_execution': review_execution_ref,
        'candidate': candidate_ref, 'added_edges': [EDGE], 'removed_unconstrained_pairs': [UNCONSTRAINED],
        'causal_edge_evidence': [EVIDENCE], 'contracts': model['contracts'],
        'state_replay_change': 'PRESERVE_DETERMINED_VALUES; REFINE_ONE_UNORDERED_CUT; NO_EFFECT_CHANGES',
        'old_fact_mapping': 'NO_EQUIVALENT_LOCAL_VALUE',
        'unmodeled_boundary': '宝玉收病危消息与死亡/身体料理之间仍保留无序；未建模旅行时延；UNKNOWN不等于未获告。',
        'source_and_corpus_review': 'NOT_CHECKED', 'authority_effect': 'NONE',
        'semantic_status': 'PENDING', 'production_admission': 'NOT_GRANTED'})


def verify(root=ROOT):
    v5_review.verify(root)
    manifest = json.loads((root / OUTPUT / 'manifest.json').read_bytes())
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                bound_bytes(root, ref)
    old = json.loads(bound_bytes(root, manifest['previous_scenario']))
    new = json.loads(bound_bytes(root, manifest['scenario']))
    assert new == amend(old)
    assert manifest['added_edges'] == [EDGE] and manifest['removed_unconstrained_pairs'] == [UNCONSTRAINED]
    candidate = bound_bytes(root, manifest['candidate']).decode().strip().split('\n\n')
    body = candidate[1:] if candidate and candidate[0].startswith('第八十六回') else candidate
    for paragraph, quote in zip(EVIDENCE['paragraphs'], EVIDENCE['quotes'], strict=True):
        assert quote in body[paragraph - 1]
    assert manifest['causal_edge_evidence'] == [EVIDENCE]
    package = json.loads(bound_bytes(root, manifest['package']))
    actual, compiled, _ = verify_material(root, package)
    assert actual == new and compiled == json.loads(bound_bytes(root, manifest['checkpoints']))
    verify_replay_refinement(compile_scenario(old), compiled)
    assert EDGE[0] in compiled['checkpoints'][EDGE[1]]['events']
    assert UNCONSTRAINED not in new['unconstrained_pairs']
    assert manifest['contracts'] == old['contracts'] == new['contracts']
    assert manifest['semantic_status'] == 'PENDING'
    assert manifest['production_admission'] == 'NOT_GRANTED' and manifest['authority_effect'] == 'NONE'
    return {'status': 'PASS', 'scope': 'SINGLE_CARE_ORDER_EDGE',
            'semantic_status': 'PENDING', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    else:
        build()
