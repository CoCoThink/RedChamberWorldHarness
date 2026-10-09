# 前80语料候选复核包

本目录由代理准备，不包含人工通过意见。pilot-audit 和 full-audit 提供固定样本的原文、定位、排版规则及空白回填表，分别有13和91个样本。page-images 提供代表性物理页图；完整原件和所有提取单元可按 asset／extraction ID 从仓库取回。

two-independent-builds.json 证明两个新进程的全部规范产物摘要一致，属于工程验证；不证明文学分类获得人工确认。legacy-index-map.json 保留88条旧索引项与87条未解析解释。pilot-to-full-map.json 通过同一载体原始范围交叠建立跨数据集关系，不按段号猜测。

人工回填、原始意见接收和复核失效规则见 docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md。完整候选仍有162条未知批语见证，跨载体对齐未确立同版关系；请保留这些待核事实。当前所有 reviews 为空。

## Materialize delivery copies

The registered archive retains every original file. Expanded large copies and the duplicate ZIP were removed after exact byte comparison.

Run `rcwh delivery materialize corpus-review /tmp/corpus-review` to recreate the complete original reading directory. Run `rcwh delivery attachments /tmp/rcwh-release-attachments` to prepare checksum-bound attachments. This does not publish them or submit reviews.
