# 独立读者填写指南

本指南分为读者与协调者两部分。读者不需要操作仓库、计算摘要或理解 schema。程序只核对收到的身份声明、原文引句与输入版本，**不会证明真实身份，也不会自动裁决文学质量**。

## 读者：先确认读什么

请协调者把本次阅读材料和相应空白 `human-review-template.json` / `reading-template.json` 一起给你。不要使用另一轮的表格，不改表里的协议、文本和上下文摘要。

| 类型 | 材料与任务 | 独立性声明 |
|---|---|---|
| 来源复核 | 12 条来源对应的原件、摘录、见证层级和 Claim 影响；核对版本与解释边界 | `independent_of_corrections`：未参与受评更正 |
| 语料审核 | pilot 的 13 个或完整候选的 91 个样本；看原件、分类和前后文 | `independent_of_builder`：未参与该语料构建 |
| P9 | 20 对匿名 A/B 小说片段，不能看协调者映射 | `independent_of_authors`、`mapping_unseen_during_review` |
| 85–87 整段阅读 | 三组匿名连续三回短稿；只读 `public/`，不能读 `coordinator/` | 与作者独立，评审期间未见映射 |
| 场景判读 | 正文、场景合同和冻结请求；核对实际事件，不以出现关键词代替判断 | `producer.kind` 为 `INDEPENDENT_HUMAN`，身份不能与作者同源 |

若看过映射、参加过写作或无法确认独立性，请如实填写并告诉协调者。不要为了让工具通过而声明 `true`。不符合该独立意见入口的材料仍应保存，不得冒充独立评审。

### 怎样填写 JSON

- 保留字段名和层级，只改需要填写的值；字符串要放在双引号里。
- `true` 表示核对成立，`false` 表示核对不成立，`null` 表示尚未填写。未填写记录不能登记为完整意见；完成一项之后再交回。
- `reviewer.id` 是协调者为你约定的稳定身份编号，不一定要填姓名。85–87 使用 `principal_id`（评审者）和 `source_id`（该意见的实际来源）。不要复用另一位读者的编号。
- `notes` / `reason` 写具体理由，最好指出原文或原件位置。不要只写“好”“已阅”。
- 来源和语料核对发现问题就填 `false`。**有效否定意见会登记，并阻止对应审查通过；不会被另一份赞成意见抵消。**

## P9：评分与偏好

每个 pair 都要填写 A、B 在所有维度上的 1–5 分，以及偏好和理由。

| 维度 | 要考虑的内容 | 分数方向 |
|---|---|---|
| `scene_cohesion` | 行动与场景是否连贯，不只是情节说明 | 越高越好 |
| `character_voice` | 话语、反应是否像这个人物而非作者的说明 | 越高越好 |
| `life_detail` | 日常细节是否推动行动，而非装饰性点缀 | 越高越好 |
| `engineering_feel` | 是否像按约束清单拼装，解释、照应是否生硬 | **越高工程痕迹越明显，越差** |

偏好可填 `A`、`B`、`TIE`（难分高下）或 `NEITHER`（两份均不满意）。分歧、平局与全部淘汰都是合法结果，不要求评出赢家。

## 85–87：整段排序与引句

按三回整体体验对三份匿名稿排序。`ranking` 是从较好到较差的分组；同一组内平局，例如：

```json
[["read-第一份编号"], ["read-第二份编号", "read-第三份编号"]]
```

实际填写时必须使用阅读包里的真实 token；每份恰好出现一次。`recommendation` 可为 `CONTINUE`（建议继续研究）或 `NEITHER`（均不宜继续）。每份稿子的四个维度都要有理由和至少一条引句。这里不填 1–5 分。

引句对象可以先只写：

```json
{"quote": "从阅读文件复制的原文"}
```

引句须连标点和空白一起精确复制。若同一句出现多次，加 `"occurrence": 2` 表示第二次，从 1 开始计数。协调者可用工具补上 Unicode 起止位置，但补完后必须让你核对，再把完整文件作为原始意见提交。不能接收后再偷偷补写你的证据。

空白表的 `report_kind` 是 `TEMPLATE`。完成后改为 `REVIEW_OPINION`，填写意见 `id`。保留 `authority_effect: "NONE"` 即可。

## 场景判读：核对事件而不是字词

冻结请求的合同列出 required beats、forbidden beats、出口与知识限制。读完每项后：

