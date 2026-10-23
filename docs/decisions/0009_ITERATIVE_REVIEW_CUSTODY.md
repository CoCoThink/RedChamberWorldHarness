# ADR 0009：迭代审阅的见证上下文、作者传承与依赖复用

日期：2026-10-23。状态：已实施；研究版v2真实复审与构建完成，克隆重建/最终CI见执行报告。

## 问题

跨页批语的版本起始标记可能在引文前页，只附目标页不足以审查见证归属。连续重绑可能把前次保管会话当成原作者。另开研究版时共享packet ID变化也会使未变来源重复审阅。语料manifest的全量source_record_digest则把不进入产品的书目元数据误当成内容依赖。

## 决定

1. 来源可显式声明`witness.context_units`；prepare加入固定抽取单元全文及原PDF页图，verify精确核对上下文与图像集合。缺省兼容旧包；实际新增阅读仍受文字/图像预算约束。
2. 重绑回执可绑定`previous_rebind_receipt`，递归验证上一所选稿的保管声明，保留原作者、实际修订者、协调编辑与全部保管者。拒绝缺失、不相干的先前声明及回执环。重绑本身不产生正文作者资格。
3. prepare可显式选择旧request；仅当完整subject及coordinator完全一致时保留旧共享packet引用。campaign另外计算实际意见覆盖。正文、来源或上下文变化必须新读；负面意见原件不得改写。
4. 语料仍完整重建所有输入、配置、依赖与全部产品，含quality_report中的source_links。全量来源元数据摘要作为观察值单独披露，只有全部产品逐字节相同时才允许它变化，不改旧manifest。缓存键加入当前来源摘要，真实crosswalk改变仍失败。

## 验收与边界

真实来源纠错需保留旧版错误记录和有效BLOCKING意见，以新来源、新依赖包及准确保管链另开版本；只重绑实际受影响章回。旧版FAIL不能由协调者理由消除。新意见需真实独立阅读，COMPLETE不是文学PASS。

回归覆盖上下文缺失/替换、二次重绑与缺失声明、共享上下文变更、语料元数据与实际crosswalk变更。模型读图不代替人工来源准入。稳定版及ACTIVE不随研究审阅改变。

2026-10-23恢复说明：此前/tmp未提交实现已丢失；本ADR对应当前重新实现及重新运行的测试，以当前提交和报告为准。

真实数据检查已复现：更正红玉批语见证后，20回历史均PASS，19回当前相容性PASS、仅92为STALE_WRITING_SOURCE；语料86产品完整重建不变（CHANGED_WITH_IDENTICAL_PRODUCTS）。92沿v4回执再绑v5，原作者链与两个保管者均可验证；研究版v2已实际完成：30项复用、46项新读，76 COMPLETE；来源纠错双读PASS、20回研究采用与实际build PASS。文学ADVISORY及旧BLOCKING原件保留，未获得正式人工准入。报告位于artifacts/agent_research/review-campaign-20261021/source-correction-evidence及rebind-v5记录。

双版本CI 39892075943 暴露新提取物的已登记Python边界：同版本时toolchain_diff为空，跨版本内容重建仍PASS但新增extractor差异分支。现仅在两侧差异表均精确由各自registered/current stamp推导、重建成功且已有合法CPython观察变化时，从原保存stamp及允许变化的叶重新计算差异表。原注册stamp、依赖、代码和全部内容仍严格比较；不复制任意新差异表，不改历史请求。伪造/缺失差异表、代码漂移及重建失败须继续拒绝。实际双版本资格以修复后的CI为准，模拟版本元数据检查单独标注。

修复后的CI 39900871856在CPython 3.12.3与3.12.13各1808 passed、1 skipped；实际研究版读本及署名链见releases/agent/research-81-100-v2，原生读者、逐项处置和克隆验收见artifacts/agent_research/review-campaign-20261021/rereview-v2。该CI是运行时基线验收，包含新产物的最终提交另跑CI，不混同验证范围。
