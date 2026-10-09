# 来源闭包迁移与摘录差异评审｜2026-10-09

本批 R0.3 已接收 7 组载体，当前 32 条 Source 均有本地 carrier；20 条脂批／靖藏录文已通过实际 PDF 重建和 Locator v2 摘录核验。另 12 条历史／论文摘录与载体存在未声明的整理、省略或版本待核，继续 UNVERIFIED。**R0.3 仍为 PARTIAL；source-locators 与 verify-all 继续失败。**

以上为首批结果，正式记录保持原字节。后续单独更正其中9条，再按故宫005664原件影像校录曹家三段，现为32条定位重取通过。最新依据及独立复核状态见[曹家原件核验](CAO_FACSIMILE_VERIFICATION_20261009.md)；九项旧更正见[摘录更正与影响复核](SOURCE_EXCERPT_CORRECTIONS_20261009.md)。

声明环境为 CPython 3.12.13、PyMuPDF 1.27.2.3，CI 使用同一 Python 版本。新资产和 receipt 尚需纳入 Git；当前工作树的 tracked 门禁会明确失败。来源内容通过只证明载体存在、引用及摘要一致，不能替代录文忠实度、见证或 Claim 推理审查。

## 正式记录

- [输入与载体选择](../../artifacts/migration/source-closure-20261009/inputs.json)：carrier／capture／extraction 资产引用及替代载体说明。
- [迁移计划](../../artifacts/migration/source-closure-20261009/plan.json)：全部当前 roots、迁移前 Source 摘要及预期载体。
- [执行审计](../../artifacts/migration/source-closure-20261009/audit.json)：Source 前后记录、逐条核验报告、显式跳过的 PDF LF 区间，以及完整证据语义快照。
- [12 条摘录差异](../../artifacts/migration/source-closure-20261009/excerpt-reviews.json)：原摘录、候选原文、可重取的字符范围、逐字符差异和待审事项；这些候选未被采用。
- [接收索引](../../artifacts/migration/source-closure-20261009/receipt-index.json)保存以上记录的 Asset／receipt 身份；[隔离检出验证](../../artifacts/migration/source-closure-20261009/checkout-verification.json)保存断网、CRLF 和 tracked 检查结果。

迁移前后的证据语义摘要均为 `4b9547d3a0f946315b5c23d75e152a3aa6fa4ea2a054f928ed689caa42cc2171`。Source ID、type、witness、tier、title、text／text_sha256、notes，以及 Claim、Decision、Implementation、TitleAxis 全部保持原值。改变仅限载体／采集绑定、locator、legacy_locator 和核验元数据；没有退役或删除失败 Source，也没有提升 W2 等级或改变 OPEN 约束。

## 已完成的 PDF 定位

20 条原引文均能在既有脂评汇校本 PDF 中逐字重取。跨行项使用有序 span 连接，跨度之间仅有 LF；引文自身未删空格、改标点、换字或省略论述。每条成功报告单独登记为 REVIEW_RECORD，绑定 Source 摘要及实际提取版本；运行时仍会重算。

正式抽取仅包含本批所需的 17 个物理页；完整前80章回抽取与 Corpus v1 尚未交付。旧 page／parsed_lines 保存于 legacy_locator。核对得到五处旧物理页码偏移：

| Source | 旧物理页声明 | 实际物理页 |
|---|---:|---:|
| 己卯第十八回“黛玉死” | 266 | 265 |
| 甲戌第二十六回“落叶萧萧” | 380 | 379 |
| 靖藏抄录第33条“情榜” | 1131 | 1130 |
| 靖藏抄录第92条“芸哥探庵” | 1136 | 1135 |
| 靖藏抄录第102条“狱庙相逢” | 1137 | 1136 |

## 历史载体与待审事项

| 采集组 | Source 数 | 载体与主要差异 |
|---|---:|---|
| 《大清律例》卷三十六 | 3 | 原 bibliography 对应的维基文库快照。亲属入视／待质衣粮摘录补了原文没有的句末标点；限制外人入狱摘录还去掉夹注符号，并将 `𫝊` 整理为 `傳`。 |
| 《大清律例》卷十 | 2 | 原 bibliography 对应的维基文库快照。主婚条文补句末标点；居丧嫁娶摘录合并夹注、删去中间条文，缺少显式省略与整理记录。 |
| 《光绪顺天府志》地理志四 | 1 | 原识典页面快照含显示简体与嵌入原文；现有摘录使用另一组繁体／异体表示，尚未核验转换及原版录文。 |
| 《曹家档案史料》二百八十六 | 3 | 原 ctext 地址返回安全验证页。替代130页录文本的第121物理页明确含奏折序号、标题和日期；文本为简体并使用“曹（兆页）”，出版版本与录文忠实度仍待独立核查。 |
| 《钦定大清会典则例》卷八十九 | 1 | 原 ctext 地址返回安全验证页，改接收识典同卷快照，保留原 bibliography。字形、标点与“皇贵妃／宫中女子／内监”的列举方式需要核对。 |
| 大觉寺租房契录文 | 1 | 北京市文物局原页面快照为简体。现有摘录省去了“连借缸三口”并改动标点；不能用繁简转换自动掩盖内容省略。 |
| 毛立平2013年论文 | 1 | 从中研院原地址接收46页 PDF。摘录位于第7物理页、印刷页9；现有摘录省去了姻亲关系的中间论述，并改动句末标点。 |

网页保存完整原字节，采集记录保存请求／最终 URL、时间、响应类型、可取得的 ETag／Last-Modified 和 carrier 摘要。安全验证页未作为 Source carrier 入库；两组替代件及原失败请求均有记录。论文下载保持 CA 和主机名核验，使用兼容旧服务器的 TLS 设置，设置也写入采集记录。

## 后续收口

逐条决定当前 text 属于逐字引文、经过整理的引文还是概括；核对替代载体版本与录文可信度，再记录具体转换／更正依据及下游 Claim 影响。单纯标点整理也须有可重现的记录；实质省略不能通过任意跳字或自报 VERIFIED 收口。此次批量迁移工具只接受不改变证据语义的载体／定位调整，会拒绝更改引文或见证的方案。

核验入口为 `rcwh sources verify-all` 和 `rcwh self-contained check --profile source-locators`；成功与缺口均从当前全部 roots 计算。真实更正完成前，不能将本报告改成来源闭包 PASS。

本批验收：435 项测试通过，仓库完整性与相对原 Git HEAD 的资产不可变性检查通过。隔离 Git 检出以 `core.autocrlf=true` 运行并禁用网络：asset-storage／source-content 通过，source-locators／verify-all 如实返回12条摘录失败，无存储或图关系发现项。隔离检出验证不替代当前工作区的 Git 跟踪；原工作区未执行 stage／commit。
