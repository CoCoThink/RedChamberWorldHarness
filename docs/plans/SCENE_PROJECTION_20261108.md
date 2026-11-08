# 可执行场景局部依赖：实施计划

基线a91e999；本轮先记录设计，再实现、验证和提交。目标是在显式的新包中，将已有world人物投影扩展到真实可执行场景的物件与人物知识；不修改原20回正文、旧请求或WORLD_PROJECTION v1算法。试点选择第86回药碗场景，只准备请求，不生成新正文。

1. 消费者盘点：旧SceneStateAdapter展开全部world人物、全部m4物件和全部YAML登记物，知识读取v03_slice2；renderer绑定这些载体整文件。feedback_report虽保存场景entry，仍重读当前全局知识库。新协议必须同时覆盖作者提示词、当前复算和历史反馈，不能只删输入摘要。
2. 增加独立SCENE_INPUT_PROJECTION v1，作为新包唯一world材料，内嵌未改动的WORLD_PROJECTION v1。查询明确chapter、characters和全部可执行场景path；每场景列出objects、object_checkpoint及knowledge_checkpoints。未知人物、物件、事实、检查点、目标根、重复ID/时序、未知载体顶层字段拒绝；query严格校验，布尔值不能伪装版本。真实场景目录每次重扫，新增/删除同回场景使当前失配。
3. 物件：显式选物件，并按identity/containment边递归闭包，保守保留这些边及全局规则，不把两个身份节点合并。已登记legacy_ref保持独立值和来源，不以别名覆盖网络状态。ENTRY只重放到前回末；明确的同回transition ID作为章内检查点，之前的新相关transition会被发现，后续transition不提前应用。桥接YAML无场内时序，只能用于ENTRY；章内物件检查点遇桥接物拒绝，避免暖药碗覆盖已冷状态。入口条件标注SCENE_LOCAL_RECONSTRUCTION_INPUT，不冒充重放结论。
4. 知识：保留本场景全部参与者、入口四桶、所选检查点之前的事件前缀及所有引用事实定义；发现新增前缀事件，检查重号/未知事实/桶/冲突。保守保留知识全局policy、来源和规则。检查点列表必须包括ENTRY及合同/guards使用的检查点；每个快照显式绑定checkpoint，不把后续知识写入ENTRY。没有对应knowledge scene时拒绝本协议，不能以None假装核验。章内物件和知识时钟各自独立，不推断它们具有跨系统同步关系。
5. 消费接口：新renderer从已复算的场景投影取entry及checkpoint视图，不调用全局SceneStateAdapter，也不绑定原world/objects/knowledge载体；仍绑定实际场景合同。所有明确参与者、required_objects与状态目标必须覆盖。反馈对新协议用冻结知识片段构造runtime，不能退回当前知识库。旧renderer v1/v2、旧投影试点与旧反馈分支保持原解释。
6. 验证：物件/知识不相关变更保持完全相同请求；相关baseline、桥接值、前缀新事件、事实定义、合同与规则变化失配；删除、重号和范围遗漏失败关闭；ENTRY/章内时点与跨回前提不混用。用真实包prepare/verify、临时导入与历史反馈证明当前失配不破坏冻结历史。临时克隆进行真实变更矩阵，原载体不改。
7. 实际交付：保存第86回新包、显式查询、投影、创建载体观察回执、DRY_RUN请求、变更报告与本地检查。运行原20回谱系、资产完整性、必要测试及全量测试，提交推送，再确认准确HEAD双版本CI。原87试点仍须通过。不授予正文语义回放、文学、人工、P9、production或stable资格。

范围限制：world全局关系/地点/制度/长线仍保守全量；物件关系边闭包和全局规则亦保守。查询人物和物件范围完整性尚待实际审读。可执行场景的已登记状态不等于候选正文真实发生。下一步才细化全局范围及开展文学窄读。
