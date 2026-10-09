# R0.4 资产导航与固定输入实施记录

后续更新：曹家三段已据故宫005664原件影像校录，全部32条Source通过定位重取；当前独立来源复核材料与写作包均为v2。详见[原件核验](CAO_FACSIMILE_VERIFICATION_20261009.md)。下文保留先前工程验收时的快照。

2026-10-09 实施 R0.4，Source 收口继续保持 R0.3 PARTIAL。曹家档案三条摘录的替代载体与版本问题尚未解决；本轮没有更正其录文、定位状态或证据判断。

## 导航

新增 40 份 annotation、7 个 collection，覆盖三份核心母本／保护锁、五种前八十回文学索引、两份证据治理规范、二十回剧情增厚卡、两份小说输入、七份历史／研究载体和既有文学评审。集合通过完整 Asset ID 建立成员关系；显示名与用途不改变证据角色、当前正文和采纳状态。数量是本轮整理快照，不是运行门禁。

`assets list` 支持 role／collection／chapter／tag 交集检索，`assets collections` 返回集合目录。导航 schema 与实体完整性检查纳入 `assets validate`、`rcwh validate` 和 tracked 门禁。实现与操作见[runbook](../runbooks/ASSET_DISCOVERY_AND_CORPUS_INPUTS.md)。

## 载体与版本依据

| 项目 | PDF 主输入 | EPUB 比较输入 |
|---|---|---|
| 完整 Asset ID | `asset:primary:hlm:zhihui:v3.1416:pdf` | `asset:primary:hlm:zhihui:v3.1416:epub` |
| SHA256 | `37441da3cb438d1b3eab2b511aa6f1695f309192fa63bea842413ff91655c1d7` | `ef840e3ff96b056594a1388d7accfe7065ad2a940568222e4075ecb7bc0ea755` |
| 版本依据 | 物理第 7 页明确“最终版，版本号3.1416”，署吴铭恩 2018.6.30 | `part0001.xhtml` 明确“最后修订：2016年5月31日”；OPF date 为 2014-08-04；整理说明署 2013.9.30 |
| 完整提取单元 | 1163 物理页 | 90 个 OPF spine 成员 |
| 正文回次容器 | 第 1 回起于物理第 14 页；第 80 回起于 1097 页；选择范围 14—1108 页 | `part0005.xhtml`—`part0084.xhtml` 对应第 1—80 回 |
| 外部材料 | 1—13 页前置材料，1109—1163 页附录；完整提取保留 | 前 6 个 spine 为封面、书名、版权、整理说明、目录、凡例；末 4 个为序跋、版本简介、靖藏批语、校读札记 |
| 提取限制 | 各回仍混有页眉、脂批、编辑注及异文 | 8767 处图片，其中 8725 处标记 `font_patch`；当前文字提取省略这些图片 |

EPUB 的现有路径／ID 带有 `v3.1416` 标签，但其正文与版权页不能支持两份文件为同版。保留原身份与字节，在阅读 annotation 中明示差别。PDF 文件元数据 modificationDate 为 2025 年，不能用它代替版次或出版日期；选择以整理说明为依据。

选择 PDF 为主输入，因为其整理说明明确声明 3.1416，现有二十条小说 Source 已绑定同一载体，且图片略字问题较少。EPUB 保留作为结构与文字比较材料，不能用缺字的提取结果覆盖 PDF。此选择仅确定语料施工输入，不证明每页校勘无误。

第 67 回的程甲附录异文在 PDF 物理第 916 页开始，EPUB 同样嵌于 `part0071.xhtml`；它不另算一回，也未自动采纳为 `MAIN_TEXT`。EPUB 第 21 回标题包含嵌批“当得起。”，说明简单提取标题或去空白不能完成层次分类。

## 固定输入与重建

配置为 [front80-pilot-v1.json](../../data/corpus/inputs/front80-pilot-v1.json)。完整 PDF extraction manifest 为 `asset:sha256:1c9dee98f867ea07dade7b69b2b8d3987c5046ddb51e1e377c5e306fd26ba900`，EPUB 为 `asset:sha256:deadbec02fe70993e96c25b12afcbb10eebf139f512a09eedd1eeda641f69d3b`；各自 output SHA 分别为 `b9278b790bc2fd8a7e90ec8ca86295a60105b0defe0843fc39cdc598e6826353` 和 `74b0c17d75d78bb3ca560f0732ebb83538602a0b55fdeb44aacefc51ecacce73`。既有 Source 继续绑定此前的定位配方。

确定性[输入盘点](../../artifacts/migration/corpus-inputs-20261009/input-inventory.json)登记为不可变 `REVIEW_RECORD`，其完整 ID／SHA 以输入配置中的 `inventory_report` 为准。该报告重算两份 extraction，绑定实际环境、盘点代码、完整选择配置和每回字符范围，列出 EPUB 图片与嵌回标签候选。去空白后的混合章节视图 80 回均不同；这一结果包含页眉、布局和提取差异，不代表有 80 个经校勘确认的正文异文。

输入固定已完成，Front80 Corpus v1 尚未构建。后续先在第 1、5、27、67、80 回检查开卷批语、诗词曲文、嵌批、双版本及末回边界，分类正文／批注／编辑文字／异文／附录，验收后再扩展全 80 回。

本报告与机器盘点由代理完成；不替代独立人工证据审查。CI 新增导航查询与 `corpus inputs --require-tracked`，干净检出演练也执行相同输入核对；验收结果另存[verification_report.json](../../artifacts/migration/corpus-inputs-20261009/verification_report.json)。

## 本轮验收

CPython 3.12.13 下，将待评审工作树物化到临时 Git 仓库，再以 `core.autocrlf=true` clone，在禁止 CLI socket／DNS 的环境下验收。导航查询、带 tracked 门禁的固定输入重建、存储与领域运行检查，以及工作流的实际校验 shell 步骤全部达到预期退出码；全套测试 **479 passed in 63.97s**。演练使用预装依赖，未改动当前仓库的索引与提交。

`source-content` 为 PASS；`source-locators` 保持 FAIL，确切缺口为曹家档案三条，不出现存储或图关系错误。因此完整自包含状态仍为 INCOMPLETE。当前资产快照为 233 个 Asset、305 条 origin；本轮只追加两份完整提取的输出／manifest 与一份登记盘点。

[完整性记录](../../artifacts/migration/corpus-inputs-20261009/integrity-report.json)确认原 Git 基线资产未改字节，本轮保护的 29 个文件（既有 provenance、抽取与定位代码、Review.md）摘要不变。全部 Source 中 29 条定位通过，3 条保留待核。正文层次 pilot 是后续验收事项。
