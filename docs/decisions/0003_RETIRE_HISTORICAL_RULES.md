# ADR 0003：退役历史规则、阶段副本与样本数量门禁

日期：2026-10-08。承接 [ADR 0002](0002_RETIRE_MIGRATION_RUNTIME.md)。目标是让仓库规则支持复原工作推进和数据扩展，避免历史迁移安排永久控制资格。

## 决定

1. 删除旧整库评审、旧来源评审、远端分支盘点和九份 P0—P8 阶段说明；有效操作合并至[搜索与写作手册](../runbooks/SEARCH_AND_WRITING.md)。重写架构入口，完整设计仍保留为目标文档。
2. 删除未被任何加载器读取的 `config/world_law.yaml`、`policy/literary_policy.yaml`、`evaluators/README.md`。原则纳入架构契约；实际 severity 由现有 evaluator 数据与代码决定。旧伪配置中的自我解释 FAIL 与实际 WARN 冲突，不能借清理升级拒绝规则。
3. 删除迁移冻结、历史完成门与 P0 盘点字段。稳定正文不可随意覆盖、下游不能制造证据、实验不能自动晋升、人工审阅和隔离分叉规则继续执行。
4. 删除 P1—P7 七份阶段状态与配套 schema。capability、literary、competitions、release、implementation 仍由 `data/project/current.json` 显式选择。M6 直接引用实际 competition；文学 owner 不再复制各章节状态或 next gate。
5. 章回范围在 `data/project/scope.json` 明确声明。领域数据、预写作与正文结构按该范围校验；图、人物、物件、文学对象不以历史总数限制扩展。
6. 保留已确认的语义锚点，新增节点须通过同等引用与权威检查。数组窗口的两个端点、叙述曲线的结构宽度、单一活跃竞争、空 OPEN 关闭集等属于结构或权限约束，继续保留。

## 验证与审计

[清理报告](../../artifacts/migration/handover-20261008/rules_cleanup_report.json)保存退役文件摘要、阶段状态和移除字段，作为审计读取，不参与当前运行时判断。原始资产及其 SHA 保持一致；本次不裁剪研究材料版本。

测试验证合法增量可通过，同时拒绝重复身份、覆盖缺口、错绑上游对象、无效人工裁决和基线正文损坏。整库验证与干净检出复测必须通过。来源内容和定位尚未闭包的限制继续如实报告。

## 2026-10-08 补充：历史快照退出运行时

删除重复解盲映射、静态机器报告、手填完成标记与任务编号门禁。原始微稿和人工评语保留；评审及修订引用绑定上游记录与正文摘要。现行检查验证实际结构、引用与权限，不以 M/P 阶段或 issue 编号证明完成。

文学状态和发布基线由项目 owner 显式选择；工作分支名称不构成权威。旧分支的未获确认裁决仍不能采纳：导入任何评审须建立对应候选版本、评审出处和盲性声明，经过正式门禁，不能复制历史状态自动推进。`literary-production quarantine` 及其运行时 schema 退役。

以下是 2026-10-07 隔离记录的原始快照，其中分支、提交数量及 CI 描述仅反映当时观察，不是远端现状，也不要求同名分支永久存在：

