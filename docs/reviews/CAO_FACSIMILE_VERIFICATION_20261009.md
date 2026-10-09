# 曹家奏折三处摘录的原件核验

2026-10-09，已找到国立故宫博物院公开的原件影像并完成三处代理校录。原档为**故宮005664**，江宁织造郎中隋赫德奏折，雍正六年三月初二日，20.2×67厘米。三个 Source 是同一原件的三处摘录。

## 原件依据

馆方[展件清单](https://theme.npm.edu.tw/NPMdreamredchamber/page-5)“大雅可观”第9件记录具奏人、日期、尺寸和典藏号。[王亮钧〈「看得見的紅樓夢」特展概介〉](https://www.npm.gov.tw/NewChineseArtDownload.ashx?bid=5142)，《故宫文物月刊》第495期（2024年6月），图5在印刷页58–59／PDF物理页3–4，刊出原件影像并标明典藏号。[郑永昌〈人物與時代—院藏清初江寧織造曹家奏摺文獻〉](https://theme.npm.edu.tw/Academic/ChineseArtDownload.ashx?bid=10245&eid=0)，同刊，图19在印刷页82–83／PDF物理页15–16，也刊出同一原件影像。

本次依据是文章中的原件照片，而非论文转引。两篇文章刊的是同一件奏折，不增加独立见证数。原 PDF、馆方目录及 HTTP 获取记录均保留下载原字节；图像按 PDF 页与 image xref 无损取出。原档身份不再依赖来历不明录本的出版版次。

## 三处校勘

| Source | 原件对照结果 | 本次处理 |
|---|---|---|
| inventory-seal | 原件是“一併查清” | 将旧引文“一並”改为“一併” |
| pawn-tickets | 原件是“床杌舊衣裳零星等件及當票百餘張” | 将“床几”改为“床杌”，补回“衣”后的“裳” |
| family-housing | 原件是“少留房產以資養贍”，下文有“在京房屋人口酌量撥給” | 原引文汉字保留；论文节引“房屋”不用于替换原件“房產” |

局部校录按竖排先右后左、每列自上而下接续，合并分列与抬头，不加现代标点、不作繁简转换。三条正式摘录使用这份明确标注的校录原文；旧带标点摘录保存在更正审计中。

原件相邻上下文的家人数量为“壹佰拾肆口”，旧130页候选录本写成“一百四十口”。该数量未在这三个 Source／Claim 中使用；本次记录差异，不扩展历史主张。旧导入编号 CAO-ARCHIVE-286／书目保留用于追溯，286不是故宫典藏号，也不代表确认了旧录本的出版版本。

三个 Claim 保留历史可行性权限：管事讯问与封固程序、典当的现实可能、抄没后酌留或酌拨家属住房。“當票百餘張”不直接证明典当频率、时序或具体现金流；安置文字也不证明小说人物获得某处房屋。判断及全部下游快照绑定在新更正记录中。

## 可复查材料

- [逐列校勘记录](../../artifacts/migration/cao-facsimile-20261009/collation-agent-v2.json)与[固定材料绑定](../../artifacts/migration/cao-facsimile-20261009/bundle-v1.json)：原档身份、下载、原图、图像位置、局部校录及三个当前 Source 摘要。
- [载体迁移审计](../../artifacts/migration/cao-facsimile-20261009/carrier-migration.json)与[摘录更正审计](../../artifacts/migration/cao-facsimile-20261009/excerpt-corrections.json)：分别记录载体／定位变化和录文变化。新校录是本地派生资产，不沿用旧候选 PDF 的 HTTP 响应。
- [公开独立复核材料 v2](../../artifacts/reviews/source-independent-v2-20261009/README.md)：绑定12条当前代理更正／校录及协议 v2。旧协议、旧 ZIP 与旧研究写作包保持原字节。
- [第89回研究写作包 v2](../../data/writing/packages/ch89-research-v2.json)：引用新的 Source 摘要；文学范例、规划、世界输入保持原绑定。

```bash
python tools/verify_cao_facsimile.py
rcwh sources verify-all
rcwh sources gap-check
rcwh literary-inputs package data/writing/packages/ch89-research-v2.json
rcwh sources audit
```

当前32条 Source 均有可重算的 Locator v2，三条技术缺口的豁免已删除。CI 要求 `sources verify-all --require-tracked` 通过，并重算原 PDF 嵌入图像及校录派生链。

**图像识读由 Codex 以 AGENT_TEXT_REVIEW 完成。** 确定性检查验证下载、原图字节、派生关系、图像位置声明及校录摘录一致性；它不独立判断手写字识读是否正确。独立人工 Source 审查仍为 PENDING，语料人工抽查和 P9 文学盲评保留原实际状态。史料核验公开出处，无需盲评。

隔离检出结果见[本次验证报告](../../artifacts/migration/cao-facsimile-20261009/verification_report.json)。原始 Review.md、既有资产、其余29条 Source 内容、全部下游证据对象、语料输入与 ACTIVE 均按本次完整性记录保护。
