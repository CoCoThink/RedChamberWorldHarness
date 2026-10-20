# 八十回后研究写作：审阅、修订与采用执行计划

日期：2026-10-21。状态：执行中；二十五项已完整登记，继续全量审阅。授权：用户要求「撰写详细计划后，再开始执行」。

## 1. 目标与范围

以已经选中的第 81–100 回二十回候选稿为基础，执行真实模型同行审阅，保管原始意见，处理异议，按需要修订和复审，最后计算研究版采用及发布资格。正文工作由实际阅读发现的问题驱动；不预设全部接受、全部重写或文学优于既有基线。

当前已有 20 回候选、85 份选定合同，候选稿合计 191,974 个字符（其中汉字 163,323）。当前稿件评估为 0 FAIL、20 PENDING；PENDING 来自同行意见和协调者决定缺失。字节完整性、篇幅、作者链、当前写作输入、写作包、安全策略和正文完整性均通过。

本次只推进模型研究轨道。来源独立人工审核、语料人工审计、P9 盲评及 stable 准入分别验收；研究结果不改 stable/ACTIVE，也不证明原作复原或 Harness 的因果文学收益。

## 2. 固定基线与入口

| 项目 | 本轮入口 |
|---|---|
| 运行时基线 | `84a56120b67de60cb1d816b09a14ffe815d755dc` |
| 既有 CI | https://github.com/CoCoThink/RedChamberWorldHarness/actions/runs/39442706273 |
| 环境 | CPython 3.12.13，仓库锁定依赖；CI 同时覆盖 3.12.3 |
| 发布请求 | `data/agent_release/research-81-100-v1/request.json` |
| 分派计划 | `data/agent_release/research-81-100-v1/review-campaign-v3.json` |
| 连续性索引 | `data/agent_release/research-81-100-v1/reading/book-segments-v2.json` |
| 执行协议 | `docs/runbooks/AGENT_RECONSTRUCTION.md`，ADR 0005–0008 |

开始时把 commit、request/campaign SHA256、工作树状态、计划任务数、审阅基线状态与实际执行根目录写入执行记录。运行时代码已经提交、推送并通过双版本 CI（各 1785 passed、1 skipped），本计划文档不改变任何审阅输入。

使用由该基线创建的独立 Linux worktree 降低文件读取开销；实际输入与主工作区一致。每个读者只收到该 worktree 绝对路径和本任务 assignment，不继承协调者对话或其他读者意见。最终把计划、执行记录、原始输出、意见、回执和快照提交回主分支，并核查输入摘要与 stable 字节。

## 3. 角色与材料

| 类型 | 任务数 | 必读与检查 |
|---|---:|---|
| CHAPTER | 56 | 分派的候选稿、写作包、政策、合同；比较正文支持、人物知识、叙述声口及场景因果。拆开的合同任务仍附正文和写作包 |
| CORPUS | 2 | 固定语料记录及全部已分派样本投影；核对分类、正文边界与使用资格 |
| SOURCE | 10 | 独立来源记录、引文和载体上下文；用图片工具逐张检查 `inspect_images`，检查位置、转录和见证归属 |
| BOOK | 8 | 81–87、87–92、92–97、97–100 四段，各两位读者；段内完整通读，逐一检查分派的接缝 |

每个 required subject 分派两位不同身份、不同新会话的模型读者。模型和会话身份属于声明，不冒充独立人工或可证明的上下文隔离。作者、修订者、保管者和协调者不计自己的同行阅读。

文字预算每项 197 KiB，当前最大 192,287 字节；图像每项最多四张、合计不超过 6 MiB。字节数不是实测 token 或完整阅读保证。读者必须通读 `read_in_full`，不能以摘要、搜索命中或文件哈希替代阅读。无法读全或看清图像时逐项 NOT_CHECKED，明确未读文件、章节或图像。

## 4. 阶段 A：执行前记录

1. 确认固定基线与 CI，检查主工作区和执行 worktree。
2. 保存 request、campaign 摘要以及只读 `review-status`。已有 ASSIGNED 必须恢复实际任务或记实中断，不重复派发。
3. 验证 76 项、无超预算、每个 subject 双读、19 处接缝覆盖完整。
4. 执行记录保存在 `artifacts/agent_research/review-campaign-20261021/`；状态报告必须注明观察时点，不能以固定百分比替代当前命令。

本阶段完成条件：输入可解析、基线清楚、无失配及遗漏。实际输入变化时停下旧计划的继续分派；新请求和新计划另存，不覆盖旧证据。

## 5. 阶段 B：首批真实闭环

按 campaign 原顺序领取前三项：第 81 回 r1、r2，第 82 回 r1。并发总数为三（主协调者另占一槽）。这三项与其余任务采用相同正式协议，完成后直接计入整轮。

