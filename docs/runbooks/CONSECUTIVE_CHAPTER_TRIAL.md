# 连续三回研究试验

研究范围为 85–87 回。`data/evaluation/pilot85_87/drafts/` 已有九份约 700–800 字的研究短稿；它们用于先比较场景与跨回行为，尚未完成整部章回的文学验收。试验不改 production 的 86/89/92/97 队列或稳定正文。

求医路线让宝玉留在大夫门上，并由紫鹃决定继续候另一位大夫；还书路线让黛玉主动归还借书，紫鹃改为直接召回宝玉，传话被门锁和行踪不明耽搁。两者在 87 回分别延伸为追问照料路线与追索错还的旧书。86 回死亡、冷药、未成稿及两个字面锚共同保留。这些具体行动是复原选择，不是新增佚稿证据。

第三组是直接写作示例。其作者已经看过设施和其他候选，明确标为 **CONTAMINATED_INTERNAL_EXAMPLE**；不能用它估计 Harness 改善效果。成本中没有记录到的 tokens、调用和用时保持 null。

```bash
rcwh pilot summary
rcwh pilot export /tmp/chapter-reading-round-1
rcwh pilot reviews /tmp/chapter-reading-round-1
rcwh pilot prepare-author --route medical --workflow DIRECT_WRITING --output /tmp/direct-task.json
rcwh pilot run-author --route medical --workflow DIRECT_WRITING --command 'python /path/to/author.py' --output /tmp/direct-run.json
```

新作者程序读 stdin、返回三回正文和真实 producer/usage。直接、旧流程、改进流程共享冻结约束、路线和预算；直接组没有 workflow_support，旧组获得原词串提示，新组获得事件、出口与知情编排。先在隔离作者上下文冻结直接组，再做其他组；不得回流评价。统一调用预算目前是一次程序调用、零修订轮次、每回 500–1600 字；provider token 预算未设定，正式比较须先冻结作者设置与该预算。这是小样试验入口，不是已完成的模型运行或改进效果结论。

导出的 `public/` 只含随机 token 的三回整段正文及 packet。`coordinator/` 保存映射与作者，packet 绑定映射承诺摘要；只把 public 交给读者，避免完整仓库访问造成解盲。每轮新 token，不复用旧公开编号。public 中的 reading-template.json 是空白 TEMPLATE，不是提交的意见。

## 排序记录

每份阅读记录至少包含 report_kind=REVIEW_OPINION、id、packet_sha256、context_sha256、reviewer、ranking、recommendation、observations 和 raw_review。reviewer 是 INDEPENDENT_HUMAN，含 principal_id/source_id、independent_of_authors、mapping_unseen_during_review。ranking 是有序 token 分组，例如 `[["read-…"],["read-…","read-…"]]`，组内平局；须恰好覆盖全部候选。recommendation 可为 CONTINUE 或 NEITHER。

observations 按 token 写 scene_cohesion、character_voice、life_detail、engineering_feel，各有 reason 和原文 spans。raw_review 是原始 JSON 的 `{path,sha256}`，原件投影只去掉 raw_review 和 authority_effect。外层绑定数组传给 `pilot reviews --bindings bindings.json`；路径相对导出目录。需两位不同人、不同来源、与作者不同源；保留分歧、平局及全部淘汰。输出没有自动赢家。

目前作者意图的出口/入口链可核验；它不证明正文实现了该状态。实际语义复核、两份独立整段阅读、一轮实质修订与重评仍待完成。缺少这些时保持 PENDING，不能扩大为连续章回生产通过。

## 声口、文体与语料

`diagnostics characters` 合并29名世界人物、18份既有声口、6份知情档案和12份补充编辑卡；缺少情境范例时弃判。`diagnostics style TEXT --poetry POEM…` 单列回目字数/结构、叙述口吻分布、对白称谓和诗词行长；语义对仗、称谓关系、声口和格律仍交判读，不用词频给“正宗”分。

`diagnostics corpus-focus` 核对261个原文绑定样本，涵盖80回、所有层、162个待定见证和对齐状态分层。另有五处内部原页观察；不是人工独立审计。`corpus query … --purpose FORMAL_EXEMPLAR` 只在相应语料审计通过后交付正文范例。研究检索保留 RESEARCH 标记，不升来源权威。
