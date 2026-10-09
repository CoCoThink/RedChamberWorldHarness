# 权威与状态转换契约 v1

## 已实现的权威边界

- 当前状态由结构化记录持有；Markdown 是解释与阅读视图，编辑文档不改变证据或采用状态。架构决策统一位于 `docs/decisions/`。
- 登记 Asset 或接收历史材料不产生 evidence、adoption、promotion 效果。
- 日常 receipt 的 RECEIVED／CLASSIFIED 由实际存储及分类事实决定；BOUND 由当前有效 Source／Implementation 绑定计算。意图角色不改变证据层级；绑定消失时状态回退。tracked 与上述状态独立。
- 证据 Source 与物理 Asset 独立；现代汇校载体不代替古本 witness 身份。
- bibliography 和内嵌摘录不能单独证明本地来源闭包。
- 导入的 page/parsed_lines 仅为定位声明，保持 UNVERIFIED。Locator v2 从固定 carrier 重建抽取，按 Unicode 字符范围重取摘录；运行时重算并核对报告绑定，自报 VERIFIED 不能绕过验证。
- imported baseline 发布清单核对正文与相关资产的字节，不伪造新的采用或审批记录。

## 当前状态 owner

`data/project/current.json` 显式选择 capability、literary、competitions、release、implementation 和 plan_constraints 六个 owner。当前值从 owner 读取，README 和界面不再另存状态副本。capability owner 只选择实验和基线，当前 PASS／BLOCKED 由所选实验的实际检查产生，不读取历史 CI 成功状态。

capability 与 literary 的稳定正文摘要必须与当前 release 一致；literary 只声明工作顺序和边界，章节状态、人工审阅与裁决从 competition 读取。当前实施总状态为 IN_PROGRESS，存储验收通过不能将其改成 COMPLETE。

实验对正式竞争的影响统一为 NONE，不按固定章节列举。文学门禁按选定章回查询；探索、评审与采用仍需独立的状态转换。

## 后续转换规则

证据边界、版本内连续性、实验控制、文学建议和操作安排分级。生成器只提交候选正文和建议增量；采用命令经验证后更新指定范围。改写被评审输入会使相应报告失效。

候选状态与发布状态独立。每次 Adoption 记录对象版本、范围、理由、未决项和依赖；发布只消费有效采用记录，不消费自由文本中的 PASS 自述。

## 证据与生成

硬证据限定不可违反的范围；未被唯一决定的空间可由人物、时代、结构与文学判断形成方案。OPEN_LOCKED 是可成立的研究结果，不是迁移欠账。保留解释分歧；不能因为能够编造答案就把它写成证据。

历史迁移状态、冻结标记和样本数量不决定当前工作资格。真正的人工评审可以改变竞争资格，修改被评审正文会使旧评审失效。稳定正文保护和候选晋升仍为独立门禁。
