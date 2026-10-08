# RedChamberWorldHarness 文学复原能力升级计划 v1.0
## ——从“证据与一致性 Harness”升级为“探佚搜索 + 文学合成实验室”
**状态：评审定稿 / FINAL**  
**日期：2026-10-07**  
**适用仓库：** `CoCoThink/RedChamberWorldHarness`  
**当前 canonical literary branch：** `literary/43-0-resume`  
**当前 stable ACTIVE SHA256：** `4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`  
**当前文学 Gate：** `CH89_MANUAL_PLOCK_THEN_REAL_BLIND_READ`  

---

# 0. 执行结论

本计划不推翻现有 RedChamberWorldHarness，也不改走“纯 LLM / 全量 RAG / 单一向量库续写”的技术路线。

当前 Harness 已经很好地解决了最困难、最不能丢失的一层问题：

> **什么是证据，什么是历史可行性，什么仍然 OPEN，什么只是当前 C 方案，什么只是正文实现。**

这一层应继续作为整个工程的 **Authority Kernel（权威内核）**。

当前 Harness 的主要不足，不在“证据不够多”，也不在“旧 Markdown 迁移得还不够”，而在以下四点：

1. **Hypothesis Space 不充分**：OPEN 被保存了，但多个可竞争大方案没有被系统地保存、组合、回放和比较。
2. **C-path lock-in 风险**：当前 C 方案进入 Reconstruction / World / Object / Prewrite 后，会自然成为后续生成默认路径，容易形成“局部最优”。
3. **Fabula 强、Sjuzet 弱**：发生了什么、谁知道什么、物件在哪里已经很强；但“曹雪芹怎样让读者知道、怎样延宕、怎样闲笔落大事、怎样收回”仍缺独立 runtime。
4. **文学搜索能力不足**：现有 Literary Evaluator 主要擅长排除显性坏写法，还不能系统地从大量可行方案中搜索“更像《红楼梦》”的组织方式。

因此，最终技术路线确定为三层架构：

```text
Layer A — Authority Kernel
Evidence / Provenance / OPEN / Historical Feasibility /
Reconstruction hard boundary / World / Object / Character Truth / P-Lock

Layer B — Reconstruction Search Lab
Hypothesis Graph / Scenario Bundle / Counterfactual Replay /
Cross-chapter Consequence / Pareto Comparison

Layer C — Literary Synthesis Lab
Narrative Discourse Runtime / First-80 Exemplar Retrieval /
Multi-candidate Structural Search / Prose Generation /
Machine Rejectors / Human Blind Review
```

其中：

- **A 层继续作为事实和边界的唯一 authority。**
- **B 层负责回答“还有哪些不同的八十回后可能成立”。**
- **C 层负责回答“在仍然成立的方案中，怎样写最像《红楼梦》”。**

---

# 1. 当前 Harness 能力评估

## 1.1 已经成熟、原则上不重构的部分

以下层应视为既有核心资产，只允许兼容性扩展，不做方向性推翻：

| 能力 | 当前判断 | 后续策略 |
|---|---|---|
| Provenance / Source / Claim / Decision | 成熟 | 保留 |
| Evidence Role / Modality / Authority | 成熟 | 保留 |
| OPEN-LOCK | 成熟 | 保留 |
| Historical Mechanism `FEASIBILITY_ONLY` | 成熟 | 保留 |
| Reconstruction Runtime | 较成熟 | 增加多假说旁路，不推翻 current-C |
| World State / Timeline | 较成熟 | 增加 scenario replay |
| Object Network | 较成熟 | 增加 scenario-specific state |
| Character Knowledge | 较成熟 | 接入 discourse / exemplar |
| P-Lock | 成熟 | 继续作为文学保护，不升证据 |
| Literary Evaluator v0.5 | 可用 | 保留为 rejector，不作为正向“曹雪芹分数” |
| Prewrite v0.6 | 可用 | 作为 Step43 上游 staging，不直接生成正文 |

## 1.2 当前不足

### A. OPEN 有“空位”，但缺“候选拓扑”

当前系统善于表达：

```text
这个问题没有硬证。
这个接口仍 OPEN。
```

但不够善于表达：

```text
OPEN 下有 A/B/C 三种主要结构；
各自消耗哪些假设；
会怎样改变第87、89、92、95、99回；
会造成哪些世界状态、人物状态和章法代价。
```

以 H04 为典型：原过程文档曾保存 O09-A/B/C、G0/G1/G2 等候选压力矩阵；迁移后核心机制保留，但“候选空间本身”被压缩。

### B. current-C 会产生隐性路径锁定

现有主链是：

