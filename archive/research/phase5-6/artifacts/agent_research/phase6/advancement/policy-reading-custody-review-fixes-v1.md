# policy阅读保存模块：复核修正与未完成边界

MODEL/NONE。替代初版slice文档中的三文件发布设计说明；初版记录保留为真实历史，未在项目registry登记过真实意见，因此不涉及旧登记格式迁移。

## 已修正

- 三文件分次发布改为完整bundle：request.json、raw.json、receipt.json先在`.rcwh-cache/policy-evidence-staging/`写全并fsync，再一次rename到固定registry。writer独占／reader共享同一OS锁。发布前中断只留下不参与registry的staging，可重试，不自动删除别人文件。
- 坏／缺receipt、额外顶层symlink不再使可读负面消失；raw能解析的VIOLATED在unverified声明中保留，完整性仍FAIL，不冒认篡改后声明已合格。schema不兼容同理保留可解析原始声明。
- 历史代码／schema／依赖不可重放与原bundle byte custody分开，replay_pending阻止clear但不拦新有效提交。raw/request/receipt损坏仍FAIL。
- 请求非对象[]／null报告错误，不崩溃；registry文件／锁须regular，FIFO拒绝而不read挂死；跨章负面仍可见为history但不误作本章改版crosswalk。
- 同candidate＋policy bytes跨路径／selection保留负面；真实改版仍需适用crosswalk，不自动洗负面。重复origin不新增意见。

## 明确未实现，不能说已闭合

- 仅扫描现存bundle不能检测整包删除；返回`inventory_completeness=PENDING_NO_INDEPENDENT_EXPECTED_BUNDLE_ANCHOR`。未来需独立冻结expected bundle inventory或其他可验证外部锚点；不是以可变caller子集代替。没有该能力不允许资格clear。
- 没有语义真假裁定／正向同行计数／author全部谱系context资格。四组long-v1共同context已按原disclosure字段逐一绑定，但短父稿与协调贡献的完整映射仍未合格。
- 历史schema版本可解析性、跨规则语义适用、所有文件系统恶意并发／整目录破坏均不由当前局部模块证明。locking只协调合作调用，不认证外部身份。
- review工具后到的较早版本报告包含多条已由bundle设计修复的问题，逐条核实际版本而非把旧行号当当前结果。后台review skill曾API timeout；实际采用的是模型直接静态报告和本会话重现／tests，没有把超时算完成审查。

## 验证

最新28项custody定向通过18.14秒，覆盖原始字节、负面并存／跨包／改版、坏成员仍见raw、历史replay后新intake、发布中断重试、reader/writer锁、FIFO、非对象request、schema损坏、顶层symlink、跨章history、无独立inventory锚点。此前联合组71 passed发生在最后五类新增前；最终全套须另跑，不追计checkpoint23。

没有真实policy读者提交、global catalog／source变更、正文改写、gate wiring、commit／push／build／stable操作。
