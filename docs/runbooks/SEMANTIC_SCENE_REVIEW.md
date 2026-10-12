# 场景语义复核

`rcwh evaluate` 将关键词检查显示为 `lint:*`。它们可以提示漏词或解释感，不能建立叙事事件、医学可行性、人物知情或出口。没有带来源的语义判读时整体为 PENDING，退出码 2；实际约束冲突为 FAIL，退出码 1。

## 请求、实际运行与复核

```bash
rcwh semantic prepare data/scenes/ch86_last_night.yaml scene.txt --authors authors.json --output request.json
rcwh semantic run request.json --command 'python /path/to/extractor.py' --producer producer.json --output trace.json
rcwh semantic check request.json reading.json
rcwh evaluate data/scenes/ch86_last_night.yaml scene.txt --authors authors.json --semantic-reading reading.json
```

作者文件是含 principal_id/source_id 的数组。producer 文件标识真实编辑或模型；MODEL 应填写 provider/name/version/family。调用者选择抽取程序，程序从 stdin 读取请求、响应 schema 和 producer，stdout 只输出 `schemas/semantic_reading.schema.json` 规定的 JSON。提示全文和摘要在请求中；运行记录保留真实输入、输出原字节的 Base64/SHA、stderr、退出码和时间。准备/运行的 PASS 仅表示请求或执行完整性。

模型输出归档为 reading 时，在 producer 增加 `trace: {path, sha256}`，绑定仓库内实际 trace 文件。除这个新增绑定外，reading 必须与真实 stdout 一致，producer 必须与所选执行器一致。缺真实运行记录、作者来源未知、同作者来源或同模型族，不取得正向独立资格。编辑记录使用 INDEPENDENT_HUMAN；本会话的标注使用 INTERNAL_AGENT 并保留待外部确认状态。系统核对已提交身份和来源声明，不能证明真实身份。

每个事件引用 Unicode `[start,end)` 原文跨度。实际事件与否定、梦境、猜测、比喻、引用分开；出口按最后实际变化确定。对白不能直接填物理状态。知情须有在先的实际观察或通信事件、观察事实和接收人物，思考或作者填写状态不能建立获知。89/92 回的知情出口通过这条事件链核对。

`semantic check` 重放的是冻结请求，包括其中的知情入口；后来的 World/Knowledge 修改不能改变这个旧请求的结果。判读的事实 ID 须在该场景冻结入口中声明，缺入口保持 PENDING。正式候选资格重新从当前正文、合同和选定 World/Object/Knowledge 入口创建请求，旧请求的 PASS 不授权当前版本。competition 和 promotion 调用同一检查器；原六个声明字段、旧 WINNER 和作者 sidecar 均不能替代语义资格。

## 真人判读准备与登记

```bash
rcwh reviews scene-template request.json --output reading-template.json
rcwh reviews resolve-spans draft-reading.json --texts scene.txt --output final-reading.json
rcwh reviews register scene-reading final-reading.json --request request.json --origin '实际接收的独立场景判读' --dry-run
rcwh reviews register scene-reading final-reading.json --request request.json --origin '实际接收的独立场景判读'
```

模板的 `report_kind: TEMPLATE` 不算意见。引句工具只在读者提交前补 Unicode 偏移，补完由读者核对，原件接收后不改写。登记命令核对当前正式合同、竞争候选正文、正式作者身份与冻结入口；原件经 REVIEW_RECORD 入库，保持原字节，追加 `scene_readings.json` 并同步该索引的闭包摘要。第89回 A 稿目前未登记作者，仍会保持作者来源未知 PENDING；不得用请求侧虚构身份绕过。版本2判读可以保存，但 competition/promotion 当前仍建版本1请求，保存不代表其被生产请求选中。同一请求已存在判读时拒绝追加，避免既有首条匹配选择器悄悄忽略新意见；本工具不覆盖旧记录。详见[读者填写指南](REVIEWER_GUIDE_ZH.md)。

`diagnostics style TEXT --reference corpus:front80:v1-candidate` 另提供未审语料的探索性文风对照，只报告观察和审计状态、`verdict: null`，不填补语义或文学判断。

## 请求版本与事实目录

`semantic prepare` 和 `evaluate` 默认 `--request-version 1`，请求、摘要和已归档判读保持原绑定；`semantic check` 按请求自身版本重建，不读取今天的 Knowledge 补事实，也不迁移旧判读。版本 1 沿用原限制：可获知事实只取自冻结入口各桶的并集，已登记但不在任何入口桶中的事实无法被合法获知。选定知识版本 `data/knowledge/v03_slice2.json` 已在 89 回入口为宝钗、小红、茜雪显式标注 `does_not_know: official_confiscation_message`（依前八十回第75回甄家抄没消息经邸报和转告逐层传到的写法），因此 89 回在版本 1 下即可核对获知。`v03_slice1.json` 原字节保留，供绑定它的 85–87 回试写记录使用。

`--request-version 2` 在冻结入口中另存排序、去重的已登记事实 ID（`fact_registry`），并把版本、提示摘要和该目录绑定进 context 摘要。目录只声明哪些 ID 合法，不使任何人物 `knows`；不在入口桶中的已登记事实按 UNSPECIFIED 处理，获知仍须在先的实际观察或通信事件、原文跨度和接收人物。未知、重复或非字符串的事实 ID、目录被篡改、版本不受支持均拒绝。物理出口须有实际变化才能通过，显式 `null` 与缺失变化分开：已核对而缺失为 FAIL，未核对或未判定为 PENDING。

## 稀疏连续性与直接引用诊断

```bash
rcwh diagnostics continuity [--chapter N]
rcwh diagnostics impact object.medicine_bowl_86.temperature
```

只读研究诊断，`authority_effect`、`evidence_effect` 均为 NONE，不采纳、不晋升、不修改任何数据。`continuity` 复用场景状态投影、M2/prewrite 现有记录和正式场景合同。结构、引用或前置条件的明确矛盾为 FAIL；正式场景只覆盖已登记章回（当前 86/89/92，其余章回缺场景合同）、场景之间没有声明的衔接或检查点、出口声明未经实际事件证明、来源上下文没有绑定到明确检查点，都保持 PENDING，不按章回相邻关系推断状态链。已声明 `legacy_ref` 的物件在 M4 与登记 YAML 之间的重叠字段差异（如药碗 `S02` 与 `xiaoxiang_room`、第 86 回后的 cold 与 warm）只作为待人工核查的桥接差异报告，不自动认定别名，也不改写任一方。

`impact` 只列出精确规范化目标在场景 `entry_state`、`preconditions`、`exit_state` 和 `knowledge_guards` 中的直接引用，不按名称、标签、章回号或正文词语推断；没有直接引用只说明所扫描的声明里没有，不代表不会受影响。来源变更的影响沿用 `provenance/corrections.py` 的 `source_impact`。

## 固定挑战与实际能力的边界

`data/evaluation/semantic_challenges.json` 固定三种绕过、出口冲突和否定诗稿案例。原请求/意见、增加物件网络的第二版及覆盖内心知情断言的第三版均保留；新版本均是明确重新核对后的版本，runtime 不刷新旧意见摘要。CI 通过内部编辑判读重放约束，三个绕过必须 FAIL；否定诗稿不会被当作实际禁情节。

这证明绑定、事件重放和约束检查可拒绝已核对反例。**尚未运行外部模型挑战测试**，不能声称某模型已自动理解这些文本。新改写若没有对应判读，返回 PENDING。模型接入后须保留挑战集上的真实请求/响应，比较误放、误拒、未判定及跨度覆盖；程序 fixture 不是模型效果证据。
