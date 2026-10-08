# 搜索、文学实验与写作操作

本文合并原 P0—P8 阶段文档的操作说明。历史完成状态、CI run 和样本数量退出操作规则；原阶段状态保存在[清理审计](../../artifacts/migration/handover-20261008/rules_cleanup_report.json)。当前状态使用 `rcwh project status` 与实际 competition 记录查询。

## 搜索链

Hypothesis 记录 OPEN 接口的显式备选和支持范围。Scenario 将相容假说组织成方案，不关闭研究 OPEN、不享有 current-C 优先权。Replay 在共同 World 基线上应用方案增量；情节位置、婚姻、居所、玉的同一性等均为方案内选择，不能写回证据层。

Replay 检查时间、资源、物件连续性、关系和人物知识；历史负担、W2 依赖和终回容量属于压力信号。current-C 方案应重现当前 World 快照，它是实现参照而非原稿概率。

Pareto 按数据声明的多轴关系比较方案；机制轴与完整轴前沿分别输出。文学启发式评分不是证据，不提供总分自动选胜。压力测试的方案集合须与选定前沿一致。

```bash
rcwh hypothesis --help
rcwh scenario --help
rcwh scenario replay --help
rcwh pareto --help
rcwh literary-stress --help
```

以上命令的具体子命令、参数以当前 CLI 帮助为准。

## 从事件到叙述

人物知识按事件检查点查询，声口资料不足时保留弃权：

```bash
rcwh knowledge scene ch92_delivery_gate --checkpoint K92-XIAOHONG-ASKS-GATE-RULES
rcwh knowledge character ch86_last_night zijuan --checkpoint K86-ZIJUAN-SEES-RAPID-DECLINE
rcwh knowledge voice qianxue
rcwh knowledge mask xiaohong /path/to/text.md
rcwh knowledge guard data/scenes/ch86_last_night.yaml /path/to/text.md
```

Literary Stress 将前沿方案变成场景 probes，要求日常行动、次要人物、人物声音、物件、文化功能、章回节奏和非解说叙述有实际承担者。每个方案覆盖其声明的窗口和维度。

Narrative Discourse 将事件安排（fabula）和讲述方式（sjuzet）分开。每张叙述卡对应一个上游 probe，保持其事件、行动、物件及信息边界；另行声明焦点人物、时间顺序、转述渠道、叙述距离和退出方式。事件可先展示后果或通过报告进入正文，不能用叙述者解释强行封闭 OPEN。

Prewrite 依据项目章回范围组装 gap cards、形成过程计划、文学规则、历史机制和 P-Lock，输出 staging 合同。诊断维度来自声明；每章场景数量由需要决定。预写作没有改写证据、自动采用或发布的权限。

```bash
rcwh narrative-discourse --help
rcwh prewrite --help
```

预写作可分别查询 `corpus [profile-id]`、`gap <chapter>`、`scenes <chapter>`、`step <33..42> [--chapter N]`、`contract <chapter>` 和 `stage <chapter>`。场景槽位随声明增长，不维护第二份固定数量表。

## 实验、盲评与修订

Controlled Microdraft 每个上游叙述卡对应一份实验稿，并按声明的比较 cells 和方案形成配对。机器检查锚点、焦点绑定、禁词、长度与评估阻断项；机器就绪不等于文学通过。匿名材料包不能泄露方案或 probe 身份。

Blind Microdraft Review 的 token、cell 排序和解盲映射必须完整对应实验稿，原始意见可核查。现有独立阅读声明来自用户提供，系统不能证明评审者在仓库外看过什么。描述性排名不自动淘汰路线。

Revision Ablation 对上游实验稿逐项配对，保持方案、probe、cell 和焦点绑定，使用已声明的修订目标。基线正文不改写；反模式减少只说明检测器结果，文学改善需重新盲评。当前能力 owner 的下一工作为配对修订盲评，不能据此绕过正式章回竞争。

```bash
rcwh microdraft --help
rcwh blind-microdraft-review --help
rcwh revision-ablation --help
```

## 正式文学生产

竞争工作顺序由文学 owner 声明，与实际 production competition 的顺序一致。机器预检、人工 P-Lock、真实盲评和裁决分开；前序竞争未裁决时，后序仍受阻。人工结果可以真实推进，不再要求永远保持历史 PENDING。

竞争记录包含候选正文身份、六字段结果、人工评审、盲性声明和裁决。缺少有效门禁的候选不能被宣布为 winner。胜出只能成为 promotion candidate；稳定正文仍须经过独立晋升路径。

历史分叉的隔离原因保存在 [ADR 0003](../decisions/0003_RETIRE_HISTORICAL_RULES.md) 的带日期审计快照中。当前权威由项目 owner 和实际候选评审记录决定；旧分支的未确认裁决不能自动采纳。分支名称不参与运行有效性判断。

```bash
rcwh project status
rcwh literary-production --help
rcwh competition --help
rcwh promotion --help
rcwh validate
```

## 按需输出评审包和整书候选

```bash
rcwh literary-suite prose /path/to/candidate.md --json
rcwh literary-suite blind comp:43-0:ch89:pressure-test --json
rcwh literary-suite blind comp:43-0:ch89:pressure-test --output-dir /tmp/rcwh-ch89-review --json
rcwh promotion promotion:ch86:b:v1-5-candidate --output /tmp/rcwh-v1.5-candidate.md --json
```

盲评输出目录必须是新目录，只将该目录交给评审者；正文来自已校验候选，token 映射保留在内部记录。既有第86回阅读结果与第89回待评审状态分别由真实记录持有，导出不会改变状态。针对章回的阅读问题仍见各章 `blind/` 下的说明文件。

