# 第89回准入工作单

本单说明第89回当前生产输入包及其人工审核依赖。所有状态都由 `ChapterAdmission` 实时计算；本单和写作包本身都不授予生产资格。

## 当前包与检查命令

当前候选包是 `data/writing/packages/ch89-production-v6.json`，标识为 `writing-package:ch89:production:v6`。检查当前状态：

```bash
rcwh literary-inputs package data/writing/packages/ch89-production-v6.json --production --require-tracked
```

截至本工作单更新时，输入工程检查通过，准入仍为 `PENDING`，因为第89回使用的来源尚无独立审阅，所用语料尚无通过的人工层级审查。运行上述命令获取实时细项。第89回正式写作只能在命令返回 `PASS` 且项目级 `rcwh project acceptance --require-tracked --require-complete` 通过后开始。

## 第89回直接依赖

当前 v6 包声明并按场景合同推导使用以下五项来源。第89回准入要求这五项都被当前选定来源审阅覆盖并通过：

| Source | 标题 | 用途／定位 |
|---|---|---|
| `src:history:beijing:1774:rental-contract` | 乾隆三十九年僧宗玉立租房契 | 租赁凭据及宅屋关系 |
| `src:history:cao:1728:family-housing:npm005664` | 雍正六年隋赫德奏折——曹家属少留房产养赡 | 曹家房产与养赡 |
| `src:history:cao:1728:inventory-seal:npm005664` | 雍正六年隋赫德奏折——曹家房产什物造册封固 | 查封、造册与物件状态 |
| `src:history:cao:1728:pawn-tickets:npm005664` | 雍正六年隋赫德奏折——旧衣什物与当票百余张 | 当票及财物凭据 |
| `src:history:daqinglu:v10:marriage-authority` | 《大清律例》卷十——尊长主婚体系 | 婚姻权限边界 |

审阅必须绑定当前选定的 `data/provenance/audits/protocol-v4.json`。协议总计16项，含上述5项和其他项目输入使用的来源。第89回直接准入只检查本回实际使用的5项；完整项目验收仍要求当前协议所列16项均完成，不能用5项局部通过代表全局来源审计通过。当前可复核材料在 `data/writing/source-review-next/`，用以下命令核对生成材料及绑定：

```bash
PYTHONPATH=src python tools/prepare_source_audit_review.py --check
```

历史来源 v1/v2 审阅包绑定旧协议，不能替代 protocol-v4 的意见。

## 语料依赖

第89回 v6 包的范例集引用 `corpus:front80:v1-candidate`，manifest 摘要为 `033395831d12b5809eb0c87a71fd2728367d1e191ccf1db94eda7259ef5057e3`。该 dataset 有91个抽查样本；当前完整审阅要求逐项判断上下文、层级和定位，并确认正文边界。审阅者还需如实承认162个未定见证和7497个未对齐段，不得猜测补齐。不要把 pilot 的意见迁移给完整候选。

项目级验收另外要求独立完成 pilot `corpus:front80:pilot:v1` 的13项审阅；这与第89回 v1 完整候选审核是两个不同的 dataset 和意见。第86回当前试点另使用 `corpus:front80:v2-candidate`，含146项，协议和意见完全独立；其意见不能替代 v1。三者材料、模板和登记通道见 `docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md`。

## 项目级待办与资格边界

第89回输入准入和项目整体完成是两个状态：

- `CHAPTER_SOURCE_AUDIT_PENDING`：第89回直接使用的来源尚未完成当前协议下的审核。
- `CORPUS_HUMAN_LAYER_AUDIT_PENDING`：第89回范例所用 v1 完整候选尚未完成人工层级审核。
- `rcwh project acceptance` 另检查16项来源的全局审核、pilot 语料审核、完整 v1 语料审核、P9 两位盲评者的20对提交，以及所有声明输入的闭包。
- 当前 v2 语料用于第86回试点的独立人工审核；它不继承 v1 意见。

独立读者指南及登记步骤见 [语料、来源与评审输入](CORPUS_AND_REVIEW_INPUTS.md) 和 [独立读者指南](REVIEWER_GUIDE_ZH.md)。审核为 `FAIL` 时应保留并登记真实负面意见；修改输入后建立新版本，不改写旧意见。模型或子代理只能提供研究性检查，不能登记为 `INDEPENDENT_HUMAN`，不能产生文学通过或准入资格。
