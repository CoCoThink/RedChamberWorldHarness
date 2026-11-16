# 人工审阅交付包（2026-11-17）

`/tmp/rcwh-human-review-handoff-20261117.zip` 是当前来源、语料和 P9 人工审阅的只读交付包。它包含来源 v4 的 16 项材料、corpus-full-v2 的 146 项分段材料和固定原始 PDF、P9 20 对盲包、空白模板及中文指南；不包含 P9 协调映射。

交付包 SHA-256：`830106d54e9b34928ff88091f9b74399455f889042946b73f635c0d7bd830201`

原始 corpus PDF：`sources/primary/hongloumeng/zhihui/v3.1416/original.pdf`，SHA-256：`37441da3cb438d1b3eab2b511aa6f1695f309192fa63bea842413ff91655c1d7`。

这只是阅读材料，不授予任何准入。收到真实意见后，保留原始 JSON 字节，按 [REVIEWER_GUIDE_ZH.md](../../../docs/runbooks/REVIEWER_GUIDE_ZH.md) 使用 `rcwh reviews register ...` 登记；来源、三个语料 lane 和 P9 必须分别登记。模型或子代理意见不能代替真人独立性声明，也不能写入这些 selection。

当前模型辅助核对保存在本目录的三个 JSON 中，统一标记 `RESEARCH_ONLY`、`human_qualification=false`、`authority_effect=NONE`、`production_admission=NOT_GRANTED`，仅用于帮助真人定位问题。
