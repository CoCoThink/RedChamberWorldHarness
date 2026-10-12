# 规划、模型写作与留出研究

本切片增加可运行的研究工具，不交付新的稳定正文，不证明失稿复原成功。默认离线；准备任务、导入计划、输出差异包不构成独立评审。

## 按回准入与当前状态

`literary-inputs package ... --production`、生产 competition 和 promotion 使用同一个章回准入服务。来源作用域取写作包声明与场景/历史机制/主张/实现依赖的并集；漏列来源、断开的引用、过期字节会阻塞，不能只列较容易审核的来源。

本回所用来源必须具备可验证定位和独立覆盖；不在当前审核协议中的来源仍待明确审核。实际用到的语料须通过现有数据集审核。本版本不创建逐段子集审核，也不把未审正文授权为正式范例。未审材料可在研究权限下使用，报告保留 PENDING。

全局非依赖来源和 P9 仍列在 `project acceptance` 的发布前提中。P9 衡量旧微稿修订实验，不再单独阻塞无关章回。`--require-complete` 仍要求整体完成。当前第89回写作包存在漏列来源，因此 production admission 会 FAIL；research package 仍可验证原件，不能据此认为准入通过。

`project status` 显示推导出的 progress/adjudication，同时保留 `declared_*` 历史声明及差异提示。现有旧第86回裁定不会自动获得当前评审资格。

## 规划资料

```bash
rcwh plan check --chapters 85-87
rcwh plan threads
rcwh plan compare-books
```

`data/planning/chapters/` 的20张卡由现有18字段来源卡、m2/m6/prewrite/m5确定性导入；文本保留来源行号、原字节摘要、记录指针。`data/planning/scenes/` 是原有候选场景的骨架，未知参与人、状态、顺序和物件绑定保持未知，不是验收通过的场景合同。

`plan import-cards` 拒绝覆盖既有结果，需要导入新版时使用新的 `--output`。导入/模型拟稿不能自动标成 EDITED。连续性结果只证明明确声明之间的兼容，不证明正文真的实现出口。

伏笔台账链接诗谶、脂批解释、长线与物件保护等既有资料；未回应可以保留 OPEN。100回/110回书框架是显式 SHADOW 分配示例，不声称原稿篇幅。替代框架未接入独立状态重放时显示 NOT_CHECKED，不借用旧100回重放结果。

## 写作与修订

```bash
# 默认 dry-run，无须密钥；打印完整请求与预算，不调用 API。
rcwh write draft data/writing/packages/ch89-research-v4.json --chapter 89

# 候选参数是不可变 draft 登记 JSON，而不是裸正文。
rcwh write feedback data/writing/drafts/ch89/<draft-sha>.json
rcwh write revise data/writing/drafts/ch89/<draft-sha>.json \
  --feedback data/writing/feedback/<feedback-sha>.json
rcwh write diff data/writing/drafts/ch89/<old-sha>.json \
  data/writing/drafts/ch89/<new-sha>.json

# 85–87 旧研究任务的可选 API 执行入口，默认只准备请求。
rcwh pilot run-author --runner anthropic --route medical \
  --workflow IMPROVED_HARNESS --output /tmp/author-run.json
```

真正调用需安装可选 `generate` extra，并在本地环境设置 `ANTHROPIC_API_KEY`（不要把密钥发到聊天或提交到仓库）。命令必须显式带 `--execute --network-consent`：这表示将完整请求发送给外部服务并承担费用。先检查 dry-run 中的材料、模型和预算；本轮实现不执行真实付费请求。

API运行记录保存实际请求、参数、返回模型、完整响应、request ID、usage、stop reason和SDK版本。密钥不写入记录。默认无自动重试/模型切换；输出截断、拒绝或非完整响应不是有效候选，失败响应留存供核查。

请求数、最大输出tokens、输入字节和超时是资源上限，不是金额承诺；输入token和可能的重试费用需要自行按实际usage核算。正式实验需将生成、反馈、修订和重试全部计入相同总预算。

新反馈始终 FEEDBACK_ONLY，不登记为正式 scene reading、独立意见或采用授权。旧不同模型族判读接口的既有规则不变。差异包可帮助编辑重读，但正式评审仍须绑定整份修订正文。

## 留出79–80研究

```bash
rcwh backtest check
rcwh backtest prepare --output /tmp/front80-author-tasks
rcwh backtest summary
```

所选版本的79–80对应一个原章回拆分，不能当作两个独立样本。研究测试的是“给定编辑计划后的成文与修订”，不是盲复原未知原稿。计划构造与作者运行分离，计划及入口事实保持草案状态，未经编辑核查不启动文学实验。

作者任务、检索和文风参照排除留出文本，近重复泄漏作为观察列出；模型预训练是否接触原文未知，逐字重合不能证明记忆来源。存世原文仅作观察到的文学参照，不是后八十回复原的真值。

没有实际运行记录、可比总预算和有效独立阅读时，效果始终 NOT_ESTIMABLE。夹具、匿名包或模型意见不能代替真人。读者是否认出原文须记录，解盲风险与分歧如实保留。

## 评审 context v2

新竞争可显式绑定 `writing_package`、`context_version: 2` 和 `context_manifest`，使用：

```bash
rcwh competition <competition-id> --prepare-context reviews/context-v2.json
```

命令只准备清单，不修改竞争记录、不授予资格。v2绑定实际创作输入、计划、合同、世界、来源载体、候选作者/运行和协议；审核台账改变不会改写创作语境，但资格仍在每次评估时重算。首版清单保守绑定多个领域全部实质文件，尚不宣称最小跨回影响分析。旧v1摘要算法完全保留。原材料变更、新输入遗漏或清单过期会被拒绝。
