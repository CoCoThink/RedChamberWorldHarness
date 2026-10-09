# 章回竞争评审的输入与当前资格

本接口接入现有六字段、P-Lock、盲读门禁。它核验意见的提交完整性、输入绑定和身份声明，不自动判断文学质量，也不能证明读者实际身份或实际未见映射。旧的 `six_field`、`human_plock`、`blind_read` 和 `workflow_progress` 保留为声明，不再直接授予当前资格。

## 1. 准备真实作者和协议

竞争记录可增加 `review_protocol: {path, sha256}`；候选增加 `authors` 和 `review_records`。正文语义意见可通过 `semantic_readings` 绑定，流程见[场景语义复核](SEMANTIC_SCENE_REVIEW.md)。路径均为仓库内相对路径，禁止外部路径和符号链接，SHA-256 为文件原字节摘要。

作者记录使用 `principal_id`、`source_id`、`kind: HUMAN | MODEL`。所有候选的作者都参与独立性核对，不能用另一候选的作者评当前候选。来源标识应稳定表示实际人或实际生成来源，不能为了独立性换别名。

MODEL 作者还需要绑定 `run: {path, sha256}`。日志按 [candidate_model_run schema](../../schemas/candidate_model_run.schema.json) 保存实际模型提供者、名称、版本、家族、会话、完整提示词及摘要、实际输入输出与各自 SHA。目前这个接入口要求模型输出原字节与候选一致；经过后续人工修改的文本不能直接复用那次运行当作最终正文日志。不得给历史候选补造运行记录或推测作者身份。HUMAN 作者无需虚构模型字段。

协议按 [candidate_review_protocol schema](../../schemas/candidate_review_protocol.schema.json) 保存 `schema_version: 1`、`id`、`minimum_reviewers`（至少 2）、实际 `questions`、`authority_effect: NONE`。修改协议需要重新评审。

## 2. 导出匿名正文

```bash
rcwh competition <competition-id> --review-packet <new-repository-relative-file.json>
```

先在记录中登记真实协议绑定。命令向新文件写入匿名正文、token、正文 SHA 与问题；遇到已有文件拒绝覆盖。标准输出给协调者返回 `context_sha256`、协议绑定、`packet_sha256` 和检查字段名称。读者只接收匿名文件，作者映射由协调者保管；新增问题也经过匿名元数据检查。新提交的 `packet.path` 与 `packet.sha256` 绑定该文件；使用 `literary-suite blind` 导出的旧目录包不能冒充此接口的包。

上下文摘要覆盖所有候选正文、匿名 token、作者记录、冻结基线、P-Lock 和当前 project/reconstruction/world/knowledge/objects/scenes/literary_eval/plocks/mechanisms/mechanism_adapters/provenance 数据。候选或这些上下文改变，旧意见不能取得当前资格。评语、手填状态与 `review_records` 自身不纳入上下文，避免循环摘要。

## 3. 接收原始意见

意见使用 [candidate_review schema](../../schemas/candidate_review.schema.json)，包含：

- `report_kind: REVIEW_OPINION`，匿名 token、正文与上下文 SHA，协议和匿名包的 `{path, sha256}`。
- 读者的 `principal_id`、`source_id`、`kind: INDEPENDENT_HUMAN`，具名独立性与未见映射声明。每个候选至少两名读者；重复主体或来源、与任一作者同主体或同来源均不计有效意见，并报错。模型诊断不能计入两名独立真人读者。
- 既有八项判断：PROVENANCE、ROLE、MODALITY、TARGET、PLACEMENT、IMPLEMENTATION、HUMAN_PLOCK、BLIND_READ。每项有结论、理由和实际正文引用，引用位置以 Python Unicode 字符偏移 `[start,end)` 表示；服务逐字校验引用。结论是阅读意见，引用存在不证明意见正确。
- `authority_effect: NONE`。只有 HUMAN_PLOCK 可用 REPLACEMENT_ACCEPTED，且替代案需要每名读者明确接受；其他项使用 PASS/FAIL。

保存读者原始结构化意见文件，再登记带 `id`、`schema_version: 1`、`raw_review: {path, sha256}`、`authority_effect` 的提交文件。原始文件必须逐字段等于提交文件去除这四个归档字段后的内容。提交文件的 `{path, sha256}` 加入对应候选的 `review_records`。保留自由文本附件可以帮助编辑，但不能用无关附件替代原意见绑定。

## 4. 查看计算结果

```bash
rcwh competition <competition-id> --json
rcwh literary-production chapter <chapter> --json
rcwh promotion <promotion-id> --json
```

`machine_report` 标记 COMPUTED_CHECK，词串规则单列为 lint，`literary_quality_verified` 固定为 false。`semantic_qualification` 从当前正文与场景合同核验实际事件、禁止情节、知情与出口；未判读或缺独立来源为 PENDING。`review_qualification` 标记 REVIEW_OPINION，其 status 仅表示提交资格：材料/身份未知或人数不足为 PENDING，绑定、正文引用、独立性违反或否决意见为 FAIL，材料完整且规定读者全部通过才为 PASS。独立性依据明确为 `SUBMITTED_IDENTITIES_AND_CUSTODY_ATTESTATIONS`。两位有效阅读意见也不能覆盖缺失的语义资格。

`declared_gates`、`declared_adjudication` 展示原声明，`adjudication` 展示当前可用裁定。第 86 回明确标记 LEGACY_UNVERIFIED，历史 WINNER-B 仍可追溯，当前资格 PENDING；当前记录虚报已完成裁定会报告一致性错误。不能通过增加历史标记取得资格。

晋升读取同一竞争资格服务。第 86 回现有拼装、正文身份与保护检查仍可通过，当前整体是 PENDING，命令退出码 2；FAIL 为 1，PASS 为 0。`--output` 可将内容检查通过、等待读者的研究候选拼装到新文件，仍返回 PENDING，导出不会授予采用或发布资格。

现有独立来源、语料审计和 P9 比较提交继续使用其原接口，整体项目尚待真实外部提交。当前章回接口不把研究意见升级为来源证据。路线排序与连续三回准备另见[85–87 回研究试点](CONSECUTIVE_CHAPTER_TRIAL.md)，其中内部示例不能充当有效直接写作对照。