```json
{
  "schema_version": 1,
  "id": "repo-governance:post-m8:20261007",
  "status": "ACTIVE",
  "authoritative_branches": {
    "release": "main",
    "literary_work": "literary/43-0-resume",
    "migration_archive": "archive/full-migration-v3-final-20261007",
    "export_snapshots": [
      "export/full-migration-snapshot-20261006",
      "export/self-contained-20261006"
    ]
  },
  "quarantined_forks": [
    {
      "branch": "literary/43-0-ch89-phase2",
      "head_sha": "69d406034960fc656ec1184425ae788ff18b6182",
      "canonical_replacement": "literary/43-0-resume",
      "state": "QUARANTINED_NON_RUNTIME",
      "merge_policy": "DO_NOT_MERGE",
      "salvage_policy": "CHERRY_PICK_OR_REIMPLEMENT_INFRASTRUCTURE_ONLY_AFTER_REVIEW",
      "reasons": [
        "diverged from canonical literary branch",
        "contains 25 unique commits and conflicting Chapter 89 candidate/adjudication artifacts",
        "records a human P-Lock/blind-read adjudication that is not independently established in the canonical workflow",
        "all recent CI runs on the fork are failing",
        "stable ACTIVE must not be affected by this fork"
      ],
      "salvage_candidates": [
        "src/rcwh/literary_production.py concept",
        "schemas/literary_production_state.schema.json concept",
        "post-M8 live-state validator separation from immutable M8 snapshot"
      ],
      "reject_as_authority": [
        "artifacts/43-0/ch89/ADJUDICATION.md",
        "artifacts/43-0/ch89/BLIND_READ_RESULT.md",
        "data/project_state/literary_resume_v1.json winner/pipeline advancement",
        "any automatic transition of Chapter 92 to READY_FOR_CANDIDATES"
      ]
    }
  ],
  "stable_active_sha256": "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"
}
```

## 2026-10-08 补充：能力选择与派生视图

最后一份 P8 阶段快照及其 schema 退出运行时，改由 capability owner 显式选择实验并实时验证。原始分支、提交、CI 和交付记录，以及 M6 的历史正文表头纠偏说明，保存在[历史资料执行报告](../../artifacts/analysis/historical-assets-20261008/execution_report.json)的 round 5 `historical_snapshot`；这些观察仅供审计。

M6 的章节对齐视图与 P7 统计从单一事实来源生成。发布与专门保护检查依据当前选择及实际登记对象，通用章回门禁替代固定第89回输出。必需文件缺失、错误正文定位、上游漂移、保护覆盖不足和未经人工审阅的裁决仍会失败。

## 2026-10-08 补充：退役旧支线与固定方案校验

删除 v0.1 事件、证据支线的四个数据／schema 文件和专用兼容校验。完整旧记录存入现有清理执行报告 round 6；死亡方向由正式来源图承接，绝命诗工作约束由场景契约承接。删除无调用 schema 辅助接口及只用于兼容测试的 WorldState 世界快照转接。

将当前模型、章回排程、世界检查点与文学选择的 17 条校验迁入带 ID、摘要、发布基线和来源绑定的方案版本；保留证据、OPEN、历史纠偏和正式文学保护。初始迁移不是新审批，替代约束的一致性检查不产生采用资格。删除 CI 遗留的 quarantine 命令，独立检出工具同时执行真实 CI shell 步骤，修补此前 smoke 清单的覆盖缺口。

## 2026-10-08 补充：摘要自报状态与物件范围

移除五个领域记录及摘要中的手填 PASS；摘要是数据视图，完整性结论由实际校验产生。物件连续性和正式评审的真实状态继续保留。独立检出报告区分命令检查结果 `check_status` 与命令返回的 `status`。

方案规则 schema 用共享定义代替三份副本；删除空 metadata 分支和三个纯计数测试，M6 摘要测试保留发布身份绑定检查。物件范围接入项目 scope，并显式声明基线；查询拒绝未声明章回，转移范围及已有保护继续验证。未新增状态 owner 或规则系统。

## 2026-10-08 补充：剩余机器自报状态与场景占位

移除另外十二份机器输入的顶层 PASS；Knowledge、Historical Adapter、Literary Suite、Prewrite 与 Pareto 摘要停止显示该值，实际校验与人工评审结论继续有效。场景种子删除无人读取的预填约束结果和 UNASSESSED 轴占位，运行结果由实际评估输出。

文学流程删除 changed:false 自我声明和无人解析的 file_ref，保留发布 SHA 绑定、实际字节校验、启动授权与章回顺序。删除两个未执行所属模块行为的重复基线测试。P6—P8 仅迁移格式变化导致的输入摘要，旧绑定和可逆字段变更进入清理账本，原稿、评审与权限不变。