```text
Evidence
→ Reconstruction current-C
→ World
→ Object
→ Character Knowledge
→ Prewrite
→ Candidate
```

虽然 current-C 在 epistemic 上没有被升级成 Evidence，但在生产实践中它已经成为默认世界。

后续候选如果都只在 current-C 附近压缩、扩写、重排，会形成：

> **C-path lock-in：形式上可逆，实际搜索空间越来越窄。**

### C. 当前更擅长“故事事实”，不够擅长“叙述组织”

目前可很好回答：

- 谁在哪里；
- 谁知道什么；
- 谁与谁是什么关系；
- 钱、药、衣、玉、书稿怎么流；
- 哪些历史机制可行。

但还不能系统表达：

- 谁是这一场的 focalizer；
- 大事是正面演出还是只写后果；
- 什么信息故意晚说；
- 这一场是推进、延宕、反衬还是闲笔；
- 这一回的“转”发生在哪里；
- 收尾为什么是一个物件、一声问话或一个未完成动作；
- 哪种前80章法被调用。

### D. Literary Evaluator 主要是负面筛查

当前 v0.5 很适合做：

- explicit exposition 阻断；
- ambiguity closure 阻断；
- culture-museum 风险提示；
- structure uniformity 风险提示；
- blind packet isolation。

但：

> **避免坏文章 ≠ 找到最好文章。**

它不应被升级成单一“文学总分器”。

### E. A/B/C 更适合决赛，不适合承担全部搜索

现有 A/B/C 机制适合作为 final blind finalists。

但如果 A/B/C 都围绕同一 current-C 轻压/强压，搜索仍属于局部 hill-climbing。

后续应改成：

```text
12–30 个结构候选
→ 硬约束筛除
→ 聚类去重
→ 5–7 个异质半决赛方案
→ 3 个匿名决赛稿
→ 真盲读
```

---

# 2. 总体改进原则

所有后续开发必须遵守以下原则。

## 2.1 不重开 Full Migration

M0→M8 已完成。

后续任何补充只能称为：

- targeted fidelity backfill；
- hypothesis runtime；
- discourse runtime；
- retrieval runtime；
- literary search runtime。

禁止重新制造“Full Migration v4”式全量搬运工程，除非未来出现新的系统性断层证据。

## 2.2 新层永远 downstream

新增 Hypothesis、Scenario、Discourse、Retrieval、Generation 全部不得：

- 修改 Evidence Role；
- 修改 Witness；
- 自动关闭 OPEN；
- 自动升级 current-C；
- 自动创造历史事实；
- 自动覆盖 stable ACTIVE。

## 2.3 current-C 必须降为“scenario 中的一员”

当前 stable / current-C 仍然保留，但在搜索层中不得被赋予默认真值优势。

必须显式表示：

```text
CURRENT_C = one admissible scenario
```

而不是：

```text
CURRENT_C = base truth to be optimized
```

## 2.4 不采用单一总分

不设计：

```text
cao_similarity = 93.7
```

也不设计：

```text
original_probability = 0.81
```

所有方案保留独立评价轴，通过 hard filters + Pareto frontier + human review 处理。

## 2.5 机器负责排错、扩展和组织，人负责最终文学判断

机器可以：

- 找矛盾；
- 找遗漏；
- 找显性越界；
- 找过度解释；
- 发现结构同质；
- 生成更多方案；
- 检索前80近似文本；
- 提供结构差异图。

机器不能自动宣布：

```text
这是最像曹雪芹的一稿。
```

---

# 3. 实施路线总览

整个升级分为 7 个阶段。

```text
P0  基线冻结与目标化 Source-Fidelity Backfill
P1  v0.7 Hypothesis / Scenario Runtime
P2  v0.8 Counterfactual World Replay
P3  v0.9 Narrative Discourse Runtime
P4  v0.10 First-80 Exemplar Retrieval
P5  v1.0 Literary Search / Multi-candidate Competition
P6  Shadow Benchmark + Step43 Integration Gate
```

注意：

- 当前 `43-0` 的 86→89→92→97 canonical literary pipeline **不因本升级重置**。
- 新能力在 `43-0` 完成前只允许 **SHADOW_ONLY**。
- 不重新裁定已经完成的第86回。
- 不用新系统伪造第89回 blind result。
- 92/97 可以做 shadow benchmark，但 canonical adjudication 仍按当前 43-0 规则完成。
- **正式启用新搜索体系的时间点：43-0 总签收之后、Step43 全书重写之前。**

---

# 4. P0 — 基线冻结与 Targeted Source-Fidelity Backfill

## 4.1 目标

