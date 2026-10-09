# 场景语义复核

`rcwh evaluate` 将关键词检查显示为 `lint:*`。它们可以提示漏词或解释感，不能建立叙事事件、医学可行性、人物知情或出口。没有带来源的语义判读时整体为 PENDING，退出码 2；实际约束冲突为 FAIL，退出码 1。

## 请求、实际运行与复核

```bash
rcwh semantic prepare data/scenes/ch86_last_night.yaml scene.txt --authors authors.json --output request.json
rcwh semantic run request.json --command 'python /path/to/extractor.py' --producer producer.json --output trace.json
rcwh semantic check request.json reading.json
rcwh evaluate data/scenes/ch86_last_night.yaml scene.txt --authors authors.json --semantic-reading reading.json
```

作者文件是含 principal_id/source_id 的数组。producer 文件标识真实编辑或模型；MODEL 应填写 provider/name/version/family。调用者选择抽取程序，程序从 stdin 读取请求、响应 schema 和 producer，stdout 只输出 `schemas/semantic_reading.schema.json` 规定的 JSON。提示全文和摘要在请求中；运行记录保留真实输入、输出原字节的 Base64/SHA、stderr、退出码和时间。准备/运行的 PASS 仅表示请求或执行完整性。

模型输出归档为 reading 时，在 producer 增加 `trace: {path, sha256}`，绑定仓库内实际 trace 文件。除这个新增绑定外，reading 必须与真实 stdout 一致，producer 必须与所选执行器一致。缺真实运行记录、作者来源未知、同作者来源或同模型族，不取得正向独立资格。编辑记录使用 INDEPENDENT_HUMAN；本会话的标注使用 INTERNAL_AGENT 并保留待外部确认状态。系统核对已提交身份和来源声明，不能证明真实身份。

每个事件引用 Unicode `[start,end)` 原文跨度。实际事件与否定、梦境、猜测、比喻、引用分开；出口按最后实际变化确定。对白不能直接填物理状态。知情须有在先的实际观察或通信事件、观察事实和接收人物，思考或作者填写状态不能建立获知。89/92 回的知情出口通过这条事件链核对。

`semantic check` 重放的是冻结请求，包括其中的知情入口；后来的 World/Knowledge 修改不能改变这个旧请求的结果。判读的事实 ID 须在该场景冻结入口中声明，缺入口保持 PENDING。正式候选资格重新从当前正文、合同和选定 World/Object/Knowledge 入口创建请求，旧请求的 PASS 不授权当前版本。competition 和 promotion 调用同一检查器；原六个声明字段、旧 WINNER 和作者 sidecar 均不能替代语义资格。

## 固定挑战与实际能力的边界

`data/evaluation/semantic_challenges.json` 固定三种绕过、出口冲突和否定诗稿案例。原请求/意见、增加物件网络的第二版及覆盖内心知情断言的第三版均保留；新版本均是明确重新核对后的版本，runtime 不刷新旧意见摘要。CI 通过内部编辑判读重放约束，三个绕过必须 FAIL；否定诗稿不会被当作实际禁情节。

这证明绑定、事件重放和约束检查可拒绝已核对反例。**尚未运行外部模型挑战测试**，不能声称某模型已自动理解这些文本。新改写若没有对应判读，返回 PENDING。模型接入后须保留挑战集上的真实请求/响应，比较误放、误拒、未判定及跨度覆盖；程序 fixture 不是模型效果证据。
