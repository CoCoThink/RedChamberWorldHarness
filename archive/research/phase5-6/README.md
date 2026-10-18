# 第五—六阶段研究过程归档（只读）

依据 ADR 0004（`docs/decisions/0004_EVIDENCE_FLOOR_SEVERITY.md`）归档，日期 2026-10-18。

这里保存旧门控设计下产生的研究过程记录：读者意见、评估报告、checkpoint、冻结清单、阻塞矩阵，以及当时把规划偏好当作硬 FAIL 的结论。它们是历史，不再参与评估、发布或测试；活数据不得引用本目录（`rcwh validate` 会拒绝）。

- `artifacts/agent_research/…`：保持原相对路径的研究产物。只有仍被活数据按精确路径、以机器可读记录绑定的文件留在原位（见 `closure-before-move.json` 的 `live` 列表；移动清单见 `moved-files.json`）。
- `data/agent_panel/`：旧模型审阅记录（含当时永久性的 FAIL/REJECT 意见）。新审阅从空 store 重新登记，可用 `severity` 与 `supersedes`。
- `retired-tests/`、`retired-tools/`：只验证这些历史记录的测试与一次性脚本（包括 325 份保护清单的检查）。原样保留以便追溯，pytest 不收集。

所有内容也保存在 git 历史中；未提交的部分只在本目录。
