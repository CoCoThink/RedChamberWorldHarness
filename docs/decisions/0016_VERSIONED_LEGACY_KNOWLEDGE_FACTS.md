# ADR 0016：歧义知识事实的版本化迁移

状态：迁移边界已采用；v0.4 知识载体和显式运行时选择已实现。本 ADR 不改判旧合同、不授予 production。

## 决定

旧事实 `daiyu_death_exact_moment` 不映射到任何一个 v6 局部事实，也不映射为多个事实的无损别名。保留旧知识文件、旧场景合同、历史写作请求及其审读记录的原始语义和字节。旧 `C1-DEATH-KNOWLEDGE` 继续为 `PENDING`，直到按其原始合同和资格协议重新审查；v6 意见不得追溯改写旧意见。

任何后续运行模型若需表达第86回的死亡知识，必须使用新的、版本化的事实定义和绑定记录，至少区分“知道死亡发生”“知道亲历者所述的相对经过”“知道可测量的确切死时”及“知道生理细节/医学死因”。旧 ID 只能作为旧版本中的历史引用；解析器不得把它静默别名到新 ID。新请求仅绑定自己选用的版本化知识投影及其依赖闭包，不因治理文件变化重绑既有请求。

本 ADR 只规定迁移边界。它不声称旧模型已迁移、新模型已完成语义审查、旧 C1 已通过，或人物/事件模型已获得 Evidence Truth。

## 依据

- `data/knowledge/v03_slice2.json` 将旧 ID 标作“黛玉死亡的确切时刻”，入口把三人列为 `does_not_know`；`K86-DEATH-OCCURS` 与 `K86-BAOYU-LEARNS-AFTER-ARRIVAL` 又分别把紫鹃、宝玉更新为 `knows`。场景 YAML 的守卫仍引用同一 ID。
- v6 将死亡事实拆为 `death_occurred`、`death_relative_account`、`death_precise_time`、`death_physiological_detail` 等独立命题。两份 amendment-v3 原读者意见均认可其局部边界，但均将 `OLD_FINDING` 评为 `PENDING`，理由是没有严格等值映射；协调处置没有更改这一状态。
- 候选正文第36段“雪雁出去以后，我还托着姑娘，气就没了”支持目击者陈述死亡发生及相对经过；它不提供钟点或可测量的精确死时。因此，旧 ID 若按字面取“确切时刻”解释，不能从该陈述推出；若按“得知死亡发生/听到经过”解释，又与字面和现有守卫不同。当前证据无法选择一个不丢信息的唯一映射。

复核时绑定的材料摘要：

| 文件 | SHA-256 |
|---|---|
| `data/knowledge/v03_slice2.json` | `37db9f32aad64636f33eb70a73130160260914e8a4ca987e03f6c45170fa88e7` |
| `data/scenes/ch86_last_night.yaml` | `30fab56f00c242eeeabccfb0a216864b1eb4d4d5eda9d833d32b114527a780fa` |
| `data/writing/local-scenarios/ch86-v6/scenario.json` | `670b6b13c9db0440a8b46e25cd4445880bb06af32c8a2374e0ee47c291bb75b5` |
| `artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md` | `7d5a3513aead66682c2102a0270346bd1468748aa3ca7fc2dce5afa263082206` |
| `artifacts/local-scenario-ch86-knowledge-split/amendment-v3/review/opinions/semantic-1.json` | `721e696109762fd3ccaf0e52f1bede576a53bd541492b7e2dbf6353a405a65fb` |
| `artifacts/local-scenario-ch86-knowledge-split/amendment-v3/review/opinions/semantic-2.json` | `f38f40d977e0fd8482fe9fa9c9b6e991acc35e26529ac355531810b642bc3ae1` |

## 实施状态与后续步骤

已实现 `data/knowledge/v04_ch86.json` 作为独立知识载体，由 `CharacterKnowledgeRuntime.from_version(..., "v0.4:ch86")` 显式加载。迁移生成器固定 v0.3 来源摘要；验证器核对旧字节未变、生成内容确定、v0.4 图完整，且旧 ID 未成为别名。CI 运行该验证器。默认 `from_repo()` 仍选择 v0.3，现有场景投影和写作请求也仍绑定 v0.3；因此本次交付没有切换写作请求，也没有声称 v0.4 已完成语义审读。

1. 为新版本生成面向请求的窄知识投影，并由新的请求记录直接绑定该投影及其校验摘要；这一步完成前不得在生产写作请求中选择 v0.4。
2. 为新版本执行场景状态回放、知识守卫变异测试和逐条语义复核。旧 C1 另按原始合同重审，不能用新版本的局部 PASS 自动结案。
3. 在旧引用全部具有明确历史版本解析前，任何兼容层对旧 ID 遇到新语义都必须拒绝或报告歧义，不得猜测。

完成上述迁移并取得所需审读前，研究模型和第86回写作准入仍为 `NOT_GRANTED`。
