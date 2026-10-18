# 完整推进路线执行总账

本页更新至2026-10-18本轮执行状态，不覆盖任何历史检查点、意见、稿件或评估。MODEL/NONE；NOT_ADOPTED_NOT_RELEASED。原批准完整路线M0–M5继续有效，但不能把计划获批当成结果预定。

## 当前批次

| 工作 | 当前状态 | 实际产物／依赖 | 剩余阻塞 |
|---|---|---|---|
| M0基线捕获 | 基线捕获与本批完整工程验收完成 | `m0-v1/inventory.json`、`baseline.json`：4119文件、20章、124未过gate、2原corpus否定记录；检查点20验证当前4131输入无漂移、325保护未变 | 研究来源／语义／文学门仍独立未闭合 |
| M0定向回归 | 13 passed，1.06秒 | `tests/test_research_advancement_baseline.py`；发生在retained helper添加前 | 不是全suite／validate，不覆盖随后新helper |
| M0完整检查 | 用户要求重试、退出auto后实际PASS | `verification/engineering-checkpoint-20/`：1690 passed、1 skipped、161.45秒，validate PASS；CPython3.12.13，4131输入无漂移、325保护未变，临时副本已清 | 两次先前拒绝记录原样保留；未执行retained helper，不授来源／文学资格 |
| P1范围与七项预审 | 七项窄预审及25项既有来源的相邻存储原文范围审读完成，原报告均已完整读核 | `literary-source-range-review-v1.md`（14项）、`historical-source-range-review-v1.md`（11项）及`source-range-adverse-findings-v1.json`：H05持续现金流过推、小红siglum／黛亡注释层边界另存，旧记录不改 | 非早本／历史原图复核，非全20正文claim-use审计；新反证未裁定关闭；解析消费者／catalog兼容实验未做，86三carrier仍阻塞 |
| P2 corpus负面核查 | 调查／支持环境context核查及另版old_kind纠正crosswalk完成 | `corpus-context-compatibility-v1.md`、`reader2-old-kind-correction-v1.json`及可重算工具／6回归：102项查49错、8负面错映射；原opinion31 FAIL保留 | 原FAIL不清；存储几何非PDF重抽；30残留title与content-only／v3迁移待定，不修改MAIN_TEXT |
| P3能力盘点与规格 | 原policy只读验证器已验收；新增原始reading bundle intake／全目录负面声明汇总及复核修正已完成定向验证 | `policy-reading-custody-review-fixes-v1.md`、`declared-author-context-inspection-v1.json`：76联合passed；四long-v1声明组与20章真实parent链可重算，不认证context资格；真实reading registry为空 | 本批完整checkpoint24已通过：1769 passed／1 skipped、171.71秒，validate PASS；4178输入无漂移／325未变，快照已清；owner可信inventory选择尚未建立（纯锚点功能见下一行）；author父稿映射／语义原子裁定／合同runtime／release接入未实现，资格与语义PENDING；旧22覆盖原切片 |
| P3外部清单锚点 | 纯checkpoint builder／显式绑定核查及后继不可删旧条目已实现，复核null入口错误已修 | `policy-inventory-anchor-slice-v1.md`、独立schema／18回归；最新联合93 passed；真实registry为空，未写owner选择 | 最终checkpoint25已通过：1787 passed／1 skipped、184.21秒，validate PASS；4188输入无漂移／325未变，快照已清；可信anchor由owner独立保存，首冻结前遗漏不可追溯，不能声称全局不可回滚历史／语义资格 |
| 文学pilot编辑预审 | 协调者完整读86v2／95v1／99v1并另存编辑分析 | `literary-pilot-preflight-v1.md` | P1–3输入版本、P4包／谱系和完整检查；无新正文／请求／import |
| M1当前批次合流 | 首个最小工程切片及来源／corpus后续批次均已完成验收；M1整体仍OPEN | checkpoint23：1740 passed／1 skipped、165.01秒，validate PASS；4165输入无漂移、325保护未变，快照已清；`m1-source-corpus-followthrough-v1.md` | 未完成显式来源consumer／真实资格、合同runtime和完整语义intake；不得把该批次完成写成M1全闭合 |
| P2隔离corpus实验 | 候选五title classifier只读sandbox compile完成，工程条件满足但不具资格 | `corpus-title-compatibility-summary-v1.md`及结果目录：baseline/候选双进程86产品成功，30 mask变更、MAIN_TEXT/ZHIPI/80 views不变，224 ID shifts、4 derived products changed | 旧31 FAIL保留；v3 adoption需新exemplar、20新package和真实新谱系；未build/register/catalog |
| M1最终工程验收 | P2隔离实验后的完整快照通过 | checkpoint26：1787 passed／1 skipped、184.29秒，validate PASS；4473输入无漂移／325保护未变，快照已清 | 仅工程结果，不授corpus/source/literary/release资格 |
| M2输入冻结 | 用户选保留v2，修正v3冻结已生成、11定向passed；v1/v2原错误记录保留 | `m2-input-freeze-v3/`：1230绑定、3427直接prepared出现0stale／68历史诊断另列；计数及draft/package关系强制核。五份旧路径经用户明确许可恢复，晚到续稿未删 | checkpoint27实际通过：1799 passed／1 skipped、185.65秒、validate PASS；4512输入无漂移／325未变，快照已清。冻结只授新修订准备，不授fresh／语义／文学通过 |
| M3真实pilot | 三章实写／作者披露／协调者整章阅读与串行正常import完成；两位新非作者匿名六全文比较已完成，三章均偏新pilot但原verdict均UNVERIFIED | `pilot-authored-v1/`、`pilot-mechanical-observation-v1.json`：86=8075/7924、95=9142/8779、99=9159/8500正文非白，length/lint/anchor PASS但语义PENDING；`pilot-imports-v1/ch86,95,99.json`分别4536/4541/4546捕获输入无漂移、四产物hash核验；`pilot-reading-inventory-v1.json`及六全文匿名包已冻结 | 90条引文及完整声明覆盖已核，read_scope EOF勘误另存、raw不改，两份登记均PENDING；显名保护已复核，99知情张力待一次限定核验；匿名不是技术隔离，原旧负面不清；checkpoint28已实际PASS：1833 passed／1 skipped、187.08秒，validate PASS；4593捕获输入无漂移、325保护未变、快照已清；不授文学／语义资格 |
| M4全20处置／复读 | 已有20回候选表；两位非作者正反序六全文比较均完成、原意见已登记PENDING；最终处置待限定核验 | `editorial-triage-prepilot-v1.md`、`pilot-comparison-disposition-v1.md`及两份raw observations/opinion；90引文精确，reader2 EOF坐标勘误另存不改raw；86/95研究偏新pilot，99文学偏新但知识张力单独OPEN | 仅94/99窄修已完成全文／自读／两位显名整章复读，正常串行import两章PASS；`final-selection-v1.json`与44subject `final-packet-v1.json`冻结。最终一位读者已顺读81–100，50引文核验；95/96明确口径断点负面与定向反方并存。其项目内报告保存被auto以Irreversible Local Destruction拒绝，未绕过，原报告留/tmp并明确两项metadata勘误；final-reader1/2共28项实际结果各已冻结并登记PENDING/FAIL；95-S3-R2合同—正文动作差异触发两份FAIL，普通evaluate最终FAIL，接口报告已保存。不把一致偏好当资格PASS或重复计旧阅读 |
| M5新evaluate／归档 | OPEN，未启动 | 冻结选择、前序验收 | 不build／allow-pending绕门 |

