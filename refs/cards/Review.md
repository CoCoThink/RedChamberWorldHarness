我看了现在 `main` 的仓库结构，整体方向已经明显正确，而且相比之前“会话里散落文档、靠路径和记忆拼上下文”的状态，已经跨过了最关键的一道坎：**仓库开始成为事实上的工作母体，而不是仅仅存代码和少量运行数据。**

当前 `main` HEAD 已经是 `8e523c56d73bb6fcc5cb807f9d9811d07176345f`。从设计上看，我会把它评价为：**资产层和来源层已经有了成熟骨架；领域权威边界比以前清晰很多；但“来源闭包、前80语料层、材料可发现性”还没有完全收口。** 也就是说，现在最值得做的不是再搬一批文件，而是把“所有重要文件都进仓库”进一步变成“任何重要结论都能从仓库独立重建”。

目前做得最好的有四点。

第一，`sources/ / research/ / data/ / artifacts/ / releases/ / archive/` 的职责已经基本分开了。`sources/` 存原始输入，`research/` 放研究成果，`data/` 放机器解释和状态，`artifacts/` 放实验与评审结果，`releases/` 放发布物，`archive/` 只保留历史审计。这比以前把“原文、研究报告、运行状态、候选正文、迁移文件”全部混在某一套历史目录里要健康得多。README 和架构文档也已经明确规定了这些边界。

第二，**Asset 和 Source 已经分开**，这是非常重要的一步。现在 `original.pdf`、`original.epub` 先作为不可变物理资产登记，Source 再表达见证、定位和证据角色。这样以后不会再发生“因为某个 PDF 在仓库里，所以 PDF 自己就成为证据判断”的混淆。现在 catalog 还保存 SHA256、字节数、origin、derived-from，这个设计是对的。

第三，大量以前只在交接包或聊天里出现的真正承重材料已经进仓库了。例如我确认目前已经存在：

- 《红楼梦脂评汇校本》PDF / EPUB 原件；
- `红楼梦八十回后佚稿复原_工作底稿_v2.1_最终母本.md`；
- `红楼梦八十回后全幅文学补完大工程计划_v6.0_R4最终放行版.md`；
- `RCWH_文学复原能力升级计划_v1.0_评审定稿_20261007.md`；
- 81—100诗词文书总表；
- 81—100相对时间轴；
- 人物在场矩阵、空间网络、钱物劳务流、玉线物流；
- 81—100二十回全幅补完卡；
- 81—100保护锁与不可破坏细节表；
- 前80人物对白语料库；
- 前80生活物质与家务索引；
- 前80回目结构解剖表；
- 前80章法技法索引；
- 前80诗词文书功能索引；
- 81—100逐回文学增厚卡；
- P7/P8 等独立盲读、实验和修订链。

也就是说，之前我担心 P10 还要“从会话里重新找前80索引”的问题，实际上你另一个会话已经提前把相当一部分这类材料正式入库了。这是很大的进步。

第四，历史迁移包没有继续污染当前 runtime。`archive/imports/`、history pack、origin index、SHA manifest 都保留了，但 README 和 ADR 已明确规定它们不自动拥有当前权威。这个取舍也很好：**历史可以追溯，但历史不能继续控制今天的程序。**

不过现在我认为有五个问题需要优先解决。

### 1. 最大缺口已经不是“文件有没有进库”，而是 **Source closure**

README 自己已经非常诚实地写出来了：

> `source-content` 和 `source-locators` 当前仍显式失败。

现有验证报告里还有：

- `source_content_remaining: 12`
- `source_locator_remaining: 32`
- `full_self_contained_status: INCOMPLETE`

我会把这个排到最高优先级。

因为“所有文件都进仓库”和“仓库可以独立证明自己的证据链”是两回事。

例如某一条 provenance Source 可能写着：

> 某脂批支持某个 literal target。

但是如果它仍然只有 bibliography 信息，或者 locator 写着 `page/parsed_lines` 却没有一个确定性的抽取器可以重新找到那段文字，那么未来换一个会话或换一个模型，仍然会出现：

> “我知道这个结论以前有人证明过，但我现在找不到原文在哪里。”

所以建议下一阶段单独做一个：

**SOURCE_CLOSURE milestone**

目标不是新增研究，而是让所有 active Source 达到：

```
Source → local Asset → deterministic locator → exact excerpt/hash
```

最终最好做到：

```
rcwh sources verify-all
12 missing carriers -> 0
32 unverified locators -> 0
```

这应该比继续做 P9 更优先，或者至少并行。

------

### 2. `sources/project/<hash>/文件名` 很适合机器，但人类可发现性偏弱

现在这种结构：

