# 确定性抽取与来源定位

R0.2 已实现 PDF、EPUB、HTML 和 UTF-8 文本抽取，以及 Locator v2 的实际摘录核验。前80章回数据集、文学标注、历史载体采集和旧定位批量对齐继续按后续批次完成。

## 声明环境

```bash
python -m pip install -e '.[dev]'
```

PDF 抽取固定使用 `PyMuPDF==1.27.2.3`；规则及依赖声明位于 `requirements/extraction.lock.json`。manifest 记录实际 Python 实现／完整版本、抽取器版本、代码摘要、依赖锁摘要和配置。重建要求与记录的环境和代码一致；环境不同会报告失效，应使用对应环境验证或建立新的 extraction，不能覆盖旧版本。

本次正式来源抽取使用 **CPython 3.12.13**，CI 固定到同一版本。可用 `uv venv --python 3.12.13 .venv` 建立环境，再激活并安装上述依赖。本次工作环境位于 `.rcwh-cache/extraction-env/`；其他 Python 版本可以构建新配方，但不能替代既有配方的重建环境。

原字符与 CRLF／LF 保留；不自动进行 Unicode 归一化、繁简转换、去标点、删空白或 OCR。HTML／EPUB 解码实体、将 `<br>` 转为 LF，跳过 head、script、style、template；每段保留 DOM 路径及原始字符范围。该抽取层不判断哪段是正文或脂批，也不把网页导航自动解释为正文。

## 构建与查看抽取

```bash
rcwh corpus extract asset:primary:hlm:zhihui:v3.1416:pdf --pdf-pages 400
rcwh corpus extract asset:primary:hlm:zhihui:v3.1416:epub
```

`--format PDF|EPUB|HTML|TEXT` 可显式指定格式，默认从登记的 media type 推断。PDF 页码是从 1 开始的物理页，必须升序且不重复；不指定页码时抽取全部页。EPUB 按 OPF spine 顺序读取本地 item，不访问外部地址。

输出包括 `manifest_ref` 及 manifest 内容。正式 manifest 和 `units.jsonl` 位于 `corpus/extractions/<recipe-digest>/`，两份文件登记为 `CORPUS_DERIVATIVE`，记录 origin 与 `derived_from`。相同输入、环境和配方重复执行返回同一版本。新配方建立新 manifest；相同字节的输出沿用已有实体。

```text
rcwh corpus show <manifest-asset-id> --unit pdf:page:400
rcwh corpus verify <manifest-asset-id>
rcwh corpus verify <manifest-asset-id> --require-tracked
```

TEXT／HTML 的单位名分别为 `text:1`、`html:1`；EPUB 使用 `epub:<item-href>`，例如 `epub:OEBPS/Text/part0008.xhtml`。每单位保存原文、文本摘要、输入资产引用和覆盖全文的节点映射。

验证从本地 carrier 实际重建并逐字节比较，检查配方身份、输入／输出摘要、派生关系、单元次序、节点范围及工具失效。即使同时改写 JSON 内容和 catalog 摘要，结果与原件重建不一致仍失败。抽取事务中断时使用 `rcwh assets recover` 恢复；读取未完成目录会失败。

## 提议定位，不自动修改 Source

```bash
rcwh sources locate src:gengchen:ch27:xiaohong-great-help \
  --extraction <manifest-asset-id> --unit pdf:page:400
```

该命令在指定抽取中寻找现有 `Source.text` 的逐字匹配。无匹配返回 `EXCERPT_NOT_FOUND`；多处匹配返回 `AMBIGUOUS_LOCATOR` 及候选位置。仅唯一匹配才返回 Locator v2 和核验报告。生成建议不会修改 Source、Claim、Decision 或 witness。

PDF 引文跨物理排版换行时，可加 `--allow-line-break-spans`。该选项仅把 LF 间断表示为多个有序 span；空格、标点、字形和其他内容都不能跳过，默认查找仍要求连续匹配。提交前复核跨度之间确实仅有 LF；迁移审计记录每个跳过区间。

将核对后的定位录入 Source 时，保留原页码／行号为单独的 `legacy_locator` 字段；Source 的 carrier、见证、tier、引文和下游证据关系须分别复核。PDF Source 不能借 EPUB 查找成功冒充 PDF 定位通过。

Locator v2 最少包含：

```json
{
  "schema_version": 2,
  "kind": "PDF_TEXT_SPANS",
  "extraction_ref": "asset:sha256:<manifest-sha256>",
  "output_sha256": "<units-jsonl-sha256>",
  "spans": [{"unit_ref": "pdf:page:400", "start": 0, "end": 10}],
  "joiner": "",
  "raw_text_sha256": "<excerpt-sha256>"
}
```

示例中的摘要和范围是占位值，实际值从建议／抽取中取得。范围按 Unicode code point 计数，零基、左闭右开；不能使用 UTF-8 字节偏移。多段摘引须按原文单元和字符位置排序，不得重叠；显式连接符仅允许空串、LF 或已支持的省略号形式。首期不支持隐式校订和自由文本替换。

## 重算核验与报告绑定

