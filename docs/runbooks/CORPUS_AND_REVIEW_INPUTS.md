# 语料候选、写作输入与独立评审

史料核验和语料抽查均公开原件、出处、版本及定位信息。曹家三个 Source 是同一份奏折的三处摘录，按通常的版本核验与史料校勘处理；九条代理摘录更正另核对更正依据及 Claim 影响。`rcwh sources audit` 汇总独立证据复核，要求与实际 Source 版本绑定，不要求匿名或 A/B 评分。当前工程检查、待交评审和生产准入由 `rcwh project acceptance` 实时计算。

本 runbook 中的盲评仅指 P9 小说原稿／修订稿比较。语料审查者应看到原件和完整分类信息，以核对正文边界。

## 公开来源复核

当前材料为 `artifacts/reviews/source-independent-v2-20261009/`，绑定 `data/provenance/audits/protocol-v2.json` 的12条Source。曹家三段已按故宫005664原件影像完成代理校录；图像识读判断与校录文本重取分开记录，详见[原件核验](../reviews/CAO_FACSIMILE_VERIFICATION_20261009.md)。

独立复核者填写该目录的 `human-review-template.json`，如实核对原件身份、摘录、见证／tier及Claim影响。原始JSON接收为REVIEW_RECORD；结构化评审增加 `schema_version: 1`、唯一 `id`、`raw_review: {asset_ref, sha256}` 和 `authority_effect: NONE`，按 `schemas/source_audit_review.schema.json` 存入 `data/provenance/audits/reviews/`。在 `data/provenance/audits/selection.json` 的reviews中通过路径和完整摘要选择。原始意见与结构化字段必须一致；未取得真实提交前保持空列表。旧v1材料保留，不回填到v2协议。

```bash
python tools/verify_cao_facsimile.py
rcwh sources verify-all
rcwh sources audit
```

正式环境使用 CPython 3.12.13 和 `requirements/extraction.lock.json` 指定的依赖。当前已经构建两个不可变数据集：

- `corpus:front80:pilot:v1`：第 1、5、27、67、80 回及靖藏附录。
- `corpus:front80:v1-candidate`：前80回及汇校本全部附录；分类仍等待人工验收。

PDF 是主输入，EPUB 是独立比较载体，二者同版关系未确立。字体、颜色和字号规则来自 PDF 物理页 6、7，配置位于 `data/corpus/builds/`。文字、换行和原件的 Unicode 字符范围逐字保留；批语分开保存，未知见证保持 UNKNOWN。第67回另一录文进入 VARIANT，附录有独立 section。章节文件是 MAIN_TEXT 阅读视图，正文事实源为 segments。

```bash
rcwh corpus verify corpus:front80:v1-candidate --rebuild --require-tracked
rcwh corpus query corpus:front80:v1-candidate --chapter 27 --keyword 红玉 --limit 2
rcwh corpus query corpus:front80:v1-candidate --kind ZHIPI --chapter 27
rcwh corpus show corpus:front80:v1-candidate hlm80:chapter:27:p00001
python tools/verify_corpus_candidates.py
```

`verify` 的 PASS 表示存储和确定性重建通过；`human_acceptance.status` 单独表达人工层次审查。当前为 PENDING。两个新进程独立重建所有规范产物，比较逐文件摘要，并禁止网络／DNS；抽取器和构建器不使用文本缓存。新的规则、文字或切分必须使用新 dataset ID 和新输出目录，现有产物不能覆盖。`corrections.jsonl` 当前只有范围头，表示明确未应用任何文字校订；修改该文件也会导致重建失败。

人工语料审查使用 `data/corpus/audit-protocols/` 中的固定协议和 `data/corpus/audits/` 中的选择记录。pilot 有 13 个样本，完整候选有 91 个样本，覆盖每回正文和所有实际文本层。阅读材料、原件页图及空白回填表位于 `artifacts/reviews/corpus-candidate-20261009/`。审查者必须独立于构建者，逐项核对分类、定位及上下文，并确认正文边界。未知见证和未对齐项必须明确承认，不能填入猜测。

填写 `human-review-template.json`，保留原始 JSON 字节，使用 `assets ingest --kind REVIEW_RECORD` 接收；在结构化 review 中增加 `schema_version: 1`、唯一 `id`、`raw_review: {asset_ref, sha256}` 和 `authority_effect: NONE`，存入 `data/corpus/reviews/`。选择记录通过 `{path, sha256}` 引用它。审查字段必须与原始 JSON 一致。空值、否定项、缺样本、旧版本或无原始提交均不形成通过记录；发现问题先保留原始意见，再修订语料为新版本。独立性依据是评审者的原始声明，程序不证明评审者身份。

