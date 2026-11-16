# 真人审阅交接包（2026-11-17）

完整只读包：`/tmp/rcwh-human-review-handoff-complete-20261117.zip`

SHA-256：`b5e612b61371738d83fe278d66e879e6ff641d58765916e608e574e6edb8a090`

该包覆盖当前所有尚未完成的人工通道：

- 当前 `protocol-v4` 的16项来源独立审核；
- `corpus:front80:pilot:v1` 的13项审核；
- `corpus:front80:v1-candidate` 的91项审核；
- `corpus:front80:v2-candidate` 的146项独立审核；
- P9 的20对盲评，至少两位独立评审者；
- 第89回 `production-v6` 输入包及准入工作单。

包内包含每条通道的协议、选择快照、manifest、原始材料、阶段文件和空白模板；P9 协调映射明确不在包内。包根目录 `MANIFEST.json` 列出78个文件的字节数和摘要。打包前已验证三个语料版本的模板绑定、v2 的146项计划、P9 的20对范围及第89回 v6 包路径。

这是研究环境的只读交接材料，不是人工意见，也不授予生产准入。模型或子代理报告仍保留在本目录，统一标记 `RESEARCH_ONLY`、`human_qualification=false`、`authority_effect=NONE`、`production_admission=NOT_GRANTED`，不写入任何当前 selection。独立真人完成意见后，按 [独立读者指南](../../../docs/runbooks/REVIEWER_GUIDE_ZH.md) 保留原始 JSON，并用 `rcwh reviews register` 登记到对应通道；登记后重新运行 `rcwh project acceptance --require-tracked`。

当前工程状态和人工缺口以命令实时结果为准。交接包不能替代来源、语料、P9 的独立真人判断，也不能替代第89回的协调准入决定。
