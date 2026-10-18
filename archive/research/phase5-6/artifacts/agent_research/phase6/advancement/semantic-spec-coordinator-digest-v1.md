# 研究语义能力规格：审计摘要与实现边界

状态：SPECIFICATION_DRAFT_NOT_IMPLEMENTED。MODEL/NONE。所委派P3预审模型报告以实际选中bytes重算policy及inspect_contract；下列为协调摘要，不是新语义评审、执行通过或人审资格。运行代码／旧schema未因本规格修改；完整工程检查仍阻塞。

## 1. 按实际包选择计数，不扫描目录取最新

选集：`revisions-v2/release-evaluation/request-v1.json`，SHA256 `9a2da8de544bbaa1e83e2984dc7db4cb142fc4423892a12673284c22bf66f47b`。20个候选、20个policy、20个v3写作包绑定和plan引用均由预审者核对。合同来自72份agent-final-v1与13份agent-final-v2，不是全部目录文件。

| 章 | 所选合同（连续范围） | 数 | anchor／policy父义务 | required／forbidden beat | entry／precondition／exit |
|---|---|---:|---:|---:|---:|
|81|v1/81-S1..3.v2|3|0／9|12／6|6／4／6|
|82|v1/82-S1..2.v2|2|0／9|8／4|4／2／4|
|83|v1/83-S1..3.v2|3|0／9|12／6|6／3／6|
|84|v1/84-S1..4.v2|4|0／9|16／8|9／5／8|
|85|v1/85-S1..3.v2|3|1／11|12／6|6／6／8|
|86|v1/86-S1..6.v2|6|2／17|21／19|11／7／12|
|87|v1/87-S1..5.v2|5|1／14|16／15|8／5／6|
|88|v1/88-S1..5.v2|5|2／19|15／16|7／5／6|
|89|v1/89-S1..6.v2|6|1／16|21／19|8／6／9|
|90|v1/90-S1..3.v2|3|1／13|10／10|7／4／5|
|91|v1/91-S1..4.v2|4|0／15|11／10|7／4／9|
|92|v1/92-S1..6.v2|6|0／25|18／16|8／6／17|
|93|v1/93-S1..5.v2|5|0／11|16／13|7／5／12|
|94|v1/94-S1..6.v2|6|0／11|18／17|9／6／9|
|95|v1/95-S1..3.v2|3|0／14|10／10|7／3／9|
|96|v1/96-S1..4.v2|4|0／12|12／8|6／5／5|
|97|v1/97-S1..4.v2|4|3／18|12／8|6／5／4|
|98|v2/98-S1..3.v3|3|0／19|9／6|4／3／3|
|99|v2/99-S1..5.v4|5|0／13|15／11|8／5／7|
|100|v2/100-S1..5.v3|5|3／25|16／11|6／5／6|
|合计|85份唯一合同，20份policy|85|14／289|280／219|140／94／151|

### 不可混淆的覆盖数量

- 38项forbidden记录已作为FORBIDDEN_DRIFT包含在289父义务中，不另加成327。
- 五P-Lock有20个required_feature子项；289不是所有自由文本原子命题的数量。
- policy义务类型：CURRENT_IMPLEMENTATION91、CROSS_CHAPTER_CONTEXT100、FORBIDDEN_DRIFT38、DECISION_BOUNDARY31、TITLE_BOUNDARY14、SEMANTIC5、PLOCK_REVIEW5、TERMINAL_PLACEMENT3、SOURCE_ONLY1、LEGACY_BOOK_SCOPE_NOT_PROJECTED1。
- 499 beats中337有ID，162无ID（required83、forbidden79，位于86–90）；无ID以原subject hash+JSON pointer定位，不改旧合同补ID。
- entry41 KNOWN／99 UNKNOWN；precondition12 KNOWN／80 UNKNOWN／2 PENDING；exit0 KNOWN／121 UNKNOWN／30 PENDING。385行状态条件，不等于385条可执行状态转移。
- 85合同均含未决，共812个字符串；26 participants KNOWN、58 PENDING、1 UNKNOWN。20个CHAPTER_ENTRY、65个局部UNKNOWN checkpoint。
- world event引用15次／14合同、object24次／15合同、knowledge2次／1合同；引用次数不是已执行事件数。
- 98–100全部13合同显式NARRATIVE_ONLY_NOT_EXECUTABLE；另外72份并不因此默认可执行。

