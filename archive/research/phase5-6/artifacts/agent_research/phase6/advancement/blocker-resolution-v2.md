# 模型级审阅与机械修复结果

日期：2026-10-18。MODEL / NONE / RESEARCH_ONLY。不是human/provider认证，不是release PASS。

## 本地机械修复

已修复共享sample reader的真实歧义缺陷：`src/rcwh/workflow/agent_panel.py`严格处理JSON/JSONL carriers；多个`segments/samples/sources`容器或非list容器拒绝，binding hash、唯一ID和text digest继续强制；AgentRelease复用同一helper。旧source compatibility custody因代码字节变化改成版本化`ch86-research-inputs-v3-compatibility.json`，旧v1/v2不覆盖。

- 定向测试：41 passed。
- checkpoint31：1841 passed、1 skipped，validate PASS；4656输入无漂移，325 protected未变，快照已清。
- 一次fresh final-evaluation-v2尝试因自动执行/共享工作区权限分类而未形成输出；未把它宣称完成或失败，正式v1 evaluation仍是唯一最终评估。

该修复只说明程序不再因错误container unwrap制造一类误报；不撤销历史19 corpus负面，也不证明PDF/source/human acceptance。

## 四路模型审阅

### Policy
`model-policy-audit-v1.json` SHA `daef55370e5c3f37a5114899fc867a51a094d349bee8ecc1ac0df08ad81d07b9`：绑定最终packet、4变化candidate/package/contracts和5 mandatory P-Locks；24条literal evidence；MODEL/NONE/PENDING、NO_OVERALL_PASS、identity/isolation未验证。最终policy semantic/identity/release仍PENDING。

### Contract
`model-contract-audit-v1.json` SHA `9a6513a37ac9e03db114dcc4e603352e1082fa5ed534b817f77189fbfc38fe79`：20合同逐项分开declared compatibility、deterministic replay、prose semantic replay；4 deterministic PENDING、16 NOT_CHECKED；prose 19 NOT_CHECKED；95-S3-R2具体FAIL保留。无world执行推断。

### Corpus
`model-corpus-audit-v1.json` SHA `e0a3700cab98a0c978792a541f6b1205955e7915539bee79c6a33f403357d5b2`：102/102样本membership/text digest、5/5 exemplar绑定机械核验；保留reader历史71 PASS/31 FAIL，19 CORPUS_PEERS仍FAIL；MODEL/NONE/PENDING、human false、isolation NOT_PROVEN，不清corpus真实性或unknown witnesses。

### Source
source subagent因API timeout未形成新报告，不能将其失败当审阅PASS/FAIL。既有`source-range-adverse-findings-v1.json`和86 carrier closure矩阵继续作为原记录。

## 当前可达状态

- 95具体合同FAIL保留，未修改正文/合同/package。
- 95/96熟粥—生米保持UNKNOWN/INPUT_CHANGE_DEFERRED，未换算。
- 86三source carriers、source authority、19 corpus negatives、policy semantic、contract prose/runtime、human/provider/author context、literary adoption仍PENDING/FAIL。
- human-only source/corpus/P9 schemas未接入模型报告；没有把subagent改写为INDEPENDENT_HUMAN。
- 仍未commit、未push、未build、未stable activation。用户选择不提交。
