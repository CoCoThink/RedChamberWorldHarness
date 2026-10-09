# 日常资产接收与分类

R0.1 已提供 `assets ingest / classify / receipt / recover`。目录存储仍是 v1 单文件，读取、序列化、Git 基线和 tracked 元数据枚举统一经过 `CatalogStore`；目录分片在 R1 实施。

## 接收文件

```bash
rcwh assets ingest /path/to/new-research.md \
  --origin chat:2026-10-08 \
  --kind PROJECT_RESEARCH \
  --role HISTORICAL_RESEARCH \
  --receipt-key research-20261008-01
```

输入是本地普通文件。接收器复制原始字节，计算完整 SHA256，登记 Asset、Origin 和 receipt；相同字节沿用已存在的资产 ID 与路径。media type 按原文件名推断，未知扩展名记为 `application/octet-stream`。URL、聊天标识和原路径属于出处记录，资产解析只使用仓库内已核对的载体。

`--origin` 必填。`--receipt-key` 是一次接收的幂等键：相同键与请求重试返回同一 receipt，不重复增加 origin；相同键收到不同内容或参数则失败。记录另一次出现时使用新键或不同 origin。不提供键时，从字节摘要、原路径、origin、kind 和 role 生成稳定的请求身份。原路径只作为出现记录，不参与之后的内容解析。

`--kind` 可选，表示本次明确的存储类别；`--role` 为可选的发现用途。role 不授予证据或采用权限。已经存在的分类资产不能用接收参数直接改换 kind。相同文件名、不同字节分别登记；已经存在的历史资产 ID 不被强制改成 SHA 型 ID。

## 暂存与分类

未指定 kind 的新资产先进入 `sources/inbox/<sha256>/`，kind 为 `UNCLASSIFIED_INPUT`。receipt 输出中有 `receipt_id`、`asset_ref`、`sha256`、原文件名、接收时间、origin、media type、意图角色和当前状态。

复制返回的完整 receipt ID 后查询或分类：

```text
rcwh assets receipt <receipt-id>
rcwh assets classify <receipt-id> --kind PROJECT_REFERENCE
```

分类把原件移动到对应类别的目录，保持资产 ID、SHA 和字节不变，同时更新该资产所有 receipt 的分类事实。每条 receipt 保留各自的意图角色。已分类资产重复指定相同 kind 是幂等操作；改换既有分类需另行调整并审查元数据，不借接收命令覆盖。

| kind | 新资产位置 |
|---|---|
| `UNCLASSIFIED_INPUT` | `sources/inbox/<sha>/` |
| `PRIMARY_TEXT_CONTAINER` | `sources/primary/received/<sha>/` |
| `PROJECT_REFERENCE` | `sources/project/<sha>/` |
| `PROJECT_RESEARCH` | `research/received/<sha>/` |
| `HISTORICAL_RECORD` | `sources/historical/<sha>/` |
| `IMPORT_RECORD` | `archive/imports/received/<sha>/` |
| `REVIEW_RECORD` | `artifacts/reviews/<sha>/` |
| `CORPUS_DERIVATIVE` | `corpus/received/<sha>/` |
| `RELEASE_TEXT` | `releases/received/<sha>/` |

`RELEASE_TEXT` 只登记收到的正文文件，不创建 Release 或 Adoption。现代汇校文件即使分类为 primary，也不会替代 Source 的 witness 判断。

抽取服务生成的 `CORPUS_DERIVATIVE` 由 `corpus extract` 在 `corpus/extractions/` 登记，并绑定输入与配方；外部接收的同类文件须另行验证，分类本身不证明可重建。

## 状态、绑定和 Git

状态是查询结果，receipt 文件不接受自报 `BOUND` 字段：

- `RECEIVED`：原件、资产、出处和 receipt 已完整写入，尚未分类。
- `CLASSIFIED`：kind 与 receipt 分类事实一致。
- `BOUND`：分类完成，而且当前有效结构化对象实际使用该资产。

当前绑定检查覆盖 `Source.container` 与 `Implementation.locator`；要求对象通过 schema、图关系有效、资产引用与摘要吻合。Source 的 locator 是否验证继续由独立 profile 判断。绑定消失或摘要不符时状态回到 CLASSIFIED；当前还支持有效的固定研究写作包，以及 P9、语料层次和来源独立审查中的正式 Review；要求相应版本／输入校验通过，原始意见引用与摘要吻合。新的对象类型按其引用契约接入。尚无对应对象的评审文件可以先接收并保持 CLASSIFIED。

`tracked` 与接收状态独立。命令不运行 `git add` 或 commit；新原件和 receipt 未纳入 Git 时显示具体 `untracked_paths`，正式存储门禁仍失败。审查后将原件、catalog／origin 更新和 receipt 一并纳入版本管理：

```bash
rcwh assets validate --require-tracked
rcwh assets validate --require-tracked --base-ref HEAD
```

## 中断与恢复

写入使用操作系统互斥锁、暂存字节、带前后摘要的事务日志和逐文件原子替换。事务目录 `data/catalog/.transactions/` 不入 Git；活跃锁位于 `.rcwh-cache/asset-catalog.lock`。进程退出后操作系统释放锁。

```bash
rcwh assets recover
```

日志已发布但事务未完成时，普通 catalog 读取返回非零并提示恢复。`recover` 向前完成同一批操作，再核对资产存储；恢复后的重复接收仍返回同一 receipt。新的 ingest／classify 也会在持有写锁后先恢复未完成事务。

若有文件在中断后被另行修改，恢复拒绝覆盖并列出冲突路径；保留日志与当前字节，先核对修改原因，再决定如何处理。不要手工删除已发布日志使半成品看起来完成。尚未发布日志的暂存目录不参与当前 catalog；无活动进程时可清理。缓存清理应在资产命令退出后进行。

接收前检查当前资产存储完整性。原件或目标已被篡改、路径穿越、符号链接、不同字节覆盖及大小写碰撞都会失败；来源定位和文献解释仍由后续独立验收负责。