## 固定范例与写作包

```bash
rcwh literary-inputs exemplars data/writing/exemplars/ch89-research-v1.json
rcwh literary-inputs package data/writing/packages/ch89-research-v3.json --require-tracked
rcwh literary-inputs package data/writing/packages/ch89-research-v3.json --production --require-tracked
rcwh literary-inputs index-map corpus:front80:v1-candidate --output artifacts/new-index-map.json
rcwh literary-inputs dataset-map corpus:front80:pilot:v1 corpus:front80:v1-candidate --output artifacts/new-version-map.json
```

研究包固定 dataset／manifest、MAIN_TEXT segment／文字摘要、选择理由、Source 整条记录、核心母本资产、六份世界输入及选定规划版本。改变任一输入使对应绑定失效。正文范例拒绝混入 ZHIPI、EDITORIAL 或 VARIANT。包里的文学理由仍属研究解释。生产准入另检查完整世界／当前规划输入、来源闭包、语料人工审查和真实 P9 提交；当前应返回 FAIL。

五份旧 Markdown 索引的 88 条表格项已保存原始字符范围和逐条映射。只有确切引文出现才记录文字命中；87 条主题性或无确切引文的项目仍未解析。命中不证明研究解释成立。pilot 到完整候选的映射使用同一原件的字符范围交叠，显式区分一对一、拆分、合并、多对多和无对应；不根据相同段号推断同一内容。

## P9 配对盲评

`data/evaluation/p9_protocol.json` 固定当前 P8 实验、问题、维度和至少两位独立评审者。`artifacts/reviews/p9-preparation-20261009/blind-pairs.zip` 含20对匿名 A/B 文本，原稿／修订稿位置各半；所有输入摘要均绑定，ZIP 可确定性重建。`coordinator-mapping.json` 仅供协调者，不能发给评审者。只提供盲包和 `human-review-template.json`；评分为1至5，engineering_feel 越高表示工程痕迹越明显，其余维度越高表示越好。偏好可填 A、B、TIE 或 NEITHER。

```bash
rcwh paired-review summary
rcwh paired-review packet --protocol data/evaluation/p9_protocol.json --output artifacts/new-blind-pairs.zip --mapping artifacts/new-coordinator-mapping.json
```

独立评审者填原始 JSON，并声明未在评审中看过映射。接收原始 JSON 为 REVIEW_RECORD 后，结构化记录增加 `schema_version: 1`、唯一 `id`、`raw_review` 和 `authority_effect: NONE`，存入 `data/evaluation/paired_reviews/`；在 `paired_selection.json` 中用路径和完整摘要选择。评分、理由、身份声明及受评输入必须与原始提交一致。不同原稿、遗漏／重复 pair、重复评审者、作者自评或无原件均拒绝。

当前 selection 的 reviews 是空数组，状态为 PENDING。程序只计算提交完整性和配对偏好信号，不产生自动文学通过、胜者、路线淘汰或 ACTIVE 变更。真实意见进入后还需依现有决策、竞争和采用流程处置；现有 P9 gate 保持待评。

## 否定意见与实时验收

来源和语料 review 的核对结论可填 true／false。有效原始否定意见同样接收、登记并加入选择；不得为了通过而将它改成 true 或漏选。任何选中的否定结论使对应审查返回 FAIL，并列出评审 ID、对象、失败字段和原始说明。达到评审人数或另有肯定意见不能覆盖已选拒绝。输入或方案修订须另建版本，原意见保留用于审计。独立性声明继续必须为 true，空值／缺项／摘要不符仍属无效提交。

```bash
rcwh project acceptance
rcwh project acceptance --require-tracked --require-complete
```

首条用于查看当前声明输入的实际验收；正常待交时返回0且 status 为 PENDING，真实拒绝或工程错误返回1。严格命令只在全部声明准入通过时返回0，待交和拒绝均返回1。报告的工程结果、人工审查和生产阻塞分别列出；它不裁决候选文学质量、不授予采用权限，也不证明完整设计或全书已完成。

选择记录属于可更新的当前 owner。加入真实 review 后，先保存原始资产与结构化 review 的绑定，再更新对应 selection；若该 selection 已列于 `data/project/closure_roots.json` 的 records，也须把其 sha256 更新为 selection 的实际完整字节摘要，否则严格闭包会正确报告旧绑定失效。所有新文件一并纳入 Git，再运行严格验收。协议、语料、Source或候选发生实质变化时，应新建相应版本并重新取得匹配版本的意见，不把旧提交改成新输入的认可。
