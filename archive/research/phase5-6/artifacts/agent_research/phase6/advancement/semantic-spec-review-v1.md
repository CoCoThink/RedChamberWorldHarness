# 语义规格实现前审查修正

MODEL/NONE。一个模型context对`semantic-capability-spec-v1.md`第5–7节及现有`agent_policies.py`只读审查；未实现、未测试、未改变release gate。以下为协调者保存的审查摘要，不回写原规格冒充其自始正确。

## 必须修正的设计缺口

1. **自引用hash**：reading不得含指向自身raw JSON的raw_submission hash。原始payload保持不变，其raw-byte binding放detached envelope。request_sha256须明确排除自身的versioned canonical preimage；context／manifest亦分别定义无环preimage。canonical JSON不能冒称原始提交字节。
2. **身份／父子crosswalk**：source pointer不唯一代表policy义务角色，同一source可生SEMANTIC／FORBIDDEN_DRIFT等不同root。root使用policy文件path/hash/数组pointer定位，source basis另存；child保留精确source pointer、role和多向crosswalk。不得按相同source pointer合并root；建dict前拒重复key。
3. **完整展开**：289 roots加20 features不等完整语义原子覆盖。以versioned显式展开规则处理受支持结构，保留完整原value；metadata不能自动变候选要求，自由文本拆分仍是有归属的解释。未解释条款／未知结构阻止complete，不以checkbox掩盖。
4. **两种依赖范围**：现policy重派生inputs与实际语义reading context分开。后者须按显式selection和受支持义务派生，不信任reader选出的context子集；缺全书context的跨章义务仍未覆盖，旧projection不改。
5. **纯验证器能力上限**：quote／pointer／interval核对只证明绑定及声明覆盖，不能证明认知性实读或自然语言蕴含。分别输出机械完整性、声明覆盖、归属语义意见和未决，不从区间铺满生成语义PASS。原拟议“fake full-reading claim”负测只可查声明的机械矛盾，不能检测内心未读。
6. **负面适用性**：按candidate bytes、规则身份／值和相关实质依赖追负面，不限exact request，否则换包可洗掉。context变更需适用crosswalk，未定映射阻止clear；receipt存在不证明指控属实，完整性错误和语义违例分别报告。未来聚合须消费完整权威registry而非caller的有利子集。

## 最小可实现切片

先仅新增只读policy manifest builder和evidence validator，复用原projection核对，生成确定root／受支持children／anchor观察／forbidden crosswalk。严格parse拒重复键／非有限值，验证raw binding、pointer/value、check key及所有正反quote的exact Unicode范围，不归一化CRLF。

输出机械完整性、结构覆盖、归属意见、解释／适用性未决和原machine anchors分别呈现。延后intake、身份matching、aggregate、合同／event replay、release wiring。`evaluate_agent_policy`保持原样：machine失败仍FAIL，anchor成功仍语义PENDING。SOURCE_ONLY不自动禁词，terminal不变全局suffix限制，标题权威不扩张。

本审查在检查点20执行期间只读进行；其报告与本页保存发生在其后，不追计入20测试覆盖。规格审查已完成，不表示实现已完成或具备真实合格读者记录。