## 现有选版与不可漂白项

- 冻结连续选择／旧评估仍86长v1、91窄v2，其余长v1。86窄v2另有正常import和一次实际完整追读，但未静默入选。
- 旧report-v3总体FAIL，19 CORPUS_PEERS FAIL，86原字保护及三个source依赖FAIL；source／candidate／contract同行及decision仍未齐。policy语义、supplemental、合同三层不能混成一个“待补意见”。
- 25项来源范围来自实际包，不只取旧report已写出的24项；86早停导致其input_scope未安装。
- corpus最终回报的31独特争议是5异文／26附录页眉，两段均EDITORIAL且旧review context已披露，不是31项MAIN_TEXT污染；另30处未分类的running-title及49项reader2 old_kind错误单列。两份原FAIL不因此撤销，无新版本／PASS。
- 85合同实际72份v1、13份v2；所有151 exit非KNOWN，65局部入口不支持，85正文语义NOT_CHECKED；新增验证接口不能从未知生成执行事实。
- 同一PDF、同上游总谱和重复作者／reader context不增加独立见证。所有人类／provider资格未由本轮模型取得。

## 权限阻塞历史与本次恢复

原完整快照及保留副本变体先前分别被auto分类器拒绝，均未执行；两份attempt记录原样保留。用户随后明确要求“重试”并退出auto，本会话直接运行原`tools/verify_research_checkpoint.py`，没有委派绕过或修改permission配置。

检查点20现已实际完成：1690 passed、1 skipped（161.45秒），validate PASS；4131输入无漂移、325保护未变，快照已删除。`tools/verify_retained_research_checkpoint.py`仍未被执行；全suite也不代表每条工具CLI路径有专门测试。此次总账更新及后续工程不追计为已被20覆盖；旧checkpoint19保持其原覆盖范围与字节。来源／语义／文学FAIL与PENDING未因工程通过改变。

## 授权状态

无新全局catalog／source登记，无正文换绑，无旧合同／policy改写，无新release evaluate／build，无commit／push，无stable v1.4/current变更，v1.5仍未激活提案。任何后续涉及这些独立授权点，仍按已批准计划处理。