1. `review-dispatch PLAN --limit 3 --model-label 'current agent environment (declared)'`。
2. 主协调者用环境子代理工具逐项启动，`fork_turns: none`，模型沿用环境路由。指令给出绝对 assignment 和根目录、阅读义务、证据严重度与输出位置。
3. 读者使用 assignment 的准确 scaffold，实际填写每个 subject 和 sample；只写分配的外部临时 JSON 文件，不改仓库、不自行登记。返回该文件绝对路径及摘要；主协调者不代填 verdict 或 notes。
4. 主协调者原样串行运行 `review-register PLAN JOB --opinion FILE --origin ACTUAL_TASK`。程序保管原始字节、输入快照、意见记录和回执。
5. 检查 COMPLETE 与 `needs_followup`，核对 reviewer/session/packet/subject、原始输出和记录关系。

首批放大条件是这条执行与收件链真实成立，不要求读者给 PASS。有根据的负面意见是有效产出；NOT_CHECKED 进入补读。格式错误不能由协调者改写成意见，应退回实际读者修正格式或按真实故障处理。

## 6. 阶段 C：完成整轮 76 项

按既有 campaign 顺序滚动领取，不同时超过三个活跃读者；全部使用新读者上下文。每当有实际结果就原样登记并释放执行槽位，继续领取。下表是无重试时的三项批次边界；故障、补读和耗时差异可改变实际组合，精确分派以 assignment 为准。

| 计划批次 | 任务 ID（每项一位新读者） |
|---:|---|
| 1 | `CHAPTER-81-000-r1`、`CHAPTER-81-001-r2`、`CHAPTER-82-002-r1` |
| 2 | `CHAPTER-82-003-r2`、`CHAPTER-83-004-r1`、`CHAPTER-83-005-r2` |
| 3 | `CHAPTER-84-006-r1`、`CHAPTER-84-007-r2`、`CHAPTER-85-008-r1` |
| 4 | `CHAPTER-85-009-r2`、`CHAPTER-86-010-r1`、`CHAPTER-86-011-r2` |
| 5 | `CHAPTER-86-012-r1`、`CHAPTER-86-013-r2`、`CHAPTER-87-014-r1` |
| 6 | `CHAPTER-87-015-r2`、`CHAPTER-88-016-r1`、`CHAPTER-88-017-r2` |
| 7 | `CHAPTER-89-018-r1`、`CHAPTER-89-019-r2`、`CHAPTER-89-020-r1` |
| 8 | `CHAPTER-89-021-r2`、`CHAPTER-90-022-r1`、`CHAPTER-90-023-r2` |
| 9 | `CHAPTER-91-024-r1`、`CHAPTER-91-025-r2`、`CHAPTER-92-026-r1` |
| 10 | `CHAPTER-92-027-r2`、`CHAPTER-92-028-r1`、`CHAPTER-92-029-r2` |
| 11 | `CHAPTER-92-030-r1`、`CHAPTER-92-031-r2`、`CHAPTER-93-032-r1` |
| 12 | `CHAPTER-93-033-r2`、`CHAPTER-93-034-r1`、`CHAPTER-93-035-r2` |
| 13 | `CHAPTER-94-036-r1`、`CHAPTER-94-037-r2`、`CHAPTER-94-038-r1` |
| 14 | `CHAPTER-94-039-r2`、`CHAPTER-95-040-r1`、`CHAPTER-95-041-r2` |
| 15 | `CHAPTER-96-042-r1`、`CHAPTER-96-043-r2`、`CHAPTER-97-044-r1` |
| 16 | `CHAPTER-97-045-r2`、`CHAPTER-98-046-r1`、`CHAPTER-98-047-r2` |
| 17 | `CHAPTER-99-048-r1`、`CHAPTER-99-049-r2`、`CHAPTER-99-050-r1` |
| 18 | `CHAPTER-99-051-r2`、`CHAPTER-100-052-r1`、`CHAPTER-100-053-r2` |
| 19 | `CHAPTER-100-054-r1`、`CHAPTER-100-055-r2`、`CORPUS-shared-056-r1` |
| 20 | `CORPUS-shared-057-r2`、`SOURCE-shared-058-r1`、`SOURCE-shared-059-r2` |
| 21 | `SOURCE-shared-060-r1`、`SOURCE-shared-061-r2`、`SOURCE-shared-062-r1` |
| 22 | `SOURCE-shared-063-r2`、`SOURCE-shared-064-r1`、`SOURCE-shared-065-r2` |
| 23 | `SOURCE-shared-066-r1`、`SOURCE-shared-067-r2`、`BOOK-shared-068-r1` |
| 24 | `BOOK-shared-069-r2`、`BOOK-shared-070-r1`、`BOOK-shared-071-r2` |
| 25 | `BOOK-shared-072-r1`、`BOOK-shared-073-r2`、`BOOK-shared-074-r1` |
| 26 | `BOOK-shared-075-r2` |

每批更新登记数、未读任务、负面意见数、故障和剩余任务。共享来源和语料意见通过所选依赖进入各回报告；不重复伪造多份共享阅读。

