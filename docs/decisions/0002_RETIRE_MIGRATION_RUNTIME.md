# ADR 0002：裁剪历史副本并退役迁移运行链

日期：2026-10-08。状态：已实施。

## 删除范围

- 根目录展开交接包及 ZIP，Python 与 pytest 缓存。
- 首次 catalog 中无当前证据、发布清单、接收文档或 P0 映射依赖的 297 份历史正文。
- `registry.py`、`coverage.py`、`completion.py` 及其 CLI、CI 检查、数据、schema 和阶段测试。
- 无消费者且与实际输出失配的 EvaluatorResult schema。
- 九份 FULL_MIGRATION 阶段文档。原始已提交文件可在 Git 基线 `f9ff4c23a47b0bf5981b9b3b93b9d964b261f2f7` 中查阅。
- 过时远端分支数量与 Issue 关闭快照。旧快照在 Git 历史中保留；当前评审导入约束见 [ADR 0003](0003_RETIRE_HISTORICAL_RULES.md)。

## 引用替换

世界、物件、重构、文学、预写作与实施对齐数据直接绑定资产 ID，不再通过文档 ID、旧包路径或 M1—M8 层叠覆盖解析。三类领域 trace 核验实际字节，不再输出从旧注册表推断的权威和 FULL 覆盖声明。预写作读取正式 release owner；文学生产验收读取实际竞争与隔离规则，不读取 M8 历史 PASS。

一次性导入器、专属旧格式解码器和旧命令别名均已退役。

## 审计与限制

删除摘要、范围和理由见 `artifacts/migration/handover-20261008/cleanup_report.json`；被排除材料的出处见同目录 `import_report.json` 的 `excluded_assets`。这些记录不表示正文仍在库中，也不承担 Source 载体职责。

本次 catalog 裁剪发生在首版提交前。已经提交的不可变资产仍受跨版本校验保护，不能用本次操作作为静默删除正式载体的先例。

证据等级、OPEN 边界、稳定发布原件、候选、评审和采用约束继续保留。当前状态用 `rcwh project acceptance` 查询。

后续规则与阶段状态清理见 [ADR 0003](0003_RETIRE_HISTORICAL_RULES.md)。
