# 第86回局部编辑模型实施

本轮在main `3e4e79f`基础上落实8份范围意见及协调选择，直接在main迭代，无新分支/工作树、无外部模型API。基线的[CI 42675113297](https://github.com/CoCoThink/RedChamberWorldHarness/actions/runs/42675113297)已双版本成功；它只验证基线，不能替代本次提交自己的CI。

## 实际产物

- [scenario.json](../../data/writing/local-scenarios/ch86-v1/scenario.json)：9名局部模型角色、6件受检器物、24个事件节点、5条显式消息链；已有角色只选id/name，新身份限定local:ch86命名空间。
- 六份v3局部合同保留原必写/禁写描述与精确引用，另选入口和事件检查点，不用种子列表编号充当事件钟。厨房/药铺劳务、米汤/热水衣物/书写用具/火箸茶盘保留叙事用途和受检升级规则。
- [dispositions.json](dispositions.json)：30条原声明、25项UNKNOWN和52条未决逐条保存；局部编辑值另列，不将其登记为Evidence Truth解决。原v2合同、旧20回、旧请求和全部原始审读不变。
- [checkpoints.json](checkpoints.json)：实际回放出的25个检查点（含ENTRY）。只包含祖先及自身；若另一支线的写入与当前节点没有先后，显示UNKNOWN_AT_UNORDERED_CUT并列出事件。不同支线向同一目标写入却没有排序时直接拒绝。
- [preparation.json](preparation.json)绑定新包、精确准备请求及计数payload导出回执；[request.json](request.json)保存完整task和保管信息，实际作者只接收export.payload。作者请求不绑定全局world/objects/knowledge/scenes载体、closure_roots、未选伏线或整份协调审读目录。

## 具体边界与新增编辑选择

病危消息与请医反馈分链。发送者在发送前须已知消息内容，接收者在因果晚于发送的送达节点才能更新；宝玉到场、问药、获知确切死亡经过三个节点分开。确切死亡经过与“已经死亡”在同一次送达中分别更新，不出现“知道死时但不知道已死”。未受检的角色知识初始化为UNKNOWN，不推断他们无知。

温药初始可为warm，放下之后的中间温度不持续追踪，保持UNKNOWN；末端单独确认同一网络药碗为cold且CONTAINS_UNFINISHED_MEDICINE，不声称冷却刚在该刻发生。再温请求没有任何状态效果。legacy药碗独立且局部状态UNKNOWN，不能覆盖网络药碗；稿夹/稿页分开，G01空字永不补，紫鹃不翻稿。

为了使第一轮后事消息链可执行，新增明确编辑选择：请医跑腿在返回后的劳务中观察已死身体，再传死讯给李纨和王夫人；他不因此知道确切死时。李纨获信与进入料理劳务分开，王夫人只登记获信后分派，不声称床边到场。具体房间、路径、时辰、旧整夜场挂接、医者实际到场和黛玉局部行动能力仍未知。这些是本次编辑模型的选择，尚未经独立正文审读。

## 字节预算与执行资格

首次256 KiB总预算拒绝，记录见[budget-rejection.json](budget-rejection.json)，未截断或发布准备请求。检查点采用ENTRY基值加逐键覆盖的无损视图，已有shared-view再合并重复值；测试逐项重建全部检查点。中间版测量232909字节，修正知识和中间药温后，最终完整request实测234426字节（包括JSON字符串转义）；加16384指令和32768输出预留共283578字节，低于显式327680字节上限，也低于旧试点350000字节总上限。token容量和实际环境上下文仍未测量；此预算不变更独立范围读者的131072字节上限。

所有事件和检查点均为EDITORIAL_MODEL_ONLY_NOT_OBSERVED / NOT_OBSERVED。局部包仅支持session dry-run/import，provider执行和production入口拒绝；通用feedback对六项返回研究骨架PENDING，不将模型回放冒充正文状态/语义核验。范围研究意见仍不登记为正文正式审读。

## 验证与下一步

相关回归299项通过（包含27项局部模型/CLI/session/谱系检查）；最后的CLI整理后，27项局部测试再次通过。覆盖提前知情、假观察、无知发送者、送达无更新、未排序写入、伪加热、填G01、合并药碗、越界ID、原未知/义务保留、production拒绝，以及真实session导入后历史完整性。无关治理和全局基线变更保持请求；所选身份/局部事件变更使当前兼容性失效，历史仍可读。仓库完整性rcwh validate通过。

真实来源与语料的完整请求重建、导出回执及payload逐字节复核另由 `python tools/verify_local_scenario_ch86.py` 执行，结果见[verification.json](verification.json)。CI已加入此检查。本轮未试写正文；下一步先使用本包完成第86回一回真实试写，再以正文引用核查消息链、身体/器物状态、全部种子义务和文学效果，通过后才讨论扩大。当前scope_status仍PENDING，production/stable未授予。
