# v4 修订、跨回审读上下文与未解决研究交付

本轮正文修订和正式模型审读已完成。当前评价 **PENDING，无FAIL发现；239门PASS、1门PENDING**。第87回的风险性质和边界仍缺依据，协调者决定保持PENDING；其他19回为研究ADOPT。正常build实际退出1，明确拒绝PENDING发布，未生成正常版本book或manifest。审阅读本仍可交接，不可称正常发布完成、人工通过或P9。

## 交付入口

- [20回审阅读本](../../../data/agent_release/research-81-100-v4-r3/reading/book.md)：r3冻结的当前全文，r4未再编辑正文。
- [机器可读交接索引](human-final-release-index.json)：发布book/manifest为null，另列reading_book、20回候选、实际评价、连续性材料和出处索引。
- [真实发布评价](final-release-evaluation.json)与[正常构建实际命令、输出、退出码](normal-build-attempt.json)。CLI的拒绝信息实际在stdout，stderr为空。
- [逐回决定与全部意见处置台账](coordinator-dispositions.json)、[三项核心问题的实际新读句证](core-causal-rulings.json)。
- [人工审阅材料说明](HUMAN_REVIEW_HANDOFF.md)、[来源/语料索引](human-material-index.json)、[下一轮具体顺序](NEXT_ITERATION.md)。索引准备不计人工信用。

## 正文结果

相对v3基线29a81d5，实际改动83、85、87、92、93五回，其他十五回精确保持。原稿作者、真正的追加编辑者及重绑保管链均保留；重绑不会被计作正文生成。最初89揭名提案因违反89-S6不揭书名约束在正式审读前撤回，当前89完整恢复v3原稿，撤回稿及其作者记录仍留历史。

83以府门带信人的有限亲闻代替船上直接镜头，满足当前视角约束；两位新比较读者均更喜欢旧版探春触空页的在场感，接受这一文学损失，不记新版全面胜出。85只把揉肩对象明确为黛玉，两位比较均持平；第五项观察仍缺，原目标未下调。

87经过实际再次修订，写出贾母余年焦虑、王夫人盼儿子有人相伴、薛姨妈拒女儿承担治病期待及贾政婚日仍照办的选择。两位新章读仍报同一缺口：未齐事项究竟是什么、已有何种规则依据、冒何风险、为何父母担责足以解释仍办。81—87连续性一FAIL一PASS；两位比较虽均偏新版人物冲突，不能消除此缺口。[实际来源范围评估](../v4-risk-revision-20261026/marriage-source-scope-assessment.json)说明现有两条固定上下文不足以补造许可、婚期、处罚或可转移法律责任。因此87PENDING，不用协调者理由关闭。

92用旧单书箱注名、缺盖角、最初收件纸不够辨识，到新纸箱貌、搬送及接件另核对，建立有限准返的实际信息变化。两位当前章读均明确确认这一因果，一位仍因碗鞋毡后再叠湿巾失措、反复被纠正和等待节奏FAIL/ADVISORY；另一位亦报重复与回题“小红寻证”强于实际送物核实。两位比较均偏新版的具体物件及悬停结尾，不将偏好扩大成全回通过或制度核证。

原二句只移到93实际领物、过门、归家吃净热粥之后、凤姐死亡之前；未增诗，不把韵句“十日”实数化成精确拘留日历。C级位置选择、旧章卡原位及两张新局部合同92-S6.v3、93-S2.v3均披露。两位93正式读者核对落位，两位新92-S6读者又完整联合读92/93确认单次放行及不重复；两位比较均稍偏旧版93的过渡，末段找针换布、交孩子与站位问题仍保留。

## 实际审读与分歧

当前r4 campaign共76项，全部COMPLETE、无needs_followup，70项完整输入复用、6份当前92新意见。r3历史74项也收到意见，其92-S6因未附93导致的NOT_CHECKED原样保留，不能因r4完成而改PASS。

r2/r3/r4实际新增正式意见分别7/17/6，共30份、106条结果；连同前版共198份正式记录、788条结果。新增14条负面均有具体根处置。全历史139条负面（137条ADVISORY、2条已在旧轮通过实际新证和新读处理的历史BLOCKING）保持原样；不是本轮存在两个未处理BLOCKING，也不能借协调者覆盖当前硬锁。

8位新分段整书读者覆盖81—87、87—92、92—98、98—100，相邻重叠一回，19接缝各有两份逐缝说明，共38份说明。81—87一负一正，87—92双正，92—98一负一正，98—100双正。巧姐暂住几日如何跨季延住、96若兰日常回信到97缺席的状态桥，虽有读者视为留白，仍接受为未解决疑问；不补造死亡、永久安置或新址送达。药盒/药包、玉样物/佩玉及99佩玉到100归石的实体链继续开放。

