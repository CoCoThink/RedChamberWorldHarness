# 来源摘录更正与影响复核｜2026-10-09

本记录解释九条历史／论文 Source 的摘录更正依据与 Claim 影响。曹家三处的后续校录另见[曹家原件核验](CAO_FACSIMILE_VERIFICATION_20261009.md)。当前定位与独立复核状态分别用 `rcwh sources verify-all`、`rcwh sources audit` 查询。

这是 Codex 的 **AGENT_TEXT_REVIEW**：本地录文比对与现有主张复核，没有声称独立人工评审或馆藏原件鉴定。载体重取、摘录更正依据和证据解释分别记录；数字录文可以重建，不代表现代标点、原始版本或历史真实性获得自动认证。

## 更正内容

| Source 组 | 数量 | 采用的处理与推理边界 |
|---|---:|---|
| 《大清律例》卷三十六 | 3 | 保留夹注界符与 `𫝊` 等载体字形，撤回补写标点。亲属入视条扩展至完整条例，恢复盗犯妻子家口禁入的例外。不能据此推定任意囚犯或旧仆当然享有探视权。 |
| 《大清律例》卷十 | 2 | 主婚条撤回补写标点；居丧嫁娶条恢复完整连续录文，包括 `〈主婚〉`、`〈除承重孫外〉` 和中间条款。只支持丧制约束婚嫁，不锁定小说婚期。 |
| 《光绪顺天府志》 | 1 | 使用固定页面显示简体，撤回未声明的繁体整理；保持通州州治具体监狱实例的范围。 |
| 《钦定大清会典则例》卷八十九 | 1 | 收窄为同一皇贵妃丧仪段内的完整姻戚成服句。它直接支持现有主张；前句现代列举标点不承担推理，不声称替代数字版本与 ctext 逐字同版。 |
| 大觉寺租契 | 1 | 恢复完整契约正文及“连借缸三口”、退租、维修、实收租价等约定。约定年租五十千与现收三十千不混同；仍为昌平铺面的类比材料。 |
| 毛立平2013年论文 | 1 | 恢复被省去的姻亲关系中间论述，保留 PDF 行换行和真实摘录边界。研究对象为南部县下层家庭；两个 Claim 继续使用 SECONDARY／INFERENCE。 |

9 项更正覆盖 11 个 Source→Claim 复核项，其中“受控入视”同一 Claim 分别复核两个来源。每项保存所有相关 Claim、Decision、Implementation、TitleAxis 的完整快照和摘要。原记录中的 Source ID、type、witness、tier、bibliography、notes，以及全部下游对象与权限均未修改；受保护快照摘要为 `ce453ca06d0cb7ea34d311a81def828a50ecd16dbb3296e1cce37175322b9d86`。

## 可追溯记录

- [更正计划](../../artifacts/migration/source-excerpt-corrections-20261009/plan.json)绑定更正前 Source 摘要、实际 Locator v2、逐项理由、范围限制和当前 Claim 摘要。
- [执行审计](../../artifacts/migration/source-excerpt-corrections-20261009/audit.json)保存全部 Source 前后版本、旧摘录与定位、逐项影响审查及实际验证报告。
- [接收索引](../../artifacts/migration/source-excerpt-corrections-20261009/receipt-index.json)保存正式记录的 Asset／receipt 身份；逐项 review 和 locator report 分别接收为不可变 REVIEW_RECORD。
- [曹家档案待核记录](../../artifacts/migration/source-excerpt-corrections-20261009/cao-carrier-review.json)记录替代件版本缺口、故宫转引线索及未采用的理由。
- [离线检出验证](../../artifacts/migration/source-excerpt-corrections-20261009/checkout-verification.json)记录隔离 Git、CRLF、断网及 tracked 检查结果。
- [当前工作区验收](../../artifacts/migration/source-excerpt-corrections-20261009/validation.json)记录真实 root 集合摘要、3 项缺口、资产不可变性及未跟踪输入。

首批迁移的 [12 条差异记录](../../artifacts/migration/source-closure-20261009/excerpt-reviews.json)和[审计](../../artifacts/migration/source-closure-20261009/audit.json)保留原字节，作为本批的前序记录；没有改写为“当时已经通过”。

## 运行约束

更正工具与仅调整载体／定位的迁移工具分开。新 text 只能由固定提取中的连续原文产生；多 span 仅允许显式跳过 PDF LF，不允许隐藏删字、繁简替换或任意连接文本。原摘录、更正前 Source 摘要、真实范围及下游快照保存在 review；Source 的 `excerpt_revision` 与新定位报告分别绑定它们。

运行时会检查 review 资产、摘录及当前影响集合。即使有人另存一个可通过的定位报告，未经对应 review 记录的文本变化仍失败。下游 Claim、Decision、Implementation、TitleAxis 的内容或关联范围变化会使影响审查失效；仅该审查过期时，可以在原摘录不变的情况下提交新的完整审查，生成 `REFRESH_IMPACT_REVIEW` 版本并保留旧链。审查结论的语义正确性仍须评审，程序只检查范围、内容和绑定的新鲜度。

原始 EPUB 曾被阅读器改写 `META-INF/calibre_bookmarks.txt`；正文及其余全部条目相同。当前文件与新书签已保存在 `.rcwh-cache/carrier-byte-investigation/`，正式 carrier 从 Git HEAD 恢复为登记摘要。后续阅读使用副本，以免阅读位置再次改写固定资产。

独立证据审查使用[语料及评审输入 runbook](../runbooks/CORPUS_AND_REVIEW_INPUTS.md)中的公开复核流程；代理更正记录不能替代独立意见。过去的测试与检出结果保存在上述审计文件中。
