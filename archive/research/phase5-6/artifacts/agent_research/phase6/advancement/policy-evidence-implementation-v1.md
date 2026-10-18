# 最小policy证据验证器：实现范围

MODEL/NONE；这是已批准P3工程切片的实现记录，不是新release／叙事产品或语义资格报告。

## 已实现

- `src/rcwh/evaluation/policy_evidence.py`：`build_policy_evidence_request(root, selection, chapter)`与`check_policy_evidence(root, request, raw_reading)`，均只读，不调用provider／catalog／世界状态写入。
- `schemas/policy_evidence_reading.schema.json`：严格提交格式，拒额外overall PASS、raw自引用或人类资格字段。
- `tests/test_policy_evidence.py`：真实20policy清单、合成隔离reader fixture、绑定／引文／覆盖负测、无写入回归与原86选版FAIL保持。

实际20章内存构造保留289 PROJECTED_ROOT、1935 STRUCTURAL_VALUE_NOT_AUTOMATIC_REQUIREMENT、20 PLOCK_FEATURE、14 ANCHOR_OBSERVATION、38 FORBIDDEN_ALIAS。1935只是结构值，含metadata，不把它们当1935条创作要求；289+20也不冒称自由文本最终原子覆盖。

root由policy path/hash/数组pointer定位，不按source pointer去重。完整原value与source basis保留，forbidden crosswalk指已有FORBIDDEN_DRIFT root。P-Lock子feature单独保留；所有结构叶／空容器留痕，不把复杂条款拆解冒称已获语义认可。

request hash明确取不含自身request_sha256的canonical payload；context／manifest分别hash。raw阅读hash在外部binding，提交不需hash自身。校验时按显式selection重建request，变candidate／policy／projection输入／选集／book candidate／validator／schema均失效。

UTF8 bytes hash与Unicode[start,end)分开，CRLF不归一化；正反引文均核原文件、范围、read_scope。strict JSON拒重复键、NaN／Infinity及指数溢出非有限数。路径复用现有仓库confinement／禁symlink。缺check为声明覆盖PENDING，重复／未知key、错quote／旧hash拒绝。

## 有意保留的边界

- 声明范围铺满和表格填满只能得到declared_structural_coverage，不能证明认知实读、引文蕴含或合格独立身份。
- 所有有效记录semantic_status、identity资格和release_gate_eligibility保持PENDING；原machine anchor失败使本检查status FAIL。
- 归属VIOLATED与counterevidence原样返回，不擅自裁成已证语义FAIL；也不会因不计正向资格而删负面。
- intake、完整author lineage解析、负面registry聚合、跨context适用crosswalk、语义原子拆分、合同prose／runtime、release wiring均未实现。没有把这些未实现能力写成PASS。
- 现有`evaluate_agent_policy`、AgentRelease、legacy/human lane、旧prepared／source／corpus／stable未接入此模块，也未改变。

## 当前实际测试记录

初始35项定向通过27.79秒。随后扩展组82项通过147.91秒（捕获时的tests版本）；之后新增负测的最新policy-evidence＋release-guard组41项通过30.18秒，git diff --check通过。这些是定向工程结果，不是最终全suite，不是实际读者提交。fixture里全部SUPPORTED故意只引同一短字，以证明精确引文／覆盖不能自动变语义PASS，不能拿fixture作真实文学证据。

本批实现不追计入checkpoint20。另有只读模型代码审查在进行，其发现与最终批次验证须另记，不预报通过。
