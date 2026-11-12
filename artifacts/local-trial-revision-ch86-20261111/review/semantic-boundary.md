# 第86回死亡知识命题边界记录

状态：**边界已记录；语义审查仍 PENDING。** 本记录只界定候选正文实际表达的命题，不修改知识库、场景模型、合同、Evidence Truth 或候选正文，也不替代独立语义审阅。

## 判定

当前共享事实 `daiyu_death_exact_moment` 的标签“黛玉死亡的确切时刻”有歧义，至少可能指：

1. 黛玉死亡这一事件确已发生；
2. 某人在场并亲历死亡发生，或事后听到亲历者讲述；
3. 可确定死亡的钟点、瞬间的生理细节或因果过程。

本候选写到紫鹃说“雪雁出去以后，我还托着姑娘，气就没了”。这能承载紫鹃对死亡发生及相对经过的亲历陈述；宝玉是在到场后听到这一陈述。它没有提供钟点、可测量的生理死时或完整医学因果。相邻叙述顺序也不能单独确定各项照护与报信的精确先后或耗时。

因此，当前审阅只接受命题 1 与有正文支撑的命题 2；不接受从中推出命题 3。由于现有事实 ID 和标签没有区分这些命题，不能据这项范围判定将合同的 `C1-DEATH-KNOWLEDGE` 从 PENDING 改为 PASS，也不能声称上游 UNKNOWN 已被解决。后续模型修订应拆分“知道死亡已发生／亲历或获告经过”与“知道精确死时或生理细节”，分别绑定证据和知识更新，再另行版本化审查。

## 绑定证据

| 文件 | SHA-256 |
|---|---|
| `artifacts/local-trial-revision-ch86-20261111/import.json` | `5e29477069fa0728e9e4fa87f228077051da05d11cd4561fc3206af772895a60` |
| `data/knowledge/v03_slice2.json` | `37db9f32aad64636f33eb70a73130160260914e8a4ca987e03f6c45170fa88e7` |
| `data/scenes/ch86_last_night.yaml` | `30fab56f00c242eeeabccfb0a216864b1eb4d4d5eda9d833d32b114527a780fa` |
| `artifacts/local-trial-revision-ch86-20261111/review/disposition.json` | `ffae6b32e00ccf36de92597f17237f66f302d1111b383f911ea0f92ab1da39fa` |
| `artifacts/local-trial-revision-ch86-20261111/review/verification.json` | `f6fd0f2ceda502050a9bd167462e285123a89c1cce77648e5711754219142750` |

这些摘要固定本记录形成时所依据的候选、知识定义、场景约束和既有审阅处置；任一变化都要求重新核对本记录。

## 与来源、语料门的关系

第86回正文审阅没有分配原始来源或语料样本，不能替它们形成资格意见。核对当前选择记录时，来源审阅 `data/provenance/audits/selection.json` 的 `reviews` 为空；完整候选及 pilot 的语料审阅选择记录均为零条意见。因此来源和语料继续为 **NOT_CHECKED / PENDING**，production 继续 **NOT_GRANTED**。本地环境未安装 `rcwh` 命令，故本次未能运行 CLI 汇总命令；上述状态依据被 Git 跟踪的选择 JSON 直接读取，不把命令缺失写成审阅通过。

边界记录本身不是独立读者意见。继续前应为命题拆分提出版本化模型与影响范围，完成相应语义审阅；来源和完整语料资格审查须另按其原件协议取得并登记独立意见。
