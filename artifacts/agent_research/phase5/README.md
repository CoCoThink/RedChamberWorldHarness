# 第五阶段研究材料

所有文件是会话 agent 研究材料，不是真人提交、provider API 实测或已通过文学验收的成稿。

## 已完成的基础

- `7a25eeb`：当前输入闭包显式选择第89回 v5 包。总体验收 PENDING，工程 PASS。
- `e3cd5a5`：会话稿登记、独立 agent 复核轨道、合同覆盖和研究版发布服务。离线全套1180通过、1跳过，validate PASS。
- `cd365cf`：独立会话回测与匿名阅读导出。离线全套1203通过、1跳过，validate PASS。

## 实际复核

`submissions/source-reader-1.json` 是初次格式不合 packet sample 声明的原始报告，原字节保留；`source-reader-1-v2.json` 仅作格式修正，把原检查完整保留在 notes，意见不变。v2及reader2登记在 `data/agent_panel/`，不是 human selections。

五项史料，两位模型核对者均指出曹家三项的旧出版版本／编号未核实，并区分当票数量与长期现金流推断。来源 panel 为 PENDING。租契、婚姻权限及材料字节在限定核对范围内 PASS。

91语料样本分别由两位模型核对者阅读，报告包括实际已查看图像和未查看的限制。reader1为 PENDING；reader2对页眉／页码层归属提出 FAIL。负面意见保留，不因另一份肯定报告被覆盖；agent-reviewed发布受阻。研究试写可以在明确候选／未核实语料基础上继续，但不能标成文学采用。

`source-panel-summary.json`、`corpus-panel-summary.json` 是各阶段输出快照，当前状态须由 `rcwh agent-panel status` 重算。

## 规划和试写

`inputs/contract-packet-*.json` 是四批五回合同起草输入，`contract-scaffolds/` 是未填充 scaffold；实际起草合同在 `data/planning/contracts/agent-v1/`，20回共85份。包含实际人物／物件记录和逐场义务；缺失角色与场景内入口明确 UNKNOWN。

初稿全20回检查零 FAIL，整体 PENDING，声明兼容 PENDING、支持范围内确定性重放 PENDING、正文语义 NOT_CHECKED。这不是全85场可执行状态已完善。模型编辑的新修订另存 `agent-edited-v1/`，不覆盖初稿。

`inputs/writing/` 固定试写输入；基线章回副本只用于协调者与显式上一回结尾上下文，不作为候选创作成就。`authored/` 存模型实际新写正文，必须完成会话登记、反馈、修订和盲读才可能进入研究采用流程。

`backtest/session-v1/author-packets/` 为79–80两路线各两个样本的实际准备。训练暴露未知，资源平衡未核实，不能证明失稿复原。协调者材料不得提供给作者或盲读者。
