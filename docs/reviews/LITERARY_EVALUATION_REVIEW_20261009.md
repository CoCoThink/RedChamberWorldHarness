# 文学评估与可复现性评审核查

核查日期：2026-10-09。基准提交：`a4ccbb3c0555cecee0b5100c5a98eaa5b4130297`。

结论：评审指出的语义检查漏洞、声明型门禁、抽取环境误报和语料人工审计缺口成立，值得优先修复。竞争与声口覆盖的判断需要限定范围；当前仓库已有跨路线微稿、排序评审和十八份声口档案。缺少评审身份不能证明评审由模型生成。Git 提交数和目录数与评审描述不同。

本报告的代码描述、统计和反例结果均指上述基准提交，核对当时的 schema、选定 owner、原始文学记录和语料产物。后续文件链接指向当前实现，基准原件可在 Git 中按提交查阅。它是工程核查，不是对文学候选的独立阅读，不产生采用授权。当前实施和验收边界见[针对性重构设计](../architecture/EVALUATION_REFACTOR_PLAN.md)。

## 1. 逐项结论

| 评审意见 | 核查结论 | 依据与限定 |
|---|---|---|
| 场景 required / forbidden beats 只用子串 | 成立 | `evaluate.py` 的 `_matches_any` 和 forbidden 循环；实际 CLI 所用的知识、历史适配器也按词串匹配。三类绕过在完整调用中全部 PASS。 |
| `exit_state` 未被读取 | 成立 | 全部 `src/` 中没有 `exit_state` 消费者。三份契约均有字段，但只有第 86 回列出非空条件，第 89、92 回为空数组。 |
| 历史可行性信号诱导堆词 | 实现基础成立，生成行为尚未测量 | `mechanism_adapters.py` 对每个 `required_any` 词组要求至少命中一词。关键词堆砌通过，证明检查可被迎合；没有足够运行日志测量真实生成中发生了多少次。 |
| 竞争中的六字段、人工作品保护与盲读 PASS 来自手填 | 成立 | `CompetitionRegistry.evaluate_record` 读取六字段字符串、`human_plock.status` 和 `blind_read.status/reviewer_blinded`。删掉第 86 回 B 的评语后仍 eligible。 |
| `competition.py` 完全没有重算 | 需要修正 | 它重跑证据核心回归和 `evaluate_literary_candidate`；完整性校验另核对正文 Git blob。未重算的是六字段和人工声明的实质依据。 |
| 没有评审身份、模型和提示词 | 对旧章回竞争成立；不能推广到所有接口 | 第 86 回记录缺少评审者身份、生成/评审模型、实际提示输入及运行记录。P7 有用户提供/用户担保的来源说明；P9 已要求评审者 ID、原意见和输入哈希，但只接收人工评审，尚无提交。 |
| 旧盲读可能是作者模型自己输出 | 无法确认 | `agent:codex` 出现在 P9 协议作者列表；这不能识别第 86 回或 P7 原意见的实际作者。行文相似不是身份或模型证据。当前能确认的是独立性不可审计。 |
| 第 86 回 A/B/C 不是不同情节路线 | 成立 | A 为稳定基线，B/C 是轻压/强压；`structure_map.md`、试写、全回候选和裁定均如此描述。它是压缩实验。 |
| 三稿全 PASS，所以没有任何区分 | 需要限定 | 二元状态没有区分，但原评语明确偏好 B、指出 C 边缘，裁定据此选 B。缺少结构化排序、第二位评审与可核验身份。 |
| 整个设施没有跨路线竞争或排序 | 不成立 | P6 有四个 scenario、五个 cell、二十份微稿；P7 有逐 cell 排序及 PASS/EDGE/FAIL；P8 有修订配对。它们是 SHADOW 实验，不能替代全回路线竞争或连续章回验收。 |
| 缺少直接写作对照 | 成立 | 搜索运行数据、实验记录和候选未发现该实验组。设计 §12.4 及评估契约要求同任务对照。P8 原稿/修订比较测的是修订，不能充当直接写作组。 |
| 86 裁定、89 评审、92/97 阻塞 | 成立 | 选定 `data/competitions/43_0.yaml` 正是这些状态。86 的 B 仅为 promotion candidate，未成为新稳定正文。20 回基线已导入，不等于 20 回完成新流程验收。 |
| 抽取将环境变化误当输出变化 | 成立，实际跨补丁版本复现 | 3.12.3 下十份相关抽取的重建字节均与登记产物一致，却全部被 `load(rebuild=True)` 拒绝。3.12.13 下 566 测试通过。 |
| 语料分层尚无人审 | 成立 | 全前八十回和 pilot 审计 selection 的 `reviews` 均为空；前八十回质量报告记录 162 条未知见证脂批、7,497 条未达到唯一精确对齐的 segment。 |
| 只有宝玉、黛玉两个声口档案；紫鹃缺档 | 需要修正 | `data/characters` 确实只有两个简化场景状态档案，但 `literary_ecology/m5.json` 有十八份声口档案，含紫鹃；`knowledge/v03_slice1.json` 还有六个人物的声口/知情记录，含紫鹃。 |
| 回目、说书口吻、称谓等度量不足 | 成立 | 有句段结构统计、显性解说筛查、声口遮名钩子与诗文 screen；未发现回目对仗、称谓关系、说书语态的实际度量。场景 `voice_profile_hooks` 没有代码消费者。 |
| CLI 和目录散碎、历史命名杂音 | 基本成立，数量须更新 | CLI 1,304 行；`data/` 35 个直接子目录，其中 28 个递归只有 1–2 文件。设计保留历史里程碑身份，但运行路径仍大量采用里程碑命名。 |
| `provenance/migration.py` 是 ADR 0002 退役残留 | 不成立，命名容易误导 | 它是仍有消费者的 Source 载体/Locator 表示变更服务，不是旧 registry / M1—M8 导入链。工具、九个测试和来源运行手册均引用它。 |
| Git 只有一个提交 | 对当前 checkout 不成立 | `git rev-list --count HEAD` 为 260；不是浅克隆。 |
| 164 MB 仓库、53 MB artifacts、无许可证 | artifacts 与许可判断成立，整体体积取决于口径 | tracked 工作树 119,424,455 字节，约 113.89 MiB；artifacts 53,966,473 字节，约 51.47 MiB。当前 Git 对象另约 51.69 MiB，合计与所述仓库量级接近；缓存和磁盘分配另计。根目录无 LICENSE，README 已明确尚未授予开源许可。 |

