# 三章导入与匿名比较执行记录

MODEL / NONE / RESEARCH_ONLY，NOT_ADOPTED_NOT_RELEASED。

## 实际完成

- 三份完整新pilot正文、作者披露及协调者全文阅读已完成。有效正文字符：86为8075（门7924）、95为9142（8779）、99为9159（8500）；length、重复段落lint及literal anchors通过，policy语义PENDING。
- 全体作者停写后，`tools/import_research_revision.py`串行走正常`import_draft`及fresh验证，三章均PASS。捕获输入分别4536、4541、4546，原输入漂移均空；candidate／prepared_request／run／draft四产物hash与真实parent／共同包核对完成。不是provider或完整输入消费认证。
- 新draft：86 `4786e55fa26717380b4e742aed4c0c6056e25c2022a18f836b902f47874035b6`；95 `4e96e6b9aa83fc1a6e43e26744b6049303cbbdfb22ab376aa5f2c02fcb096639`；99 `2fd7d323f16754c4730ab2a8a3efc845835539033c9f9e27ba0fc2860fb47633`。
- `pilot-reading-inventory-v1.json`与六全文`pilot-comparison-v1/packet.json`已实际冻结，packet SHA256 `4558704e742ce05f5c3ae663a69f3272ac8ee6e9c786f5d2a8289cbde91d1c44`。正文原字节复制，不加编辑说明。映射另存`pilot-comparison-coordinator-v1/`。
- 实际import／packet／handoff／import guard联合20 passed（2.36s）。后加quote／声明覆盖检查与guard回归不是实际读者结论。

## 当前真实阅读状态

两位新非作者模型读者已经启动，各完整阅读六份；reader1按subject正序、reader2全反序。仅可打开public packet、六全文、instructions及opinion schema，不交映射、旧意见、编辑目标或作者disclosure。各只允许新写自己的observations及opinion，写完冻结，不反复抽样读者获取PASS。

此记录生成时两位仍在执行，**没有匿名比较结果、文学赢家、三章采用决议或全20最终处置**。`editorial-triage-prepilot-v1.md`只是已有全书读报下的二十回候选动作，不提前授权全部重写。原selection、全部拒稿／负面、95／96生熟量口径歧义保持。

## 最小核验范围

`check_pilot_readings.py`只核bound bytes、六subject逐一覆盖、声明行区间并集、正反序声明、不同reader/session、非作者session、逐字引用以及不冒称technical isolation；不认证认知、人物理解、文学质量或身份。实际意见全部保留，原始FAIL／REJECT不得省略；false／NOT_PROVEN不升格。

最终评估按原计划F只执行一次普通evaluate，不调用build。复用旧snapshot方法新增可传request/output路径的最小helper；直接复核发现旧式仅检查已捕获路径会漏掉新增输入，且跨平台可能误称Linux，新helper已加重列输入集合与Linux guard，并有定向反例。此时还未运行最终evaluate；15项quote／evaluate guard定向通过不代表最终评估已发生。

完整工程检查点28等两位读者停写与意见冻结后执行，避免边写边快照。无commit／push／build／stable变更。
