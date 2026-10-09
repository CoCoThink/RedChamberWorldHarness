# Review 后续工程收口与实际验收

本次逐项核对原始 Review 的五项建议，并补齐评审反馈和验收报告的两处工程遗漏。承重文件、来源定位、语料构建和原件校录已经落地；独立评审尚无实际提交，不能据此宣称全部设计或文学生产通过。

## 已收口的工程事项

| Review 建议 | 已实现与验证 |
|---|---|
| 来源闭包 | 全部32条 Source 的本地载体、确定性摘录和定位通过；三项曹家来源缺口豁免已删除；原件识读明确登记为代理校录 |
| 材料可发现性 | roles、collections、章节导航及固定输入盘点均有 CLI 与结构化记录 |
| 前80语料 | pilot 与完整前80候选已构建，五个文本层分开；离线双构建一致；分类验收单独保留 |
| 新材料接收 | 幂等入库、分类、绑定计算及中断恢复已实现，原件字节保持不变 |
| 目录分片 | ID 分片作为事实源，索引由程序生成，旧 Git baseline 的不可变比较继续执行 |

本次发现并修复：来源／语料 review schema 原先只允许肯定结论，真实否定意见无法进入结构化验收。现在结论字段允许 true／false，原始意见仍须与结构化记录逐字段相符，评审独立性要求保持原契约。任何选中的否定意见都会产生 FAIL，即使其他意见表示通过；拒绝意见依旧形成正式资产绑定，不因结论不利而消失。工程回归允许未取得意见的 PENDING，但会拒绝实际否定结果。

新增 `rcwh project acceptance`，从当前 owner、声明 roots、全部来源、语料和固定写作包计算实际状态。它分别报告工程检查、待交评审及生产准入，不读取文档中的 PASS 作为结论。`--require-complete` 在任何待交或拒绝项存在时返回非零；全部声明准入实际通过后才返回0。该命令的 PASS 仅指 Review 后续输入验收，不替代正文裁决、采用或全书发布。

隔离检出工具已加入严格声明闭包、实时验收和严格验收检查；`full_self_contained_status` 改为从严格声明闭包结果计算。CI 同样运行实时验收，真正的评审拒绝会使检查失败。历史报告保持原字节。

## 尚需真实输入的三类验收

| 项目 | 当前真实状态 | 已准备的接入口 |
|---|---|---|
| 12条来源更正／校录 | 独立提交0，PENDING；公开原件和出处，不盲评 | [来源复核材料 v2](../../artifacts/reviews/source-independent-v2-20261009/README.md) |
| pilot／完整语料分层 | 独立提交各0，PENDING；13／91样本，公开载体与定位 | [语料复核材料](../../artifacts/reviews/corpus-candidate-20261009/README.md) |
| P9文学配对 | 独立提交0，至少2位评审者；20对匿名文本 | [P9提交说明](../../artifacts/reviews/p9-preparation-20261009/README.md) |

要求来自实际的 [Source review schema](../../schemas/source_audit_review.schema.json)、[Corpus review schema](../../schemas/corpus_audit_review.schema.json) 和 [P9协议](../../data/evaluation/p9_protocol.json)，其中 reviewer.kind 均要求 INDEPENDENT_HUMAN。本次代理核验不能充作这些原始人工意见。完整设计中的第89回生产、连续章回、采用和全书发布依赖相应验收；保持未通过状态，不以空模板、准备材料或代理自评代填。

真实提交到达后的原始意见接收、结构化选择与摘要更新见[评审 runbook](../runbooks/CORPUS_AND_REVIEW_INPUTS.md)。否定意见须保留，并按发现项修订：Source 更正使用正式更正审计；语料修改创建新 dataset；文本修订创建新候选。输入摘要变化使旧评审失效，不能直接编辑原始意见或旧派生资产消除拒绝。

```bash
rcwh project acceptance
rcwh project acceptance --require-tracked --require-complete
python tools/verify_foundation_checkout.py --output artifacts/migration/review-closeout-20261009/verification_report.json
```

当前工程验收与待交项的固定快照见[验收报告](../../artifacts/migration/review-closeout-20261009/acceptance_report.json)，干净检出、实际 CI 与测试结果见[隔离验证](../../artifacts/migration/review-closeout-20261009/verification_report.json)。隔离验证在提交前物化候选树，不改用户仓库的暂存区或提交历史；报告记录当时的基线提交与实际候选树摘要。