解决 H04 暴露出的一个问题：

> effective semantic coverage = FULL，并不等于原过程文档中的候选结构和论证粒度完全无损。

本阶段不做全量二次迁移，只补对“多方案搜索”真正有用的历史结构。

## 4.2 新增数据

新增：

```text
data/fidelity/
  audit_registry.json
  hypothesis_source_backfill.json
```

建议状态：

```text
MIGRATED_EXACT
MIGRATED_COMPRESSED
MISSING_MACHINE_NODE
SUPERSEDED
REFERENCE_ONLY
```

每条记录至少包括：

```yaml
source_document:
source_section:
semantic_item:
current_runtime_refs:
fidelity_status:
loss_type:
needed_for_hypothesis_search:
backfill_action:
authority_effect: NONE
```

## 4.3 第一批审计对象

不扫全部 249 项，只审计会影响大结构搜索的文档：

1. 婚期 / 贾母 / 主婚权；
2. 家败与居所；
3. 宝玉羁押；
4. 通灵玉两次失还；
5. 妙玉结局；
6. 宝钗婚后处境；
7. 凤姐死亡与巧姐线；
8. 甄宝玉送玉；
9. 出家与情榜；
10. 总回数 / 终局编号 OPEN。

## 4.4 H04 必补项示范

H04 至少补：

- `O09-A/B/C` hypothesis nodes；
- `G0/G1/G2` marriage-placement hypothesis nodes；
- “批准 / 名义主婚 / 出资 / 操办”四角色模型；
- “妻子财产责任存在法律区分”的独立 historical source/claim；
- 居所候选矩阵的 typed feasibility profile。

## 4.5 验收条件

- 不新增任何 `MUST` 剧情；
- 不改变 current-C；
- 所有 backfill node 有原文 locator；
- 所有 backfill 只进入 hypothesis/search 输入，不进入 Evidence promotion；
- `rcwh validate` 与全部旧测试继续 PASS。

---

# 5. P1 — v0.7 Hypothesis / Scenario Runtime

这是本升级最重要的一期。

## 5.1 目标

把：

```text
OPEN = 不知道
```

升级为：

```text
OPEN = 多个可管理、可组合、可回放、可比较的候选假说。
```

## 5.2 核心对象

### 5.2.1 Hypothesis

新增 schema：

```text
schemas/hypothesis.schema.json
```

对象示例：

```yaml
id: HYP-O09-B
question_ref: OL-xxx
title: 贾母仍在但实权下降
status: ADMISSIBLE
authority: HYPOTHESIS_ONLY

support_refs:
  - ...
counter_refs:
  - ...

requires:
  - ...
excludes:
  - ...

open_consumption:
  - ...
historical_cost: LOW
world_effect_refs:
  - ...
chapter_effects:
  - 87
  - 89

cannot_prove:
  - ...
```

### 5.2.2 Scenario Bundle

新增：

```text
schemas/scenario_bundle.schema.json
data/scenarios/
```

一个 bundle 是多个兼容 Hypothesis 的组合：

```yaml
id: SCN-G1-O09B-HOUSE2
status: ADMISSIBLE
authority: SCENARIO_ONLY

hypotheses:
  - HYP-G1
  - HYP-O09-B
  - HYP-HOUSING-TRANSITIONAL

hard_constraints:
  result: PASS

open_interfaces:
  consumed: [...]
  preserved: [...]

world_replay:
  status: PENDING

evaluation_axes:
  evidence_fit:
  contradiction_risk:
  open_consumption:
  historical_cost:
  chapter_economy:
  structural_echo:
  literary_fertility:
```

## 5.3 兼容性图

新增：

```text
data/hypotheses/compatibility.json
```

关系：

```text
COMPATIBLE
CONDITIONAL
MUTUALLY_EXCLUSIVE
REQUIRES
DOMINATES_ONLY_UNDER
```

禁止简单布尔化所有关系。

## 5.4 Scenario Generator

新增命令：

```text
rcwh hypothesis list
rcwh hypothesis get <id>
rcwh hypothesis alternatives <open-id>

rcwh scenario generate
rcwh scenario validate <scenario-id>
rcwh scenario compare <id1> <id2> ...
rcwh scenario frontier
```

`scenario generate` 只能组合已有 hypothesis，不得自己创造新的剧情节点。

## 5.5 current-C 去默认化

将当前路线映射为：

```text
SCN-CURRENT-C
```

并明确：

```text
search_priority = NONE
evidence_bonus = NONE
baseline_convenience_bonus = NONE
```

stable ACTIVE 仍用于回归与对照，但不再是 Hypothesis Search 的默认最优解。