BOOK 全部为 ADVISORY，缺失和异议照实展示，不新增机器门控。协调者另汇总跨段的人物、物件、称谓、日期与伏笔问题；接缝全覆盖不等于任意远距离呼应已全部核查。

## 7. 故障、恢复与补读

- 429/500/502/503/504 或真实中断按协议处理，每轮最多三次尝试，前两次退避 5、10 秒；故障原件保留，失败尝试不计阅读。
- `review-fail` 必须携带准确 `--assignment-sha256`，保留真实错误内容。超时或丢失先停止原任务，再记实中断，不能同时保留两个活跃读者。
- 服务故障持续时处理其他可执行任务，报告 FAILED/EXHAUSTED。修复原因后用 `review-reopen --reason` 明确开新轮，不自动无限重试。
- NOT_CHECKED/PENDING/UNVERIFIED 是补读线索。实际补读使用新会话，保留逻辑读者及 supersedes；旧记录不删除。
- 输入已变必须建立新版本；只在 packet、subject 和实际输入未变、双读资格满足时复用已有完整意见。
- 如发现收件、快照或归属方面的程序缺陷，保留失败现场，先修复实际阻塞并完成相应回归，再继续。无需因为出现一条文学异议而改 Harness 门控。

## 8. 阶段 D：协调者阅读与异议处置

收齐后分别报告「收到有效意见」「实际读全」「存在阻断异议」「具备采用条件」，不得把 COMPLETE 当作文学 PASS。

协调者逐回阅读全部相关 candidate、package、contract、source、corpus 意见及 prior-context 异议，再参考 BOOK 意见。建立问题台账，每条保留原记录、精确位置、证据、严重度、影响章回、处理选择和理由。

- 字节/结构失败与 A-W1 支撑的 LOCKED MUST/MUST_NOT 违反，以及有效 BLOCKING 负面，需修复并真实复审；协调者理由不能直接解除阻断。
- 规划偏好、P-Lock 替代方案、风格、节奏和历史可行性建议按适用证据层级裁决；不能为了保住原稿改变读者原话或严重度。
- 既有第 95 回说话人、第 86 回时序、第 99 回贾芸语体及当票痕迹列为待核线索，先检查当前文字再决定修订或说明保留理由。
- 对全部负面意见留下逐条理由；新意见进入后更新旧决定的覆盖。分组合同、共享来源和语料异议不得遗漏。

本阶段产出：逐项问题台账、每回处置说明、受影响正文与依赖清单，以及真实绑定全部相关意见的协调者决定。结论可为 ADOPT/REJECT/PENDING，不能预设全部采用。

## 9. 阶段 E：针对性写作与复审

先处理阻断、明确的日期/称谓/物件/知识矛盾，再决定声口、节奏和口味建议。按连续两三回为一组安排修订，明确每组前文状态与后文影响；保存原稿和原始反馈。

每份实际修改建立新 draft/父稿/编辑归属。切换写作包另开请求，不把重绑会话列为新正文作者。修改后的 selection、edition、packet、读本和 campaign 使用新路径；未变材料在满足资格时复用有效意见，已变候选、合同或上下文由真实读者复审。新正文须重新检查长度、结构、历史保管、当前相容性和章回政策。

复审发现新问题时继续有依据的有限修订，不以达到预定轮数自动宣告通过。若无法消解阻断，保留该回及整版 PENDING/FAIL 和具体原因，其余不受影响的研究可继续。

## 10. 阶段 F：验收、构建与提交

1. 重新计算 review-status、写作历史与当前输入、agent-release evaluate，保存可复核报告。
2. 完整通读与双读覆盖、原始意见和快照可验证；异议与协调者决定绑定正确；BOOK 按原 ADVISORY 策略呈现。
3. 研究版门控 PASS 才构建所选研究版正文。尚有缺项时只构建 `.pending/<edition>/<revision>/manifest.json`，不标成已采用正文。
4. 核对发布作者链、二十回覆盖、实际选择及 stable/ACTIVE 字节。不得以修改全局进度或审核选择制造通过。
5. 将计划、真实审阅证据、修订和决定提交、推送，执行相应完整性检查和 CI。若仅新增意见而无运行时代码修改，不为意见内容编写镜像测试；使用已有校验器验收。

完整设计验收、正式人工准入和 stable 所有者决定保持各自状态。结束报告给出实际完成数、未解决问题、已采用/待定章回及具体文件，不将模型阅读结果宣称为原作真实性结论。

## 11. 当前执行记录

- 初始观察：76 PENDING、0 正式意见、0 协调者决定。
- 详细计划完成后才启动首批；后续结果写入本次执行目录，不预填 PASS。
- `status-003.json` 检查点：12 COMPLETE、3 ASSIGNED、61 PENDING，无 needs_followup；21条负面结果均为 ADVISORY，未修改候选或生成采用决定。执行记录与存储完整性 PASS。

- `status-004.json` 检查点：25 COMPLETE、3 ASSIGNED、48 PENDING，无 needs_followup；34条负面结果均为 ADVISORY，原件及存储完整性仍 PASS。
