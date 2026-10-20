# 会话 agent 研究轨道

第五阶段采用会话内子 agent 起草、核对和阅读，不另行调用付费模型 API。主协调者保留分配与映射，记录会话来源和输入字节；这不是受控外部模型实验，也不提供供应商实测模型、token 或账单证明。

## 执行顺序

1. E：会话稿登记与独立的 agent 复核记录。
2. K：显式切换第89回闭包包版本；抽取第86回旧晋升安全策略，另建研究版发布服务。
3. F：五项史料、91个语料样本的两份模型同行核对。
4. G：81–100全部20回、85个骨架的版本化合同起草与编辑。
5. H：85–87两路线、每路线两个样本的试写与修订比较。
6. I：79–80给定计划的会话回测，训练暴露未知，不能证明失稿复原。
7. J：逐回起草、反馈、修订、匿名比较；只有明确采用且依赖核对通过的章回可进入研究版。

## 资格与证据边界

- `MODEL_SUBAGENT` 永远不是 `INDEPENDENT_HUMAN`。真人 schema、selection、稳定版 ACTIVE 不接受 agent 结果。
- 评审者 session ID 与模型名是声明，字节保管可检验，模型身份、上下文隔离、人与人意义上的独立性不可验证。
- 两路线共用事实、范例、入口和输出目标；仅指导及反馈流程不同。不能用信息不对称宣称 Harness 因果效果。
- 负面意见不被另一个 packet 或新 ID 隐藏；修订后的新字节须重新审查，旧意见保留。读者可用 `supersedes` 取代**自己**的旧记录，旧记录仍留在历史中。
- `AGENT_EDITED` 是发生过模型编辑的流程状态，不等于文本正确、场景重放通过或真人验收。
- 声明兼容、已有事件的确定性状态投影、正文支持的语义判断分列。未知事件和场景内入口留 `PENDING/NOT_CHECKED`，不会以直接复制声明来制造 PASS。
- 会话稿使用 `SESSION_AUTHORED_NOT_PROVIDER_VERIFIED`，没有伪造的 API 响应、request ID、usage 或支付预算。
- 报告中的全局 `agent_panel` 仅是研究意见展示，不计入真人准入；逐包研究发布另核对其实际依赖和稿件。
- 缺合同、政策、来源核对、语料核对或足够阅读时只产生待验收材料，不能标成 `agent-reviewed` 成稿。
- `releases/stable/v1.4` 不动；研究版目标固定为 `releases/agent/`，不改 stable ACTIVE。

## 门控严重度（ADR 0004）

研究版发布按 `src/rcwh/findings.py` 的证据地板判定：

- **BLOCKING → FAIL**：字节/结构/非目标章完整性；违反 lock-eligible、全部 A-W1 支撑的 LOCKED MUST/MUST_NOT 决策（例如 A-W1 字面约束锚点丢失）；读者声明为 BLOCKING（或未声明严重度）的负面意见。
- **WARNING / ADVISORY → 报告不阻断**：B 级与历史可行性约束；规划卡导出的合同 beat、P-Lock 锚点（`REPLACEMENT_CASE`）、作者首选。读者对这类问题给 FAIL 时应写 `"severity": "ADVISORY"`；协调者在决定中对每条异议给出理由后可 ADOPT。
- **INFO**：未实现的检查（正文语义回放、policy 专项语义阅读），不是 PENDING。
- **PENDING** 只表示确实缺输入（未解析的依赖来源、缺合同范围、缺决定）或不足两位读者。

研究版 PASS 只写入 `releases/agent/`，标注 MODEL 审阅、`independent_human_admission=false`；stable/ACTIVE 仍由所有者裁决。

## 明确选择合同版本

模型初稿、编辑修订和协调者修正都追加保存，不取目录中的“最新版本”作为默认。当前混合选择 `data/planning/contracts/agent-final-v1/` 使用80份 v2及第99回5份 v3的原字节副本。

```bash
rcwh plan check --chapters 81-100 --contracts-directory data/planning/contracts/agent-final-v1
```

副本保留原前驱路径，检查只在该原前驱与当前选中前驱**字节完全一致**时允许路径别名；同ID或同回次但内容不同仍拒绝。第99回的另一改序只是未选中的文学方案，不通过篡改源场景顺序获得 PASS。零 FAIL仍可能整体 PENDING，尤其局部入口和正文语义尚未核查。

## 写作输入与历史谱系（v2）

新请求默认采用 renderer v2。准备请求仍是只读操作；导入会话稿或执行 provider 请求时保存内容寻址快照。原路径的现行文件被修改或退休后，已登记稿仍按快照验证原请求、正文、作者和父稿关系。读取历史不会重新调用当前渲染器。

```bash
# 当前研究版选中的 20 回：历史完整性与当前输入相容性分列
python tools/verify_writing_lineage.py

# 单稿；--production 另查当前生产准入，不会由历史 PASS 推定准入
rcwh write check data/writing/drafts/ch89/RECORD.json --current --production

# v1 旧稿只追加迁移凭证和快照，必须先通过原协议全部校验
rcwh write freeze-history data/writing/drafts/ch89/RECORD.json

# 对明确选中的旧稿批量迁移；失败不会重写原稿或替换旧输入摘要
python tools/verify_writing_lineage.py --freeze-history
```

`historical_integrity=PASS` 表示所存历史字节与关系可核实；`current_compatibility=CURRENT/STALE/NOT_CHECKED` 单独说明当前写作依据是否相容。生产审核、来源核对和人工资格仍独立计算。研究发布分别检查 `AUTHOR_PROVENANCE` 和 `CURRENT_WRITING_INPUTS`，历史有效但当前依据过期的稿件不能通过后一个门控。

治理闭包配置、进度、审核 selection 不再作为作者提示词的全局依赖。所选写作包、计划、场景、材料和模板变化仍会使当前相容性失败；新依赖也须通过重渲染核对。修订保留父稿原依据，切换写作包应建立新的起草请求。尚未迁移的 v1 保留原检查行为；已失配的 v1 必须在拥有可核实原字节的历史检出中迁移。详见 [ADR 0005](../decisions/0005_WRITING_INPUT_CUSTODY.md)。

## 已知限制

模型预训练接触前八十回的情况未知，不能以重合阈值证明记忆。79–80在所选版本中是一原回拆成两半，不是两个独立留出样本。原文识别和同类写作偏好会影响模型读者。会话路由、耗时与实际资源无法按原 API 预算核算，因此研究比较必须另标 `RESOURCE_PARITY_NOT_VERIFIED`，现有 provider 回测的严格资格不被改写。
