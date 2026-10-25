# 会话 agent 研究轨道

第五阶段采用会话内子 agent 起草、核对和阅读，不另行调用付费模型 API。主协调者保留分配与映射，记录会话来源和输入字节；这不是受控外部模型实验，也不提供供应商实测模型、token 或账单证明。

## 当前执行输入（v4-r2）

本轮使用 `data/agent_release/research-81-100-v4-r2/request.json`、同目录 `review-campaign-v1.json` 和 `selection-81-100-v7.json`。修改83、85、87、92、93五回；89揭书名提案因违反现行合同在派读前撤回，恢复v3原稿。首版冻结e3b46d2及v4请求留档，不计正式新读或成功CI；当前执行证据见[本轮目录](../../artifacts/agent_research/v4-correction-20261026/DESIGN_AND_IMPACT.md)与[v4计划](../plans/POST80_V4_REVISION_20261026.md)。

```bash
rcwh agent-release review-status data/agent_release/research-81-100-v4-r2/review-campaign-v1.json
python tools/verify_writing_lineage.py
python tools/verify_agent_release.py --build-smoke
```

新读须等本版输入双版本CI成功。下文v3的完成数字和路径作为历史实例保留；实际本轮派发/登记要使用上面的v4-r2计划路径。COMPLETE不等于文学通过；两个核心因果问题另需新正式读者引用原句验证。

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

## 发布作者链与批量审阅

已完成的v3基线入口为 `data/agent_release/research-81-100-v3/request.json`（13回定向改文，执行计划见 [v3计划](../plans/POST80_V3_REVISION_20261025.md)）；v1保留为包含来源归属错误及BLOCKING意见的历史研究版。prepare 从选择器携带逐回 `rebind_receipt`；连续重绑另由 `previous_rebind_receipt` 保留前次声明；发布报告中 `reviews.authors` 为正文贡献者，`reviews.author_lineage` 另列原作者链、协调者改动与保管会话。不能把重绑会话宣称为新提示词的正文作者。

```bash
rcwh agent-release prepare research-81-100-next \
  --selection data/agent_release/selection-81-100-v7.json --chapters 81-100 \
  --coordinator-session-id coordinator:release-v1 \
  --reuse-request data/agent_release/research-81-100-v3/request.json

rcwh agent-release review-status data/agent_release/research-81-100-v3/review-campaign-v1.json
python tools/verify_agent_release.py --build-smoke
```

当前 v3 edition 沿用纠错后的来源，另有13回实际定向编辑稿；上面的 prepare 示例用于新增 edition。已备好的 `research-81-100-v3/review-campaign-v1.json` 共 76 项任务：56 项章回、10 项来源、2 项语料、8 项连续性。运行时默认同时五项；本轮计划设为三项；每项材料两位读者。合同读者同时看正文和写作包。来源附固定载体上下文和原页图像，文字每项最多 197 KiB、图像每项最多四张且合计 6 MiB，分别报告。语料按样本投影并校验原 carrier。

v3的76项已实际齐备（30复用、46新读），另有10位新上下文模型比较读者；20回研究采用、正常build及240门核验通过。原始负面和文学分歧保留，87、92中央因果仍待下版处理；COMPLETE和研究门控不代表人工或文学全通过。原始意见、逐项处置、克隆复现及最终提交状态见[执行报告](../../artifacts/agent_research/v3-revision-20261025/EXECUTION_REPORT.md)。

跨版本复用通过 `--reuse-request` 显式选择前版。仅完整subject、coordinator、绑定与上下文相同时保留旧packet；意见覆盖另由campaign核对。当前v3准备时76项中30项可复用，46项需新读（38章回、8整书）；来源分组重排仍可能增加未改条目的组合复审，不能将任务数解释成同样数量的内容都变了。未改条目的原始意见继续保留。

连续性审读使用 `reading/book-segments-v2.json` 和四个分段：81–87、87–92、92–98、98–100。相邻段重叠一回，每段两位独立读者，共八个 BOOK 任务。每段 UTF-8 正文不超过 197 KiB；19 处接缝全部位于某一段内部。意见固定 ADVISORY，发布 manifest 逐段展示进度；`reading/book.md` 是组装校验原件，不再分派给单个读者。字节预算是实测文件大小，不是模型 token 数；读者若仍无法读全，必须报 NOT_CHECKED 和未读范围。

### 主 agent 环境内执行（默认路径，无适配器）

1. 先运行 `review-status`，检查是否存在上次已领取的 ASSIGNED 任务。主 agent 按环境实际空闲子代理槽位领取；`--limit` 限制包括已领取任务在内的总数，不能超过该 campaign 的实际 batch_size（本轮三个）。

```bash
rcwh agent-release review-dispatch data/agent_release/research-81-100-v3/review-campaign-v1.json \
  --limit 3 --model-label '当前环境实际路由模型（声明）'
```

2. 命令返回 assignment 文件路径，其中已经由 scaffold 生成准确的身份、packet、subject、样本检查和阅读清单。主 agent 用当前环境的子代理工具逐项启动全新读者，把这个 assignment 路径及仓库根目录交给读者。要求完整阅读 `job.read_in_full`，用图片工具查看全部 `job.inspect_images`（存在时），按 `instructions` 填写 `opinion_scaffold`，只返回实际意见 JSON。只读本任务 subjects。读者不自行登记或改仓库文件。BOOK 任务必须逐一检查 `job.continuity.seams` 的两回接缝。SOURCE 逐图检查引文、定位与见证归属；图像不可读时填写 NOT_CHECKED。

