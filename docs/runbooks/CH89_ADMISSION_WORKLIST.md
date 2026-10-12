# 第89回准入工作单

本单列出第89回正式准入仍需的人工条件，由 `ChapterAdmission` 实时计算得出，本身不授予资格。

```bash
rcwh literary-inputs package data/writing/packages/ch89-production-v5.json --production
```

当前结果为 `PENDING`，阻塞项只剩：

- `CHAPTER_SOURCE_AUDIT_PENDING`
- `CORPUS_HUMAN_LAYER_AUDIT_PENDING`

## 写作包

`data/writing/packages/ch89-production-v5.json` 沿用 v4 的世界、计划、范例与资产绑定，补列了 v4 漏掉的两项来源。这两项是从 `data/scenes/ch89_confiscation_message.yaml` 经 `data/mechanism_adapters/v04.json`、`data/mechanisms/r4_historical.yaml` 推导出的。v4 不改写，也不继承 v4 下的任何评审资格。

`project acceptance` 目前仍从 `data/project/closure_roots.json` 读取 v4，所以总体报告里仍有 v4 的缺列失败。要把闭包根切换到 v5，须作为单独的治理变更：更新闭包记录并重新进行严格验收。

## 来源复核（5项）

协议：`data/provenance/audits/protocol-v2.json`。材料：`artifacts/reviews/source-independent-v2-20261009/`（可用 `rcwh delivery materialize source-review-v2` 恢复）。

| Source | 标题 | 定位 |
|---|---|---|
| `src:history:beijing:1774:rental-contract` | 乾隆三十九年僧宗玉立租房契 | HTML_TEXT_SPANS html:1 [3760,3879) |
| `src:history:cao:1728:family-housing` | 雍正六年隋赫德奏折——曹家属少留房产养赡 | TEXT_SPANS text:1 [909,955) |
| `src:history:cao:1728:inventory-seal` | 雍正六年隋赫德奏折——曹家房产什物造册封固 | TEXT_SPANS text:1 [810,844) |
| `src:history:cao:1728:pawn-tickets` | 雍正六年隋赫德奏折——旧衣什物与当票百余张 | TEXT_SPANS text:1 [859,892) |
| `src:history:daqinglu:v10:marriage-authority` | 《大清律例》卷十——尊长主婚体系 | HTML_TEXT_SPANS html:1 [2443,2468) |

本回准入只要求这五项各自通过复核；其余七项属于发布前提，不阻塞第89回。

## 语料审核（1个数据集）

`corpus:front80:v1-candidate`，manifest `033395831d12b5809eb0c87a71fd2728367d1e191ccf1db94eda7259ef5057e3`，共91个样本。至少需要1名独立审查者，并如实承认162个未定见证和7497个未对齐段。现行审核以整个数据集为单位，不按回切分子集。材料见 `artifacts/reviews/corpus-candidate-20261009/`。

## 资格边界

两类审核的 schema 都把 `reviewer.kind` 固定为 `INDEPENDENT_HUMAN`。模型或子代理生成的核对报告只能作为反馈或预审材料，不能登记成上述审核，也不能改变准入结果。
