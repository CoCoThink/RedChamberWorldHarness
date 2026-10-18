# 最小policy验证器代码复核与修正

MODEL/NONE，工程复核，不是语义裁定。原`policy-evidence-implementation-v1.md`记录的初版与测试范围保持，不追改为已含修复。

## 已确认并修正的两处错误

1. **请求比较类型不敏感**：原以Python dict相等比较重建请求，True==1／86.0==86可使被改payload等于原request，而实际canonical hash preimage不同。协调者实际重现`python_equal:true, canonical_equal:false`。现按canonical bytes比较整个request，额外测试schema_version布尔替换、嵌套chapter浮点替换，均拒绝。
2. **跨已读区间误拒**：原quote只允许单一区间包住，合法[8,12)在[0,10)+[10,20)的并集中仍被拒。现统一按区间并集判断完整scope与quote；邻接、重叠、乱序区间均支持，真正[9,10)gap仍拒。区间本身继续严格int且非bool、0<=start<end<=Unicode长度。

未将candidate-only证据、正反polarity语义裁定、每叶单独source basis或独立资格当成已实现：当前slice保留原value／parent／raw binding并明确语义PENDING，后续qualification不能凭这些机械完整性结果通关。

## 测试与历史覆盖

- 检查点21对修复前冻结树实际通过：1727 passed、1 skipped（166.26秒），validate PASS，4143输入无漂移、325保护未变，临时副本已清。
- 代码审查在21运行中只读完成，协调者等待21 result写出后才修代码／tests，因此没有制造输入漂移。21通过不表示这两处错误不存在，也不覆盖之后修复。
- 修复后最新定向组47 passed（31.69秒），包含原release policy guard，git diff --check通过。
- 修复后最终完整验证须另建checkpoint22，不能把21或早期35／82／41计作最新全树结果。

## 不变边界

没有AgentRelease wiring／固定PENDING删除，没有新语义合格意见、负面清除、SOURCE_ONLY禁词化或terminal suffix化。旧policy／合同／选版／prepared／corpus／catalog／stable输入不因本修复变化。新validator的自身hash变化会使此前仅内存构造的request身份变化，必须重建，不能把内存hash旧值宣称当前请求。
