"""Materialize the root's explicit editorial rulings after reading all opinions."""
from pathlib import Path
import json
from rcwh.generation.records import binding

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def main():
    comparison = json.loads((O / 'comparison/summary.json').read_bytes())
    assert comparison['status'] == 'COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS'
    assert len((O / 'comparison/coordinator-read.jsonl').read_text().splitlines()) == 10
    intents = json.loads((O / 'coordinator-intents.json').read_bytes())['chapters']
    choices = {
        81: '正文及完整审阅输入未变，沿用合格旧意见；两位81—87读者亦核对本回至82的称谓、月诗与旧匣接缝。无新增匿名比较，不扩称全新文学复审。',
        82: '保留v2天明时态修正和夹信候递；两位整段读者核对81→82、82→83。姜包自证和细密核问的旧节奏成本仍在，研究采用不表示已消除。',
        83: '两位匿名读者均偏v3，具体收益是普通弓套、衬布和两路经手可辨；多说明物件也增加账本感。采用这些局部修正，同时认同两位正式读者所报R4只经家书/传闻与直接船上回叙的字面张力仍在，下一版本须改镜头或正式版本化规划，不把偏好票当作合同全兑现。',
        84: '匿名一位微弱偏v3、一位TIE；只减一句权限复核，主体情感与大部分重复相同。研究版采用小幅压缩，仍保留正式回话未齐，承认首次权责、传令与后续停喜活累积过密；84→87决定因果仍未闭合，不据此证明历史婚期许可。',
        85: '两位匿名读者均偏v3相对时间锚点、减少纸页分类及班次自证；病中停手与宝钗帮理的区别值得保留。两轮分纸/壶水仍长、紫鹃过度能干感及揉肩代词歧义未解，第五项观察仍缺。S2/S3路径争议经根核实为同字节别名而非内容断链，原FAIL与r1 PASS并列保存，不改合同冒充五项完成。',
        86: '本回未改，保留找人、得讯、赶到与前日记混锚点、最后一夜P-Lock及冷药结尾；两位81—87读者核对85→86、86→87，不用结构或安全门证明情感达标。重绑历史中的实际称呼编辑仍归编辑者，不误列纯保管。',
        87: '两位匿名读者均略偏旧v2：v3两次突出正式回话未齐却无人面对条件而继续成婚，使筹婚段更妨碍人物重心；两位章读及两位81—87读者的同一因果ADVISORY成立。根仍将v3作为本轮研究候选采用，理由是显露未决条件和未放行旧单，使研究读本如实呈现待解决前提；这不是文学胜出，也不把透明承认未知当作问题解决。没有证据可在冻结稿上补许可，更不回退成已妥结的暗示。将84—87实际责任人、已知范围及明知未齐仍推进的选择列下一正文版本最高优先级，须联合新读；接受本版节奏退步与中央因果缺口。',
        88: '正文与完整章级输入未改；保留交接与麝月持续劳动，两位87—92读者核对87→88、88→89。药盒与后回药包无同一证明，维持分列；劳动成本的呈现不自动抵消节奏意见。',
        89: '两位匿名均略偏v3：小红、茜雪有受控在场与不同关心，宝钗应声即止让欠薪者的话保留余响，留空比问号少概念化。新增复核传话也增开销，多处候问仍同腔；正式r1关于旧薄书未明示《庄子》的ADVISORY成立，89→98书名接口未完成，药盒/药包不强并。按现有有限消息链采用，不将新增场当作所有交接已闭合。',
        90: '完整相同输入复用意见，两位87—92读者核对89→90及90→91的准入、送饭、押收区别；保留历日仍粗与消息限度，不补唯一罪名或制度日期，不宣称等待细务节奏已全部改进。',
        91: '完整相同输入复用意见，两位87—92读者核对90→91、91→92；纸与玉样物有无名接办人收妥，不据此认定就是宝玉佩玉，也不补收件者身份。研究采用仍保留物件同一性与后续物流开放。',
        92: '两位匿名均TIE：直接拒换饭更有冷硬口气，旧版被点名打断也有落空节奏，不能宣称短答使全回更好。采用本轮当班者有限答复以固定小说现场边界，绝不上升普遍监规；认同两位章读关于旧单抽象、留置到准返缺具体变化的中央因果不足，以及两位S6对末韵句预支门外经历的异议。93才领物交碗实过门的单次链经两位BOOK读者核实，但不消除92问题。下版需92—93联合具体化问讯变化并协调收束，不用新罪名或提前释放凑合同；本版接受未解与重复报信成本。',
        93: '正文和完整章级输入未变，复用原意见；两位92—98读者实际核对92准返、93领物交公碗实出门及93→94白事后接续。采用真实单次释放链，不外推92留置事项已写明或全部脱困，保留前回韵句的时间张力。',
        94: '两位匿名均小幅偏v3动作代替旧包自证，优势只在一处。采用取衣卷褥的具体改文，认同两位正式读者所报鞋、鸡、褥边多轮故障拖慢，定数天工旁注及伤/断问答不自然仍在。暂住几日并未变永久；后回承认无近讯不补成延住过程，下一版应合并一轮故障并处理小曲变词。',
        95: '两位匿名均偏v3少两轮量米/熟粥教学、通过近讯与拟留门口接上跨季牵挂；仍不能证明暂住为何延长或新址已送达。采用局部减重复，不取消正式一PASS一ADVISORY对麝月三次直说劳动成本的分歧。保留宝玉催门而未腾手的本版笑料功能，承认与原R3说话人不同，不称原笑料无损。量米木碗与吃饭碗不强合。',
        96: '两位匿名均轻微偏v3删无据劝诗指责、以回望未完信承接；同时都认为新增冬日两碗半回想显解释，旧版熟人失言也有棱角。采用更贴现场的家常提醒及跨季熟粥回声，接受含蓄损失，后续可减显式成长提示。两满一半仅熟粥，生米不作换算；半碗归谁不强推，近讯不等于全知，回信仍留家等待实际递达。',
        97: '两位匿名均TIE：旧版直接双箸起笔更有力，新版寄信后时距与无准信使等待知识边界更明确。研究采用相对时距以接96—97，承认起笔损失和三线细务趋同，若兰当下不在不证明死亡、分居或军务原因；两位BOOK已核回信实际递达，不等于全人物命运闭合。',
        98: '两位匿名均偏v3惯口加分神的误包动机、减少只指纸的追补假设及末段重复辨纸；两位正式章读PASS仍有后段家务过密意见。采用单次误取本人归还的因果压缩，也承认回程删短损失不耐与身体代价、惯口解释仍是旁白。包布、客册借阅条、各纸件及接饭不混同；89薄书身份未明、99后实体归石亦不能倒证。',
        99: '两位匿名均微弱偏v3，决定性理由是贾芸讲渡口揪袖受辱比整齐主题判词更像自身怨气；玉绦、当票和夜色仅增加落点，不单独等于文学进步。采用具体声口及未赎当票痕迹，承认寻人路线控诉偏满、宝玉离去迫切仍多以不答呈现；99携玉不证明100实体交接，末段待补旧衣与典衣不强并。',
        100: '匿名一票v3、一票v2：压缩试衣可减重复，也损失误读和拖到明日的含蓄，舍不得的直说过早定性；两人都报十二名像名册，公服分箱也有陈列感。根采用v3明确幼时回顾、99后多年实授、妇人未退出及母冠帔/儿公服分属的实际可读性收益，并选择保留C-format十二芳讳而不补榜评。接受上述文学成本与中段仍密，不宣称新版胜出或将C-format升为原稿证据；保留两条硬评、开放下层、太虚/青埂峰另层收束及人间未尽后事。',
    }
    chapters = {str(ch): {'outcome': 'ADOPT', 'rationale': intents[str(ch)]['editorial_choice_and_limits'] + ' 实际阅读后的裁定：' + text}
                for ch, text in choices.items()}
    provisional = [json.loads(s) for s in (O / 'root-read-rulings.jsonl').read_text().splitlines()]
    issues = []
    pending_phrases = [
        '最终采用还须结合A/B比较。', '最终文学取舍待A/B比较。', '最终取舍待A/B比较。',
        '最终取舍仍结合A/B比较。', '最终结合匿名比较裁定。', '最终结合BOOK与匿名比较裁定。',
        '最终结合匿名比较具体判断本轮一处改文的收益和限度。',
        '待匿名比较判断局部改文收益，重复说理列后续可压缩范围。',
        '等待匿名比较并保留旧异议。',
        '最终结合匿名比较决定本轮压缩收益，后续可合并一组重复动作而不消灭日常后果。',
        '最终以实际匿名比较判断局部修订效果，模型PASS不等于文学终验。',
        '最终结合匿名比较裁定局部改文得失。',
        '最终结合BOOK和匿名比较裁定。',
    ]
    for entry in provisional:
        receipt = json.loads((O / f"registration-{entry['registration']:03d}.json").read_bytes())
        rationale = entry['rationale']
        for phrase in pending_phrases:
            rationale = rationale.replace(phrase, '')
        text = '；'.join(choices[ch] for ch in entry['affected_chapters'] if ch in choices)
        issue = {'record_sha256': receipt['record']['sha256'], 'subject_id': entry['subject_id'],
                 'ruling': entry['ruling'].replace('_PENDING_COMPARISON', '') + '_FINAL_RESEARCH_DISPOSITION',
                 'rationale': rationale + ' 全部比较及BOOK意见实际读完后的最终取舍：' + text,
                 'affected_chapters': entry['affected_chapters']}
        if entry['subject_id'] in {'contract-85-2', 'contract-85-3'}:
            issue['resolution_evidence'] = [binding(R, (O / 'predecessor-alias-evidence.json').relative_to(R).as_posix())]
        issues.append(issue)
    assert len(issues) == 34
    books = {
        'book-continuity-81-87': '两位均FAIL/ADVISORY，六处接缝各双读，84→87自设待答前提未闭合。根承认原因缺口；两位匿名又略偏旧版而非新版，因此本轮研究采用仅保留显式可检验未知，不记文学PASS，下一版本须补有依据的责任决定并联合新读。其他物件、称谓、知识边界的正面核对不抵销此问题。',
        'book-continuity-87-92': '两位均PASS，各核五缝；准入/迁居/留置/消息边界可接，但药盒与药包、玉样物与通灵玉同一未证。服制、迎春后事及旧单未结仍开放。92末只准返未出门；此PASS不取消87及92章读缺口，亦不授予世界状态登记。',
        'book-continuity-92-98': '两位均PASS，各核六缝；93领物交碗实出门、散扣留城与新衣包入乡、当票未赎、96留家回信97实际递达、98一次误包本人归还均有动作。巧姐延住及新地址实际送达、若兰何因何时不在仍未写；显式未知和跨季锚点避免字面相撞，不等于事项已完成。92末韵句及留置因果的ADVISORY仍成立。',
        'book-continuity-98-100': '两位均PASS，各核两缝；99归还客册借阅条、续绦佩身与100明确回顾/多年实授、母冠帔儿公服分属可辨。人间→太虚→青埂峰是所选C层转换，不证明99携玉至100归石的现实经手全链；宝玉终年及宝钗麝月后事未定，不称全部伏线闭合。',
    }
    result = {'status': 'FINAL_ROOT_AUTHORED_RULINGS_AFTER_READING', 'scope': 'RESEARCH_EDITION_NOT_UNANIMOUS_LITERARY_PASS',
              'chapters': chapters, 'new_issue_rulings': issues, 'book_continuity_rulings': books,
              'comparison': binding(R, (O / 'comparison/summary.json').relative_to(R).as_posix()),
              'required_future_work': [
                  '最高优先级84—87明确知情范围与实际责任决定，联合新读；本轮透明未知仍未解决中央因果。',
                  '最高优先级92—93以有限具体事项/交接差异承接留置与准返，协调末韵句和93单次出门，联合新读。',
                  '83 R4镜头、85第五项缺证及揉肩代词、89薄书书名接口按NEXT_ITERATION.md处理，不下调旧目标冒充完成。',
                  '94小曲旁注和多轮故障、95直说劳动与说话人、96回声解释、98/100重复动作及100名单含蓄损失，另版压缩后实际比较。',
                  '巧姐跨季延住/新址送达、若兰缺席、药盒药包及佩玉至归石实体同一按实际可知证据追踪，不编终局。',
                  '独立人工来源复核、全语料人工覆盖、P9正式文学盲评及生产/stable准入未完成。',
                  '全局world仍为实际依赖；需要变更时再设计可复原且拒绝漏依赖的版本化读集/事件投影。',
              ], 'authority_effect': 'NONE', 'P9_credit': False}
    target = O / 'root-rulings-final.json'
    assert not target.exists()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'chapters': len(chapters), 'specific_new_issue_rulings': len(issues), 'P9_credit': False}))


if __name__ == '__main__':
    main()
