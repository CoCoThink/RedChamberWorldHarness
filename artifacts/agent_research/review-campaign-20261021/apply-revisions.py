"""One-off, evidenced editorial revisions; no provider calls or peer votes."""
from copy import deepcopy
from pathlib import Path
import difflib
import json
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.corpus.locators import source_digest
from rcwh.generation.records import binding, bound_bytes
from rcwh.generation.session import prepare_request, import_draft
from rcwh.generation.writing import feedback_report
from rcwh.graph import ProvenanceGraph
from rcwh.workflow.attribution import release_attribution
from rcwh.workflow.review_campaign import status

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / 'revisions'
EDITS = {
    82: [('到了天明才一盏盏隐去', '早已一盏盏隐去')],
    86: [
        ('另带一人往潇湘馆去。雪雁见她动身，', '又叫人取干净绢子和薄衫，自己候着东西齐了便过去。雪雁见她已作安排，'),
        ('等跟班的赶上宝玉，雪雁已转回园内。', '那跟班听了，又往前面几处去找。'),
        ('宝玉听见，先问：“谁来说的？”跟班的答是雪雁，紫鹃叫赶快去。他又问大夫去了没有，跟班的说来人没说。宝玉本待再问，脚下已向外走，衣带还松着，跟班的伸手要替他理，他把那手拨开了。廊口的小厮见他出来，忙说自己是从哪边来的，宝玉只听见“潇湘馆”，便从他身旁走过去。小厮一愣，也跟着追了上来。\n\n', ''),
        ('雪雁立刻道大奶奶已动身过来，二爷那里也有人去找了。', '雪雁立刻道大奶奶已知道，说取齐东西就来，二爷那里也有人去找了。'),
        ('宝玉还在赶来的路上。', '宝玉那里还没有消息。'),
        ('宝玉进园子时，', '那跟班直到此时才寻着宝玉。宝玉听见，先问：“谁来说的？”跟班的答是雪雁，紫鹃叫赶快去。他又问大夫去了没有，跟班的说来人没说。宝玉本待再问，脚下已向外走，衣带还松着，跟班的伸手要替他理，他把那手拨开了。廊口的小厮见他出来，忙说自己是从哪边来的，宝玉只听见“潇湘馆”，便从他身旁走过去。小厮一愣，也跟着追了上来。\n\n宝玉进园子时，'),
        ('他抬眼问她：“药不是还没吃么？', '他望着那盏药，眼前却是从前她尝药蹙眉的样子，连日子也记混了，抬眼问她：“药不是还没吃么？'),
    ],
    91: [
        ('书办去催接办，她们仍只能在廊下候着。',
         '书办去催接办，她们仍只能在廊下候着。过了一会儿，里头出来一人，先接过那张记录，照着念了“玉样物一”，再将干纸连物一并收妥。书办问他收着了么，那人答收着了，方让她们离开；平儿仍没听见他的名字。'),
        ('方才拾物的纸还未收毕，便问：“这个还带不带话回去？”书办回来道：“只说已记，交回的事还待接着办。”',
         '方才拾物的纸已随小物交进去，便问：“这个还带不带话回去？”书办回来道：“只说已记，纸与物都已收妥。”'),
        ('干纸已折起一边，余下的一边还张着；', '方才放小物的地方已经空了；'),
        ('写的是“玉样物一”，仍待那边接着处理。', '写的是“玉样物一”，纸与物都交给那边的人收妥了。'),
        ('平儿提了一句残雪里拾起的小物，', '平儿先说青灰袄已经认回，左袖里面有奶奶亲自认过的白布，又提了一句残雪里拾起的小物，'),
        ('侄儿没有问得这句话，不敢混说。', '没有问得这句话，不敢混说。'),
    ],
    95: [('那件典青夹袄', '那件青夹袄')],
    96: [('仍旧量两碗半么', '仍照旧量米么'), ('麝月仍量了两碗半，', '麝月照平日的分量量了米，')],
    97: [
        ('她一时忘了刚放在床上的旧衣，', '她一时忘了搭在椅背上的旧衣，'),
        ('他望着那包被退回去的旧衣已不在，手往椅背摸了一下，椅背空着，只有她挂的一件灰衣。',
         '他望见她挂的一件灰衣，手往旁边的椅背摸了一下，那里空着，便将手收回来。'),
        ('惜春是在宝玉走后接着裁纸的。', '昨日宝玉走后，惜春接着裁纸。'),
    ],
    98: [
        ('贾芸看见茶叶在壶口浮着，问这就是早起数过的么。麝月道：“昨日说了，今日才数，你别把我们这点茶说成数了两天。”',
         '贾芸看见茶叶在壶口浮着，问这壶里放了几片。麝月道：“才数过，泡开了又混在一处，待我再告诉你几片么？”'),
        ('宝玉将米数纸的背面拿来，', '宝玉起身将高处的米数纸取回，翻到背面，'),
        ('甄宝玉便去翻夹页，', '甄宝玉便去翻宝玉那本书中的夹页，'),
        ('他想起上午小厮抱书站门口，', '他想起来时小厮抱书站门口，'),
    ],
}

def write(relative, value):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    assert not target.exists(), f'one-off output already exists: {relative}'
    target.write_bytes(raw)
    return binding(ROOT, relative)