使用本环境的 `collaboration.spawn_agent` 时设置 `fork_turns: "none"`，在 message 中提供绝对仓库根路径和该 assignment 路径，并要求返回原始意见 JSON；task_name 为该任务独有名称。不要继承主 agent 的长对话、作者提示词或其他读者的意见，以免挤占阅读上下文和污染独立判断。模型沿用当前环境路由；只有用户另行指定时才覆盖。

读者必须区分结论与严重程度：`verdict` 只允许 `PASS/FAIL/REJECT/PENDING/UNVERIFIED/NOT_CHECKED`；`ADVISORY` 填在 `severity`，例如建议性不通过是 `FAIL` + `severity: ADVISORY`。交回前用 `schemas/agent_review.schema.json` 自检。格式校验失败原件单独保管，原读者自行校正结构另存；不替读者改意见，不给校正增加阅读信用。

3. 主 agent 原样保存返回的 JSON（不替读者填 verdict/notes），串行登记：

```bash
rcwh agent-release review-register data/agent_release/research-81-100-v3/review-campaign-v1.json JOB_ID \
  --opinion /tmp/returned-opinion.json --origin '实际子代理任务和会话说明'
```

也支持既有 `rcwh agent-panel register /tmp/returned-opinion.json --origin '实际子代理任务和会话说明'`。随后 `review-status` 会凭准确的分派身份、packet、subject、原始输出及登记回执核实并计入 COMPLETE；无需伪造 runner 的 stdout 文件或事件。其他读者的意见不会被冒认成本任务。

4. 子代理确实返回 503 等临时错误时，主 agent 登记故障并继续处理其他任务：

```bash
rcwh agent-release review-fail data/agent_release/research-81-100-v3/review-campaign-v1.json JOB_ID \
  --assignment-sha256 ASSIGNMENT_SHA256 --status-code 503 --reason '保留实际服务错误内容'
```

ASSIGNMENT_SHA256 使用 dispatch 返回的 `assignment.sha256`；迟到错误不能作用到新尝试，重复同一错误不会再次扣次数。超时或任务丢失同样携带该哈希，使用 `--interrupted --reason '实际原因'`；先确保原任务已停止。每轮最多三次尝试，前两次分别退避 5、10 秒。其他错误不自动重试。每次尝试使用新会话，保留旧故障与原件；失败不计意见。格式错误、空 scaffold、身份或 subject 不符不能登记为完成，应保留原件并报失败，不能改填 PASS。

5. 重复领取、启动、登记和状态检查，直至收到全部意见或明确报告 FAILED/EXHAUSTED。恢复时 ASSIGNED 保留为进行中，不能悄悄重派；主 agent 应恢复原子代理或记录真实中断。COMPLETE 只说明收到了有效格式的意见，意见仍可为 PENDING/NOT_CHECKED 或负面。文学门控与协调者决定仍独立计算。本流程只调用当前环境提供的子代理能力，不启动 API provider，不要求密钥或新增付费预算。

`needs_followup=true` 表示仍需补读。用 `review-reopen PLAN JOB_ID --reason '实际未读范围与补读原因'` 重开，再 dispatch、启动真实读者、登记；骨架自动携带旧记录的 supersedes。已经完整审阅且输入未变的意见可供新计划复用，状态显示 `reused=true` 及实际记录，仍可显式重开。永久故障修正后或重试耗尽后的再次执行，也须明确记录重开原因。不得通过重开自动改写 verdict。

协调者须实际展开每份新意见全部 `notes/sample_checks`，输出截断则续读；看见该次工具响应并读完后，另起一次工具调用记录阅读声明。不能把展示意见和标记已读放在同一执行单元内，登记完成也不代表协调者已经阅读。声明只是自述，不是机器阅读证明；过早或错误的声明保留撤回痕迹，实际读完后再记，不增加同行阅读信用。

协调者汇总 candidate、package、contract、source、corpus 全部相关意见，逐项给出异议处置理由；拆组后的合同意见不能遗漏。BOOK 意见仍为 ADVISORY。PENDING 构建写入 `.pending/<edition>/<revision>`，审阅完成后可沿用原 edition 正式发布。

### 已有本地适配器的可选路径

`review-run PLAN --worker-command COMMAND` 仍支持 JSON stdin/stdout 协议及自动临时故障重试，但不是主 agent 执行的前提。存在 ASSIGNED 任务时拒绝混用 runner，避免重复启动。两条路径使用同一份 scaffold、字节校验、意见原件和恢复进度。

改正文需建立新 edition 和计划；候选稿、写作包、政策或 packet 改变后，旧计划拒绝继续派发，应以新路径运行 `review-plan REQUEST --out NEW_PLAN.json`。加入协调者决定不改变审阅依据，可继续原计划。旧读本、packet、campaign 和 request 快照保留；前版研究v2保留自身v1计划，当前v3另有自身v1计划，两者的连续性分段均使用v2读本格式。已登记意见保存当时输入快照，当前路径变化不冒充历史损坏。既有 request 副本、packet 和意见不覆盖，未处理的口味类 ADVISORY 留给协调者裁决。运行时与新选稿先提交、推送并确认 CI，再启动读者。详见 [ADR 0008](../decisions/0008_REVIEW_INPUT_CUSTODY_AND_FOLLOWUP.md)。

## 已知限制

模型预训练接触前八十回的情况未知，不能以重合阈值证明记忆。79–80在所选版本中是一原回拆成两半，不是两个独立留出样本。原文识别和同类写作偏好会影响模型读者。会话路由、耗时与实际资源无法按原 API 预算核算，因此研究比较必须另标 `RESOURCE_PARITY_NOT_VERIFIED`，现有 provider 回测的严格资格不被改写。
