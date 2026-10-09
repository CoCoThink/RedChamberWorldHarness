# 领域对象与引用契约 v1

依据：[完整设计](../RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md)。当前已实现 Asset、Origin、Source／Implementation 物理绑定、ExtractionManifest、Locator v2 及 imported release；其余对象按后续阶段实现。

## 已实现的契约

- `data/catalog/assets.yaml` 是当前唯一资产目录；schema_version 为 1。`CatalogStore` 统一读写、Git 基线读取及需跟踪元数据枚举，领域调用者不假设单文件布局。ID 与路径分离，版本字节固定。
- `data/catalog/origins.jsonl` 记录每次材料出现。每条 origin 与 asset 双向引用，SHA 必须一致。
- exact-SHA 内容只有一个实体，可有多个 origin；不同 SHA 不自动合并。
- `data/catalog/receipts/` 保存日常接收事实；重试同一请求不增加 origin。未分类输入显式使用 `UNCLASSIFIED_INPUT`，分类可移动路径但不改变资产 ID 和字节。
- `data/provenance/*/*.yaml` 明确 schema_version。Source.container.ref 直接引用资产 ID；Implementation.locator.asset_ref 直接引用正式正文资产。
- Source witness/type/tier、Claim 支持关系、Decision 状态和 OPEN 语义不因入库变化。
- 资产路径必须位于仓库内，拒绝绝对路径、路径穿越、链接和大小写碰撞；每次解析核对字节数与 SHA。
- 旧文件名和旧包路径保留在 origin 或迁移报告中，正常解析器不使用旧路径或 basename 回退。
- 原始来源、发布物和 artifact 保持原始字节；新结构化元数据使用 LF，避免跨平台 checkout 改变候选的 Git blob 身份。
- 派生输入以 `derived_from` 表达，要求引用存在且无派生环。该关系不授予证据权威。
- `corpus/extractions/` 中的 manifest／units 文件登记为 `CORPUS_DERIVATIVE`；manifest 绑定 carrier、抽取配置、工具及代码／依赖摘要，units 绑定同一输入。重复配方幂等，重建逐字节核对产物。
- Locator v2 的 `extraction_ref` 引用 manifest 资产，`spans` 引用其中的 `unit_ref`，范围为 Unicode code point 的零基左闭右开区间。Source 报告绑定摘录、定位、Source 内容和校验器；普通资产验证检查引用，来源验证重取正文。
- 新接收来源的 `carrier_capture` 引用固定 HTTP 采集记录，并核对记录中 carrier 的 ID／SHA。批量 Source 迁移保存前后记录和完整证据语义快照；成功报告登记为资产，未匹配摘录保持 UNVERIFIED。

## 后续对象

Hypothesis、ReconstructionBranch、BookPlan、SceneContract、DraftRevision、Review、Adoption 采用固定版本引用。支持/反对、互斥、场景前置、采用和发布关系分别定义；依赖图由正式记录推导。

## 验证入口

```bash
rcwh assets validate
rcwh assets resolve asset:primary:hlm:zhihui:v3.1416:pdf
rcwh sources trace decision:cliff-release:function
rcwh sources verify-all
```

CI 使用 `--require-tracked`；既有版本使用 `--base-ref <commit>` 比较，拒绝文件与摘要同时改写后继续使用原 ID。
