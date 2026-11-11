# 第86回审读后修订 v4

当前候选入口为本目录 `import.json`，正文为 `ch86-authored-v4.txt`。这是同一主会话作者的实际修订，未启动新读者；独立意见 **0**，文学/语义 **PENDING**，来源/语料 **NOT_CHECKED**，production **NOT_GRANTED**。旧稿21条发现、1项FAIL和7项PENDING保留原结论，不能套到新字节或由作者销项。

## 本轮计划及实际实现

1. 核对输入main `5d8c1bc5ce2687e4b039f18cb8f27376431cfe83` 的双Python CI：已success，响应见input-ci.json。这是输入CI，不是本次提交CI。
2. 不改旧模型/合同，另建 `data/writing/local-scenarios/ch86-v2/` 和对应v2包：补列S2的黛玉/雪雁、S4的雪雁及S6的李纨/雪雁；声明具名参与者须列出、匿名照护劳务的有限范围、受检消息/知情/持有/移动须先登记。米汤盛器等仍只评叙事功能，未声称完成其状态回放。scope-delta.json逐条绑定旧/新原件；新模型除合同选择及追加编辑说明外，与原模型相同；六合同除名单和范围声明外不变。
3. 绑定当前父稿、完整21条原始发现与两项非PASS合同义务，另存feedback.json和revision-notes.md。原始意见全文及协调处置均以摘要绑定。未重复放入PASS义务和文件阅读声明，不声称这些未嵌入内容被本次完整消费；原始记录仍完整可追溯。旧作者反馈、style、来源及语料结论未复评，未变为PASS。
4. 实际修订：53段/18243字节降为42段/13526字节，减少25.9%。压缩普通照护、宝钗探病、候医和赶路；保留米汤口角、明日安排、药铺/厨房工作、紫鹃死后失神和冷药。G01以“小院苔痕”“花影后头空着的”定位，黛玉指尖欲揭夹又滑回，紫鹃不翻稿；不补空字、不新增诗、不推断中止机制。李纨接手语气侧重事务；宝玉的米汤半句话是本回眼前反应，不引入虚构共同往事。效果仍需新盲读。
5. 导入为同一真实作者新draft，父稿仍为import-v3.json选定的8a29f5d…；保留请求、payload、真实导出receipt、作者run及不可变blob快照。导入核对曾发现session-id误带前缀导致双重session:，该次回执另存rejected-import-author-prefix.json，原run/draft/blob不改；该次尚未启动的准备manifest另存rejected-review-manifest-author-prefix.json，当前manifest重新绑定正确回执；使用无前缀session-id重新导入，当前import.json必须与父稿principal完全一致。生成新段落账及作者自查24事件/5消息/40义务映射；映射是作者提议，非独立语义验收。
6. 准备新读集，核验后直接提交推送main，按新准确SHA跟踪CI；待输入CI通过再安排新候选的独立复核，不铺开20回。

## 修订请求增长的修复

原revise-v2会把整层父修订任务再次嵌入。本次真实完整请求327276字节，加预留共368236，超过原327680上限；拒绝结果见budget-rejection.json，未派发，未放宽门槛。

新增显式 `--revision-template revise-v3`，选择完整基础写作约束、直接父稿全文、当前完整选定feedback与notes，披露移除的历史wrapper层数。旧全文、旧feedback和旧notes留在不可变父稿谱系中，**不宣称在新请求内或已复评**。只展开结构已知的wrapper；存在未知附加约束就拒绝，避免静默丢失。旧v1/v2字节行为保留，当前及历史验签都用同一选择规则重建。

新payload283250字节，另留16384指令和24576输出，共324210，仍低于327680；正文13526低于输出预留。字节不是token实测，也不是主会话上下文容量或消费证明。复用基础约束不承诺任意未来反馈永不增长，超限仍拒绝。

修订API继承冻结父包v1，本轮不伪装成换包修订。完整scope增量进入已绑定notes，可按父模型无损重建v2；**新审读选择v2**，原证据/UNKNOWN/事件/消息不变。这个边界写入scope-delta和notes，verify.py同时核对二者及新模型/合同，不能把v2 package说成旧父稿原本的输入。

## 完整审读包

最初直接派发缩进JSON使contract-1达148602字节，超131072门槛，被拒绝，见review-budget-rejection.json。现将完整JSON仅移除无意义缩进，另存reading-inputs；reading-views.json逐一绑定7对原件/视图，核验解码后所有值完全相同，无删字段、摘要或截断。读者将读取这些完整视图，不宣称读取源文件原字节。

新manifest为review/manifest.json：两份盲读各含预留47895字节，合同两组分别123199、126748，均低于131072。指令/输出各预留16384字节，token容量NOT_MEASURED。盲读不提供作者自查、合同或旧意见；合同组分别读完整scenario视图、整稿及三份完整合同视图。

所有任务NOT_STARTED；没有用旧稿四份意见填充新任务。后续独立复核须记录真实启动/额外指令字节、实际读集、原始意见和失败，批次最多3位；本轮没有启动或登记新审读。

## 复验入口

```bash
PYTHONPATH=src python artifacts/local-trial-revision-ch86-20261111/verify.py
python artifacts/local-trial-revision-ch86-20261111/prepare.py --check
pytest -q tests/test_revision_selection_v3.py tests/test_revision_templates.py
```

verify的PASS仅限保管、范围增量、当前输入兼容性和预算；不改变文学、语义、来源或生产准入。实际验证结果见verification.json。

本地两组测试分别144项、116项通过（存在重叠，不相加为独立用例数）；仓库 `rcwh validate`、旧稿谱系/准备快照/原意见保管及新稿verify均通过，具体入口见local-checks.json。本次提交CI须按新准确SHA另查，不借用输入CI。