- 已检查的约束 ID 放进 `coverage`；仍不确定的约束 ID 放进 `unresolved`。不确定也可以提交，结果保持 PENDING。
- `events` 按正文的事件顺序填写；原文引句放进 `spans`，偏移同样可由工具在提交前补齐。
- `scope` 区分实际发生 `ACTUAL` 与否定 `NEGATED`、设想 `HYPOTHETICAL`、梦 `DREAM`、比喻 `METAPHOR`、引用 `QUOTED`。
- 实际物理变化写 `effects`；对白或内心想法本身不能证明人物已死亡、物件已移动。
- 知情变化写 `knowledge`；获知须指向实际观察/通信的 `source_event`，并在来源事件写出 `observations`（事实）与 `observers`（接收人物）。人物不能因叙述者知道而自动知道。
- `source_event: null` 或 effect 的显式 `value: null` 可有合法含义，不要与“未填写”混淆；以场景 schema 和语义检查器为准。

事件记录复杂时可以请协调者解释字段，但判断和理由必须是你的。当前场景登记命令仅接收真人意见；模型判读走已有 `semantic run/check` 的轨迹验证。

## 协调者：准备与接收

先看当前入口：

```bash
rcwh reviews status
```

来源/语料完整材料仍通过 `delivery materialize` 准备，P9 使用已登记盲包。85–87 默认登记入口选定 `artifacts/analysis/evaluation-refactor-20261009/pilot-reading/`，只交付其中 `public/`。`pilot export` 的每次新导出都有不同 token；使用新包时须显式调整 `data/evaluation/pilot85_87/review_selection.json` 的 export_root 和两个实际摘要，不改 study.json，不混用旧包意见。

收到完整原件后可先预检，再登记：

```bash
rcwh reviews register source /path/to/source-opinion.json --origin '独立来源复核，本轮实际接收' --dry-run
rcwh reviews register source /path/to/source-opinion.json --origin '独立来源复核，本轮实际接收'
rcwh reviews register corpus-pilot /path/to/pilot-audit.json --origin '独立语料审核'
rcwh reviews register corpus-full /path/to/full-audit.json --origin '独立语料审核'
rcwh reviews register p9 /path/to/p9-opinion.json --origin '独立配对盲评'
rcwh reviews register pilot /path/to/sequence-opinion.json --origin '独立整段阅读'
```

来源、语料、P9 的默认意见 id 由原件摘要生成，也可用 `--id` 指定。pilot 的 id 必须由读者在原件填写，不能在接收时替换。

提交前补偏移（不会覆盖已有输出）：

```bash
rcwh reviews resolve-spans draft-opinion.json --texts /path/to/public --output final-opinion.json
```

场景入口还需原冻结请求，用于验证当前合同、正文、入口与正式候选作者信息：

```bash
rcwh reviews scene-template request.json --output reading-template.json
rcwh reviews resolve-spans draft-reading.json --texts /path/to/exact-candidate.md --output final-reading.json
rcwh reviews register scene-reading final-reading.json --request request.json --origin '独立场景判读'
```

场景正文必须匹配当前竞争候选。作者不明时不能在请求中编造作者；仍可保存意见，但不会取得独立通过资格。同一请求已有判读时登记命令拒绝追加，因为既有选择器只读首条；更换选择须另行显式处置，本工具不覆盖旧意见。

### 登记、状态与回滚

命令保存原始字节，生成结构化记录，追加对应 selection，并仅更新该 selection 在闭包中的实际摘要。它不会改协议、候选稿或旧提交来让检查通过。来源、语料、P9 和场景原件经 REVIEW_RECORD 资产入库；pilot 原件用仓库路径与摘要保存，以兼容现有比较检查器。

- `--dry-run` 不写原件、记录、selection 或闭包；检查器的运行锁不属于意见数据。
- 登记成功仍可能退出 2（该 lane 人数不足/判断待定）或 1（真实否定意见造成 FAIL）。看 `registered: true`，不要只凭退出码误认“没有保存”。
- 登记中的普通异常会恢复选择与闭包原字节，删除本次结构化记录，**已接收的原件保留**。若文件发生并发变更，回滚不会覆盖它，会报告冲突需人工处理。
- 评审者的身份和独立性是提交声明，不是经工具认证的身份。

登记后再由操作者纳入版本控制，并跑严格验收；本工具不会自动执行 Git：

```bash
rcwh project acceptance
rcwh project acceptance --require-tracked --require-complete
```

两份有效 85–87 阅读会进入 `pilot summary` 的真实计数并移除“两位比较读者”待办，但新鲜对照、语义复核、实质修订与重评未完成时，试验总体仍是 PENDING。登记和人数达标都不等于文学采用或发布。
