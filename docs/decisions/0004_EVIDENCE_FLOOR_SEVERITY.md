# ADR 0004：门控回到"证据是地板"，规划偏好不再升级为硬门

日期：2026-10-18。状态：已实施（研究版发布路径）；稳定版路径保留人工门。

## 问题

项目设计早已规定：证据限定不可违反的范围，作者首选与 P-Lock 可替换且不得反向升级为证据（母本 v2.1 三类结论；设计 v1.0 §6"文学建议不应通过不断升级为硬规则来获得执行力"；`docs/PLOCK_LITERARY.md`）。实现却违背了它：

- 规划卡细节被抄进 agent 场景合同的 `required_beats`；读者发现缺失即 FAIL。合同上的 `scope`/`epistemic` 标签从未被任何门读取。第95回"当票压针线盒"一句计划卡措辞因此阻断了整章。
- P-Lock 精确锚点（从 v1.4 正文摘取的句子）按逐字 CONTAINS 硬门执行，不经权威检查。
- 多道门在代码上不可能返回 PASS（agent policy、补充史料门、正文语义回放写死为 NOT_CHECKED），PENDING 不区分"未实现""缺输入""缺读者"。
- 负面意见永不可撤；全局 store 任何坏记录让所有 subject 失败；协调者驳回异议后结果仍为 FAIL。

结果是研究版发布只可能产出 PENDING 或 FAIL。

## 决定

1. 统一严重度词汇 `src/rcwh/findings.py`：

   | 级别 | 来源 | 效果 |
   |---|---|---|
   | BLOCKING | LOCKED + MUST/MUST_NOT 决策，lock-eligible 且全部 claim 为 A-W1（前八十回正文/早期批语的一手见证）；字节、结构、非目标章完整性 | FAIL |
   | WARNING | 其他 LOCKED 决策（历史可行性、非内证、W2 支撑） | 报告 |
   | ADVISORY | CURRENT/OPEN 作者首选、P-Lock 锚点、规划卡导出的 beat、无引用依据的 beat | 报告，可附理由替换 |
   | INFO | 未实现的检查（如正文语义回放、policy 专项语义阅读） | 只报告 |

   PENDING 只因 `INPUT_MISSING` 或 `NEEDS_REVIEWER`；`NEEDS_OWNER` 只在 stable 范围生效。

2. 合同 beat 按依据定级（`evaluation.semantics.beat_severity`）：只有引用了 BLOCKING 决策的 beat 缺失才 FAIL；其余记为 `ADVISORY_UNMET`。
3. Agent policy 锚点按依据定级（`agent_policies._derive`）：P-Lock 锚点 ADVISORY，丢失时为 `REPLACEMENT_CASE`；A-W1 字面约束（如第100回"情不情"）仍 BLOCKING。
4. 审阅面板：结果可声明 `severity`（缺省 BLOCKING）；非 BLOCKING 的负面意见计为完整审阅并保留为 advisory。读者可用 `supersedes` 取代自己的旧记录，旧记录保留在 `superseded_opinions`。packet 范围的摘要只判本 packet 的记录；store 级问题进入 `store_findings`，仍使 `rcwh validate` 失败。
5. 研究版发布：协调者对每条异议给出有理由的裁决后可 ADOPT；BLOCKING 负面仍让 CANDIDATE_PEERS 失败，协调者无法解除。删除永远 PENDING 的 `SUPPLEMENTAL_SOURCE_EVIDENCE` 门；未解析的依赖引用为 PENDING（缺输入），绑定/完整性错误为 FAIL。
6. 研究版 PASS 只是本地字节绑定的 MODEL 审阅，`independent_human_admission=false`、`stable_active_effect=NONE`。stable/ACTIVE 仍由所有者决定，`promotion.py` 稳定路径和人工审阅通道不变。
7. 研究过程记录归档到 `archive/research/phase5-6/`，不再参与评估、不再由测试钉死；仍被活数据按哈希绑定的文件原地保留为活输入。

## 不变

- 证据层（Source → Claim → Decision）及其完整性校验、W2 不得单独承重。
- P-Lock 注册表与元数据；只改变其在门中的效力。
- 前八十回语料、`sources/project/*`、`data/world`、`data/provenance`、`releases/stable`。