## 5.6 第一批要进入 Hypothesis Runtime 的核心 OPEN

优先：

- 金玉婚精确相位；
- 贾母婚时状态；
- 家败前后居所；
- 宝玉羁押原因 / 时长 / 释放路径；
- 凤姐终局具体机制；
- 巧姐转移路径；
- 玉的两次失还身份；
- 妙玉失庵后的具体落点；
- 甄宝玉送玉机制；
- 99→100 外框转换方式。

## 5.7 验收条件

- 至少 10 个核心 OPEN 有显式 alternatives；
- 至少生成 8 个结构上真正不同的 81–100 scenario bundle；
- current-C 只是其中一个；
- 所有 bundle 必须通过 Evidence/OPEN hard validator；
- 不存在“历史可行 → 剧情 MUST”；
- 不用单一总分选 winner；
- CLI 可列出每个 scenario 的后果差异。

---

# 6. P2 — v0.8 Counterfactual World Replay

## 6.1 目标

当前 World Runtime 主要 replay current-C。

本阶段要求：

> 同一套世界模型可以在不同 Scenario Bundle 下重放。

## 6.2 改造原则

不复制一套新的 World。

改成：

```text
World Baseline
+ Scenario Delta
→ Scenario World Replay
```

## 6.3 新增对象

```text
data/scenario_deltas/
schemas/scenario_delta.schema.json
```

Delta 类型：

```text
CHARACTER_STATE
RELATION_STATE
RESIDENCE
RESOURCE
AUTHORITY
KNOWLEDGE
OBJECT
BODY
PRESENCE
SOCIAL_SYSTEM
```

## 6.4 必须支持的差异回放

例：

```text
SCN-O09-A
vs
SCN-O09-B
vs
SCN-O09-C
```

系统应能输出：

- 第87回主婚权差异；
- 婚礼资源差异；
- 第88/89权威坍缩速度差异；
- 若贾母先死，丧期占用的时间容量；
- 对90、92后续资源的影响。

另一个例子：

```text
G0 vs G1 vs G2
```

应能输出：

- 婚前/婚后贫困状态；
- 宝钗角色位置；
- 袭人离场相位；
- 89抄没时夫妻单元是否已成立；
- 92羁押时宝钗身份；
- 第95贫寒夫妻生活是否成立。

## 6.5 反事实矛盾类型

至少检测：

```text
TIMELINE_CONTRADICTION
KNOWLEDGE_LEAK
RESOURCE_IMPOSSIBILITY
OBJECT_TELEPORTATION
RELATION_STATE_CONFLICT
MOURNING_WINDOW_CONFLICT
PRESENCE_CONFLICT
AUTHORITY_CONFLICT
```

## 6.6 CLI

```text
rcwh scenario replay <scenario-id>
rcwh scenario chapter <scenario-id> <chapter>
rcwh scenario diff <scenario-a> <scenario-b>
rcwh scenario contradiction <scenario-id>
```

## 6.7 验收条件

- 至少 5 个 scenario 可完整 replay 84→100；
- current-C replay 与现有 runtime 结果完全一致；
- 反事实 scenario 不污染 current-C；
- 有 deterministic snapshot tests；
- 不改变 stable ACTIVE。

---

# 7. P3 — v0.9 Narrative Discourse Runtime

这是从“故事工程”走向“小说工程”的关键一期。

## 7.1 目标

新增独立的 Sjuzet / Discourse 层，明确表达：

> 不只是发生什么，而是作者怎样让它发生在读者面前。

## 7.2 新增 Scene Discourse Schema

建议字段：

```yaml
scene_id:
chapter:

focalizer:
narrative_distance:
knowledge_window:

scene_function:
  # ADVANCE / DELAY / COUNTERPOINT / ECHO / MISDIRECTION /
  # DOMESTIC_LANDING / COMIC_RELIEF / AFTERMATH / TRANSITION

event_visibility:
  # DIRECT_SCENE / REPORTED / PARTIAL / AFTERMATH_FIRST /
  # OFFSTAGE / DELAYED_REVEAL

information_reveal:
information_withheld:

primary_action:
secondary_action:
background_life:

tonal_register:
friction_source:

chapter_rhythm_position:
  # OPEN / SETUP / BUILD / TURN / PRESSURE / RELEASE / CLOSE

ending_vector:
  # OBJECT / QUESTION / SOUND / GESTURE / INTERRUPTION /
  # EMPTY_SPACE / UNFINISHED_SPEECH / NARRATOR_TURN

echo_refs:
  - front80 scene/chapter exemplar IDs

anti_exposition_rule:
ambiguity_rule:
```

