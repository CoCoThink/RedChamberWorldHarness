# 参与方式

规则以 `AGENTS.md` 为准。这里只说日常怎么改。

## 改正文

直接改 `book/` 下对应的回。用 `git diff` 读改动，满意再提交，提交信息写改了什么。不满意就 `git checkout` 放弃重来。

## 改设定

改 `bible/`：

| 文件 | 内容 |
|---|---|
| `outline/ch081.md` … | 每回大纲卡。frontmatter 里的 `cast`、`parallel`、`keep` 供工具读取 |
| `characters.md` | 人物声口、主场回次、去世回次 |
| `timeline.md` | 相对时间轴 |
| `arcs.md` | 跨回线索与物件母题 |
| `evidence.md` | 证据节点、先后顺序、脂批直引字面 |
| `style.md` | 风格守则 |
| `vocab.md` | 时代语汇与称谓 |
| `glossary.md` | 卡里的代号是什么意思 |

底线只有一条：**证据和推演分开。** `evidence.md` 里 A-W1、B-W1 是证据，必须保留；C 是本项目的推演，可以改写。不要为了让情节顺而把推演改成证据。

大纲卡 frontmatter 可写的字段：

```yaml
cast: [黛玉, 紫鹃]          # 出场人物，名字与 characters.md 的标题对应
parallel: [57, "77:晴雯"]   # 前八十回参照；"回次:关键词"从关键词所在段落起摘
keep: ["再温一温"]          # 正文必须原样保留的字句
avoid: [遗言, 托梦]         # 正文出现就提醒
```

每张卡还有一节"回末状态"：三至五行，写本回结束时谁知道了什么、要紧的东西在谁手里、钱与日子到了哪一步。填了之后，下一回的上下文会带上这一节（"上一回结束时"）；没填就不出现。分段通读会给出建议，由你决定填不填。

## 工具

`python -m pip install -e '.[dev,model]'` 之后可直接用 `rcw`；不安装也可以在仓库根目录用 `python -m rcw`。

```bash
rcw context 86 --task revise --notes notes/ch086.md > /tmp/ctx.md   # 拼上下文，交给 agent 或自己读
rcw check 86                                                    # 只给提醒
rcw review 86                                                   # 模型读稿，意见追加到 notes/ch086.md
rcw review 84-88                                                # 分段通读：节奏、人物、线索、衔接，意见追加到 notes/span-084-088.md
rcw context 84-88 > /tmp/span.md                                # 同上，交给 agent 读
rcw revise 86 notes/ch086.md                                    # 模型按笔记修订，写回 book/ch086.md
```

`revise` 和 `review` 把最近一次的提示词和回复存在 `.rcw/`（不进 git）。模型默认 `claude-opus-5-5`，可用环境变量 `RCW_MODEL` 改。

## 改代码

先回答"这让哪一回更好读或更好写"。答不上来就不改。能改数据解决的，不加代码。