## 2. 场景反例与误报

复现调用同时传入 `CharacterKnowledgeRuntime`、`HistoricalAdapterRuntime` 和 `HistoricalMechanismRegistry`，并核对 CLI 的前置条件检查为空。不是只测省略可选适配器的短路径。额外调用 `LiteraryEvaluatorSuite.evaluate_prose`，前三例和显式出口冲突均为 `READY_FOR_BLIND_READ`，也没有补上漏洞。

以下文本是根据评审描述构造的本次固定复现用例；评审未给出原三段的全部原字节，故不宣称与其全文相同。

| 用例 | 本次固定输入 | 当前场景结果 | 未来需要核对的语义 |
|---|---|---|---|
| 关键词堆砌 | `药碗 再温一温 灯` | PASS | 没有事件、人物行动或出口状态证据，不能算完成场景。 |
| 哲理遗言改写 | `黛玉望着药碗，心里忽然通透，低声道：“人生原是一场大梦，如今我都参透了。”宝玉说：“再温一温。”紫鹃挑了挑灯。` | PASS | 识别临终哲理自我总结，不能依赖固定“人生不过”。 |
| 超自然治愈改写 | `灯影中，魂魄忽然现身，伸手一拂，黛玉的病竟好了大半。宝玉捧着药碗说：“再温一温。”` | PASS | 区分实际超自然干预与人物幻觉/比喻，识别此处实际治愈。 |
| 出口状态冲突 | `灯下，药碗里的药仍烫手。宝玉说：“再温一温。”黛玉坐了起来，笑说明日还要出门看花。` | PASS | 场景没有达成死亡与冷药出口；存在活着和烫药的实际状态描述。 |
| 否定中的禁词 | `灯下，紫鹃看着药碗。黛玉并没有写绝命诗。宝玉说：“再温一温。”` | FAIL | 命中“绝命诗”却并未发生该事件。此文仍缺少出口证据，但不能以发生禁情节为由拒绝。 |