```
sources/project/c1946d9ff097372a/
  红楼梦八十回后佚稿复原_工作底稿_v2.1_最终母本.md
```

从不可变资产角度很干净。

但是当 project reference 达到一两百份以后，人很难回答：

> “全书规划的核心母本有哪些？”
>
> “前80文学范例有哪些？”
>
> “哪些是证据治理文档？”
>
> “哪些是第89回相关材料？”

目前所有这些很大一部分都只是：

```
kind: PROJECT_REFERENCE
```

它过于宽泛。

我的建议不是重新移动文件，也不是复制一套目录，而是给 Asset Catalog 增加**逻辑分类层**。

例如：

```
collections:
  - id: collection:project:core-masters
    members:
      - asset:...工作底稿_v2.1
      - asset:...工程计划_v6.0
      - asset:...能力升级计划_v1.0

  - id: collection:front80:literary-exemplars
    members:
      - asset:...人物对白语料库
      - asset:...生活物质与家务索引
      - asset:...章法技法索引
      - asset:...回次结构解剖表
```

同时给资产增加非权威性的 tags：

```
roles:
  - MASTER_DRAFT
  - GOVERNANCE
  - FRONT80_INDEX
  - CHAPTER_CARD
  - HISTORICAL_RESEARCH
  - LITERARY_REVIEW
```

这里的 `role` 只是**发现和组织信息**，绝不能自动产生 Evidence authority。

这样以后新会话可以直接：

```
rcwh assets list --role MASTER_DRAFT
rcwh assets list --collection front80:literary-exemplars
```

而不是搜索100多个 SHA 目录。

------

### 3. 现在最需要真正落地的是 `corpus/`

完整设计里其实已经把正确结构写得很清楚：

```
corpus/
  front80/<dataset-version>/
    manifest.json
    chapters/
    annotations.jsonl
    segments.jsonl
    alignment.jsonl
    corrections.jsonl
    editorial_tags.jsonl
    quality_report.json
```

但当前实际 tree 里我还没有看到正式 `corpus/`。

目前你已经有非常好的“前80二级研究资产”：

- 人物对白语料库；
- 生活物质与家务索引；
- 诗词文书功能索引；
- 回目结构解剖表；
- 章法技法索引。

但这些仍然属于**研究者整理的 Markdown 索引**。

接下来最好不要继续让模型直接“读 PDF + 读这些索引 + 自己想办法对齐”。

应该建正式的：

**front80 corpus v1**

例如：

```
{
  "segment_id": "hlm80:ch32:p014",
  "chapter": 32,
  "kind": "MAIN_TEXT",
  "text": "...",
  "asset_ref": "asset:primary:hlm:zhihui:v3.1416:epub",
  "locator": {
    "epub_item": "...",
    "char_start": 12345,
    "char_end": 12661
  }
}
```

再单独保存脂批：

```
{
  "segment_id": "...",
  "kind": "ZHIPI",
  "witness": "...",
  "linked_main_text": "..."
}
```

最重要的是：

**正文、脂批、编者按、异文不能混。**

这一层建成以后，未来 P10、P11、人物声口、章法近邻检索、诗文检索都不再依赖“某会话曾读过原文”。

我会把它定义为当前仓库最重要的基础设施增量之一。

------

### 4. 要建立统一的“新材料入库协议”，否则几个月以后又会重新散掉

现在这一轮大迁移把历史材料救回来了，但如果以后工作方式还是：

> 上传一个文件 → 在聊天里研究 → 过两周再想要不要提交仓库

问题还会重演。

建议以后任何真正承重的输入都走统一入口。

例如：

```
rcwh assets ingest FILE \
  --origin chat:2026-10-08 \
  --role PROJECT_RESEARCH
```

或者：

```
rcwh sources receive FILE
```

建议至少记录：

```
asset:
  sha256:
  original_filename:
  received_at:
  origin:
  media_type:
  intended_role:
  classification_status:
```

然后有三个状态：

```
RECEIVED
CLASSIFIED
BOUND
```

含义分别是：

- **RECEIVED**：文件已经安全进库，不会丢；
- **CLASSIFIED**：已经判断应该属于 primary / project / historical / research / review；
- **BOUND**：已经被 Source、Claim、Plan、Review 等正式对象使用。

这样以后哪怕用户一次上传20个资料，也可以先做到：

> “全部入库，暂时不赋予权威。”

而不是为了整理分类而拖延入库。

------

### 5. 需要防止 `data/catalog/assets.yaml` 最终变成新的巨型单体

目前大约百余资产时，一个 YAML 还可以接受。

但是等到下面这些真正进入仓库：

