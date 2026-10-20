# ADR 0006：发布作者链与审阅规模

状态：已实现，研究轨道；继承 ADR 0004、0005。

## 问题

重绑稿的会话记录只证明新输入下登记了哪些字节。它不证明新提示词生成了正文。旧发布请求未引用 `rebind-v4/receipts/`，会把重绑会话误列为原作者。单回阅读无法发现当前二十回正文的回际断裂；试点材料大小与同时启动十位读者的服务可靠性，也不足以支持直接铺开。

## 作者与保管

选择器逐回显式绑定 `rebind_receipt`，`agent-release prepare` 将其原样带入请求，发布 manifest 的章回 bindings 和 `reviews.author_lineage` 同时保留回执和原作者链。既有候选稿、合同和审阅 packet 保持原字节。

发布校验当前草稿的完整冻结历史，并另核实回执的当前/前驱草稿、正文、写作包及章回。前驱作者记录按绑定字节、会话 author-run、原请求和修订反馈关系检查；不对已经退休的旧输入强行重渲染，`previous_writing_inputs_replay=NOT_CHECKED` 明示这一界限。模型身份仍是声明。

原作者与修订者进入 `contributors`；只做重绑的会话进入 `custodians`。有正文改动时，回执必须含精确 unified diff 和原因，该会话另列 `COORDINATOR_EDITOR`。因此第 86 回的既有称谓小改有编辑署名，其余十九回不会新增正文作者。原作者、修订者和保管会话都不能作为自己的章回、依赖或整书审阅者。已知 `rebind-` 会话及其后续修订缺少回执时拒绝通过作者门；后续修订可继续引用祖先重绑回执。

## 当前整本读本

prepare 按发布使用的同一稳定底本、所选候选稿和项目章回顺序拼接 `reading/book.md`。`reading/book.json` 固定全部章回字节、19 处接缝与阅读重点：时序、物件状态、称谓、知识获得及后文照应。BOOK packet 的策略固定为 ADVISORY，自动安排两位独立声明的读者。

整书意见与其他意见一样按原件登记、保留异议及 supersedes 历史；BOOK 的负面意见即使未写 severity，也只产生 ADVISORY。manifest 在 `advisories.book_continuity` 展示意见和覆盖度。缺审读、异议、读本过期分别可见，但不增加门控。`BOOK_STRUCTURE` 继续只代表结构检查；整书审读不会自动证明语义正确。

正文变动需要新 selection / edition 和对应新 packet、读本、campaign；旧 packet 和意见不得覆盖。派发计划保存当时 request 的不可变副本，并单独核对当前的审阅依据；后续协调者决定不属于读者输入，不会中断派发。候选稿、包、政策或审阅 packet 改变时拒绝继续，已登记意见仍由原 packet 留存。

## 分批、材料拆分与恢复

`agent-release review-plan` 以实际依赖计算任务。每项 CANDIDATE、PACKAGE、CONTRACT、SOURCE、CORPUS subject 均安排两位读者。章回组超过默认 197 KiB 时按完整 subject 分组；合同组仍附候选稿和写作包供对照，避免脱离正文。单份过大合同不会截断后冒充完整阅读，而是显式报告超预算。

语料只导出所需完整样本记录，保留 carrier 哈希及记录 ID，加载时重新比对原 carrier；不会让读者通读重复的整个 JSONL。整书任务例外地保留完整全文，并明确报告其体量。

`review-run` 通过本地适配器执行：JSON assignment 从 stdin 输入，包含字节绑定、阅读清单及由既有 scaffold 生成的意见骨架；stdout 必须为真实填写的 AGENT_REVIEW_OPINION。适配器负责启动实际独立读者。程序不自行调用付费服务，不根据 scaffold 编造意见。

默认最多五个任务同时执行，允许 1–6。只对退出码 75、stderr JSON 的 429/500/502/503/504 以及超时自动重试，最多三次，退避 5、10 秒；其他失败不自动重试。任务、原始 stdout/stderr、失败、登记记录逐次追加保留。登记串行化；失败尝试不计意见，已登记任务恢复时不重复执行。空 verdict、空 notes、换 packet、换审阅身份、漏 subject 都拒绝登记。运行完成只表示已收到意见，意见可为 PENDING 或负面，不能冒充文学通过。

## 验证与铺开

`tools/verify_agent_release.py` 核对真实二十回评估零 FAIL、作者回执齐全、所有必审 subject 恰有两项任务及当前整书读本。`--build-smoke` 在 HEAD 的临时克隆中执行真实 `build --allow-pending`，验证 manifest 落盘；PENDING 只生成 manifest，不输出已审正文。CI 两个 Python 版本都执行该验证。

口味类试点意见保留原审阅记录，由新读者及协调者决定；本次不改正文。大规模写作/审阅须在提交推送及 CI 通过后开始；本次只准备和验证 harness，不制造正式审阅意见。
