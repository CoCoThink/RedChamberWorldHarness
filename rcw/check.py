"""对正文做字面层面的检查。只给提醒，不拦截。"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from functools import lru_cache

from .repo import CHAPTERS, Repo, dialogue_share, han_count

# 风格守则里列出的工作台词、抽象词（命中即提醒，具体改不改由作者定）
JARGON = ["状态", "机制", "资源", "风险", "现金流", "信息差", "心理", "创伤", "功能", "执行", "价值",
          "继续", "开始", "问题", "办法", "实际", "具体", "检查", "内容", "反应", "正常", "简单", "完整", "习惯性"]
# 与前八十回比较频率的口语词
DRIFT = ["已经", "一下", "一点", "仿佛", "似乎", "终于", "慢慢"]
SPEECH = r"[^“”。！？\n]{0,6}?道[：，]?“"


@lru_cache(maxsize=4)
def _front80_rates(root: str) -> dict[str, float]:
    repo = Repo(root)
    text = "".join(repo.front80(i) for i in range(1, 81))
    n = han_count(text) or 1
    return {w: text.count(w) * 1e4 / n for w in DRIFT}


def check_chapter(repo: Repo, n: int, text: str | None = None) -> list[str]:
    text = repo.chapter(n) if text is None else text
    if not text.strip():
        return ["正文为空"]
    o = repo.outline(n)
    body = text.split("\n", 1)[1] if text.startswith("# ") else text
    out = []

    title = text.splitlines()[0].lstrip("# ").strip()
    if o.title and title != o.title:
        out.append(f"回目与大纲不一致：{title}")
    for k in o.keep:
        if k not in text:
            out.append(f"缺少必须保留的字句：{k}")
    for a in o.avoid:
        if a in body:
            out.append(f"出现大纲 avoid 里的词：{a}（{body.count(a)} 处）")

    for name, died in repo.deaths().items():
        if n > died:
            m = re.search(re.escape(name) + SPEECH, body)
            if m:
                out.append(f"{name}已于第{died}回去世，此处像是在说话：{m.group(0)}")

    lengths = [han_count(repo.chapter(i)) for i in CHAPTERS if repo.chapter(i)]
    if lengths:
        mid, mine = statistics.median(lengths), han_count(body)
        if mine < mid * 0.75 or mine > mid * 1.33:
            out.append(f"字数 {mine}，全书中位数 {int(mid)}")

    share = dialogue_share(body)
    if share < 0.3:
        out.append(f"对话占 {share:.0%}，前八十回约五成")

    hits = {w: body.count(w) for w in JARGON if w in body}
    if hits:
        out.append("工作台词或抽象词：" + "、".join(f"{w}×{c}" for w, c in sorted(hits.items(), key=lambda x: -x[1])))

    n_han = han_count(body) or 1
    base = _front80_rates(str(repo.root))
    for w in DRIFT:
        rate = body.count(w) * 1e4 / n_han
        if rate > max(base[w] * 3, base[w] + 2):
            out.append(f"“{w}”每万字 {rate:.1f} 次，前八十回 {base[w]:.1f} 次")

    ascii_marks = re.findall(r"[0-9,;:?!()]", body)
    if ascii_marks:
        out.append("正文里有阿拉伯数字或半角标点：" + "".join(sorted(set(ascii_marks))))

    grams = Counter()
    for run in re.findall(r"[一-鿿]{6,}", body):
        grams.update(run[i:i + 6] for i in range(len(run) - 5))
    rep = [(g, c) for g, c in grams.most_common(20) if c >= 4 and not any(g in k for k in o.keep)][:3]
    if rep:
        out.append("重复的六字串：" + "、".join(f"{g}×{c}" for g, c in rep))
    return out


def run(repo: Repo, chapters: list[int]) -> str:
    lines = []
    for n in chapters:
        warns = check_chapter(repo, n)
        lines.append(f"第{n}回：" + ("无提醒" if not warns else ""))
        lines += [f"  - {w}" for w in warns]
    return "\n".join(lines)


__all__ = ["check_chapter", "run"]
