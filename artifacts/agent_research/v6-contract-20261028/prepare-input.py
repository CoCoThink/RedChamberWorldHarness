"""Version a bounded contract clarification; retain prose, dissent and authors."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json

from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding, bound_bytes
from rcwh.generation.session import prepare_request, import_draft
from rcwh.schema import validate_instance
from rcwh.workflow.attribution import release_attribution
from rcwh.workflow.release_packets import prepare, _write_immutable
from rcwh.workflow.review_campaign import plan, status

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REL = O.relative_to(R).as_posix()
OLD = 'data/agent_release/research-81-100-v5/request.json'
BASE = 'data/agent_release/research-81-100-v6'
CONTRACTS = 'data/planning/contracts/agent-final-v1'


def write(path, value):
    return _write_immutable(R, path, value)


def main():
    selection = json.loads((R / 'data/agent_release/selection-81-100-v9.json').read_bytes())
    row = next(r for r in selection['chapters'] if r['chapter'] == 87)
    previous = deepcopy(row)
    versions = [(1, 3, 4), (2, 3, 4), (3, 3, 4), (4, 2, 3), (5, 2, 3)]
    old_refs = {n: binding(R, f'{CONTRACTS}/87-S{n}.v{old}.json') for n, old, new in versions}
    new_paths = {n: f'{CONTRACTS}/87-S{n}.v{new}.json' for n, old, new in versions}
    design = {
        'kind': 'ROOT_CONTRACT_SCOPE_CLARIFICATION', 'baseline_request': binding(R, OLD),
        'plan': binding(R, 'docs/plans/POST80_V6_CONTRACT_20261028.md'),
        'old_contracts': list(old_refs.values()),
        'review_basis': [binding(R, f'data/agent_panel/records/{h}.json') for h in [
            '18520a765790c85537e8c52dcfec6e488d176222534ce791e6798cacc89b7bca',
            'a2dec51afac41080d4c4f7477cf3a024ce0b10eacb39114f649255b437deff8b']],
        'scope': 'C_CURRENT_IMPLEMENTATION_CONTRACT_NOT_HISTORICAL_RULE',
        'decision': '将87-S2逐轮穷尽改为多轮婚议及所承接筹备段累计核对；所有实质约束保留，各轮所提方案不得反向抹去已呈现限制。新版本不获得原版本审阅结论。',
        'unchanged': ['20回正文', '章卡与seed', '世界状态及所有UNKNOWN/PENDING', '史料及原引文', 'v5全部原始意见及发布文件'],
        'prose_edit': False, 'peer_credit': False, 'human_credit': False,
        'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
    design_ref = write(REL + '/design-decisions.json', design)
    changes, refs = [], {}

    def change(c, field, value, reason):
        old = deepcopy(c[field])
        if old != value:
            c[field] = value
            changes.append({'contract_id': c['id'], 'field': field, 'before': old, 'after': deepcopy(value), 'reason': reason})

    for n, old, new in versions:
        c = json.loads(bound_bytes(R, old_refs[n]))
        change(c, 'revision', f'v{new}', '新版本，不覆盖旧合同')
        if n > 1:
            change(c, 'entry_from', new_paths[n - 1], '本包实际选中前驱；仅来源列表次序，非时序核证或出口状态继承')
        if n == 1:
            change(c, 'function', '在本轮C级小说安排的实际守毕之后，将婚议拆成多次内宅小谈，为主婚权、资源压缩与不同动机留下真实形成过程；丧务常态化或数月经过本身不构成除服。', '与v5已另版的首项时间约束一致，不核证历史期限')
        if n == 3:
            change(c, 'function', '承接本轮C级小说实际守毕后议婚，以丧后收敛与连续支出解释缩小的婚礼，真正建立夫妻生活而非骗局，同时保留名义主婚与实际组织的区别。', '避免把缩礼误作服期未满仍可成婚的许可')
        if n == 2:
            beats = deepcopy(c['required_beats'])
            beats[2]['description'] = '核查范围为本回多轮婚议及所承接的筹备段，累计以实际话语或动作呈现婚事规模同时受刚过丧事的收敛与连续丧务、药钱支出压缩，且家计尚非赤贫；必须能分别指出两种压力及其缩减筹办的后果。服毕后再议婚不等于恢复排场；不伪称服期未满的法律禁令仍直接适用。单轮谈话可以只推进住处、女儿负担或其他具体问题，不要求逐轮复述全部压力。'
            beats[3]['description'] = '在上述婚议—筹备序列中累计落实实际服毕的前提、丧后收敛、连续开支、主婚与实际主持的组织权、凤姐病中负担，并分别给出具体依据；同一处可承接数项，不强求每轮都有全套。每轮所提规模与分工不得推翻已经呈现的限制，不得借为宝玉好或长辈认可跳过先前守服义务、两家应允、实际组织或病中负担。'
            for index in (2, 3):
                prior = beats[index].get('editorial_override')
                beats[index]['editorial_override'] = {
                    'decision': design_ref, 'previous_contract': old_refs[n],
                    'scope': 'CUMULATIVE_SEQUENCE_WITH_ALL_CONSTRAINTS_RETAINED',
                    'authority_effect': 'NONE', 'previous_editorial_override': prior}
            change(c, 'required_beats', beats, '正式读者建议：累计范围与逐轮不矛盾并列，保留全部实质要求；不是本轮已通过证据')
        unresolved = list(c['unresolved'])
        if n == 1:
            unresolved = [
                'mourning_obligations: 本轮C级写作要求实际领服次并守毕后议婚；小说具体日历、历史元妃服期及制度程序仍未经核证，世界也没有场级服毕事件。不能由数月、缩礼或家长应允推出历史许可。'
                if s.startswith('mourning_obligations:') else s for s in unresolved]
        if n == 3:
            unresolved = [
                'ritual: 本轮C级写作要求实际守毕后低调成礼；历史期限与礼法程序未核证，场级仪礼、主办及供应链尚无可执行世界事件。写作要求不等于已注册完成。'
                if s.startswith('ritual:') else s for s in unresolved]
        if n == 4:
            unresolved = [
                'placement: 当前选中的87-S5已明确要求园外—返回—第一餐的叙事过渡；该写作义务不再待选择。仍未决的是园外移动及场级时点的模型绑定，B03/VW2-05不因此成为原稿固定回次。候选是否落实须由新独立阅读判断。'
                if s.startswith('placement:') else s for s in unresolved]
        change(c, 'unresolved', unresolved, '分清当前写作义务、未核史制和未注册世界状态；旧措辞保留于逐字段台账及旧合同')
        change(c, 'notes', c['notes'] + f' ROOT_V6_CONTRACT_SCOPE: 本版由{old_refs[n]["path"]}另版。历史notes中“本批前一v2”只说明旧版编辑，本版活动前驱以entry_from为准；前驱仍仅SOURCE_LIST_ORDER_NOT_VERIFIED_CHRONOLOGY，绝不继承状态。详见{REL}/contract-changes.json。正文未改，原87-S2.v3字面FAIL和文学分歧保留，新审阅PENDING。', '披露另版来源与无新增审阅资格')
        errors = validate_instance(c, R / 'schemas/agent_scene_contract.schema.json')
        if errors:
            raise ValueError(errors)
        refs[n] = write(new_paths[n], c)
    ledger = write(REL + '/contract-changes.json', {
        'kind': 'EXACT_CONTRACT_FIELD_CHANGES', 'design': design_ref,
        'contracts': [{'previous': old_refs[n], 'current': refs[n]} for n, _, _ in versions],
        'changes': changes, 'authority_effect': 'NONE'})
    package = json.loads(bound_bytes(R, row['writing_package']))
    package['id'] = 'writing-package:ch87:agent-research:v6'
    package['purpose'] += ' v6另版澄清累计婚议范围和前驱路径；同字节保管稿不是新正文生成，全部新合同待独立复核。'
    replacements = {old_refs[n]['path']: refs[n] for n in refs}
    package['plan'] = [replacements.get(b['path'], b) for b in package['plan']]
    row['writing_package'] = write('data/writing/packages/ch87-agent-research-v6.json', package)
    rebind = 'data/agent_release/rebind-v6-20261028'
    prepared = write(rebind + '/ch87-request.json', prepare_request(R, package_path=row['writing_package']['path'], chapter=87, renderer_version=2))
    imported = import_draft(R, row['candidate']['path'], prepared['path'], session_id='rebind-v6-20261028:ch87', session_model_label='current agent environment; custody only; NO new prose generation or editing')
    row.update(candidate=imported['candidate'], draft=imported['draft'])
    row['rebind_receipt'] = write(rebind + '/receipts/ch87.json', {
        'schema_version': 1, 'kind': 'REBIND_DISCLOSURE', 'chapter': 87, 'edition': 'rebind-v6-20261028',
        'previous': {k: previous[k] for k in ['candidate', 'draft', 'writing_package']},
        'current': {k: row[k] for k in ['candidate', 'draft', 'writing_package']},
        'previous_rebind_receipt': previous['rebind_receipt'], 'prose_identical_to_previous': True,
        'declaration': '只为另版合同重绑同字节保管稿。本轮未生成或编辑正文；全部原作者、真实编辑及旧保管链保留，原文非v6新包生成。',
        'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'})
    before = release_attribution(R, previous)
    after = release_attribution(R, row)
    if before['contributors'] != after['contributors']:
        raise ValueError('custody must not change actual contributors')
    write(REL + '/attribution.json', {'before': before, 'after': after, 'contract_changes': ledger, 'prose_changed': False})
    selection['id'] = 'selection:81-100:v10'
    selection['basis'] = 'v5正文原样保留；仅87另版合同、显式保管重绑和连续作者回执。原FAIL与比较分歧不改写。'
    selected = write('data/agent_release/selection-81-100-v10.json', selection)
    result = prepare(R, 'research-81-100-v6', selected['path'], list(range(81, 101)), coordinator_session_id='coordinator:release-v1', max_book_read_bytes=197 * 1024, reuse_request_path=OLD)
    write(REL + '/prepare-output.json', result)
    planned = plan(R, BASE + '/request.json', BASE + '/review-campaign-v1.json', batch_size=3, max_read_bytes=197 * 1024, max_attempts=3)
    write(REL + '/campaign-plan.json', planned)
    observed = status(R, BASE + '/review-campaign-v1.json')
    write(REL + '/campaign-baseline.json', observed)
    document = json.loads((R / (BASE + '/review-campaign-v1.json')).read_bytes())
    current = json.loads((R / (BASE + '/request.json')).read_bytes())
    old = json.loads((R / OLD).read_bytes())
    changed = [a['chapter'] for a, b in zip(current['chapters'], old['chapters'], strict=True) if a['panel'] != b['panel']]
    if changed != [87] or any(a['candidate'] != b['candidate'] for a, b in zip(current['chapters'], old['chapters'], strict=True)):
        raise ValueError('unexpected review/prose impact')
    summary = {'status': 'PREPARED_PENDING_INDEPENDENT_REVIEW', 'request': binding(R, BASE + '/request.json'),
        'plan': planned['plan'], 'changed_chapter_packets': changed, 'prose_changed_chapters': [],
        'states': dict(Counter(j['status'] for j in observed['jobs'])),
        'fresh_jobs': [j['id'] for j in observed['jobs'] if not j['reused']],
        'jobs': len(observed['jobs']), 'max_reading_bytes': max(j['reading_bytes'] for j in document['jobs']),
        'budget_unit': 'UTF8_BYTES_NOT_MEASURED_TOKENS', 'peer_credit': False, 'authority_effect': 'NONE'}
    write(REL + '/preparation-summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with rebuild_scope():
        main()