## 7.3 Chapter Discourse Contract

每回新增：

```text
opening_strategy
scene_count_target_range
major_event_visibility
midpoint_turn
late_pressure
ordinary-life_ratio
direct_exposition_cap
ending_strategy
echo_family
```

这些不是 Evidence，不是硬格式，只是生成约束与评审对象。

## 7.4 前80章法库

从已有 Literary Ecology 中抽取：

- 大事后置；
- 闲笔承重；
- 人物误会；
- 旁观者转述；
- 小物落地；
- 热场转冷；
- 笑语压悲；
- 回末突转；
- 诗文作为行动而非说明；
- 空间变化承载身份变化。

每个技术节点必须有 front-80 exemplar refs，而不是模型自行总结。

## 7.5 第89回 shadow 示例

不改变 canonical candidate。

只在 shadow 中标注：

- 官面抄没是否正面写过多；
- 大事件如何沉入菜、粥、衣、药、钥匙、井；
- shared yard 是 aftermath 还是 exposition；
- 最后“谁家的水桶还在井边？”为何属于 QUESTION ending vector；
- 是否形成从制度→生活的真正 discourse descent。

## 7.6 验收条件

- 86/89/92/97 四回有完整 discourse annotation；
- 至少 20 个前80 discourse technique node 有 exemplar；
- 系统能比较两稿的“叙述策略差异”，而不是只比较字数；
- 不产生自动文学 winner；
- 所有字段允许 `UNKNOWN/ABSTAIN`，禁止伪精确。

---

# 8. P4 — v0.10 First-80 Exemplar Retrieval

## 8.1 目标

解决“只有 profile，没有原文近邻”的问题。

生成第93回时，不仅知道某人物 voice profile，还应能检索：

> 前80中与该人物、关系、压力、场景功能、物质活动最接近的实际文本实例。

## 8.2 索引原则

不把 embedding 当 authority。

建立两层：

### A. Canonical Segment Registry

Git 可审计：

```text
data/corpus/front80_segments.jsonl
```

每段至少有：

```yaml
segment_id:
chapter:
line_range:
text_sha256:
speaker:
characters:
location:
scene_function:
material_actions:
emotion_pressure:
relationship_context:
narrative_mode:
literary_form:
tags:
```

### B. Retrieval Cache

可重建，不是 authority：

```text
.cache/retrieval/
```

支持：

- BM25 / lexical；
- metadata filters；
- semantic embeddings；
- reranking。

Embedding 结果不得进入 Evidence。

## 8.3 查询接口

```text
rcwh exemplar character baochai
rcwh exemplar scene --function DOMESTIC_LANDING
rcwh exemplar relation baoyu-baochai
rcwh exemplar material medicine
rcwh exemplar ending QUESTION
rcwh exemplar similar <scene-contract>
```

## 8.4 检索输出纪律

输出必须区分：

```text
retrieved because of:
- lexical overlap
- metadata similarity
- semantic similarity
```

禁止模型把“相似段落”说成“后80原稿证据”。

## 8.5 生成时的 exemplar 预算

每个候选场景建议：

- 2–4 个结构 exemplar；
- 2–4 个 voice exemplar；
- 1–3 个 material-life exemplar；
- 最多 8–10 个总 exemplar。

避免把大量原文塞进 prompt 造成拼贴。

## 8.6 验收条件

- 前80 corpus segment IDs 稳定可追溯；
- 相同查询 deterministic metadata filter 一致；
- embedding 可重建；
- blind packet 中不暴露 retrieval lineage；
- 能对 86/89/92/97 给出人工可接受的近邻检索。

---

# 9. P5 — v1.0 Literary Search / Multi-candidate Competition

## 9.1 目标

把 A/B/C 从“全部搜索空间”改成“决赛”。

## 9.2 两阶段搜索

### Stage 1：结构候选

只生成 scene / discourse / event organization，不写完整 prose。

目标数量：

```text
12–30
```

每个结构候选必须声明：

```text
scenario_bundle
discourse_contract
scene_order
major_event_visibility
ending_vector
front80_exemplar_refs
```

### Stage 2：结构筛选

先通过 hard filters：

- Evidence；
- OPEN；
- World；
- Object；
- Character Knowledge；
- Historical Adapters；
- P-Lock minimum；
- explicit exposition；
- ambiguity closure。

随后做 structural diversity clustering。

### Stage 3：半决赛

保留：

```text
5–7
```

要求彼此在以下至少两项明显不同：

- scene order；
- focalizer；
- event visibility；
- major delay pattern；
- ending vector；
- social landing mechanism；
- scenario bundle。