```text
rcwh sources verify <source-id>
rcwh sources verify <source-id> --report-output /path/to/new-report.json
rcwh sources verify-all
rcwh sources verify-all --require-tracked
rcwh self-contained check --profile source-locators
```

`verify` 返回 carrier 和 locator 核验；可将实际定位报告写入新文件，拒绝覆盖。`verify-all` 从全部当前 Source roots 计算 root 集合摘要，报告缺 carrier、未验证／失效 locator、图关系及存储发现项。空 roots 失败。`source-content` 继续检查载体与声明摘要，不证明摘录出现在原件；`source-locators` 与统一入口使用同一摘录验证逻辑。

核验报告绑定 Source 内容摘要、Locator 摘要、抽取输入／输出、工具及校验器代码摘要。Source 的记录摘要排除 `locator_verification`，避免报告引用自身。声明字段 `UNVERIFIED / STALE / VERIFIED` 不能替代实际重取；界面显示的核验状态来自本次计算。

如需保存并绑定报告，先将报告作为资产接收，再在 `locator_verification` 登记 `report_ref`、`report_sha256` 和 `source_record_sha256`。声明 VERIFIED 必须具备这些字段；运行时仍重新验证，并要求存储报告与当前结果完整一致。见证、引文、定位、输入、工具或报告发生变化时失败，不能通过修改 PASS 标志绕过。

新接收网页和论文同时绑定 `carrier_capture`，指向已登记的 HTTP 采集记录；记录请求／最终 URL、获取时间、响应类型及可取得的 ETag／Last-Modified，并绑定 carrier ID／SHA。来源检查核对采集记录、载体关系及实际摘要；安全验证页不能当作原文。

批量迁移工具 `tools/migrate_source_closure.py --plan PLAN.json` 默认只检查与提议；加 `--apply --audit-output artifacts/migration/NEW-AUDIT.json` 后注册成功报告，事务写入 Source 和审计。计划必须覆盖全部当前 roots，匹配原记录摘要；更改 witness、tier、引文或下游证据关系会被拒绝。未匹配项仅接收载体，继续 UNVERIFIED。迁移不接受任意跳字或文本替换；当前待复核项见[来源迁移评审](../reviews/SOURCE_CLOSURE_20261009.md)。

`--require-tracked` 同时检查 Asset、当前 Source 文件、使用中的抽取配方和 schema／依赖锁。新输出和元数据需审查后纳入 Git；命令不自动 stage 或 commit。提取成功也不等于 Corpus v1 完成或证据解释已通过。

## 单独更正摘录与复核影响

`tools/correct_source_excerpts.py` 用于已有引文确有整理／省略问题的单独更正，不改变 Source ID、type、witness、tier、载体绑定或下游对象。更正前完整记录保存在不可变 review；新 Source 用 `excerpt_revision` 绑定 review 及前序记录摘要，定位报告绑定新版本。

按 `schemas/source_excerpt_correction_plan.schema.json` 准备计划：指定 reviewer 的真实类别与名称；逐项提供 `source_id`、`before_sha256`、实际 Locator v2、`rationale`、`limitations` 和每个受影响 Claim 的 `claim_id`／`claim_sha256`／保留理由。Claim 摘要使用 `canonical_bytes` 的 SHA-256。遗漏、重复或摘要过期的 Claim 审查会被拒绝。代理审查填写 `AGENT_TEXT_REVIEW`，不能冒充独立人工意见。

```bash
python tools/correct_source_excerpts.py --plan reviewed-plan.json
python tools/correct_source_excerpts.py --plan reviewed-plan.json --apply \
  --audit-output artifacts/migration/NEW-CORRECTION/audit.json
```

第一条只提议；第二条重建提议、分别接收更正 review 和实际 locator report，再事务写入 Source 与新审计。新 text 从同一提取单位的连续 span 取得，多段仅允许跳过 PDF LF；隐式删字、任意连接、省略号拼接及自由字形替换均拒绝。要改变载体或见证，应另走相应迁移／证据审查，不能混进摘录更正。

Source 的新摘录必须与 review 的 `after_excerpt` 一致；影响审查绑定所有相关 Claim、Decision、Implementation、TitleAxis 的当前记录及集合。文本变化或影响集合过期会使 `source-content`／`source-locators` 整体失败，即使底层 locator 仍能逐字重取。仅影响审查失效时，可使用相同摘录和定位、更新后的 Source／Claim 摘要及新的审查理由重新提交；工具生成 `REFRESH_IMPACT_REVIEW` 版本，保留此前 review。有效摘录的无变更重提仍被拒绝。

`--require-tracked` 还检查更正 review schema 和影响审查所用的 provenance 文件。实际操作示例、版本限制与当前缺口见[2026-10-09更正记录](../reviews/SOURCE_EXCERPT_CORRECTIONS_20261009.md)。原始 EPUB／PDF 使用阅读副本，避免阅读器将书签写回固定 carrier。

退出码：0 为本次检查通过；1 为内容、依赖、定位或存储失败；2 为调用或抽取配置错误。无文本扫描 PDF、无匹配引文、越界范围、重复匹配和不支持的内容均保留明确失败。
