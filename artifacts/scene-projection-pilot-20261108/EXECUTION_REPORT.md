# 可执行场景局部依赖研究试点

基线a91e999，分支research/scene-projection-20261108。先记录[实施计划](../../docs/plans/SCENE_PROJECTION_20261108.md)，设计决定见[ADR0013](../../docs/decisions/0013_SCENE_INPUT_PROJECTIONS.md)。本轮扩展可执行场景输入机制，没有生成或改动真实正文、重绑原20回或改变既有审阅和发布材料。

新增独立SCENE_INPUT_PROJECTION v1材料协议，复用请求/renderer v2，内嵌未改动的WORLD_PROJECTION v1。当前准备与复核重新扫描真实场景、物件图和知识事件前缀，新增相关场景、关系、交接或知识事件也会被发现。载体摘要仅进入创建回执；投影保存实际消费值、查询、合同、事实定义与实际宿主规则摘要。不是只从摘要列表删掉大文件。

renderer对本协议从冻结投影读取entry，不调用全局SceneStateAdapter，不绑定world/objects/knowledge原始载体；实际场景合同仍绑定。feedback_report对本协议用冻结知识片段构建runtime，并显式生成v2语义请求，事实注册不等于人物已知。旧请求、旧world试点和旧反馈仍走原解释。

物件按显式选择及identity/containment关系递归闭包，保留独立身份，不自动合并雪中玉与通灵玉。网络状态和legacy登记的状态、位置、来源分别保存；物件ENTRY到前回末，合同entry_state标明SCENE_LOCAL_RECONSTRUCTION_INPUT。命名物件transition仅用于同回且属于选择闭包的检查点，重放其前缀；没有章内时序的legacy桥接物遇命名物件检查点拒绝，不会用静态暖药碗覆盖已重放冷状态。

知识保存本场景全部参与者、入口四桶、显式检查点前的事件及引用事实定义；合同和guards要求的检查点不得遗漏。入口、已知、相信、怀疑与不知道保持分列。知识事件时钟和物件transition时钟独立，不推断同步。所有前缀均检查冲突，不能靠后续移除掩盖早期冲突。未知实体、事实、检查点、缺端点关系、重号/歧义时序、未知载体顶层字段及范围遗漏拒绝。

真实活动包为`data/writing/packages/ch86-scene-projection-pilot-v2.json`；[查询](query-v1.json)显式选5位world人物、第86回唯一可执行场景、药碗及ENTRY物件时点和4个知识检查点。[创建结果](preparation-v2.json)及[实际DRY_RUN请求](prepared-request.json)保存原字节，实际请求431610 UTF-8字节，非实测token。没有provider调用、usage、账单或新正文。开发v1原型的包、投影、请求和变更报告保留历史；增加关系端点拒绝后规则已失配，活动工具仅选择v2。

[真实包变更矩阵](real-package-mutations.json)在一次性git克隆中运行宿主实际实现和显式覆盖的工作树材料。报告绑定宿主规则，不冒充未提交实现来自克隆HEAD。无关物件、未来交接和其他场景知识变化保持完全相同请求；新增相关前回交接、legacy状态、新知识前缀事件、选中事实定义和新增同回场景使当前失配。原载体不改，结束复核恢复后的原请求。

[216项定向测试](tests.txt)通过，覆盖身份关系递归闭包、不合并节点、检查点前后区别、删除实体和桥接、遗漏范围、历史导入/读取及当前失配。历史反馈测试在临时fixture中实际导入临时短文本，再修改和删除当前知识载体，证明语义请求和检查仍使用同一冻结知识；不计为真实作者、独立读者或正式正文。命名物件章内检查点用fixture验证；本轮真实86包只使用物件ENTRY，不宣称真实药碗具有已核定章内时序。

[原20回谱系](original-20-lineages.json)、[原87 world试点](previous-world-pilot.json)、[仓库完整性](repository-validation.txt)及[资产完整性](assets-validation.json)均按实际结果保存。资产检查462资产、534来源，require-tracked及相对a91e999检查PASS，无findings。`tests-initial.txt`保留闭包预期少算未来包含节点的测试失败；修正预期后通过。`full-tests-interrupted.txt`为补齐规则时主动中止的较早测试，不计作最终验证。

范围限制：world全局关系、地点、制度与长线仍保守全量；物件图闭包跨章，故未来的相关关系边也可能扩张当前范围。知识全局policy、来源与规则保留；人物/物件范围完整性尚未审读。未登记world人物或缺knowledge scene不自动补造状态。真实正文状态、文学质量、人工史料、P9、production与stable仍按原门控。本轮工程试点不能替代这些资格。后续先审定实际范围与跨系统时点，再细化保守全局依赖、扩展真实章内物件样例及开展文学窄读。

本轮也没有解决大合同/来源原文造成的提示词体积问题。[大小观察](size-observation.json)仅统计字节与文字数量，不是实测token或上下文准入；不能因为局部依赖检查通过就启动大规模模型调用或声称审阅读集已符合预算。

最终本地全量测试实际1890 passed、1 skipped（428.49秒），见[完整日志](full-tests.txt)及[验证绑定](local-validation.json)。本轮CI加入真实可执行场景变更矩阵，保留原87试点、v5历史重建、v6当前版重建及双版本全量测试。提交与准确HEAD的双版本CI在推送后实际核对，不预造CI绿灯；最终答复附实际run。
