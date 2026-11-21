# 红楼梦八十回后续书

《红楼梦》第八十一至一百回的续书正文，以及写它用的设定和一个小工具。

## 目录

| 目录 | 内容 |
|---|---|
| `book/` | 正文，每回一个文件。这是唯一的产出物 |
| `bible/` | 设定：每回大纲卡、人物、时间线、跨回线索、证据、风格守则、时代语汇、术语 |
| `notes/` | 修订笔记，作者的和模型读稿的，用完可删 |
| `rcw/` | 写作工具，约 600 行 |
| `refs/` | 参考资料，只读：前八十回正文（`front80/`）、脂批（`zhipi/`）、脂汇本原件（`primary/`）、原工程的工作文档（`cards/`）、另一版续书正文（`alt/v6-r2/`） |

## 怎么写

每一回的流程：

1. 读 `book/ch0NN.md`，把想改的写进 `notes/ch0NN.md`。也可以先让模型读一遍：`rcw review NN`。
2. 修订。两种方式任选：
   - 交给 agent：`rcw context NN --task revise --notes notes/ch0NN.md`，把输出交给 Claude Code 等 agent，让它直接改 `book/`。
   - 调用 API：`rcw revise NN notes/ch0NN.md`。
3. `rcw check NN` 扫一眼提醒。
4. `git diff` 读改动。满意就提交，不满意就 `git checkout -- book/`。

大纲本身有问题，就改 `bible/`，不要加代码。

## 安装

```bash
python -m pip install -e '.[dev,model]'
python -m pytest -q
```

调用模型需要 API 凭据（`ANTHROPIC_API_KEY`，或 `ant auth login`）。模型默认 `claude-opus-5-5`，可用环境变量 `RCW_MODEL` 改。

## 历史

2026 年 11 月以前，这个仓库是一套审计、准入、评审框架（RedChamberWorldHarness）。完整的旧实现、评审记录和原始资料都保留在 git tag `pre-cleanup`：

```bash
git checkout pre-cleanup
```
