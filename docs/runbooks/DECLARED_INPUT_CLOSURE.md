# 声明范围的输入闭包与目录分片

`data/project/current.json` 的 closure owner 选择 `data/project/closure_roots.json`。配置必须选择 ALL_LOADED Sources；还明确选择七个阅读集合、Review 原件、当前 P6/P7/P8、语料构建与数据集、语料审查协议、P9 selection 和第89回研究写作包。项目评审原件 Review.md 已通过统一入口登记，字节保持不变；新的 Source／语料／P9 人工复核记录尚未取得。

验证器沿本地 Asset 的 derived_from、结构化 Asset 引用及 `{path, sha256}` 文件绑定遍历；Source 实际定位、corpus 实际重建及原有项目 owner 验证同时执行。所有正式输入、配置、schema、代码和产物纳入 Git tracked 检查。URL、旧接收路径只保留出处意义，不能被读取为内容回退；绝对路径、链接、缓存中的正式输入和未跟踪输入拒绝。报告输出明确范围、根集合摘要和实际输入摘要，不代表全书采用或发布完成。

```bash
rcwh self-contained check --profile declared-inputs --require-tracked
rcwh sources verify-all --require-tracked
rcwh sources audit
rcwh sources gap-check --require-tracked --base-ref HEAD
rcwh self-contained check --profile declared-inputs-regression --require-tracked
```

前两项是严格定位／闭包验收。当前32条来源定位检查通过；三条曹家摘录使用故宫005664原件影像的明确代理校录，详见[原件核验](../reviews/CAO_FACSIMILE_VERIFICATION_20261009.md)。声明闭包还要求 `source_evidence_audit` 通过，目前12条代理更正／校录的独立人工复核仍为 PENDING，故完整声明闭包继续失败。后两项约束工程回归；它们保留实际 `closure_status`，不替代人工验收。

`data/project/source_gap_baseline.json` 已删除全部三项临时豁免，保留全部32个固定 Source ID 防止删除 roots。CI 直接要求 `sources verify-all --require-tracked` 通过；`sources gap-check` 另检查固定 roots 与禁止重新扩大豁免。确定性校录定位通过不表示手写字识读已获得独立人工认可。

曹家档案需要公开出处的版本核验、录文校勘和逐字定位；source_evidence_audit 是公开材料的独立复核。两者均不要求盲评。P9 的匿名文学比较单独由 `paired-review` 管理，其评分不作为史料核验依据。

源码和产物尚未提交时，工作树的 require-tracked 检查会失败。隔离验证工具将预期工作树复制到临时 Git 仓库并检出，检验该候选树；不会 stage 或 commit 用户仓库：

```bash
python tools/verify_foundation_checkout.py --output artifacts/migration/new-closure-verification.json
```

报告路径必须新建，不能覆盖过去登记的审计记录。工具核对 CRLF 检出、禁止 CLI 网络及 DNS、运行实际 workflow shell 步骤和完整测试。CI 以已固定的 CPython 3.12.13 安装依赖后进行校验。

## Catalog 分片

当前正式入口是 `data/catalog/catalog.json`（布局版本2）。Asset 和 Origin 分别按完整 ID 的 SHA256 前两位分片，非空分片内按完整 ID 排序；单文件 v1 只用于读取旧 Git commit。迁移前后的233个资产和305条 origin 完全一致。

```bash
rcwh assets index
rcwh assets index --rebuild
rcwh assets validate --require-tracked --base-ref HEAD
```

`assets.index.json` 是布局、各分片及发现元数据的派生索引；无索引或过期索引导致查询失败，重建不能修复正式分片本身的损坏。读写入口、接收事务、tracked 检查和 Git 不可变比较已经切换。混用新旧布局、漏分片、未声明分片、错分片、重复 ID 和越界路径都会失败。后续语料文件进入分片目录；segments 不逐段登记物理 Asset。