def run():
    execution = status(ROOT, 'data/agent_release/research-81-100-v1/review-campaign-v3.json')
    assert execution['status'] == 'PASS' and not any(j['needs_followup'] for j in execution['jobs'])
    selection = json.loads((ROOT / 'data/agent_release/selection-81-100-v2.json').read_bytes())
    assert not (ROOT / 'data/agent_release/selection-81-100-v3.json').exists()
    # Check every replacement before creating any revision records.
    for row in selection['chapters']:
        text = bound_bytes(ROOT, row['candidate']).decode()
        for before, after in EDITS.get(row['chapter'], []):
            assert text.count(before) == 1, (row['chapter'], before, text.count(before))
            text = text.replace(before, after)
    summary = []
    for row in selection['chapters']:
        chapter = row['chapter']
        if chapter not in EDITS:
            continue
        previous = deepcopy(row)
        old = bound_bytes(ROOT, row['candidate']).decode()
        new = old
        for before, after in EDITS[chapter]:
            assert new.count(before) == 1, (chapter, before, new.count(before))
            new = new.replace(before, after)
        base = f'{OUT.relative_to(ROOT).as_posix()}/ch{chapter}'
        feedback = write(base + '-feedback.json', feedback_report(ROOT, row['draft']['path']))
        notes = ('本次为协调者实际局部编辑，保留原作者及父稿。根据真实同行意见和已核正文修正以下具体点，'
                 '不宣称由新提示词重新生成，不新增史实、强行指认物件或改变人物结局。\n' +
                 '\n'.join(before + ' → ' + after for before, after in EDITS[chapter]) + '\n')
        note_ref = write(base + '-editorial-notes.txt', notes.encode())
        prepared = prepare_request(ROOT, parent_path=row['draft']['path'], feedback_path=feedback['path'],
            notes_path=note_ref['path'], revision_template='revise-v2', renderer_version=2,
            model='current-agent-environment')
        request = write(base + '-request.json', prepared)
        text = write(base + '-edited.txt', new.encode())
        result = import_draft(ROOT, text['path'], request['path'], session_id=f'coordinator-edit-20261023:ch{chapter}',
            session_model_label='current agent environment (declared); coordinator actual editor',
            parent_path=row['draft']['path'], feedback_path=feedback['path'])
        row.update(candidate=result['candidate'], draft=result['draft'])
        attribution = release_attribution(ROOT, row)
        assert attribution['contributors'][-1]['principal_id'] == f'session:coordinator-edit-20261023:ch{chapter}'
        record = {'chapter': chapter, 'previous': previous, 'current': row, 'import': result,
            'diff': '\n'.join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile='previous', tofile='current', lineterm='')),
            'attribution': attribution, 'peer_review': 'PENDING_NEW_CONTEXT'}
        write(base + '-result.json', record)
        summary.append(record)
    row = next(r for r in selection['chapters'] if r['chapter'] == 92)
    previous = deepcopy(row)
    source = ProvenanceGraph.from_repo(ROOT).sources['src:gengchen:ch27:xiaohong-great-help']
    assert source['witness']['siglum'] == 'JIAXU'
    package = json.loads(bound_bytes(ROOT, row['writing_package']))
    package['id'] = 'writing-package:ch92:agent-research:v5'
    package['purpose'] += ' 仅更正红玉批语为甲戌本并补归属起始页；正文未由新请求生成。'
    next(s for s in package['sources'] if s['source_ref'] == source['id'])['record_sha256'] = source_digest(source)
    row['writing_package'] = write('data/writing/packages/ch92-agent-research-v5.json', package)
    base = 'data/agent_release/rebind-v5/ch92'
    request = write(base + '-request.json', prepare_request(ROOT, package_path=row['writing_package']['path'],
        chapter=92, renderer_version=2, model='current-agent-environment'))
    result = import_draft(ROOT, row['candidate']['path'], request['path'], session_id='rebind-v5:ch92',
        session_model_label='current agent environment (declared); custody only, no prose generation')
    row.update(candidate=result['candidate'], draft=result['draft'])
    receipt = {'schema_version': 1, 'kind': 'REBIND_DISCLOSURE', 'chapter': 92, 'edition': 'rebind-v5',
        'current': {k: row[k] for k in ('candidate', 'draft', 'writing_package')},
        'previous': {k: previous[k] for k in ('candidate', 'draft', 'writing_package')},
        'previous_rebind_receipt': previous['rebind_receipt'], 'prose_identical_to_previous': True,
        'declaration': '正文未由v5提示词生成；只重绑纠正见证后的92回包。原作者与修订者沿previous和前次回执保留，v4及v5会话均为保管者。',
        'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
    row['rebind_receipt'] = write('data/agent_release/rebind-v5/receipts/ch92.json', receipt)
    attribution = release_attribution(ROOT, row)
    assert row['candidate'] == previous['candidate']
    assert len(attribution['receipt_chain']) == 2
    assert not any(a['principal_id'].startswith('session:rebind-') for a in attribution['contributors'])
    write('data/agent_release/rebind-v5/ch92-result.json', {'import': result, 'attribution': attribution})
    selection['id'] = 'selection:81-100:v3'
    write('data/agent_release/selection-81-100-v3.json', selection)
    write(f'{OUT.relative_to(ROOT).as_posix()}/summary.json', summary)
    print(json.dumps({'status': 'PASS', 'revised': sorted(EDITS), 'rebound_identical': [92], 'review': 'PENDING'}, ensure_ascii=False))

if __name__ == '__main__':
    with rebuild_scope():
        run()
