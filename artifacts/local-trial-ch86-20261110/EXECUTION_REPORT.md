# 第86回局部模型真实试稿（2026-11-10—11）

当前稿：[ch86-authored-v3.txt](ch86-authored-v3.txt)，正式导入回执：[import-v3.json](import-v3.json)。当前主会话直接在main写作，没有新分支、工作树、外部模型API或新增子代理。原20回研究版选择器没有切换；这回是新写的单回研究试稿，不是重绑旧正文。

## 实际写作与保管

事前计划为 `docs/plans/CH86_LOCAL_TRIAL_20261110.md`，输入为已通过双版本CI的main `93b35f81f47df31033fbad635ea542e0ccb04b14` 所准备局部请求。输入工程复验见 `input-verification.json`；该原准备记录的NOT_STARTED不原位改成已执行，实际执行另见 `execution.json`。

作者读取本回章节卡、六合同必写/禁写、角色器物及事件消息模型、所选范文片段和来源限制。工具曾有组合输出截断，随后用紧凑输出重读写作相关内容；不声称完整234426字节payload及全部工具元数据被实际消费或理解。导出回执始终为 `consumption_proof=false`，模型配置为未核验声明，没有伪造供应商响应、token或账单。

首次短稿 `ch86-first.txt`、展开稿v1、删重复句的v2均保留。v2先实际导入，作者为 `session:main-agent:ch86-local-trial:20261110`；作者自查发现86-S2药铺接力未明确写出。原自查及完整离线反馈没有删除或改成通过。随后以真实父稿、局部反馈、notes及导出回执准备并导入v3，仅在P15补药铺来药、厨房煎备、热水分备。v3有6151个Unicode字符（含标题、标点和换行）、5095个基本汉字及扩展A汉字、18243个UTF-8字节；计数不是模型token实测。

v3候选SHA256为 `20f02d73098a58d532e4727c14611d8880f08a574c65130d2a28e0ccc5fa7bef`，draft为 `data/writing/drafts/ch86/8a29f5df97aa191a44609649e9d3e6eb23ff364a985d9d5134e078010d93e993.json`。作者运行、父稿、输入快照、反馈、notes、请求和payload均以实际字节绑定。四次作者编辑见 `execution.json`，未导入的短稿/v1不冒充正式父稿或独立作者。

## 试跑暴露的问题与修复

1. **当前兼容性误报。** 实际v2新稿被标STALE，唯一差异是 `shared-values-v1.md`：复算漏做共享视图封装，输入列表少了说明模板。原失败见 `current-compatibility-before-fix.json`。现让兼容性复算采用准备请求相同的封装；回归验证未变输入CURRENT、模板实际修改STALE且历史稿仍可读。没有放宽历史哈希或忽略真实变化。
2. **修订请求增长。** 完整离线反馈的诊断复算请求为290353字节，加原预留后339505，超327680，拒绝且未截断/派发，见 `revision-budget-rejection.json`。第一次改用局部反馈、但仍保留32768输出预留的请求也被拒绝。最终明确选择局部反馈，并把这次完整正文的输出预留设为24576字节；上下文上限327680和指令预留16384不变。实际请求279134字节，含预留320094，PASS；实际正文18243字节也低于输出预留。局部反馈保留六项骨架PENDING、完整性诊断和作者漏写问题，原style与声明连续性报告保存在完整反馈，不因未附本次修订而通过。

离线请求的model字段沿用现有renderer允许的模型标识，仅为离线准备参数；真实作者配置另在主会话运行声明，不能据此宣称相应供应商模型执行。准备时无效限额字段或不合renderer要求的model标签均遭拒绝，没有以这些失败准备生成的请求登记正文。

## 作者自查与独立审读

`paragraphs-v3.json`保留53段全文引句、字节范围和摘要（含标题）。`author-selfcheck-v3.json`提出24事件、5消息和40合同义务的引文映射；这是同一作者自报，不是语义重放或独立PASS。原30项声明、25项UNKNOWN、52项未决均未改写。

仍需独立核对：G01不引原句时能否识别；相对死亡经过是否足以支持模型的death_exact_moment标签；请医跑腿观察加紫鹃口头确认是否需另登记入口；李纨/雪雁在结尾继续料理与S6参与者范围；药铺接力是否在ordinary_care范围；未逐一注册的普通道具；照护/等待重复、人物声音及情感效果。作者新增的叙事不能作为填补历史UNKNOWN的新证据。

活动计划为 `review-v3/manifest.json`。两位正文盲读只读完整新正文、协议和空骨架；合同/状态分两组，每组读完整新正文、完整局部模型及三份完整合同。分组最大完整读集与预留129281字节，低于131072；指令和输出各预留16384，token仍未实测。不把作者自查、另一读者意见或其他版本交给盲读者。合同组未获分配的三合同、原史料和语料应列未读；两组汇总前不声称整回全覆盖。

本轮没有启动这四位读者，四项均NOT_STARTED，0份独立正文意见；`review/`是未派发父稿材料，显式不选。标准骨架为本次局部研究协议，不伪造成正式agent-panel发布意见。此前8位范围读者的授权和意见不重复计算。下一步在本版输入准确SHA双版本CI成功且获启动授权后，按最多3并发派发；失败/未读原件保留，顺序最多重试两次，不由协调者代写。无需本地外部worker适配器。

## 复核入口

```bash
python artifacts/local-trial-ch86-20261110/verify_trial.py
python artifacts/local-trial-ch86-20261110/prepare_review.py --check
pytest -q tests/test_prompt_view.py tests/test_writing_lineage.py tests/test_local_scenario.py
pytest -q tests/test_session_generation.py tests/test_generation_feedback.py
rcwh validate
```

共享视图/谱系/局部模型96项回归、会话生成/反馈132项回归已通过，rcwh validate输出PASS并退出0；后两项原输出分别见session-feedback-tests.log、repository-validation.json。真实稿件历史保管、当前兼容性和读集核验见 `verification.json`；仓库CI已新增实际试稿验证步骤。提交前结果与本次提交后的准确SHA CI分别记录，不以基线CI替代本版CI。所有工程PASS仅限所列保管/兼容/预算检查；语义、文学、范围和production仍未授予，stable与真人准入没有变化。
