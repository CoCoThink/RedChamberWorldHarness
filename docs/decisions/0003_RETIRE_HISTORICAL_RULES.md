# ADR 0003：退役历史规则、阶段副本与样本数量门禁

日期：2026-10-08。状态：已实施。承接 [ADR 0002](0002_RETIRE_MIGRATION_RUNTIME.md)。

## 决定

- 当前状态由 `data/project/current.json` 显式选择 owner；章回范围由 `data/project/scope.json` 声明。competition 保存章节进度，capability 选择实验，release 选择稳定基线。文学 owner 只声明顺序与边界。
- 历史迁移冻结、完成门、分支名称、任务编号、机器自报 PASS 和节点数量不决定当前资格。图、人物、物件及文学对象按身份、范围、引用闭合、上游覆盖和实际行为验证。
- 旧状态副本、无人读取的伪配置、兼容运行链、重复解盲映射和静态机器报告退出运行时。章节对齐、统计、匿名阅读包及整书候选从正式输入生成。
- 稳定正文核验实际字节；下游不能制造证据，实验不能自动晋升。OPEN 边界、已确认语义锚点、单一活跃竞争、结构宽度和人工评审约束继续执行。
- 评审与修订绑定对应候选、上游身份、正文摘要和原始意见。旧分支的未获确认裁决须经过正式导入与门禁，不能复制状态自动推进；具体历史分支快照查 Git 历史。
- 当前模型、排程、世界检查点和文学选择由版本化方案约束；初始迁移和约束一致性检查不授予采用资格。死亡方向由来源图承接，绝命诗工作约束由场景契约承接。
- 声口不能自动认人，历史适配器不能发明情节。规则来自实际 policy；清理自报字段不能改变 severity 或消除已知覆盖缺口。

操作见[搜索与写作](../runbooks/SEARCH_AND_WRITING.md)和[基础操作](../runbooks/FOUNDATION.md)。必需输入缺失、正文定位错误、上游漂移、保护覆盖不足和未经实际审阅的裁决仍会失败。

## 审计

[规则清理报告](../../artifacts/migration/handover-20261008/rules_cleanup_report.json)保存退役文件摘要与移除字段；[历史资料执行报告](../../artifacts/analysis/historical-assets-20261008/execution_report.json)保存后续版本整理、研究提取、引用修复和旧状态快照。逐版本原身份、出处及精确差异由 `data/catalog/history.json` 选择的不可变历史包保存，可用 `rcwh assets history --list` 查询。

历史记录只供追溯。当前工程、来源及人工审查状态由 `rcwh validate`、`rcwh sources audit` 和 `rcwh project acceptance` 重新计算。