### Stage 4：完整 prose

只为 5–7 个半决赛生成完整文本。

### Stage 5：机器筛查

机器只能：

```text
REJECT
FLAG
READY_FOR_HUMAN
```

不能：

```text
WINNER
```

### Stage 6：匿名决赛

人工或独立 reviewer 选 3 稿进入：

```text
A/B/C final
```

此时才使用现有 blind-review 体系。

## 9.3 Candidate Lineage

每稿记录：

```yaml
candidate_id:
content_sha256:
scenario_id:
discourse_contract_id:
exemplar_set_hash:
generation_model:
generation_config_hash:
parent_candidate_ids:
machine_findings:
```

blind surface 必须完全剥离这些字段。

## 9.4 多 critic 设计

不要让一个 evaluator 同时生成又评价。

至少分：

1. Boundary Critic；
2. World/Continuity Critic；
3. Discourse Critic；
4. Voice/Character Critic；
5. Compression/Exposition Critic。

各 critic 只能输出局部 finding。

不设统一“文学AI评委”。

## 9.5 Pareto 轴

候选比较保留以下独立轴：

```text
evidence_fit
contradiction_risk
open_consumption
historical_cost
world_coherence
chapter_economy
front80_structural_echo
voice_fidelity
discourse_indirection
literary_fertility
```

不求加权总分。

## 9.6 验收条件

- 至少 12 个结构候选；
- 聚类后至少 5 个真正异质候选；
- A/B/C 决赛稿不得仅是字数压缩差；
- blind reviewer 看不到 lineage；
- stable ACTIVE 不自动更新；
- winner 仍只能成为 `PROMOTION_CANDIDATE`。

---

# 10. P6 — Shadow Benchmark 与 Step43 Integration Gate

## 10.1 为什么先 Shadow

43-0 已经是当前项目的文学压力测试基准。

不能中途换规则后宣称结果可直接横比。

因此新系统在 43-0 结束前必须：

```text
authority = SHADOW_ONLY
stable_active_effect = NONE
competition_effect = NONE
```

## 10.2 Shadow 对象

### Chapter 86

已 adjudicated。

新系统只做 retrospective benchmark：

- 能否生成比原 A/B/C 更异质的结构；
- 能否找回更多前80 exemplar；
- 能否识别 B 为什么优于 A/C；
- 不重开 winner。

### Chapter 89

当前 canonical 仍先完成真实 manual P-Lock + blind read。

新系统不得参与 canonical blind。

之后才可做 retrospective shadow。

### Chapter 92 / 97

可以在 canonical pressure test 旁边建立 shadow candidate pool，但：

- shadow 结果不影响 canonical gate；
- 不能自动解锁 predecessor；
- 不提前写入 competition winner。

## 10.3 Integration Gate

43-0 完成后，召开一次正式 integration review。

只有同时满足下列条件，Step43 才切换到新系统：

- Hypothesis Runtime 无 authority leak；
- Scenario replay 稳定；
- Discourse Runtime 有真实增益；
- Exemplar retrieval 没有拼贴化；
- Multi-candidate search 确实增加结构多样性；
- 人工 blind review 认为 shadow pool 至少在部分回目显著优于 old local A/B/C；
- CI 全 PASS；
- stable 不变。

如果不满足，则保持旧 Step43 流程并继续改良，不强制上线。

---

# 11. 分支与仓库治理方案

由于仓库刚完成分支治理，后续禁止重新堆积长期 feature branch。

采用串行短分支：

```text
feature/hypothesis-runtime-v0.7
feature/scenario-replay-v0.8
feature/discourse-runtime-v0.9
feature/exemplar-retrieval-v0.10
feature/literary-search-v1.0
```

规则：

1. 每次只允许 1 个主要 feature branch 活跃；
2. 从 `literary/43-0-resume` 最新 head 建；
3. 默认 `SHADOW_ONLY`；
4. PR 合并后立即删除 branch；
5. 不从 quarantined `literary/43-0-ch89-phase2` cherry-pick 文学裁定；
6. 如需借用旧 fork 基础设施，只重实现 concept；
7. 不修改 `main` release authority；
8. 不修改 stable ACTIVE；
9. 所有新 schema 都必须有 regression tests；
10. 新 runtime 不得让旧 CLI 行为漂移。

---

# 12. 测试体系扩展

新增测试分为六类。

## 12.1 Authority Tests

必须证明：

- Hypothesis 不可升 Evidence；
- Scenario 不可关 OPEN；
- Exemplar 不可升 Evidence；
- Literary Search 不可 promote stable；
- Historical Adapter 仍只有 negative/feasibility authority。