- 前80 corpus；
- 每次正式 web snapshot；
- 每次 blind review；
- 每轮候选全文；
- 新史料；
- 81—100全书生产；
- 最终 release；

asset 数量很容易从几百变成几千甚至几万。

那时一个巨大的：

```
data/catalog/assets.yaml
```

会产生三个问题：

- merge conflict；
- diff 极难审查；
- 人工定位困难。

建议趁现在还早，预先设计成**分片 source of truth + 自动生成总索引**。

例如：

```
data/catalog/assets/
  primary.yaml
  project.yaml
  historical.yaml
  research.yaml
  reviews.yaml
  releases.yaml
```

或者按 ID 首字母/hash 分片。

然后：

```
data/catalog/assets.index.json
```

由程序自动生成，不人工维护。

这不一定马上迁移，但 schema/API 最好现在就别假设“catalog 永远只有一个文件”。

------

## 我建议把“必须全部入库的重要材料”正式定成 8 类

以后不要再靠会话习惯判断。

| 类别                             | 是否必须进仓库   | 推荐位置                                                     |
| -------------------------------- | ---------------- | ------------------------------------------------------------ |
| 红楼梦原始版本、脂本、汇校本     | 必须             | `sources/primary/`                                           |
| 正式采用的历史一手资料           | 必须             | `sources/historical/`                                        |
| 实际使用的网页资料               | 必须保存固定快照 | `sources/web_snapshots/`                                     |
| 项目母本、计划、治理规范         | 必须             | `sources/project/`                                           |
| 研究报告、历史机制核查、文学分析 | 承重的必须       | `research/`                                                  |
| 前80正文切片和文学范例           | 必须             | `corpus/front80/`                                            |
| 真实人工评审、盲读意见           | 必须             | `artifacts/reviews/` 或结构化 `data/evaluation/` + raw asset |
| 被采用或进入正式竞争的正文       | 必须             | `artifacts/` → Adoption → `releases/`                        |

还有一类容易忘：

**会影响后续决策的聊天结论。**

它不应该保存整个聊天，而应该转化成正式对象，例如：

- 新 evidence claim → `data/provenance/claims/`
- 新 OPEN → OpenQuestion
- 新假说 → `data/hypotheses/`
- 新文学规则 → evaluation protocol / revision target
- 新人工意见 → Review
- 新正式决定 → Decision / Adoption

聊天本身不是长期数据库。

------

## 当前仓库里我最喜欢的一个设计变化

是这一句：

> Markdown 是解释与阅读视图，编辑文档不改变证据或采用状态。

这是后面整个项目能不能稳定的关键。

以前我们经常有这种风险：

```
某报告.md 写着 PASS
↓
模型看到 PASS
↓
把它理解成当前系统真的已经 PASS
```

现在改成：

```
事实 owner / structured record
        ↓
   runtime validation
        ↓
   Markdown explanation
```

这是正确的方向。

类似地，Git branch 也不再等同于 ReconstructionBranch，这也是很重要的改进。以后一个 `main` 可以同时保存四条复原方案，而不用用四个 Git 分支代表四种小说世界。

------

## 我会调整你当前规划中的一个优先级

如果未来目标是：

> “以后任何一个新会话，只给它仓库地址和 main，就能继续工作。”

那么接下来的优先级我建议不是：

**P9 → P10 → P11**

而是：

**R0 Repository Closure → P9 / Corpus v1 → P11**

其中 R0 很短，但非常重要：

1. 补齐 active Source 的 **12 个 local carrier 缺口**；
2. 实现并验证 **32 个 locator**；
3. 建立 unified asset ingest；
4. 建立逻辑 collection / role index；
5. 定义 corpus build 输入资产；
6. 让 CI 明确检查：

```
no external chat dependency
no /mnt/data dependency
no hidden attachment dependency
no untracked authoritative input
```

完成以后可以真正宣布：

> **仓库，而不是会话，是项目的唯一长期事实载体。**

------

### 一个最终判断

现在的设计已经不是“仓库整理方案”了，它已经开始变成真正的**数字文献学 + 小说复原工作台**。

最大的优点是：权威分层已经比较稳，历史迁移也没有继续绑架 runtime。

最大的风险不再是文件丢失，而是：

> **文件虽然都在仓库，却没有形成可导航、可定位、可重建的知识闭包。**

所以我接下来最建议你做的不是继续“大搬家”，而是做三件很具体的事：

**Source Closure、Front80 Corpus、统一 Ingest。**

这三项完成以后，后面无论是 P9 盲评、P11 大规模候选搜索，还是最终81—100全书生产，都可以真正做到**只依赖仓库，不依赖任何旧会话**。