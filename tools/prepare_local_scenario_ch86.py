"""Build the chapter-86 editorial scenario pilot without changing historical truth."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.local_scenario import compile_scenario, SCOPE
from rcwh.generation.records import append_bytes as publish_bytes, binding
from rcwh.generation.runner import Budget
from rcwh.generation.session import prepare_request, export_request, verify_prepared_request
from rcwh.io import load_data

DIRECTORY = 'data/writing/local-scenarios/ch86-v1'
PACKAGE = 'data/writing/packages/ch86-local-scenario-v1.json'
OUTPUT = 'artifacts/local-scenario-ch86-20261110'
DECISIONS = 'artifacts/scope-review-20261110/coordinator-decisions.json'


def append_bytes(root, relative, raw):
    path = root / relative
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('refusing to replace a different local pilot artifact: ' + relative)
        return binding(root, relative)
    return publish_bytes(root, relative, raw)


def build(root):
    decision = json.loads((root / DECISIONS).read_bytes())
    local = lambda name: 'local:ch86:' + name
    ids = {'雪雁': local('xueyan'), '医者': local('doctor'), '请医跑腿': local('doctor-runner')}
    actors = [{'id': r['existing_entity_id'] or ids[r['name']], 'name': r['name'],
               'registration': 'EXISTING_IDENTITY_ONLY' if r['existing_entity_id'] else 'NEW_LOCAL_IDENTITY',
               'duty': r['selected_duty'], 'provenance': 'COORDINATOR_EDITORIAL_CHOICE_NOT_EVIDENCE'}
              for r in decision['roles'] if r['selected_representation'] != 'NARRATIVE_LABOR_ROLES']
    xy, doctor, runner = (ids[n] for n in ('雪雁', '医者', '请医跑腿'))
    bowl, legacy = 'OBJ-MEDICINE-BOWL-86', 'medicine_bowl_86'
    folder, pages, pot, fire = (local(n) for n in ('folder', 'pages', 'medicine-pot', 'stove-fire'))
    objects = [{'id': oid, 'name': name, 'registration': registration}
               for oid, name, registration in [(bowl, '网络药碗', 'EXISTING_IDENTITY_ONLY'),
                   (legacy, '独立legacy药碗', 'EXISTING_IDENTITY_ONLY'),
                   (folder, '稿夹', 'NEW_LOCAL_IDENTITY'), (pages, '夹内稿页', 'NEW_LOCAL_IDENTITY'),
                   (pot, '药吊子', 'NEW_LOCAL_IDENTITY'), (fire, '炉火', 'NEW_LOCAL_IDENTITY')]]
    identities = {r['id']: r for r in load_data(root / 'data/world/m3_core.json')['characters']}
    identities.update({r['id']: r for r in load_data(root / 'data/objects/m4.json')['objects']})
    old_bowl = load_data(root / 'data/objects/medicine_bowl.yaml')
    identities[old_bowl['id']] = old_bowl
    for row in [*actors, *objects]:
        if row['registration'] == 'EXISTING_IDENTITY_ONLY':
            row['identity_record'] = {k: identities[row['id']][k] for k in ('id', 'name')}
    fact_ids = ['illness_severe', 'critical_decline', 'death_occurred', 'death_exact_moment', 'doctor_delayed']
    initial = {f'actor.{a["id"]}.knowledge.{f}': 'UNKNOWN' for a in actors for f in fact_ids}
    initial.update({'actor.daiyu.life_state': 'ACTIVE', 'actor.daiyu.body_action_capacity': 'UNKNOWN',
                    'actor.baoyu.location': 'UNKNOWN', 'actor.baoyu.arrival': 'NOT_ARRIVED',
                    f'object.{bowl}.temperature': 'warm', f'object.{bowl}.status': 'CONTAINS_UNFINISHED_MEDICINE',
                    f'object.{bowl}.holder': 'zijuan', f'object.{bowl}.placement': 'CARE_USE',
                    f'object.{legacy}.temperature': 'UNKNOWN', f'object.{legacy}.status': 'UNKNOWN',
                    f'object.{folder}.opened_by_zijuan': False, f'object.{pages}.gap': 'UNFILLED',
                    f'object.{pot}.use': 'CARE', f'object.{fire}.state': 'LIT'})
    events = {}
    def event(eid, participants, description, observed=(), effects=(), requires=()):
        events[eid] = {'id': eid, 'participants': list(participants), 'description': description,
                       'observed_facts': list(observed), 'effects': list(effects), 'requires': list(requires),
                       'execution': 'NOT_OBSERVED', 'scope': SCOPE}
    def effect(target, before, after, reason, basis=None):
        row = {'target': target, 'from': before, 'to': after, 'reason': reason}
        if basis is not None: row['basis'] = basis
        return row
    def knowledge(actor, fact, eid=None, message=None):
        return effect(f'actor.{actor}.knowledge.{fact}', 'NOT_KNOWN', 'KNOWS',
                      '局部计划中的观察/送达，不声明已发生或已在正文实现。',
                      {'kind': 'MESSAGE', 'id': message} if message else {'kind': 'OBSERVATION'})
    event('ordinary_care', ['daiyu', 'zijuan', xy, 'baochai'],
          '普通病晨仍安排明日；宝钗交接米汤/热水一次，紫鹃雪雁持续照护，不作临终告别。',
          ['illness_severe'], [knowledge('zijuan', 'illness_severe'), knowledge(xy, 'illness_severe'),
            knowledge('baochai', 'illness_severe'),
            effect(f'object.{bowl}.holder', 'zijuan', None, '选择放下同碗，后续不换碗。'),
            effect(f'object.{bowl}.placement', 'CARE_USE', 'SET_ASIDE', '只表示相对取放，具体房间仍未知。'),
            effect(f'object.{bowl}.temperature', 'warm', 'UNKNOWN', '初次温药之后不持续观测中间药温，不能自动把warm带到到场时。')])
    event('doctor_delay_observed', [doctor, runner],
          '请医跑腿在医者一端获知普通事务延误；具体病家、诊断、时长、路线不设定。',
          ['doctor_delayed'], [knowledge(runner, 'doctor_delayed')])
    event('doctor_reply_sent', [runner], '请医跑腿携延误反馈返回，和雪雁病危消息分链。')
    event('doctor_feedback', [runner, 'zijuan'], '请医反馈到达紫鹃；不表示医者已到床边。', effects=[
        knowledge('zijuan', 'doctor_delayed', message='doctor-reply')])
    event('unfinished_revision', ['daiyu', 'zijuan'],
          '伸手改字而未成；G01空字不补，紫鹃不翻稿。身体能做多少仍UNKNOWN，不编中止机制。',
          requires=[{'target': 'actor.daiyu.life_state', 'value': 'ACTIVE'}])
    event('rapid_decline_observed', ['daiyu', 'zijuan', xy], '观察最后突变后才报病危，不把长病程等同本刻预知。',
          ['critical_decline'], [knowledge('zijuan', 'critical_decline'), knowledge(xy, 'critical_decline')])
    event('critical_message_dispatched', [xy, 'zijuan'], '雪雁受托携病危消息出发；内容不含尚未发生的死时。')
    event('death_witnessed', ['daiyu', 'zijuan'], '紫鹃目击死亡，生命终点来自长期病程，不归因婚姻、失玉或缺药。',
          ['death_occurred', 'death_exact_moment'], [
              effect('actor.daiyu.life_state', 'ACTIVE', 'DEAD', '新编辑模型的死亡节点，不回写Evidence Truth。'),
              knowledge('zijuan', 'death_occurred'), knowledge('zijuan', 'death_exact_moment')])
    event('body_care_started', ['zijuan'], '先处理身体、热水衣物；不追加礼俗清单或抒情长哭。')
    event('runner_observes_death', [runner, 'zijuan'],
          '新增明确编辑选择：请医跑腿在返回后的劳务中看见已死身体，承担后事通知；不知确切死时。',
          ['death_occurred'], [knowledge(runner, 'death_occurred')])
    event('household_notices_sent', [runner], '请医跑腿携死讯通知李纨和王夫人，传播路径与时长保持未知。')
    event('liwan_notified', ['liwan', runner], '李纨收到死讯，尚未据此宣称到床边。', effects=[
        knowledge('liwan', 'death_occurred', message='liwan-death-notice')])
    event('liwan_arrives', ['liwan'], '显式登记李纨进入身体料理劳务；具体房间和路线未知。')
    event('liwan_takes_care', ['liwan', 'zijuan'], '李纨接手热水衣物第一轮身体料理。')
    event('wangfuren_notified', ['wangfuren', runner], '王夫人获死讯，不默认亲见死亡。', effects=[
        knowledge('wangfuren', 'death_occurred', message='wangfuren-death-notice')])
    event('wangfuren_assigns_work', ['wangfuren'], '王夫人分派后事第一轮和持续劳务；不默认已到床边。')
    event('baoyu_receives_critical_message', ['baoyu', xy], '宝玉迟获病危消息；不含确切死时，不强定相对身体料理的顺序。', effects=[
        knowledge('baoyu', 'critical_decline', message='critical-message')])
    event('baoyu_departs', ['baoyu'], '收到病危消息后赶来；未知出发地点、路线、时辰。')
    event('baoyu_arrives', ['baoyu', 'zijuan'], '死亡之后到场，不赶上最后一息；到场不自动更新死时。', effects=[
        effect('actor.baoyu.arrival', 'NOT_ARRIVED', 'ARRIVED', '局部到场边界，非全局空间移动。')])
    event('baoyu_asks_rewarm', ['baoyu', 'zijuan'], '只问“药还没吃么？再温一温”；请求不执行，不加热、不代饮、不换碗。')
    event('death_time_notice_sent', ['zijuan'], '问药后紫鹃传达她目击的死时；不用具体钟点数字填补未知。')
    event('baoyu_learns_death_time', ['baoyu', 'zijuan'], '到场并问药之后才获知确切死亡经过；不是预先带来的知识。', effects=[
        knowledge('baoyu', 'death_occurred', message='death-time-notice'),
        knowledge('baoyu', 'death_exact_moment', message='death-time-notice')])
    event('medicine_cools', [], '新增末端检查边界：本节点核定同碗为冷；中间药温UNKNOWN，不声称现实冷却耗时或刚在本刻变冷。', effects=[
        effect(f'object.{bowl}.temperature', 'UNKNOWN', 'cold', '计划的末端冷药检查，不把未知的转冷时刻改成已知。'),
        effect(f'object.{fire}.state', 'LIT', 'OUT', '炉火熄是末端编辑安排，不推导缺药致死。')])
    event('terminal_cold_unfinished_medicine', ['baoyu', 'zijuan'], '同一网络药碗：未尽且冷，无人再温；请求未执行。')
    before = deepcopy(decision['proposed_local_order']['before'])
    before += [['ordinary_care', 'doctor_delay_observed'], ['doctor_delay_observed', 'doctor_reply_sent'],
               ['doctor_reply_sent', 'doctor_feedback'], ['death_witnessed', 'runner_observes_death'],
               ['runner_observes_death', 'household_notices_sent'], ['household_notices_sent', 'liwan_notified'],
               ['household_notices_sent', 'wangfuren_notified'], ['liwan_notified', 'liwan_arrives'],
               ['liwan_arrives', 'liwan_takes_care'], ['body_care_started', 'liwan_takes_care'],
               ['baoyu_asks_rewarm', 'death_time_notice_sent'], ['death_time_notice_sent', 'baoyu_learns_death_time'],
               ['baoyu_learns_death_time', 'medicine_cools'], ['medicine_cools', 'terminal_cold_unfinished_medicine']]
    messages = [
        ('doctor-reply', runner, 'zijuan', 'doctor_reply_sent', 'doctor_feedback', ['doctor_delayed']),
        ('critical-message', xy, 'baoyu', 'critical_message_dispatched', 'baoyu_receives_critical_message', ['critical_decline']),
        ('liwan-death-notice', runner, 'liwan', 'household_notices_sent', 'liwan_notified', ['death_occurred']),
        ('wangfuren-death-notice', runner, 'wangfuren', 'household_notices_sent', 'wangfuren_notified', ['death_occurred']),
        ('death-time-notice', 'zijuan', 'baoyu', 'death_time_notice_sent', 'baoyu_learns_death_time', ['death_occurred', 'death_exact_moment'])]
    # Only the facts whose acquisition is explicitly modeled start NOT_KNOWN.
    # Unmodeled beliefs/knowledge remain UNKNOWN, never inferred ignorance.
    for row in events.values():
        for change in row['effects']:
            if '.knowledge.' in change['target']:
                initial[change['target']] = change['from']
    originals = {}
    contracts = []
    participants = [['daiyu', 'zijuan', xy, 'baochai'], ['zijuan', doctor, runner], ['daiyu', 'zijuan'],
                    ['daiyu', 'zijuan', runner, 'liwan', 'wangfuren'], ['daiyu', 'zijuan', xy, 'baoyu'], ['baoyu', 'zijuan']]
    checkpoints = [['ordinary_care'], ['doctor_delay_observed', 'doctor_reply_sent', 'doctor_feedback'],
                   ['unfinished_revision'], ['death_witnessed', 'body_care_started', 'runner_observes_death',
                    'household_notices_sent', 'liwan_notified', 'liwan_arrives', 'liwan_takes_care',
                    'wangfuren_notified', 'wangfuren_assigns_work'],
                   ['rapid_decline_observed', 'critical_message_dispatched', 'baoyu_receives_critical_message', 'baoyu_departs', 'baoyu_arrives'],
                   ['baoyu_asks_rewarm', 'death_time_notice_sent', 'baoyu_learns_death_time', 'medicine_cools', 'terminal_cold_unfinished_medicine']]
    entries = ['ENTRY', 'ordinary_care', 'doctor_feedback', 'death_witnessed', 'unfinished_revision', 'baoyu_arrives']
    required_objects = [[bowl, pot, fire], [pot], [folder, pages], [pot, fire], [], [bowl, fire]]
    # New v3 records carry obligations with their exact descriptions and typed
    # source citations, without copying all unrelated source packets into prompts.
    for i in range(1, 7):
        old_path = f'data/planning/contracts/agent-final-v1/86-S{i}.v2.json'
        old = json.loads((root / old_path).read_bytes())
        preserved = {k: deepcopy(old[k]) for k in ('entry_state', 'exit_state', 'preconditions', 'unresolved',
                                                  'knowledge_binding', 'event_refs')}
        originals[old['id']] = preserved
        obligations = {k: [{'description': beat['description'], 'citations': beat['citations'],
                            'epistemic': beat['epistemic']} for beat in old[k]]
                       for k in ('required_beats', 'forbidden_beats')}
        contract = {'kind': 'LOCAL_SCENE_CONTRACT', 'version': 1, 'revision': 'v3', 'id': old['id'],
                    'chapter': 86, 'scope': SCOPE, 'status': 'UNREVIEWED_EDITORIAL_MODEL',
                    'participants': participants[i-1], 'required_objects': required_objects[i-1],
                    'entry_checkpoint': entries[i-1], 'checkpoints': checkpoints[i-1],
                    'temporal_rule': 'CAUSAL_DAG_NOT_SEED_LIST_ORDER',
                    'original_declarations': preserved, **obligations,
                    'authority_effect': 'NONE', 'evidence_effect': 'NONE'}
        ref = append_bytes(root, f'{DIRECTORY}/contracts/86-S{i}.v3.json', canonical_bytes(contract))
        contracts.append(ref)
    scenario = {'kind': 'LOCAL_EDITORIAL_SCENARIO', 'version': 1, 'chapter': 86, 'scope': SCOPE,
                'authority_effect': 'NONE', 'evidence_effect': 'NONE', 'production_admission': 'NOT_GRANTED',
                'actors': actors, 'objects': objects, 'initial': initial,
                'initial_basis': 'EXPLICIT_EDITORIAL_INITIALIZATION_NOT_WORLD_STATE_OR_EVIDENCE',
                'facts': [{'id': f, 'meaning': {'illness_severe': '病重', 'critical_decline': '最后突变已需报病危',
                          'death_occurred': '已死亡', 'death_exact_moment': '目击/获告具体死亡经过（不填写钟点）',
                          'doctor_delayed': '医者受普通事务延误'}[f]} for f in fact_ids],
                'events': list(events.values()), 'before': before,
                'messages': [{'id': m, 'sender': a, 'receiver': b, 'sent_at': s, 'received_at': r,
                              'facts': fs, 'route': 'UNKNOWN', 'duration': 'UNKNOWN'} for m,a,b,s,r,fs in messages],
                'containment': [{'container': folder, 'contained': pages}],
                'invariants': [{'kind': 'DISTINCT', 'ids': [bowl, legacy, pot]},
                               {'kind': 'NO_EFFECT', 'event': 'baoyu_asks_rewarm'},
                               {'kind': 'ACQUIRE_AT', 'target': 'actor.baoyu.knowledge.death_exact_moment',
                                'event': 'baoyu_learns_death_time'},
                               *[{'kind': 'CONSTANT', 'target': k, 'value': initial[k]} for k in [
                                   f'object.{bowl}.status', f'object.{folder}.opened_by_zijuan',
                                   f'object.{pages}.gap', f'object.{legacy}.temperature', f'object.{legacy}.status',
                                   'actor.daiyu.body_action_capacity', 'actor.baoyu.location']]],
                'unconstrained_pairs': decision['proposed_local_order']['unconstrained_pairs'],
                'unresolved': decision['proposed_local_order']['unresolved'],
                'narrative_roles_and_props': [r for r in decision['roles'] if r['selected_representation'] == 'NARRATIVE_LABOR_ROLES'] +
                                            [r for r in decision['objects'] if r['selected_representation'].startswith('NARRATIVE_')],
                'upgrade_rule': 'Any narrative role/prop used for checked message, possession, motion or state needs explicit local registration before use.',
                'original_declarations': originals, 'seed_ids': [f'86-S{i}' for i in range(1,7)],
                'contracts': contracts, 'pressure_phases': decision['pressure_phases'],
                'source_conflicts': [r for r in decision['choices']],
                'extra_editorial_choices': ['请医跑腿观察已死身体后传后事通知；不是目击确切死时。',
                                           '起始温药后中间药温UNKNOWN；末端medicine_cools核定为冷，不确定真实转冷时刻。',
                                           '李纨通知与到场分开；王夫人不设床边到场。'],
                'realization_in_prose': 'NOT_STARTED', 'semantic_replay': 'NOT_CHECKED'}
    compiled = compile_scenario(scenario)
    scenario_ref = append_bytes(root, f'{DIRECTORY}/scenario.json', canonical_bytes(scenario))
    append_bytes(root, f'{OUTPUT}/checkpoints.json', canonical_bytes(compiled))
    package = json.loads((root / 'data/writing/packages/ch86-scene-projection-pilot-v2.json').read_bytes())
    package.update(id='writing-package:ch86:local-scenario:v1', world=[scenario_ref],
                   plan=[binding(root, 'data/project/plan_constraints_v1.json'), binding(root, 'data/planning/chapters/ch86.json'), *contracts],
                   purpose='第86回局部编辑模型v1。计划检查点不是已发生事实；保留原UNKNOWN。仅研究准备，未试写/未审正文，不授予production或stable。')
    append_bytes(root, PACKAGE, canonical_bytes(package))
    from verify_local_scenario_ch86 import dispositions
    from rcwh.generation.local_scenario import verify_material
    _, _, selected_contracts = verify_material(root, package)
    append_bytes(root, f'{OUTPUT}/dispositions.json', canonical_bytes(dispositions(root, scenario, compiled, selected_contracts)))
    packet = prepare_request(root, package_path=PACKAGE, chapter=86, renderer_version=2,
                             budget=Budget(max_input_bytes=327680), prompt_view_version=1,
                             context_limits={'version': 1, 'max_context_bytes': 327680,
                                             'overhead_reserve_bytes': 16384, 'output_reserve_bytes': 32768})
    verify_prepared_request(root, packet)
    request = append_bytes(root, f'{OUTPUT}/request.json', canonical_bytes(packet))
    exported = export_request(root, request['path'], directory=f'{OUTPUT}/export')
    receipt = {'status': 'PASS', 'scope': 'LOCAL_EDITORIAL_MODEL_AND_PREPARED_REQUEST_ONLY',
               'source_decision': binding(root, DECISIONS), 'scenario': scenario_ref, 'package': binding(root, PACKAGE),
               'request': request, 'export': exported, 'events': len(events), 'actors': len(actors),
               'objects': len(objects), 'byte_admission': packet['byte_admission'],
               'scope_status': 'PENDING', 'prose_realization': 'NOT_STARTED', 'production_admission': 'NOT_GRANTED',
               'authority_effect': 'NONE', 'original_inputs_unchanged': True,
               'original_contracts': [binding(root, f'data/planning/contracts/agent-final-v1/86-S{i}.v2.json') for i in range(1,7)]}
    append_bytes(root, f'{OUTPUT}/preparation.json', canonical_bytes(receipt))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    from rcwh.corpus.dataset import rebuild_scope
    with rebuild_scope():
        build(parser.parse_args().root.resolve())
