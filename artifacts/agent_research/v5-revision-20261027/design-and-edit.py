"""Root's actual prose revision; no independent-reader or human credit."""
from copy import deepcopy
from pathlib import Path
import difflib
import json

from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding, bound_bytes
from rcwh.generation.session import prepare_request, import_draft
from rcwh.generation.writing import feedback_report
from rcwh.workflow.attribution import release_attribution

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REL = O.relative_to(R).as_posix()
OLD = 'data/agent_release/research-81-100-v4-r4/request.json'


def write(path, value):
    target = R / path
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    if target.exists():
        assert target.read_bytes() == raw, 'resume would replace retained bytes: ' + path
        return binding(R, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return binding(R, path)


def main():
    selection = json.loads((R / 'data/agent_release/selection-81-100-v8.json').read_bytes())
    rows = {row['chapter']: row for row in selection['chapters']}
    edits = []

    def replace_line(ch, number, after, issue):
        old = bound_bytes(R, rows[ch]['candidate']).decode().splitlines()[number - 1]
        assert old and after and old != after
        edits.append(dict(chapter=ch, issue_id=issue, before=old, after=after))

    replace_line(84, 89,
        '宫中正式服制的条目，起初还没有送齐。王夫人问过，凤姐便将门上回的照实说，不拿已经换上的素衣作答。又过两日，贾政从外头带回本家应守的服次，叫跟出去的人在王夫人跟前读明白，才交各处照办。针线房原来拿不准的几件衣裳，领回去重做；王夫人翻着历，将各人应守到的日子记在旁边。有人拿做喜活的旧单来问，凤姐抬手叫收回，道：“服还没守完，就照旧日子催起来了？先搁着。”那张纸便压回别单下面，没有换上一个新日子。',
        'MOURNING_ACTUAL_WAIT_84_87')
    replace_line(87, 3,
        '自黛玉去后，又过了几个月。贾母房里的饭桌照旧摆着，人却比先前坐得疏了些；有时说起一个人的口味，说到半句，便换了话。元春丧后领回的服次，家中各人已照着守毕。王夫人收起记日子的那本历，原先搁下的喜单才又拿出来；纸边压得发软，仍是从前写的，不能照旧日子用了。针线房来问亮颜色的料子可否动，她让只取房里必要的几样，余下仍存着。外头应酬的帖子也没有一齐回，鸳鸯每日替贾母分开，老人想见的，才另叫人请。',
        'MOURNING_ACTUAL_WAIT_84_87')
    replace_line(87, 9,
        '王夫人道：“娘娘的服虽守完了，家里才过这些事，也不宜忽然闹起来。”贾母的手在炉套上停了一停，说：“这我知道。先前该候的，我们也候了。如今你同老爷说，再同姨太太慢慢商量，别拿我的话去催她。”薛姨妈听了，原来要说的那句吉利话便收住，只道：“孩子从小在跟前，一旦要她另过日子，我倒想不出先该问哪一桩。”贾母道：“那也不是出去不回来了。屋子总还在，你想她，自有见的时候。”',
        'MOURNING_ACTUAL_WAIT_84_87')
    replace_line(87, 17,
        '王夫人回房，贾政正问家中近来几项开销。她待账上的话说完，才将贾母的意思并薛姨妈的话告诉他。贾政听罢，先叫将原来的喜单拿来，见上头还是丧前的日子，便推到一旁，道：“这个不算。两家如今各有什么话，另商量了再择日。”王夫人道：“所以今日先同老爷说。老太太虽愿意，姨太太还没有定话。”贾政点头，又问办事的人可仍都在凤姐那里候。她说正要去问，贾政便道：“她那身子，还当从前使么？”王夫人原想叫凤姐总理一遭，听了便把这句话留在心里。',
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    replace_line(87, 25,
        '媒人来回了几遭，屋子、衣饰都有了着落，日子却还没有定。王夫人又来见贾政，说贾母近日总问，自己也盼早些。贾政将纸搁下，道：“才说不赶，如今又赶什么？”王夫人道：“宝玉如今肯吃饭了，日里却仍坐着发怔。我想叫他们早有个家常过的日子。”贾政道：“他坐着发怔，倒要靠娶亲来治？”王夫人脸上热起来，半晌道：“不敢说治得好。我是他母亲，只盼他回来有个肯说话的人。”',
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    replace_line(87, 27,
        '到了贾母跟前，王夫人说起这话，贾母听着，手炉放在膝上，许久才道：“我也想早看见他们两口子过起来。只是你同姨太太说，她若还有话，别因我年纪大了便不肯说。”王夫人问是否再候些时，贾母望着她，道：“该候的那一层已经候过，如今别替人家作主。你去问她究竟。”鸳鸯在旁替她拢好炉套，贾母还想问宝玉午饭吃了多少，王夫人答不上来，便先叫人往怡红院问去。',
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    replace_line(87, 29,
        '薛姨妈听了，却没有立刻应日子。她将手里的针插回去，道：“我把女儿嫁过来，不是叫她替宝玉治病的。往后他有不好的，你可别说是成婚不中用。”王夫人道：“这句话我记着。”薛姨妈望着她：“你前儿说她明白，往后有个人可问，我回来想了一夜。她进门先是过自己的日子，不是接你们一家子的事。”王夫人有些难为情，道：“住处和她跟前的人，照前头商量的。凤丫头身上缺的差事，另寻人接，不给她。”薛姨妈这才将针线拢进笸箩，道：“那你把日子拿来，我也问问她，别样样临到头才告诉。”',
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    replace_line(87, 31,
        '王夫人回来，将薛姨妈的话告诉贾政。贾政问母亲可知道，听说已回过，才叫将两家商量的日子另写一张，拿去给贾母看。王夫人接了纸，又问席面，他只道：“照先说的，别到临头又添。”她先去贾母处，回来才叫管事媳妇照日子分派。廊下一个婆子说老太太要借喜事冲一冲，平儿问她几时得了这句话，婆子含糊一笑，便低头收起手里的样子。棚、满廊彩灯和戏的单子仍压着，平儿把另写的日子交出去，没有把那些旧单夹进去。',
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    old = bound_bytes(R, rows[87]['candidate']).decode().splitlines()[48]
    replace_line(87, 49, old.replace('丧中本不宜闹，他们偏在这上面逞能。', '才过这些丧事，他们偏在这上面逞能。'), 'MOURNING_ACTUAL_WAIT_84_87')
    old = bound_bytes(R, rows[87]['candidate']).decode().splitlines()[50]
    tail = old[old.index('原先压下的棚、灯、戏并没添回去。'):]
    replace_line(87, 51,
        '到了定下的日子，王夫人天未亮便起来，先问薛家送来的衣被可齐，再叫管事媳妇看着迎送。她还待叮嘱一遍客数，那媳妇已将改过的单子递上，旧时那张另压在下面，折角还翘着。' + tail,
        'FAMILY_AUTHORITY_NOT_EXEMPTION')
    old = bound_bytes(R, rows[95]['candidate']).decode().splitlines()[10]
    end = old[old.index('贾芸应下，才说附近两处'):]
    replace_line(95, 11,
        '贾芸来得倒早。宝钗先问巧姐近来怎样，贾芸道：“这阵子没得着近信。入秋平姑娘来过那回，不是说刘家肯再留她过冬么？琏二叔应了，冬衣也托车带去了。姥姥说家里炕窄，添铺盖也搁不下，平姑娘只送了孩子穿的。”宝钗记起来，道：“原说几日，一季一季留到如今。开春总还得再问，不能只叫那边替咱们等着。搬定以后，也得给平儿留个门口，别有话来又寻不着。”' + end,
        'QIAOJIE_RENEWED_TEMPORARY_STAY')
    old = bound_bytes(R, rows[97]['candidate']).decode().splitlines()[2]
    replace_line(97, 3,
        '自寄出上封信后，又过些日子。起初若兰有一晚未回来，湘云只叫将饭留着，第二日便仍照两个人的数预备。后来留过的饭又热了一回，她先吃了，另一碗搁到夜深，也没有人动。此后仆妇盛饭总要问，她嫌问得烦，又说不出明日该留多少。这日将箸摆在桌上，才发现又摆了两副。' + old[old.index('靠自己的一副齐着碗沿'):],
        'RUOLAN_ABSENCE_ONSET_WITHOUT_CAUSE_VERDICT')
    design = {
        'kind': 'ROOT_V5_ACTUAL_EDITORIAL_DESIGN', 'basis_request': binding(R, OLD),
        'changed_chapters': [84, 87, 95, 97], 'edits': edits,
        'decisions': [
            {'issue_id': 'MOURNING_ACTUAL_WAIT_84_87', 'choice': '84增加实际收到本家服次、分派及记日；87在实际守毕后才重新议婚。取消从数月经过自动推出除服，取消始终等待不明许可却强行成婚。', 'level': 'C_CURRENT_FICTION', 'limit': '不锁历史元妃服期、年日、法律处罚或宫廷婚嫁批准；两条史料并未证明小说具体服次，已明确为另版重设。丧后收敛、支出与数月缓冲继续约束规模。'},
            {'issue_id': 'FAMILY_AUTHORITY_NOT_EXEMPTION', 'choice': '主婚权只决定两家婚约、日子与组织，不再替代丧制或转移孩子法律责任；矛盾改落宝钗是否被当作疗治者和家务接班者，四方声音与具体分工仍在。', 'limit': '本轮删去泛称宫中待复的旧设，不宣称以新对白解决旧设的适法性。必须全新双读及文学比较。'},
            {'issue_id': 'QIAOJIE_RENEWED_TEMPORARY_STAY', 'choice': '95补入秋已由刘家同意、贾琏应允、平儿实际送冬衣的续住；暂住逐季延长和刘家炕窄的代价仍可见。', 'level': 'C_CURRENT_FICTION', 'limit': '贾芸没有最新近信；不宣称永久安置、巧姐终婚、孩子同意或新住址已送到。'},
            {'issue_id': 'RUOLAN_ABSENCE_ONSET_WITHOUT_CAUSE_VERDICT', 'choice': '97在湘云可知范围内补首次一夜未归、留饭再热、后来仍未归的起点；由份饭动作转入本回。', 'level': 'C_CURRENT_FICTION', 'limit': '不造死亡、军务、遗弃、旅途或终局。96信是写信当时日常，97缺席不再无起点突变。'}],
        'deferred': [
            {'chapter': 83, 'reason': '本轮限定婚事与两处状态桥；传信口供的节奏仍保留为负面，不宣称已压缩。'},
            {'chapter': 85, 'reason': '第五观察缺证仍开放，不改目标。'},
            {'chapter': 93, 'reason': '交孩子/换布找针及站位密度仍是文学风险，保留原意见供下一轮，不机械删去临终劳动。'},
            {'chapters': [89, 99, 100], 'reason': '书名与物件身份、归石物流不在本轮补造；保持历史纠正和留白披露。'}],
        'design_assistance': 'NONE_ROOT_DESIGNS_AND_EDITS', 'peer_credit': False,
        'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
    design_ref = write(REL + '/design-decisions.json', design)
    # Explicit alternate timing under unchanged no-unbuffered-marriage goal.
    contract_refs = {}
    for sid in ['87-S1', '87-S2', '87-S3']:
        original_path = f'data/planning/contracts/agent-final-v1/{sid}.v2.json'
        c = json.loads((R / original_path).read_bytes())
        c['revision'] = 'v3'
        note = 'ROOT_V5_C_TIMING_RESET: 按原87章卡丧期后议婚目标，84实际领服次、87实守毕后重新议婚；并非历史元妃服期考证。保留数月缓冲、无万能豁免、丧后收敛及连续支出约束，不继续假设婚日在未尽丧期内。原v2与负面完整保留。'
        c['notes'] += ' ' + note
        c['unresolved'].append(note)
        descriptions = {
            '87-S1-R1': '黛玉死后数月与元春丧务由急骤到常例分别；数月本身不构成除服。依本轮C级改设，84须实际领回本家服次并照办，87须先实守毕才重新议婚，不悬置正式许可后靠长辈担责照办。内宅多次小谈落于服毕之后，不由一次会议授予婚嫁豁免。',
            '87-S2-R3': '每次谈话须显示婚事规模同时受刚过丧事的收敛与连续丧务、药钱支出压缩，但家计尚非赤贫。服毕后再议婚不等于恢复排场；不伪称服期未满的法律禁令仍直接适用。',
            '87-S2-R4': '每谈规模都分别落实实际服毕后的丧后收敛、开支与组织权，不用为宝玉好盖掉先前守服义务、主婚和实际主持、凤姐病中负担。',
            '87-S3-R1': '成礼缩写但明确确实成夫妇。承接84实际领服次和87实际守毕后议婚，规模仍受丧后收敛与开支约束；主婚名义、两家应允和实际组织分别写，不用长辈万能豁免，不伪造礼法规程或法定期限。'}
        for index, beat in enumerate(c['required_beats'], 1):
            beat_id = beat.get('id', f'{sid}-R{index}')
            if beat_id in descriptions:
                beat['description'] = descriptions[beat_id]
                beat['editorial_override'] = {'decision': design_ref, 'previous_contract': binding(R, original_path), 'authority_effect': 'NONE', 'scope': 'C_FICTION_TIMING_NOT_HISTORICAL_RULE'}
        contract_refs[sid] = write(f'data/planning/contracts/agent-final-v1/{sid}.v3.json', c)
    row = rows[87]
    previous = deepcopy(row)
    package = json.loads(bound_bytes(R, row['writing_package']))
    package['id'] = 'writing-package:ch87:agent-research:v5'
    package['purpose'] += ' v5显式改设为实际服毕后议婚；新合同为C级编辑时间安排，非历史许可。'
    package['plan'] = [next((ref for sid, ref in contract_refs.items() if b['path'].endswith(sid + '.v2.json')), b) for b in package['plan']]
    row['writing_package'] = write('data/writing/packages/ch87-agent-research-v5.json', package)
    base = 'data/agent_release/rebind-v5-20261027/ch87'
    request = write(base + '-request.json', prepare_request(R, package_path=row['writing_package']['path'], chapter=87, renderer_version=2))
    result = import_draft(R, row['candidate']['path'], request['path'], session_id='rebind-v5-20261027:ch87', session_model_label='current agent environment; custody only, original body NOT generated by new package')
    row.update(candidate=result['candidate'], draft=result['draft'])
    row['rebind_receipt'] = write('data/agent_release/rebind-v5-20261027/receipts/ch87.json', {
        'schema_version': 1, 'kind': 'REBIND_DISCLOSURE', 'chapter': 87, 'edition': 'rebind-v5-20261027',
        'previous': {k: previous[k] for k in ['candidate','draft','writing_package']},
        'current': {k: row[k] for k in ['candidate','draft','writing_package']},
        'previous_rebind_receipt': previous['rebind_receipt'], 'prose_identical_to_previous': True,
        'declaration': '新包只重绑同字节保管父稿，原正文非本次包生成；随后另作真实有父稿编辑。所有原作者/编辑与旧保管链保留。', 'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'})
    summary = []
    for ch in design['changed_chapters']:
        row = rows[ch]
        previous = deepcopy(row)
        old = bound_bytes(R, row['candidate']).decode()
        new = old
        for e in edits:
            if e['chapter'] == ch:
                assert new.count(e['before']) == 1
                new = new.replace(e['before'], e['after'])
        assert new != old and new.endswith('\n')
        base = REL + f'/revisions/ch{ch}'
        feedback = write(base + '-feedback.json', feedback_report(R, row['draft']['path']))
        editor = f'coordinator-v5-edit-20261027:ch{ch}'
        notes = write(base + '-editorial-notes.json', {'kind': 'ROOT_ACTUAL_EDITORIAL_REVISION', 'chapter': ch, 'editor': 'session:' + editor, 'design': design_ref, 'declaration': 'Root actual edit; no design delegation or peer credit. Original authors, editors, custodians and negatives remain.', 'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'})
        request = write(base + '-request.json', prepare_request(R, parent_path=row['draft']['path'], feedback_path=feedback['path'], notes_path=notes['path'], revision_template='revise-v2', renderer_version=2))
        text = write(base + '-edited.txt', new.encode())
        result = import_draft(R, text['path'], request['path'], session_id=editor, session_model_label='current agent environment; root actual v5 editor', parent_path=row['draft']['path'], feedback_path=feedback['path'])
        row.update(candidate=result['candidate'], draft=result['draft'])
        attribution = release_attribution(R, row)
        assert attribution['contributors'][-1]['principal_id'] == 'session:' + editor
        record = {'chapter': ch, 'previous': previous, 'current': deepcopy(row), 'import': result, 'editorial_notes': notes, 'attribution': attribution, 'diff': '\n'.join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile='v4-r4', tofile='v5', lineterm='')), 'peer_review': 'PENDING_NEW_INPUT_CI_AND_NEW_READERS'}
        write(base + '-result.json', record)
        summary.append({'chapter': ch, 'candidate': row['candidate'], 'draft': row['draft'], 'changed_bytes': len(new.encode()) - len(old.encode())})
        print(json.dumps(summary[-1]), flush=True)
    rows[84]['review_context_chapters'] = {'chapter-84': [87], 'contract-84-3': [87]}
    rows[87]['review_context_chapters'] = {'chapter-87': [84], 'contract-87-1': [84], 'contract-87-3': [84]}
    rows[95]['review_context_chapters'] = {'chapter-95': [94]}
    rows[97]['review_context_chapters'] = {'chapter-97': [96], 'contract-97-1': [96]}
    # Exact current 92/93 context is retained by the selection explicitly.
    old_rows = {r['chapter']: r for r in json.loads((R / OLD).read_bytes())['chapters']}
    if old_rows[92].get('review_context_chapters'):
        rows[92]['review_context_chapters'] = old_rows[92]['review_context_chapters']
    selection['id'] = 'selection:81-100:v9'
    write('data/agent_release/selection-81-100-v9.json', selection)
    write(REL + '/revision-summary.json', {'status': 'IMPORTED_NOT_REVIEWED', 'changed_chapters': design['changed_chapters'], 'revisions': summary, 'selection': binding(R, 'data/agent_release/selection-81-100-v9.json'), 'authority_effect': 'NONE'})


if __name__ == '__main__':
    with rebuild_scope():
        main()