## 12.2 Scenario Tests

检测：

- hypothesis incompatibility；
- timeline contradiction；
- world state conflict；
- knowledge leak；
- resource impossibility；
- object teleportation。

## 12.3 Discourse Tests

只做结构检查，不做“美学真理”：

- required ending vector 存在；
- event visibility 与 contract 一致；
- narrator exposition 超限；
- withheld info 被提前泄露；
- focalizer knowledge 越界。

## 12.4 Retrieval Tests

- segment hash 稳定；
- metadata filter deterministic；
- source line 可追溯；
- embedding cache 可丢弃重建；
- retrieval result 不进入 authority graph。

## 12.5 Search Diversity Tests

防止 12 个候选其实是一稿改字：

- scene order distance；
- focalizer difference；
- ending-vector diversity；
- scenario diversity；
- event-visibility diversity。

## 12.6 Blind Isolation Tests

继续确保 reviewer 看不到：

- scenario ID；
- candidate lineage；
- model；
- machine score；
- evidence fit；
- A/B/C mapping；
- adjudication state。

---

# 13. 新 CLI 总表

最终建议新增：

```text
rcwh fidelity summary
rcwh fidelity document <doc-id>

rcwh hypothesis list
rcwh hypothesis get <id>
rcwh hypothesis alternatives <open-id>

rcwh scenario generate
rcwh scenario validate <id>
rcwh scenario replay <id>
rcwh scenario diff <a> <b>
rcwh scenario frontier

rcwh discourse scene <scene-id>
rcwh discourse chapter <chapter>
rcwh discourse compare <candidate-a> <candidate-b>

rcwh exemplar similar <scene-or-contract>
rcwh exemplar character <id>
rcwh exemplar relation <a-b>
rcwh exemplar ending <type>

rcwh literary-search plan <chapter>
rcwh literary-search generate-structures <chapter>
rcwh literary-search cluster <chapter>
rcwh literary-search semifinal <chapter>
rcwh literary-search blind-packet <competition-id>
```

---

# 14. 计划评审

以下是对初稿方案的正式自审。

## 14.1 评审维度

| 维度 | 初稿风险 | 评审结论 |
|---|---|---|
| 是否会污染 Evidence | 新增层太多可能越权 | 必须全部 downstream / SHADOW_ONLY |
| 是否重开迁移工程 | Source-fidelity 容易无限扩张 | 改为 targeted backfill |
| 是否拖慢当前89 | 若先升级再继续89，会阻塞 | 43-0 canonical 不等待升级 |
| 是否破坏实验可比性 | 92/97若换方法会与86/89不一致 | 新系统只 shadow，43-0不换正式规则 |
| 是否过度工程化 | 全部249逐条重做不划算 | 只补影响 hypothesis search 的材料 |
| 是否制造假精确 | 综合评分容易变伪概率 | 禁止单一总分，采用 Pareto |
| 是否把 embedding 当知识 | 向量相似易偷渡权威 | retrieval cache 非 authority |
| 是否增加巨量生成成本 | 30篇完整小说代价过高 | 先结构后 prose |
| 是否让AI自评AI | generator/judge 同源偏差 | 多 critic + 人类 blind |
| 是否使分支再次失控 | 多版本并行会堆 branch | 串行单 feature branch |
| 是否重开86赢家 | 新系统回测可能误作重新裁定 | retrospective only |
| 是否能真正改善文学 | 只做更多 schema 不够 | 强制新增 discourse + exemplar + search diversity |

## 14.2 初稿被修改的关键点

### 修改一：不在第89正式 Gate 前切换新体系

原先可以考虑立即升级后再做89。

评审后否决。

理由：

- 当前会话已不具备独立 blind 身份；
- 89 gate 已有合法 pipeline；
- 中途改评审工具会改变实验条件。

最终决定：

> **先按现行规则完成 43-0；新能力全程 shadow。**

### 修改二：不做第二次 Full Migration

H04 的确暴露 source-fidelity 缺口，但不能据此把所有旧文档重新逐行结构化。

最终决定：

> 只 backfill 会影响“多方案搜索”的高价值知识。

### 修改三：Hypothesis Runtime 优先于 Discourse Runtime

两者都重要，但如果 current-C 路线本身不是最优，先把 prose 写得更好也只是局部优化。

所以顺序定为：

```text
Hypothesis
→ Scenario Replay
→ Discourse
→ Retrieval
→ Generative Search
```

### 修改四：A/B/C 保留，但后移

A/B/C 已经有成熟 blind infrastructure，不应该废掉。

最终把它从“搜索空间”重新定义为：