另有4位全新自主限读的A/B模型比较读者，10个逐回选择：83两票v3、85两票TIE、87两票v4、92两票v4、93两票v3。所有reason/evidence/risks均由根实际展开后另行记录阅读声明。匿名是自愿限读，非技术隔离；资源平等未核证，阅读声明非机器证明，模型比较非P9。

## Harness实改

新增按subject声明的`review_context_chapters`：prepare把当前相邻候选真正写入packet，评价重算当前选择并拒绝旧候选/漏上下文，且排除相关作者、编辑和保管者。campaign预算由合同本身改为完整subject及context按路径去重的总读集，单项仍超预算即拒分派，不能只标exceeds_budget再继续。详见[ADR0010](../../../docs/decisions/0010_CROSS_CHAPTER_REVIEW_CONTEXT.md)。

实际92拆成三组、各两位读者，读集173813/163171/118382字节，均低于197KiB；这是实测字节，不是实测token。r4保留20回全部候选、谱系、写作包及BOOK packet，只改92审阅上下文；其他19章packet精确复用。

3次真实临时故障（两次503、一次429）与新上下文重试全部保留：r3实际20次启动得到17份成功意见，失败不计同行信用。当前r4六次启动六份成功。全过程只用主agent环境原生子代理，无自行调用外部模型provider/API或密钥。

增加核心处置约束：未解决章节不能ADOPT，至少两位不同实际新读者、当前packet、真实引句及根解释，未读/伪造引句/重复读者均拒绝。7项专门对抗测试通过，合成fixture仅用于测试不算同行证据。审阅仍按scaffold生成、串行登记，根看到完整notes/sample_checks后另一次调用记录已读；BLOCKING不可覆写。

89内部IF-016确实存在于嵌套semantic_obligations规则，不能推成本回须揭名。三条历史协调者的错误推论以追加更正保留原记录，不改读者话，也不消除其余节奏与物件接口问题。

world等全局文件仍是实际整文件依赖；本轮没有实现事件/状态语义投影，不能宣称未来全局任意小改均不影响兼容性。历史谱系完整性与当前输入兼容性仍分开核验。

## 验证及提交状态

输入冻结9172e79900d7341de9d3a77277fe3e888672dc56的[双版本CI](https://github.com/CoCoThink/RedChamberWorldHarness/actions/runs/40328297205)均成功，各1815 passed、1 skipped，之后才启动当前六位新读者。前两轮也各有自己的输入提交与双绿回执，不能互相代用。针对完整跨回读集、上下文变更失效及作者独立性的32项定向测试通过。

20回writing lineage历史完整性及当前兼容性均PASS；资产核验和仓库完整性PASS。正常build未使用allow-pending，真实拒绝已保存。初次验收脚本错误限定stderr，导致脚本失败；[更正记录](normal-build-harness-correction.json)保留这一失败，修正为先保存实际输出再检查两路，随后实际重跑成功核对拒绝，没有重建丢失输出。

执行审计、local交接、payload提交后的克隆验证与最终HEAD的CI须分别核验；本报告不以输入CI替代最终提交CI。克隆工具内部使用allow-pending，仅可在一次性克隆生成PENDING manifest且无book，不能称PASS版本复现。下面的交付阶段记录在真实完成后追加；缺失即尚未完成。

执行审计实际PASS，复核三轮输入CI先于全部启动、真实失败/重试、30份新记录的原件和根阅读声明、19缝双读、4份比较，以及当前请求只在输入冻结后增添决定。历史来源、world、scenes、v1—v3版本和stable对29a81d5保持。审计详见[actual-execution-verification.json](actual-execution-verification.json)。[本地交接验证](final-local-validation.json)实际PASS，但release_status仍PENDING、normal_build_succeeded=false，不能读作正常版本已构建。

索引组装脚本初次执行因循环变量覆盖binding helper而报TypeError，未生成交接产物；改名后实际重跑通过。[失败与更正](local-delivery-harness-correction.json)保留，不增加审读信用，不改变任何候选、意见或处置。

payload提交为`f522e82c833009fbbe7619c8478afa89b785c360`，其已提交HEAD的真实一次性克隆验证已PASS。工具核验当前20回作者链、76项覆盖、19接缝与197KiB完整读集预算；最大实际读集199577字节。克隆使用显式allow-pending，结果仍PENDING，只生成临时manifest、text=null且无book；一次性目录随验证销毁，工作树不发布PENDING或正常版本。回执见[committed-clone-verification.json](committed-clone-verification.json)及[绑定到payload提交的保管说明](committed-clone-custody.json)。

随后提交仅追加以上回执和本段说明，再推送`research/v4-20261026`；最终提交本身的双版本CI必须按最终HEAD另行确认。报告不虚构尚未产生的最终CI自引用回执，最终回复提供实际HEAD及对应GitHub run。正常发布仍由87PENDING阻止，下一正文动作按NEXT_ITERATION先作适用范围论证。