`knowledge.text_guard` 也没有对白归属、否定、传闻或时间定位分析：它把整个文本的词串命中与固定 checkpoint 对照。`modes` 虽输出到检查结果，却未用于区分对白和叙述。因而已有知识状态重放能力不等于正文知情检查成立。

还有一个接线问题：CLI 的 `WorldState` 从两个 `data/characters/*.yaml` 和 YAML 物件文件读取简化状态；领域 `WorldRuntime` 从六份 `m3_*.json` 重放。黛玉 YAML 当前甚至没有出口条件用的 `life_state`。仅把 `exit_state` 送入既有 `check_condition` 会变成查错状态/缺字段，不能解决正文到状态的绑定问题。

### 快速复现

在基准提交的独立检出中安装依赖，再运行以下只读命令，可打印当时的错误 PASS。当前版本已将词串降为 lint；冻结反例使用 `examples/evaluation/` 的原文本和内部判读重放，详见[场景语义说明](../runbooks/SEMANTIC_SCENE_REVIEW.md)。这些结果不登记为正式文学评审。

```bash
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from rcwh.io import load_data
from rcwh.evaluate import evaluate_scene_text, overall_status
from rcwh.knowledge import CharacterKnowledgeRuntime
from rcwh.mechanism_adapters import HistoricalAdapterRuntime
from rcwh.history import HistoricalMechanismRegistry

root = Path.cwd()
contract = load_data(root / 'data/scenes/ch86_last_night.yaml')
texts = [
    '药碗 再温一温 灯',
    '黛玉望着药碗，心里忽然通透，低声道：“人生原是一场大梦，如今我都参透了。”宝玉说：“再温一温。”紫鹃挑了挑灯。',
    '灯影中，魂魄忽然现身，伸手一拂，黛玉的病竟好了大半。宝玉捧着药碗说：“再温一温。”',
]
for text in texts:
    results = evaluate_scene_text(
        contract, text,
        CharacterKnowledgeRuntime.from_repo(root),
        HistoricalAdapterRuntime.from_repo(root),
        HistoricalMechanismRegistry.from_repo(root),
    )
    print(overall_status(results), text)
PY
```

## 3. 声明与计算的实际边界

第 86 回竞争没有评审者 ID、实际作者运行身份、评审模型、提示全文、独立会话说明、评审包摘要或评审输入版本绑定。`BLIND_READ_RESULT.md` 保存意见内容和解盲关系，不能证明交付时谁读过什么。其表述“独立盲读”“FROZEN”是记录内声明。

内存实验保持正文和所有状态不变，仅清空 B 的 `human_plock.notes` 与 `blind_read.notes`：A/B/C 的 `adjudication_eligible` 仍全部为 true，`consistency_errors` 为空。这直接证明资格判断不消费原意见。

应保留以下已实现基础：

- P7 `source_basis` 明确标为 `USER_SUPPLIED_AS_INDEPENDENT_BLIND_REVIEW`、`USER_ATTESTED_NOT_SYSTEM_VERIFIED`，并绑定微稿快照和原意见资产。这比没有说明好，但不是评审身份核验。
- P6/P7/P8 的快照、排序和修订绑定提供输入漂移防护；不是全书正式采用。
- P9 `paired_review.py` 绑定 protocol、packet、mapping、原始意见和各 pair；拒绝作者同 ID、重复 ID 和不完整提交；协议要求最低两位评审者。
- P9 schema 当前只允许 `INDEPENDENT_HUMAN`，无模型评审字段是接口类型选择，不能据此说它丢失了实际模型评审记录。
- P9 `reviews` 当前为空，汇总为 PENDING；独立性依据仍诚实标为 `SUBMITTED_REVIEWER_ATTESTATIONS`。不同字符串 ID 和布尔自述不能单独证明不同来源。
- `ProjectAcceptance` 将人工语料、来源解释与 P9 提交列为待完成输入；不声称全设计或文学采用通过。