## 2. 真实当前结果与可达性

预审者实算：85 declared均PENDING；replay20 PENDING、65 NOT_CHECKED；prose85 NOT_CHECKED。单条53次状态相符不能说成53份合同通过；另有57未知状态、20覆盖不足、20未决draft、65局部checkpoint不支持、4未绑定knowledge checkpoint结果。

20policy结构检查无误；19 anchor PASS／语义PENDING，86原选v1两个原字缺失而FAIL。86窄v2 anchor PASS／总语义PENDING，仍未被现有release或连续阅读选集中选用。

`agent_release.py:_policy`固定PENDING是缺少专门consumer的保守状态；不是可删的拼写错误。CONTRACT_PEERS要求declared、deterministic replay、prose三层实际PASS及同packet package／contract同行。正文意见不能写入世界状态。

`planning/contracts.py`现有replay仅支持首scene章入口、已支持character effect、绑定world/object前缀、显式knowledge前缀／scene。它不把合同自己声明当entry、不传播未实现局部前序、不从对话推物权、不把persist当exit事件。

旧`evaluation/semantics.py`可借鉴Unicode引文、候选／合同／context hash、ACTUAL与梦／否定／引用等模式区分，但其MODEL需要provider trace和模型家族隔离；现有SESSION_AUTHORED_NOT_PROVIDER_VERIFIED不能塞进旧lane冒充合格。旧registered_reading取首条的行为也不能直接照搬为新lane的负面聚合规则。

## 3. 四组须真实新增输入的问题

- **88-S3b**：现选只有S1–S5，无婚后短返致谢seed。婚前许可／药盒／离府或字面“好歹留着麝月”均不等于婚后执行。若修，新增选版scene、seed、合同及有依据的婚后checkpoint；不能把86药盏充作88药盒。将来总数可能不再85。
- **98亲还玉**：编辑选PERSONAL_CARRIER_C，旧OT98-04／05仍zhen_messenger。现98-S3只去掉冲突refs、留早期context，不是执行已完成。需新object/event版本真实同物custody由zhen_baoyu连续转交，不改名alias使者、不补雪中玉身份。
- **99顺序**：source S1,S2,S3,S4,S5与narrative S1,S2,S5,S3,S4分别绑定；entry_from原索引不是runtime状态。寺院先呈现不能让家属提前知道，章末粗粒度出家event不证明离门立即抵寺。S4家中终镜后不再加第二尾。
- **100神话角色／状态**：警幻、空空道人有叙事角色但registry_id null、participants UNKNOWN，不是空演员表。需明确另版frame角色与typed state才可能执行；不能把榜上姓名当出场演员或把复本质当人间玉运输。人间→太虚→青埂峰与terminal功能可正文审读，不能替runtime/entity PASS。

## 4. 最小专门consumer规格（待实现前评审）

拟一个研究专用engine，不接旧human／semantic index。拟接口：

- `make_research_request(root, selection_binding, chapter, candidate_binding, draft_binding, package_binding, subject_binding, subject_kind, context_bindings, protocol_binding)`
- `check_research_reading(root, request, raw_reading_binding)`
- `summarize_research_readings(root, request, registry_binding)`

subject_kind仅POLICY_PROTECTION／CONTRACT_PROSE。单独request、reading、report schema严格additionalProperties:false；lane研究、MODEL、RESEARCH_ONLY、authority/evidence NONE、human false。不让模型填写可获授权的聚合PASS。

### 请求必须冻结

