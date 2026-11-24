"""rcw：红楼梦续书写作工具。

  python -m rcw context 86 [--task revise|review|write] [--notes 笔记文件]
  python -m rcw context 84-88        # 几回连读的上下文
  python -m rcw check [86 87 ...]
  python -m rcw review 86            # 模型读稿，意见追加到 notes/ch086.md
  python -m rcw review 84-88         # 分段通读，意见追加到 notes/span-084-088.md
  python -m rcw revise 86 笔记文件   # 模型按笔记修订，直接写回 book/ch086.md
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from . import check, context
from .repo import CHAPTERS, Repo, parse_span


def _save(repo: Repo, name: str, text: str) -> None:
    d = repo.root / ".rcw"
    d.mkdir(exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def _notes(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"找不到笔记文件 {path}")
    return p.read_text(encoding="utf-8")


def cmd_context(repo: Repo, a) -> int:
    first, last = parse_span(a.chapter)
    if first == last:
        ctx = context.build(repo, first, a.task, _notes(a.notes), a.limit)
    else:
        ctx = context.build_span(repo, first, last, a.limit)
    sys.stdout.write(ctx.text)
    context.report(ctx)
    return 0


def cmd_check(repo: Repo, a) -> int:
    print(check.run(repo, a.chapters or list(CHAPTERS)))
    return 0


def _ask(repo: Repo, ctx: context.Context, effort: str) -> str:
    from .model import ModelError, complete
    context.report(ctx)
    _save(repo, "last_prompt.md", ctx.text)
    print("正在调用模型……", file=sys.stderr)
    try:
        reply = complete(ctx.text, effort)
    except ModelError as exc:
        raise SystemExit(str(exc))
    _save(repo, "last_response.md", reply)
    return reply


def cmd_review(repo: Repo, a) -> int:
    first, last = parse_span(a.chapter)
    if first == last:
        ctx, name = context.build(repo, first, "review"), f"ch{first:03d}.md"
    else:
        ctx, name = context.build_span(repo, first, last), f"span-{first:03d}-{last:03d}.md"
    reply = _ask(repo, ctx, a.effort)
    path = repo.root / "notes" / name
    path.parent.mkdir(exist_ok=True)
    stamp = datetime.date.today().isoformat()
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## 模型读稿意见（{stamp}）\n\n{reply}\n")
    print(f"意见已追加到 {path.relative_to(repo.root)}")
    return 0


def cmd_revise(repo: Repo, a) -> int:
    from .model import ModelError, extract_chapter
    original = repo.chapter(a.chapter)
    reply = _ask(repo, context.build(repo, a.chapter, "revise", _notes(a.notes)), a.effort)
    try:
        text = extract_chapter(reply, original)
    except ModelError as exc:
        raise SystemExit(f"{exc}（完整回复在 .rcw/last_response.md）")
    name = repo.chapter_path(a.chapter).name
    _save(repo, f"{name[:-3]}.before.md", original)  # 修订前的稿子，含尚未提交的改动
    repo.chapter_path(a.chapter).write_text(text, encoding="utf-8")
    print(check.run(repo, [a.chapter]))
    subprocess.run(["git", "diff", "--stat", "--", f"book/{name}"], cwd=repo.root)
    print(f"用 git diff 读改动。不满意，回到修订前：cp .rcw/{name[:-3]}.before.md book/{name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rcw", description="红楼梦续书写作工具")
    p.add_argument("--root", help="仓库根目录，默认从当前目录向上找")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("context", help="输出某回（或几回连读）的上下文")
    c.add_argument("chapter", help="86，或 84-88")
    c.add_argument("--task", default="revise", choices=list(context.TASKS))
    c.add_argument("--notes")
    c.add_argument("--limit", type=int, help="字数上限，默认不限；超出时先去掉时代语汇、术语，再缩范文与衔接，并在报告里写明")
    c.set_defaults(func=cmd_context)

    k = sub.add_parser("check", help="检查正文，只给提醒")
    k.add_argument("chapters", type=int, nargs="*")
    k.set_defaults(func=cmd_check)

    for name, func, helptext in (("review", cmd_review, "模型读稿写笔记；84-88 为分段通读"),
                                 ("revise", cmd_revise, "模型按笔记修订正文")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("chapter", type=int if name == "revise" else str)
        if name == "revise":
            s.add_argument("notes")
        s.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
        s.set_defaults(func=func)

    a = p.parse_args(argv)
    repo = Repo(a.root) if a.root else Repo.find()
    return a.func(repo, a)