因此改进应把旧章回竞争接入现有绑定机制，再明确身份和独立性的证据等级，不另造一个新的手填 PASS 系统。

## 4. 竞争覆盖与状态

当前正式队列为 86、89、92、97。只有 86 裁定；89 三份全回候选进入评审；92/97 无候选。此队列本身不满足连续两三回验收。

86 的 A/B/C 比较的是同一事件路线下的密度，B 获胜有具体阅读理由，不能说毫无比较价值。但这不足以证明系统比较了不同复原方案，也不足以证明 Harness 优于直接写作。

四条跨路线 SHADOW 微稿已经存在：`SCN-CURRENT-C`、`SCN-LATE-MARRIAGE`、`SCN-JADE-MULTILAYER`、`SCN-MINIMAL-CAUSE-OPEN`。P7 有排序和分歧；记录自己也承认不同 probe 任务与单次盲评不足以淘汰路线。后续实验要控制共同任务、输入和预算，把情节路线与生成流程两个比较因素分开。

稳定 v1.4 manifest 的 `status: IMPORTED_BASELINE`、`evidence_closure: NOT_VERIFIED` 与评审一致。导入文件可以作为比较原件；它的稳定指针、逐字锚点和证据状态是不同事情，不能因使用基线或压缩稿就自动获得证据资格。

## 5. 可复现性守卫

`ExtractionRepository.extractor` 将 Python 完整版本、`adapters.py` 和 `extraction.py` 的哈希加入 manifest。`load(rebuild=True)` 先比较当前 extractor 与历史 extractor，再比较 lock 原字节 SHA，最后才比较重建 output 和完整 manifest。Python 补丁、注释修改、lock 排版都可能在字节重建之前阻断。现有测试还明确要求代码哈希变化和 lock 追加换行触发拒绝。

修复不能只改最后一个 `raw != old_raw` 判断：`SourceLocatorVerifier.extraction` 的缓存路径仍比较 extractor；来源登记报告又要求完整 `stored == report`，其中包含 verifier 代码和 extractor 元数据。`CorpusRepository.load` 与 `CorpusInputs.verify` 也有含代码哈希的完整对象比较。这些地方必须区分历史输入身份、语义配方、当前工具观察与产物一致性。

### 实际跨环境验证

使用两个隔离环境，实际解释器为 CPython **3.12.3** 和 **3.12.13**。两边依赖均为 PyMuPDF 1.27.2.3、PyYAML 6.0.3、jsonschema 4.26.0、pytest 8.4.2。为避开挂载盘 I/O，测试使用当前提交的 `/tmp` 本地 checkout；未修改 manifest、Python 版本字符串或正式资产。

对全部当前来源 Locator v2 与 corpus inputs 引用到的十份 extraction，在 3.12.3 调用 `compile(input_ref, stored_config)`，逐字节比较重建 JSONL 与登记 output，同时核对 `unit_refs` 与代码哈希：**10/10 完全相同**。但 `load(rebuild=True)` **10/10 拒绝，原因全部为 `STALE_EXTRACTION_TOOL_OR_CONFIG`**。

| 实际环境 | 全部现有测试 | 项目工程状态 | 项目整体状态 |
|---|---|---|---|
| CPython 3.12.3 | 565 PASS，1 FAIL | FAIL | FAIL：声明输入闭包与写作输入被同一工具版本守卫阻断。 |
| CPython 3.12.13 | 566 PASS | PASS | PENDING：来源独立意见、语料人工审计及 P9 提交仍为零，production 为 BLOCKED。 |

