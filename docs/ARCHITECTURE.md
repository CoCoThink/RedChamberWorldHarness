# RCWH 当前架构入口

本仓库以《红楼梦》八十回后复原的研究、规划、创作、评审和发布为目标。完整目标结构见[基础设施设计](RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md)；各模块的实际完成情况由 `rcwh project status` 查询。

## 数据与运行时

- Asset catalog 识别本地字节、不可变版本和 origin；来源图在 `data/provenance/` 中维护 Source → Claim → Decision → Implementation。
- Reconstruction、World、Character Knowledge、Object Network 描述当前复原方案及其连续性；其事实不能反向取得证据权威。
- Hypothesis、Scenario、Replay、Pareto 及文学实验支持方案探索；搜索或实验通过不构成采用。
- Prewrite、Scene Contract、文学评估和 Competition 支持候选创作与真实评审；候选晋升与稳定正文发布分别处理。
- `data/project/current.json` 选择状态与方案约束 owner，方案约束另绑定版本 ID 和摘要；竞争进度只存于 competition 记录，文学工作流只声明顺序和边界。`data/project/scope.json` 声明章回范围。

当前还没有完整实现统一语料重建、全书规划、连续章回编辑、采用与正式发布闭环。资产存储验证不能替代来源内容和定位闭包。

## 契约与操作

| 主题 | 文档 |
|---|---|
| 对象、版本与引用 | [对象契约](architecture/OBJECTS_AND_REFERENCES.md) |
| 权威、状态转换 | [权威契约](architecture/AUTHORITY_AND_TRANSITIONS.md) |
| 全书与场景设计 | [规划契约](architecture/BOOK_AND_SCENE_CONTRACTS.md) |
| 评估、盲评与采用 | [评估契约](architecture/EVALUATION_AND_ADOPTION.md) |
| 迁移、验收范围 | [验收契约](architecture/MIGRATION_AND_ACCEPTANCE.md) |
| 资产入库、追溯与验证 | [基础操作](runbooks/FOUNDATION.md) |
| 搜索、文学实验与生产门禁 | [搜索与写作操作](runbooks/SEARCH_AND_WRITING.md) |
| 历史规则退役 | [ADR 0003](decisions/0003_RETIRE_HISTORICAL_RULES.md) |

校验依据是对象身份、作用范围、引用闭合、上游覆盖和行为边界。历史节点总数、测试数量、CI run 和迁移 PASS 都不能决定当前工作资格。稳定正文的实际摘要和定位仍须严格核对。