> **匿名决赛层。**

### 修改五：禁止总分

所有历史、结构、文学轴保持可分解。

最终筛选顺序：

```text
hard blocker
→ contradiction
→ diversity
→ Pareto
→ human review
→ blind final
```

---

# 15. 定稿后的执行顺序

这是最终推荐的施工次序。

## Phase 0 — 立即开始

建立：

```text
feature/hypothesis-runtime-v0.7
```

先实现 Targeted Source-Fidelity Backfill + Hypothesis schema。

不动89 canonical state。

**Gate 0：**
- schema PASS；
- authority regression PASS；
- H04 sample PASS；
- stable unchanged。

## Phase 1 — Hypothesis Runtime

完成 10 个核心 OPEN 的 alternatives。

建立至少 8 个 admissible scenario bundles。

**Gate 1：**
- current-C 不再是唯一结构；
- scenario bundle 可解释；
- 无 evidence leak。

## Phase 2 — Counterfactual Replay

让至少 5 个 bundle 重放 84→100。

**Gate 2：**
- current-C replay 与现有 runtime 等价；
- 非 current-C 可发现真实差异和矛盾。

## Phase 3 — Discourse Runtime

先标注 86/89/92/97。

随后扩展到 81–100。

**Gate 3：**
- 能解释不同候选的“怎么讲”，不只“讲什么”。

## Phase 4 — First-80 Exemplar Retrieval

建立 segment registry 和 hybrid retrieval。

**Gate 4：**
- 可追溯；
- 不拼贴；
- 不升 evidence。

## Phase 5 — Literary Search v1.0

实现：

```text
12–30 structures
→ hard filtering
→ diversity clustering
→ 5–7 semifinal prose
→ 3 blind finalists
```

**Gate 5：**
- final A/B/C 在结构上确实异质；
- machine 无 winner authority。

## Phase 6 — 43-0 Shadow Benchmark

86 retrospective；
89 post-adjudication retrospective；
92/97 shadow。

**Gate 6：**
评审新系统是否比旧 A/B/C local pressure test 有明显增益。

## Phase 7 — Step43 Integration

仅在 Gate 6 PASS 后，正式把 v1.0 设为 Step43 默认候选搜索流程。

此后再执行原大工程：

```text
43 正式重写
44 文化非展览馆
45 诗词质量/身份
46 知识密度
47 章法
48 80→81接轨
49 人物/物件长线
50 纯文学盲读
51 边界终审
52 多版本出版
```

---

# 16. Definition of Done

本升级只有满足以下全部条件才算完成：

1. current-C 不再垄断搜索空间；
2. 主要 OPEN 有可查询 alternatives；
3. 不同 scenario 可独立 replay；
4. 世界一致性校验支持 counterfactual；
5. Narrative Discourse 成为一等 runtime；
6. 前80 exemplar 可按场景功能检索；
7. 候选生成先搜索结构，再生成 prose；
8. final A/B/C 来自真正异质候选；
9. Literary Evaluator 继续只做 rejector / flagger；
10. 人类 blind review 仍是文学最终 gate；
11. 所有新增层 `authority != EVIDENCE`;
12. stable ACTIVE 未经 Promotion Gate 永不变化；
13. 旧 43-0 canonical adjudication 不被 shadow 系统反向改写；
14. CI / pytest / validate 全 PASS；
15. 仓库分支继续保持可治理，不重新产生长期 branch 堆积。

---

# 17. 最终技术决策

最终不选择以下路线：

```text
纯 LLM 长篇续写
全量向量库 RAG 后直接生成
单一“曹雪芹相似度”打分
全贝叶斯化原稿概率
重新做一遍 Full Migration
用图数据库替换 Git-native source of truth
```

最终采用：

```text
Git-native Authority Kernel
+
Typed Hypothesis / Scenario Search
+
Counterfactual World Replay
+
Narrative Discourse Runtime
+
Auditable First-80 Exemplar Retrieval
+
Structure-first Multi-candidate Generation
+
Machine Rejectors
+
Human Blind Literary Adjudication
```

这条路线的核心目的不是把文学创作“自动化”，而是：

> **最大限度扩大仍符合证据的可能空间，最大限度阻止 current-C 路径依赖，再用前80原著的叙事生态和严格盲读，把搜索逐步收敛到文学上最有可能成立的版本。**

从工程目标上说，RedChamberWorldHarness 应当从：

> **“不让我们写错”**

升级到：

> **“不让我们过早选错，同时帮助我们在可行空间里找到更好的文学解。”**

这就是本次 v1.0 升级计划的最终定稿方向。
