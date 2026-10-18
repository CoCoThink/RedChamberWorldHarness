# 剩余阻塞解决矩阵

日期：2026-10-18  
状态：**NOT_ADOPTED_NOT_RELEASED / RESEARCH_ONLY / MODEL / authority NONE**

用户决策：
- 95合同—正文差异：**保留FAIL归档**，不修正文、不修合同、不改package。
- source/corpus/human/provider外部证据：**暂不提供，保持阻塞**。
- Git提交：**不提交**，保持未发布研究树。

## A. 已经闭合的本地工程事项

|事项|状态|证据|说明|
|---|---|---|---|
|四个变化章的真实谱系|RESOLVED|`pilot-imports-v1/`、`extension-imports-v1/`|正常fresh import、parent/package/request一致、原输入无漂移；custody不等文学或资格PASS|
|20回最终研究选择|RESOLVED_RESEARCH_ONLY|`final-selection-v1.json`|20章全覆盖；所有selection effect为READING_ONLY_NOT_ADOPT|
|最终packet绑定|RESOLVED_CUSTODY_ONLY|`final-packet-v1.json`|44 subjects：20 candidate、4 package、20 contract；不是20章全同行通过|
|全书连续阅读|RESOLVED_RESEARCH_READING|外部`/tmp/rcwh-final-reading-b2420fb4/fullbook-reader1-v1.json`|81→100真实顺读；项目内复制曾被权限拒绝，原报告保留；不是human/provider资格|
|最终普通evaluate|RESOLVED_EXECUTION|`final-evaluation-v1/`|一次正常Linux快照evaluate，FAIL、未build、无漂移、snapshot清理|
|工程完整性|RESOLVED_ENGINEERING_ONLY|`engineering-checkpoint-29/`|1838 passed、1 skipped、validate PASS；不授source/literary/release资格|
|stable/current/proposal保护|RESOLVED_PRESERVATION|stable hash与325 originals核验|本轮未改stable/current/proposal及保护原件|

## B. 仍然阻塞但用户明确选择保留的事项

|阻塞|状态|根因|本地可做的事|本轮处置|
|---|---|---|---|---|
|95-S3-R2合同—正文|PRESERVED_FAIL|合同要求“当票压针线盒”；正文写入旧针线匣底；两份最终reader均标具体FAIL|可在新授权分支修正文或合同并重跑完整contract/review/import/evaluate|按用户选择保留FAIL；旧合同、正文、reader FAIL不改不洗|
|95→96“两碗半”|PENDING_INPUT_DECISION|95为熟粥分出量；96为生米投入量；没有共同量器/产出/配额证据|只能做版本化输入决定或接受UNKNOWN；禁止换算和静默删“仍”|保留原反证，`INPUT_CHANGE_DEFERRED`|
|86 exact P-Lock/source carriers|PRESERVED_FAIL + PENDING_EXTERNAL_EVIDENCE|三个dependent carrier仅为项目研究载体；locator/source/human qualification未闭合，两个exact anchors在原选长v1缺失|只能接入真实权威原始载体、locator、qualified review并新建版本谱系|无外部证据，不改source/status，不waive|
|19章CORPUS_PEERS|PRESERVED_FAIL|原registered model/corpus negatives仍有效；容器读取bug的机械诊断不等于原负面撤销|可修共享容器reader并回归；若要clear需新corpus/exemplar/peer/adoption分支|当前reader实现与回归已有；保留旧FAIL，不重算为PASS|

## C. 本地代码可改但当前不能合法清除发布门的事项

|事项|状态|为什么不能在本地模型批次中清除|
|---|---|---|
|Policy semantic consumer|PENDING_NOT_IMPLEMENTED / NOT_AUTHORIZABLE_HERE|现有`policy_evidence.py`只做结构、引用、机械检查，semantic/identity/release仍PENDING；完整consumer需289 obligations、20 P-Lock features、negative crosswalk、qualified readings。实现代码不产生人类/provider资格或语义真值|
|Contract declaration/replay/prose|PENDING_NOT_IMPLEMENTED|85合同exit无KNOWN、65 checkpoint unsupported、13 narrative-only；现有prose replay明确NOT_CHECKED。代码可聚合，不可从正文相似动作生成runtime事实|
|Author/context identity|PENDING_INCOMPLETE_MAPPING|四组long-v1是声明组，不是认证runtime context；短父稿与provider身份未闭合|
|CANDIDATE_PEERS/COORDINATOR_DECISION|PENDING|最终意见是MODEL、isolation false、human false；panel负面优先且不能靠多数覆盖；没有合法ADOPT decision|
|Tracked input closure|BLOCKED_BY_USER_DECISION|严格closure要求正式输入/config/schema/code/output Git tracked；用户本轮选择不提交。不能伪造tracked或把未提交树当正式release输入|

## D. 外部证据／权限才能解决的事项

|事项|状态|需要的真实输入|
|---|---|---|
|12 source independent-human reviews|PENDING_EXTERNAL_EVIDENCE|原始载体/图像或权威facsimile、locator、Source→Claim→Decision→Implementation审计、独立人类审阅|
|Corpus human acceptance / P9 paired review|PENDING_EXTERNAL_EVIDENCE|独立于builder/authors且mapping unseen的合格人类评审；确认layer/locator/context/unknown witnesses；原负面保留|
|Human/provider qualification|NOT_AUTHORIZABLE_HERE|可认证provider trace、真实context/identity、独立人类提交；模型声明、Git用户、session label、hash均不够|
|Literary adoption|PENDING_EXTERNAL_DECISION|外部合格阅读与owner adoption decision；模型偏好不构成采用|
|Stable release/build|NOT_AUTHORIZED|只有原义所有gate PASS且另有明确build授权才可进行；当前FAIL/PENDING且用户未授权|

## E. 最终结论

“解决所有阻塞”在当前授权和证据条件下不能诚实地变成release PASS。能完成的本地工作已经完成：真实custody、机械验证、容器读取诊断/回归、全书阅读、最终evaluate和归档。剩余阻塞属于具体FAIL、缺失输入、未实现语义能力或外部资格/授权；继续生成正文不能解决它们。

本轮合法终点：保留全部负面与UNKNOWN，保持`NOT_ADOPTED_NOT_RELEASED`，不build、不commit、不push、不改stable。后续若取得真实原始载体、合格人类/Provider评审、95分支所有者决定或提交授权，必须开启新的版本化分支，不能覆盖本矩阵或旧最终报告。