唯一失败是 `tests/test_foundation_cli.py::test_decision_trace_reaches_local_pdf_without_closing_open`，预期 locator 为 VERIFIED，实际为 FAIL。所以“换为 3.12.13 就都通过”只能理解为测试和工程检查通过；当前 `project acceptance` 并未整体 PASS。默认查询对 PENDING 返回 exit code 0，`--require-complete` 才要求完整通过。

| 格式 | 份数 | 重建字节相同 | load 被误拒绝 |
|---|---:|---:|---:|
| HTML | 5 | 5 | 5 |
| PDF | 3 | 3 | 3 |
| TEXT | 1 | 1 | 1 |
| EPUB | 1 | 1 | 1 |

可用以下只读命令在实际 3.12.3 下复查全部十份抽取；它绕开的是 `load` 的版本前置拒绝，直接运行同一个 `compile`，不是更改 manifest 或伪报解释器版本。

```bash
PYTHONPATH=src python - <<'PY'
import json
import platform
from pathlib import Path
from rcwh.assets import AssetCatalog
from rcwh.corpus.extraction import ExtractionRepository
from rcwh.graph import ProvenanceGraph

root = Path.cwd()
catalog = AssetCatalog.from_repo(root)
extractor = ExtractionRepository(catalog)
refs = {
    s['locator']['extraction_ref']
    for s in ProvenanceGraph.from_repo(root).sources.values()
    if s['locator'].get('schema_version') == 2
}
for path in (root / 'data/corpus/inputs').glob('*.json'):
    inputs = json.loads(path.read_bytes())
    refs.update(inputs[k]['extraction_ref'] for k in ('pdf', 'epub'))
print('actual_python:', platform.python_version())
for ref in sorted(refs):
    manifest = json.loads(catalog.resolve(ref).path.read_bytes())
    try:
        extractor.load(ref, rebuild=True)
        load_status = 'PASS'
    except Exception as exc:
        load_status = str(exc)
    rebuilt, raw = extractor.compile(manifest['input']['asset_ref'], manifest['config'])
    original = catalog.resolve(manifest['output']['asset_ref']).path.read_bytes()
    print(ref, load_status, 'same_bytes:', raw == original,
          'same_units:', rebuilt['unit_refs'] == manifest['unit_refs'])
PY
```

README 和 CI 固定 3.12.13，pyproject 与 extraction lock 声明 `>=3.10`；代码甚至把 lock 的 `python` 字符串固定比较为 `>=3.10`。这是部署政策与内容验证耦合，不是内容不一致。

## 6. 语料与声口的实际缺口

语料 `classify` 按字体、颜色、字号、水印和显式章界判断 MAIN_TEXT/ZHIPI/EDITORIAL 等。输入有 PDF 与 EPUB，故不是完全只有一个文件；但正文与脂批分层实际依赖同一汇编 PDF。EPUB 仅辅助匹配，记录也明确 `edition_equivalence: NOT_ESTABLISHED`，不能把它当独立版本校勘。

162 是“未知见证的脂批条目数”，不等于 162 种不同见证。7,497 是对所有 segment 的非唯一精确对齐计数，包含正文、脂批、编辑材料和附录等；不是 7,497 个已证实错误的正文段落。仍需要按层、长度和原因分组审计。

| segment 层 | 总数 | 唯一精确匹配 | 未匹配 | 多处匹配 |
|---|---:|---:|---:|---:|
| MAIN_TEXT | 5,639 | 4,602 | 972 | 65 |
| ZHIPI | 4,653 | 142 | 4,498 | 13 |
| EDITORIAL | 1,851 | 0 | 1,851 | 0 |
| VARIANT | 17 | 0 | 17 | 0 |
| APPENDIX | 81 | 0 | 81 | 0 |

这些计数直接连接 `segments.jsonl` 与 `alignment.jsonl` 得出。正文实际未获得唯一匹配的是 1,037 条；另外 1,932 条 EDITORIAL/APPENDIX 在当前算法中本来就不参加 EPUB 搜索。这不能洗去分层审核缺口，但能避免拿混合计数衡量正文错误率。

