# 资产导航与固定语料输入

在 CPython 3.12.13、锁定的 PyMuPDF 1.27.2.3 环境下执行。安装与抽取规则见[来源定位](SOURCE_LOCATORS.md)。

## 查找既有材料

```bash
rcwh assets collections
rcwh assets list --role MASTER_DRAFT --collection collection:core:master-drafts
rcwh assets list --collection collection:front80:literary-exemplars --chapter 27
rcwh assets list --role CHAPTER_CARD --chapter 92
rcwh assets list --role HISTORICAL_RESEARCH
rcwh assets list --tag comparison-input
```

多个条件取交集。输出保留完整 Asset ID、SHA、实际路径、显示标题、版本、用途、覆盖回次与集合。回次表示材料覆盖范围；前八十回综合索引可能覆盖全部 80 回，具体引用仍须定位段落。未知集合、非法回次和失效实体返回非零。

`data/catalog/annotations/` 保存可编辑的阅读元数据，`collections/` 保存显式完整 Asset ID 的集合成员。分类字段遵守独立 schema；重复 ID、未知资产、重复成员、未知角色或擅自添加权威字段都使存储验证失败。没有显式 annotation 时，已分类 receipt 的 role 仅作为发现提示；显式 annotation 可以修正提示。标题和文件名不参与身份解析。

用途枚举为 `MASTER_DRAFT`、`GOVERNANCE`、`FRONT80_INDEX`、`CHAPTER_CARD`、`HISTORICAL_RESEARCH`、`LITERARY_REVIEW`。用途与集合的 `authority_effect` 恒为 `NONE`；正文采纳、证据角色、来源定位、独立评审和保护锁继续由各自对象判断。编辑导航不会改写原始资产或 Source／Claim／Decision。

## 验证前八十回输入

```bash
rcwh corpus inputs data/corpus/inputs/front80-pilot-v1.json
rcwh corpus inputs data/corpus/inputs/front80-pilot-v1.json --require-tracked
```

配置固定 PDF 主输入、EPUB 比较输入、各自载体和完整抽取 manifest 的 ID／SHA、80 回覆盖、版本依据所在单元、PDF 物理页范围，以及 pilot 回次 1、5、27、67、80。验证重新抽取两份原件，检查配方、解释器、依赖锁和代码，再重算盘点并逐字节比对已登记的不可变报告。输入、范围、选择理由、环境或盘点算法变化使旧报告失效。`--require-tracked` 另检查资产、导航、输入配置、schema、抽取及盘点代码和依赖锁的 Git 跟踪。

返回 `PASS` 的范围为固定输入选择与抽取重建；输出仍明确 `corpus_status=NOT_BUILT`、`edition_equivalence=NOT_ESTABLISHED`。章节切片保留页眉、批注、编辑文字及第 67 回异文，尚未得到可供文学统计的 `MAIN_TEXT`。两载体的比较视图只删除 Unicode 空白，不转简繁、不补图片文字、不拼接版本。视图差异也可能来自页眉、布局和提取形式，不能直接当作校勘异文数量。

盘点保存 PDF 元数据与版本自述、逐回字符范围与摘要、范围外前置材料／附录、EPUB OPF 元数据和 spine 顺序、全部图片的成员 SHA、原始字符位置、DOM 路径与 alt。图片 alt 只用于指出缺字风险，当前原始提取文字保持不变。重复回次标签仅作为内嵌异文候选，需在 pilot 中判断。

## 更换输入或重算盘点

先接收新原件并完成新的完整 extraction，然后以新配置声明其身份与用途。新建盘点文件，审查选择依据，登记新报告后绑定新配置：

```bash
rcwh corpus input-inventory data/corpus/inputs/NEW.json --output /tmp/NEW-inventory.json
rcwh assets ingest /tmp/NEW-inventory.json --origin CORPUS_INPUT_REVIEW --kind REVIEW_RECORD
rcwh corpus inputs data/corpus/inputs/NEW.json
```

新配置按 `corpus_inputs.schema.json` 编写；盘点生成阶段 `inventory_report` 可以为 `null`，验证阶段必须绑定接收返回的完整 Asset ID／SHA。输出使用排他创建，拒绝覆盖已有文件。报告记录确定性盘点和选择依据，不构成独立人工校勘或证据审查。已登记报告保留原字节，发生修订则接收新版本。

直接用阅读器打开已登记 EPUB 可能写入书签并破坏原件 SHA；阅读或人工复核应使用副本。此前实际发生过该情况，恢复记录见[摘录更正复核](../reviews/SOURCE_EXCERPT_CORRECTIONS_20261009.md)。

此处描述 R0.4 输入核对的范围，不代表后续数据集状态。R1 已登记 pilot 和完整前80候选，正文及批注已分层；当前人工验收仍待评。使用 corpus verify 查看候选的存储／重建及 human_acceptance，见[语料与评审 runbook](CORPUS_AND_REVIEW_INPUTS.md)。