1. exact selection／candidate／draft／package／policy或contract、上下文、协议／schema／prompt摘要；禁止隐式latest。
2. 完整父稿／修订／协调者谱系与实际context披露，不只章级伪session label。
3. 原合同／policy pointer+value digest清单、所有子项及自由文本并列义务的明确拆分。应覆盖289父义务及20P-Lock子feature、499beats、385状态条件、812未决项处置及参与／物／顺序／知识边界；数量本身不证明覆盖语义。
4. 必需邻章、基线比较、来源／seed／plan／state／event／decision／既有负面；缺所需context不许自动N/A。

### 原阅读记录必须声明

- request/candidate/subject/context/protocol精确hash，MODEL作者与reader上下文、实际暴露与隔离NOT_PROVEN，不认证provider或人类。
- 真实read_ranges；它们可审计但不数学证明已阅读。
- 每expected obligation恰一项SATISFIED／VIOLATED／UNKNOWN／CONTEXT_ONLY，含rationale、所有子项、支持与反证、未决原因。
- exact raw Unicode[start,end) quote与文件绑定；不可把UTF8 bytes当字符，不归一化、不从别文件抄相似句。
- 禁令／缺失不能捏造“缺失引文”；要求完整检查范围、最近相关证据和解释，无范围为UNKNOWN。
- events区别呈现序／因果序、角色／registry身份、HUMAN／TAIXU／QINGGENG、实际／梦／引用等模式；annotation绝不修改世界状态。

### 聚合与资格

binding_integrity、obligation_coverage、attribution、declared_context_eligibility、semantic_result、deterministic_replay、release_gate_eligibility分开。真实违例或完整性失败优先FAIL；未知／缺项／缺context／缺资格PENDING；完整研究正文语义判断即使PASS也不取得人审、来源或runtime资格。

正面资格排作者／修订者／协调者、重复session／context／source alias；false或未知隔离不改true。若用于原研究panel发布证据，仍至少两名完整合格reader，并不替代candidate/package/contract peer。实际归属有效的负面不能因其不计正向独立性而消失。

consume全部append-only raw／receipt并核projection；同subject跨packet有效负面保留。新bytes可新审但保留旧FAIL crosswalk；相同bytes换packet不能清零。

特殊语义：SOURCE_ONLY不要求插入也不自动禁词；生成回目不成历史权威；P1_TERMINAL不是普遍无尾字符regex（89同scene应答不自动FAIL），100解释性coda仍检查；旧book-scope不得变成agent20章singleton限制或静默省略。

## 5. 最低负测与兼容验收

- 缺／重复／未知obligation、只读一半并列项或一个P-Lock feature；不得完整PASS。
- 候选、policy、合同、state、decision、邻章、schema／prompt旧hash；错文件／空／越界／归一化／bytes错位引文；完整性FAIL。
- literal在但功能缺、绝命诗、未成稿补齐、超知消息、解释尾巴；不能被anchor PASS掩盖。
- self／作者／协调者、alias、多label同context、false隔离；不计正面资格，负证不消失。
- raw／projection不符、漏负面receipt、后PASS覆盖同bytes FAIL；拒绝。
- dream／negated／quoted不能执行实际beat；未知状态不作已知相等；空events／exit不是成功；禁止模型注入状态。
- 88婚前字面代婚后、98使者代亲还、99观众先知转家人知识／instant travel、100名册人物代演员／frame代运输；拒绝或保持明确unsupported PENDING。
- 13份NARRATIVE_ONLY即使正文一致也仍不通过原deterministic gate。
- supplemental研究完整性／解释PASS不能闭合旧三carrier或授历史资格。实际4章选同set，旧report仅显示3章是86早停，不是86未依赖。
- 旧source graph、默认scope、legacy/human lane、prepared bytes和旧负面不变；无新记录默认PENDING。

## 实施决议

规格仍为草案。可建设验证证据完整性的consumer，但当前85份合同无一已有KNOWN exit，不能承诺实现consumer便可release PASS。policy专门阅读可填原本缺少的能力，但必须真覆盖、真独立且保留原literal／machine约束。supplemental还需P1原义证据路径，P3不自动关闭。不同语义的“叙事研究输出”若需要，触发计划中的另行确认点，不擅自创建新PASS产品。