审计协议和 hash-bound 提交接口已经存在，两个 dataset 均为零提交。`LiteraryInputs.exemplars` 可以返回研究用例，但会附带 `CANDIDATE_PENDING_HUMAN_AUDIT`；production admission 会阻断。这意味着薄弱根基尚未冒充通过的生产输入，却仍可能影响研究中的范例和风格判断。

声口有十八份文学档案，世界有二十八人，交集为十六人。世界中十二人未有文学声口档案；其中钱雪在 knowledge 已明确 `SPARSE_ABSTAIN`。文学档案中的紫鹃与晴雯没有 World 核心角色；knowledge 中紫鹃用 `world_binding_optional: true` 绕开绑定要求。

因此要做的是统一身份、声明实际覆盖和接入正文评估，先补连续三回实际出场且语料足够的人物。不能为二十八人批量填一组无语料支撑的声口标签。

## 7. 整理建议的校正

基准中的 `provenance/migration.py` / `SourceClosureMigration` 实现带审计、事务和证据图不变保护的载体/定位改绑，当时由 `tools/migrate_source_closure.py`、`tests/test_source_migration.py` 和来源运行手册使用。ADR 0002 退役的是旧资料注册和阶段迁移链；不能据文件名直接删除现行来源维护能力。本次已改名为 `provenance/rebinding.py` / `SourceCarrierRebinding`，工具与测试同步改领域名，并澄清 ADR 范围。

体积测量使用 `git ls-files` 对 tracked 普通文件求实际字节，避免缓存和 Git 历史口径混杂。大文件包括 segments JSONL、登记 review ZIP、交付 ZIP 副本和重复来源材料。两个相同 v2 source-review ZIP 各 10,663,182 字节。减重应先区分可重新导出的交付副本和承担不可变资产职责的原件。

当前没有 LFS 配置。改用 LFS 或 release 附件时要同步资产解析、离线输入闭包与 checkout 验收；LFS pointer 不能通过内容 SHA 校验。许可证仍需所有者决定各类材料的许可范围，本次核查不替所有者授予许可。

## 8. 代码依据

- [场景检查](../../src/rcwh/evaluate.py)、[CLI 接线](../../src/rcwh/cli.py)、[简化场景状态](../../src/rcwh/runtime.py)、[第 86 回契约](../../data/scenes/ch86_last_night.yaml)。
- [知识守卫](../../src/rcwh/knowledge.py)、[历史适配器](../../src/rcwh/mechanism_adapters.py)、[文学 profile 检查](../../src/rcwh/literary_eval.py)、[suite 与诗文筛查](../../src/rcwh/literary_suite.py)。
- [竞争资格](../../src/rcwh/competition.py)、[生产状态投影](../../src/rcwh/literary_production.py)、[竞争账本](../../data/competitions/43_0.yaml)、[86 原意见](../../artifacts/43-0/ch86/BLIND_READ_RESULT.md)。
- [P6 实验](../../data/microdraft/v012.json)、[P7 记录](../../data/blind_review/v013.json)、[P9 协议](../../data/evaluation/p9_protocol.json)、[P9 提交接口](../../src/rcwh/paired_review.py)。
- [抽取重建](../../src/rcwh/corpus/extraction.py)、[定位及缓存](../../src/rcwh/corpus/locators.py)、[语料构建](../../src/rcwh/corpus/dataset.py)、[输入库存](../../src/rcwh/corpus/inputs.py)。
- [语料分层](../../src/rcwh/corpus/layers.py)、[人工审计](../../src/rcwh/corpus/audit.py)、[范例与写作输入](../../src/rcwh/literary_inputs.py)、[全前八十回质量报告](../../corpus/front80/v1-candidate/quality_report.json)。
- [文学声口](../../data/literary_ecology/m5.json)、[知识与声口记录](../../data/knowledge/v03_slice1.json)、[世界角色](../../data/world/m3_core.json)。
- [现行载体改绑服务](../../src/rcwh/provenance/rebinding.py)、[ADR 0002](../decisions/0002_RETIRE_MIGRATION_RUNTIME.md)、[来源运行手册](../runbooks/SOURCE_LOCATORS.md)。