整书候选由 promotion 清单中的基线资产和替换章节构建，先核对基线、章节和整书 SHA，再完成原有回归；成功后才能写入新的输出文件。复用完整候选不会自动修改稳定正文或形成发布。日常验证在内存中构建，不依赖常驻的整书副本。

P7 的原始独立阅读意见已登记为 REVIEW_RECORD，运行时用 asset ID 核验原字节；导入的排版副本可用历史查询复原。解盲映射直接从绑定的 P6 记录生成，不另存 MAPPING 文件。P7、P8 用记录 ID 和摘要绑定 P6 的完整记录与正文原字节；P8 另绑定 P7 评审记录摘要。上游变动会拒绝旧评审或修订的使用，须建立新版本并重新评审，不能仅刷新摘要掩盖变更。P8 配对仅保存基线 token 与修订信息，场景、probe、cell、基线路径由已校验的上游记录解析。

六字段、机器文学预检与 promotion 回归结果按需查询，不再维护静态 PASS 报告。领域 summary 的数量由实际对象计算；旧 `completion`、`acceptance` 和 `all_acceptance` 自证字段退出接口。数据使用 `schema_version` 声明结构版本，旧任务编号不构成有效性条件。

能力 owner 现为 `data/project/capability.json`，只选择实验类型、记录路径和发布基线。`project status` 与 `revision-ablation` 读取同一选定实验；能力状态、权限和下一门禁来自当前检查与实验声明。旧分支、提交、交付清单和 CI 成功记录只保存在[清理审计](../../artifacts/analysis/historical-assets-20261008/execution_report.json)的 round 5，不证明当前实验通过。目前支持的能力实验类型为 `REVISION_ABLATION`；新增实验类型需要实现相应验证器。

P7 只保存每个 token 的原始 verdict、工程感判断、每个 cell 的排序，以及方案说明、修订目标。cell 从已绑定的 P6 解析，rank、top2 和方案统计按需计算。`EDGE(偏弱)` 原文保留，按明确的 `verdict_categories` 归入 EDGE；分类不会改变评语或自动裁决。

文学 summary 使用 `active_gates` 显示当前活跃章节；`literary-production chapter <N> --json` 的 `gates` 显示所选章节的门禁，替代固定第89回字段。实验不干预任何正式竞争，由通用 `competition_effect`／`effects.competitions` 约束。门禁继续依赖实际候选、人工评审和裁决。

M6 的章节 alignment 从正文定位、计划、保护表和实施事实生成。`object_query_locations` 保留人工选择的物件查询位置；专门 P-Lock 与范围内实际登记的保护项一致，不限制固定数量。检查核对所选 release 身份、正文原字节及连续章节范围，不借某次 promotion 的快照证明当前正确。

`rcwh validate` 统一检查必需领域文档，并沿 owner 选择检查能力、文学、方案约束和实验记录；缺失文件会失败。旧 WorldState 保留场景前置条件读取接口；未使用的状态写入与人物查询接口已退役，完整世界状态仍由 WorldRuntime 提供。

方案版本由 `owners.plan_constraints` 与 `plan_constraints_binding` 共同选择，`rcwh project status` 显示其身份、摘要、权限和迁移／提案性质，`rcwh validate` 检查约束与实际领域状态。调整模型、排程或文学选择时应建立新版本，并在隔离工作副本中更新选择；仅修改运行数据会因偏离所选约束而失败。校验通过只说明方案与约束一致，正式采用仍须完成有效评审和既有门禁。

旧 `data/events/` 与 `data/evidence/` 支线已退役。黛玉死亡方向以来源图中的 `claim:daiyu:death-direction`／`decision:daiyu:death-direction` 为准；不写完整绝命诗的工作约束继续由 `ch86_last_night` 场景契约及文学检查承担。WorldState 只读取场景前置条件所需人物与物件，世界快照直接通过 WorldRuntime 查询。

Reconstruction、World、Object、Literary Ecology、Implementation Alignment、Knowledge、Historical Adapter、Literary Suite、Prewrite 和 Pareto 的 `summary` 只展示数据与引用身份，不再返回或打印手填的顶层 `status: PASS`。查询成功的退出码表示请求已完成；领域完整性使用 `rcwh validate` 检查，`object continuity` 继续根据实际连续性检查返回 PASS／FAIL。验证报告中的 `check_status` 表示该命令达到预期结果，`status` 仅在命令实际返回该字段时记录。

物件网络在 `data/objects/m4.json` 中显式声明 `baseline_chapter`（当前为 80），有效演进章回来自 `data/project/scope.json`。`object get`、`object jade` 省略 `--chapter` 时查询项目最后一个章回；显式查询只允许基线或项目实际列出的章回，章回范围中的空缺也会拒绝。转移事件必须属于项目章回，基线必须早于项目第一回。当前第96回接济和第100回终局属于保留的模型检查点；删去检查点覆盖会失败，不能用缩小范围绕过保护。

场景状态查询仅接受 `character` 与 `object` 根名。旧空 metadata 回退已删除，未知根名明确报告无效前置条件。

场景种子只保存候选定义、假说与权限等输入，不存放预填的 hard_constraints PASS 或固定 UNASSESSED 轴占位。约束阻断由实际场景校验与回放计算，轴向比较由 Pareto 评估提供。实验的顶层手填 PASS 已删除；回放、文学压力、叙事、微稿和修订仍返回实际运行结果。P7 的人工评审与来源审计记录继续保留。

文学流程选择中的 stable_active 仅绑定发布正文 SHA256；发布清单负责解析实体路径，正文是否改变由实际文件字节检查决定。文学流程 ACTIVE、显式启动授权、章回顺序与人工门禁继续有效。
