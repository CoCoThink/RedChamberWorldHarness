# 第五阶段研究材料

所有文件是会话 agent 研究材料，不是真人提交、provider API 实测或已通过文学验收的成稿。

## 当前实际阅读入口

- 全部81–100实际新稿已研究登记。未采用首轮研究合订稿179333字符：`draftbook/research81-100-9f79656973430f7d7731f157741f8928d9831e003707b2d391e13ef918c51720.txt`。
- 另选实际修订的研究合订稿166111字符：`draftbook/research81-100-5cd704d41ef32f0972e78c7ba94cc24a6f526f9c4dc9b24d6c323bb76bbe641e.txt`。两份选择与转换各有内容寻址manifest，均NOT_ADOPTED_NOT_RELEASED，不覆盖彼此，不自动取较新或较长稿。
- 81–91及94–100均完成一轮实际修订；92干净重写、93干净重写＋真实发还物窄修。后七回短稿有明显长度不足，实际文学阅读与发表资格分开。
- 实际中段双读者结果见`MIDDLE_READING_RESULTS.md`，全书进度见`FULLBOOK_PROGRESS.md`，阻塞见`RELEASE_BLOCKERS.md`，后段与末三回全文评读继续。所有原负面意见／拒用稿保留；稳定ACTIVE不变。

## 已完成的基础

- `7a25eeb`：当前输入闭包显式选择第89回 v5 包。总体验收 PENDING，工程 PASS。
- `e3cd5a5`：会话稿登记、独立 agent 复核轨道、合同覆盖和研究版发布服务。离线全套1180通过、1跳过，validate PASS。
- `cd365cf`：独立会话回测与匿名阅读导出。离线全套1203通过、1跳过，validate PASS。

## 实际复核

`submissions/source-reader-1.json` 是初次格式不合 packet sample 声明的原始报告，原字节保留；`source-reader-1-v2.json` 仅作格式修正，把原检查完整保留在 notes，意见不变。v2及reader2登记在 `data/agent_panel/`，不是 human selections。

五项史料，两位模型核对者均指出曹家三项的旧出版版本／编号未核实，并区分当票数量与长期现金流推断。来源 panel 为 PENDING。租契、婚姻权限及材料字节在限定核对范围内 PASS。

91语料样本分别由两位模型核对者阅读，报告包括实际已查看图像和未查看的限制。reader1为 PENDING；reader2对页眉／页码层归属提出 FAIL。负面意见保留，不因另一份肯定报告被覆盖；agent-reviewed发布受阻。研究试写可以在明确候选／未核实语料基础上继续，但不能标成文学采用。

后续只读复核 `submissions/corpus-findings-verification.json` 确认了页眉／页码混入的观察，但现行 APPENDIX/VARIANT 优先按范围分类，未规定这些层必须排除页级家具：两项属可能的设计／契约缺口。第79回页前缀依标题字符偏移归属、`[麂]` 原件校字记号在当前原字节契约下未确认为缺陷。该复核不撤销 reader2 的 FAIL，不替代完整新版本复核。

## 重试与版本保留

HTTP 400/524 中断后，主协调者先检查落盘字节再恢复原任务，不把失败通知当作作者完成声明。回测四份首稿已经各自确认并登记，修订使用独立父稿／反馈绑定。首组反馈原 JSON 含未转义换行，保留原文件；`feedback-*-one-v2.json` 仅修正 JSON 编码、意见全文不变。试写 direct sample2 的初稿长度不足，作者另存 `-v2.txt` 扩充达标，仍是同一个样本，不计作额外独立实验。

反馈工具未请求模型时旧第86回报告的 schema FAIL 是工具状态误报；修正工具后另存 `pilot-direct-one-feedback-v2.json` 索引与新报告，旧报告字节保留。缺少语义判读继续 PENDING，不自动使正文通过。

`source-panel-summary.json`、`corpus-panel-summary.json` 是各阶段输出快照，当前状态须由 `rcwh agent-panel status` 重算。

## 规划和试写

`inputs/contract-packet-*.json` 是四批五回合同起草输入，`contract-scaffolds/` 是未填充 scaffold；实际起草合同在 `data/planning/contracts/agent-v1/`，20回共85份。包含实际人物／物件记录和逐场义务；缺失角色与场景内入口明确 UNKNOWN。

初稿全20回检查零 FAIL，整体 PENDING，声明兼容 PENDING、支持范围内确定性重放 PENDING、正文语义 NOT_CHECKED。这不是全85场可执行状态已完善。全部85份模型编辑的新修订另存 `agent-edited-v1/`，不覆盖初稿。

编辑曾为第99回提出另一播放顺序，实际检查发现两处断链；`agent-edited-v2/99-*.v3.json` 恢复已选源链，改序只保留为未选提议。当前混合目录 `agent-final-v1/` 保留80份 v2＋5份 v3原字节，支持原前驱路径的 byte-identical 别名，不放宽不同内容的匹配。完整选择检查为85场零 FAIL、总体 PENDING；无正文语义 PASS。

`inputs/writing/` 固定试写输入；基线章回副本只用于协调者与显式上一回结尾上下文，不作为候选创作成就。`authored/` 存模型实际新写正文，必须完成会话登记、反馈、修订和盲读才可能进入研究采用流程。

`backtest/session-v1/author-packets/` 为79–80两路线各两个样本的实际准备，四份首稿及四份修订均已写成。训练暴露未知，资源平衡未核实，不能证明失稿复原。协调者材料不得提供给作者或盲读者。

`backtest/consumption-limitations.json` 保留实际作者披露：Harness 请求的首条消息约450万字符，包含大量文风特征，一份修订的工具显示被截断，未完整进入模型语境。保存的提示摘要只能证明字节保管，不能证明模型完整消费。当前回测不据此宣称输入暴露等量或 Harness 因果优势；更小支持包须另起版本，不改写本轮冻结材料。
