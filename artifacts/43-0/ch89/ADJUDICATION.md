# 43-0 / 第89回｜最终裁定 v1.0

状态：**ADJUDICATED**

## Gate汇总

| 候选 | 六字段 | 机器P-Lock状态 | 人工P-Lock | 盲读 | 结论 |
|---|---|---|---|---|---|
| A | PASS | REPLACEMENT_CASE | REPLACEMENT_ACCEPTED | PASS | 合格基线 |
| B | PASS | REPLACEMENT_CASE | REPLACEMENT_ACCEPTED | PASS | **WINNER** |
| C | PASS | REPLACEMENT_CASE | REPLACEMENT_ACCEPTED | PASS（边缘） | 合格下限 |

三稿的机器 `REPLACEMENT_CASE` 都由同一个既有技术原因触发：P1_TERMINAL要求锚句成为绝对末字，而稳定基线在“谁家的水桶还在井边？”之后仍保留麝月“又是我的”与提灯出门。锚本身并未丢失，人工P-Lock均接受。

## 裁定

**WINNER-B / REVISE-B**

B胜出的原因不是“删得最多”，而是：

- 删除的是重复证明程序规则的第二层说明；
- 保留的是程序与小生活发生摩擦的具体场景；
- 凤姐仍靠问药、问铺盖、管饭、找车显出能力；
- 贾芸仍靠车行风险、等候钱、脚钱显出作用；
- 从“准话”到“只能拿几样”的转折更快；
- 后半回借院、共井、小灶、借物、错枕头、水桶收尾获得更清楚的中心地位。

C的风险是制度摩擦过薄；A的风险是制度规则过度复现。

## Promotion状态

B只进入：

`PROMOTION_CANDIDATE`

**不自动覆盖 stable ACTIVE。**

当前稳定正文仍是v1.4，SHA256仍为：

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

任何真实升版必须另走独立promotion gate。

## 下一压力回

第89回裁定后，43-0顺序推进到：

**第92回｜READY_FOR_CANDIDATES**

第97回继续等待第92回完成。
