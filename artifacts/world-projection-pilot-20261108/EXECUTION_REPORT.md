# World局部依赖研究试点

基线873c768，分支research/world-projection-20261108。[事前设计](../../docs/plans/WORLD_PROJECTION_20261108.md)先于实现，规则见[ADR0012](../../docs/decisions/0012_RESEARCH_WORLD_PROJECTIONS.md)。本轮没有生成新正文、重绑原20回、修改world载体或改动任何既有审阅/研究版/stable材料。

实现独立WORLD_PROJECTION v1材料协议，复用已有v2请求和内容快照；默认renderer仍为2，v1/v2旧请求的解释保持原样。投影文件保存实际选中字段及查询，绑定规则实现摘要；原始载体摘要仅进入独立创建回执。包校验及请求重新准备会按查询复算，因此新增相关事件/知识不能因没有旧ID被漏掉。相关事实变化使当前STALE，新导入被拒绝，历史快照仍可读取。

只支持无可执行scene的研究骨架。renderer拒绝旧v1、混合world、错章、遗漏活动合同明确参与者以及可执行SceneStateAdapter。研究骨架participants:null保持未知，不伪造人物注册。关系、制度、地点、全局状态、来源和长线保守全量；这些变化仍可使多个试点失配，不能宣称world全部局部化或范围完整性已验收。

活动包是`data/writing/packages/ch87-world-projection-pilot-v3.json`，投影明确选11位人物，包含活动合同声明的全部参与者及黛玉、元春和平儿的关联上下文。[创建结果](preparation-v3.json)及[实际DRY_RUN请求](prepared-request.json)均保存。实际请求403301 UTF-8字节，无原始m3文件绑定；这是字节数，不是实测token。没有模型调用、usage、账单或正文生成声明。v1/v2包为开发过程中算法升级前的真实创建快照，当前已失配，仅留历史，未用于起草。

[真实包变更实验](real-package-mutations.json)在一次性git克隆中运行当前宿主实现和明确覆盖的工作树材料，报告绑定三个实现文件和包；不冒充未提交代码来自克隆HEAD。实验使用真实prepare/verify链，无模拟包校验：无关人物、未来事件和无关事件保持完全相同请求；相关基线状态和新增相关事件都STALE。旧整文件包在无关人物修改下作为对照确实失配。临时克隆退出后清理，真实world不改。

[182项局部检查](tests.txt)通过，覆盖新增组知识、规则变化、实体删除、未知字段、布尔版本伪装、历史快照读取、当前相容性、导入拒绝、冻结父稿修订及消费者拒绝。测试正文/导入只在临时fixture中，不计入真实写作或同行信用。[仓库完整性](repository-validation.txt)与[原20回谱系](original-20-lineages.json)均PASS；原请求仍保持原world绑定，没有静默迁移。

后续先审定人物/事件范围，再扩展可执行场景的object与knowledge入口和场内checkpoint，细化全局关系/地点/长线的查询范围，并建立新的请求/包版本和实际审阅。机制试点不授予文学、人工、P9或生产/stable准入。全量测试、资产检查与提交结果按实际完成另行记录。

全量本地测试实际1859 passed、1 skipped（406.62秒）；462资产、534来源的require-tracked及相对873c768版本检查PASS，无findings。见[完整验证绑定](local-validation.json)。本轮CI新增同一真实包变更实验，仍保留v5原提交历史重建、v6当前提交严格重建与双Python全量测试。最终准确提交的CI结果在推送后核对，不用本地检查预造绿灯；最终答复提供实际run。
