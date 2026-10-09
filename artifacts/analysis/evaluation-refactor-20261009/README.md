# 评估重构的实际核验与准备材料

本目录保存工程结果和供下一轮阅读使用的材料。没有真实人工意见、外部模型效果报告或发布授权。

- [结果摘要](summary.json)：两套真实 Python 环境各670项测试通过，工程验收 PASS；完整文学验收仍 PENDING。
- [3.12.13 的 CRLF 干净检出报告](checkout-final-3.12.13.json)：全部20个 CI shell 步骤、来源/语料重建及完整测试。
- [3.12.3 测试输出](pytest-3.12.3.txt)与[严格 tracked 输入验收](acceptance-3.12.3.json)。该报告的 tracked 状态在隔离检出建立；生成报告时，原工作区尚未暂存或提交。暂存后的原工作区追加验收因挂载盘文件 I/O 阻塞超过七分钟而中止，没有产生结果。
- [原工作区资产核验](assets-original-workspace.json)与[957个相关文件原字节对照](workspace-byte-equivalence.json)。对照记录的是测试时的字节；提交检查随后删除了六个新 CLI handler 文件末尾的多余空行，未修改运行逻辑。
- [五个固定反例](semantic-replay-summary.json)：只证明内部判读的约束重放，不证明实际模型的识别能力；对应实际 CLI 报告为 `semantic-*.json`。
- [三回试点状态](pilot-summary.json)：两条因果路线、九份短稿，直接示例受污染，效果 NOT_ESTIMABLE。
- [匿名三回阅读包](pilot-reading/public/packet.json)：仅交付 `pilot-reading/public/`。`pilot-reading/coordinator/` 保存映射，供协调者使用。空白 TEMPLATE 不算评审。
- [六份作者任务准备记录](author-requests/preparation-report.json)：相同路线/约束/预算下的直接、旧、改进流程；程序调用和外部作者运行仍为0，provider token 预算待冻结。
- [语料焦点包核验](corpus-focus.json)、[人物覆盖](character-coverage.json)、[文体观察](style-observations.json)：全局独立语料审计数仍为0。
- [本地附件清单](release-attachment-manifest.json)：四份已核对原字节的附件已准备，状态 NOT_PUBLISHED。用 `rcwh delivery attachments NEW_DIRECTORY` 可重新生成；22份移除副本也已实际恢复并逐件核验。

实质剩余工作是外部语义校准、来源与语料独立审计、隔离生成有效流程对照、两位整段读者及修订后重评。工程通过不授予候选采用或稳定正文变更。权属仍待逐项核实，所有者选择暂不授权，见[分项许可方案](../../../docs/architecture/RIGHTS_AND_LICENSING.md)。
