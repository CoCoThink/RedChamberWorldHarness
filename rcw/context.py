"""把正文与设定拼成一段给写作模型（或 agent）读的中文上下文。"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from .repo import CHAPTERS, QUOTE, Repo, chapters_in, han_count, sections

LIMIT = 30000  # 单回写作与修订，字（不含空白）
SPAN_LIMIT = 80000  # 分段通读
COMMENT = re.compile(r"<!--.*?-->", re.S)

INTRO = ("你在续写《红楼梦》第八十一至一百回。下面依次是：任务、风格守则、本回大纲、相关证据、跨回线索与史料边界、"
         "时间线、出场人物、前后回衔接、前八十回范文，以及本回现稿。")

TASKS = {
    "revise": ("按文末的修订笔记修订本回。输出修订后的整回正文：第一行是回目（以“# ”开头），到回末为止，"
               "不加任何说明。笔记没有要求改动的地方尽量保留原文；“必须原样保留的字句”一字不改。"),
    "review": ("以读者兼编辑的身份通读本回现稿，对照大纲与风格守则写一份修订笔记。先说写得最好的两三处，"
               "再按轻重列出问题；每条引用原文短句指明位置，并给出具体改法。只写笔记，不重写正文。"),
    "write": ("依据大纲写出本回整回正文：第一行是回目（以“# ”开头），到回末为止，不加任何说明。"),
}

SPAN_TASK = ("以编辑身份连读下面几回正文，只看段落与全书层面的问题，不逐句挑错：一、节奏：各回冷热、悲喜、快慢是否单调，"
             "相邻回是否重复同一种场面；二、人物：谁出场太少、谁消失太久、谁的声口在几回之间走了样；三、线索：跨回物件与伏笔"
             "是否接上，前一回埋下的后一回是否忘了，时间、称呼、谁知道什么、东西在谁手里有无前后矛盾；四、衔接：回与回之间"
             "的时间和情绪是否接得上。每条注明回次、引原文短句，并给出改法。最后为每一回写三至五行“回末状态”建议"
             "（谁知道了什么、要紧的东西在谁手里、钱与日子到了哪一步），供作者填进大纲卡。只写笔记，不重写正文。")

# bible 里提到文件名的地方，换成上下文里的小节名，避免把路径交给模型
FILE_NAMES = {"`evidence.md`": "“证据”一节", "`timeline.md`": "“时间线”一节", "`style.md`": "“风格守则”",
              "`characters.md`": "“出场人物”一节", "`vocab.md`": "“时代语汇”一节", "`arcs.md`": "“跨回线索”一节",
              "`history.md`": "“史料边界”一节"}


def size(text: str) -> int:
    return len(re.sub(r"\s", "", text))


def scrub(text: str) -> str:
    """去掉文件名；各段内部标题统一下降两级，挂在"## 段名"之下。"""
    text = COMMENT.sub("", text)
    for k, v in FILE_NAMES.items():
        text = text.replace(k, v)
    return re.sub(r"^(#{1,4}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", text, flags=re.M)


# ---------- 各段取材 ----------

def evidence_for(repo: Repo, n: int) -> str:
    keep = []
    for head, body in sections(repo.doc("evidence.md")):
        if head.startswith(("R01", "P01")):  # 证据表、先后顺序表：只留本稿落点涉及本回的行
            lines = body.splitlines()
            rows = [l for l in lines[2:] if l.startswith("|") and n in chapters_in(l.rstrip("| ").rsplit("|", 1)[-1])]
            if rows:
                keep.append(f"# {head}\n" + "\n".join(lines[:2] + rows))
        elif head:
            keep.append(f"# {head}\n{body}")
        else:
            keep.append(body)
    return "\n\n".join(keep)


def end_state(body: str) -> str:
    """大纲卡"## 回末状态"一节里作者真正填了的行；没填返回空串。"""
    for head, text in sections(body):
        if head == "回末状态":
            lines = [l for l in COMMENT.sub("", text).splitlines() if l.strip()]
            return "\n".join(l for l in lines if not re.fullmatch(r"-?\s*[^：]{1,12}：\s*", l.strip()))
    return ""


def with_end_state(body: str) -> str:
    """把卡里的回末状态换成只含已填内容；没填就整节去掉。"""
    state = end_state(body)
    return re.sub(r"^## 回末状态\n.*?(?=^## |\Z)", (f"## 回末状态\n\n{state}\n\n" if state else ""),
                  body, count=1, flags=re.S | re.M)


def arc_items(repo: Repo, n: int) -> list[str]:
    keep = []
    for head, body in sections(repo.doc("arcs.md")):
        if head == "跨回接口总锁":  # "1. **84→87丧期缓冲**：……"按标题里的首尾回次取区间
            for item in re.findall(r"^\d+\. .+$", body, re.M):
                title = item.split("：", 1)[0]
                nums = chapters_in(title)
                if nums and min(nums) <= n <= max(nums):
                    keep.append(item)
        elif head:
            for sub, text in sections(body, level=3):
                if n in chapters_in(text):
                    keep.append(f"# {sub}\n{text}")
    return keep


def arcs_for(repo: Repo, n: int) -> str:
    return "\n\n".join(arc_items(repo, n))


def history_for(repo: Repo, n: int) -> str:
    """史料边界：开头说明加上标题括号里回次包含本回的条目；一条也不涉及就不放。"""
    secs = sections(repo.doc("history.md"))
    keep = [f"# {h}\n{b}" for h, b in secs if h and n in chapters_in(h)]
    if not keep:
        return ""
    intro = re.sub(r"^# .*\n", "", secs[0][1]).strip()
    return "\n\n".join([intro] + keep)


def cast_for(repo: Repo, names: list[str]) -> tuple[str, list[str]]:
    chars, out, missing, seen = repo.characters(), [], [], set()
    for name in names:
        entry = chars.get(str(name))
        if entry is None:
            missing.append(str(name))
        elif entry not in seen:
            seen.add(entry)
            out.append(entry)
    rules = next((f"# {h}\n{b}" for h, b in sections(repo.doc("characters.md")) if "规则" in h), "")
    return "\n\n".join(out + ([rules] if rules else [])), missing


def body_of(chapter: str) -> str:
    return chapter.split("\n", 1)[1].strip() if chapter.startswith("# ") else chapter.strip()


def clip(paras: list[str], budget: int, from_end: bool = False) -> str:
    out, used = [], 0
    for p in (reversed(paras) if from_end else paras):
        if used and used + size(p) > budget:
            break
        out.append(p)
        used += size(p)
    return "\n\n".join(reversed(out) if from_end else out)


def neighbors(repo: Repo, n: int, budget: int) -> str:
    prev = repo.chapter(n - 1) if n - 1 in CHAPTERS else repo.front80(80) if n == 81 else ""
    nxt = repo.chapter(n + 1) if n + 1 in CHAPTERS else ""
    parts = []
    if prev:
        parts.append(f"# 上一回结尾\n{clip(body_of(prev).split(chr(10) * 2), budget * 2 // 3, from_end=True)}")
    if nxt:
        parts.append(f"# 下一回开头\n{clip(body_of(nxt).split(chr(10) * 2), budget // 3)}")
    return "\n\n".join(parts)


def excerpt(text: str, budget: int, keyword: str | None) -> str:
    paras = [p for p in body_of(text).split("\n\n") if p.strip()]
    if not paras:
        return ""
    if keyword:
        start = next((i for i, p in enumerate(paras) if keyword in p), 0)
        return clip(paras[start:], budget)
    best, best_score = 0, -1.0  # 没给关键词：取对话最密的一段，作口吻范例
    for i in range(len(paras)):
        window = clip(paras[i:], budget)
        if size(window) < budget * 0.6 and i:
            break
        score = sum(size(q) for q in QUOTE.findall(window)) / max(size(window), 1)
        if score > best_score:
            best, best_score = i, score
    return clip(paras[best:], budget)


def parallels(repo: Repo, refs: list, budget: int) -> str:
    if not refs:
        return ""
    each, parts = budget // len(refs), []
    for ref in refs:
        num, _, keyword = str(ref).partition(":")
        text = repo.front80(int(num))
        if text:
            parts.append(f"# 第{int(num)}回" + (f"（{keyword}）" if keyword else "") + f"\n{excerpt(text, each, keyword or None)}")
    return "\n\n".join(parts)


# ---------- 组装 ----------

@dataclass
class Context:
    text: str
    sizes: dict[str, int]
    notes: list[str]


def build(repo: Repo, n: int, task: str = "revise", notes: str = "", limit: int = LIMIT) -> Context:
    if n not in CHAPTERS:
        raise SystemExit(f"回次应在 81–100 之间，收到 {n}")
    if task not in TASKS:
        raise SystemExit(f"task 应为 {'、'.join(TASKS)} 之一")
    o = repo.outline(n)
    cast, missing = cast_for(repo, o.cast)
    warn = [f"大纲 cast 里这些人在 characters.md 中没有条目：{'、'.join(missing)}"] if missing else []
    keep = "\n".join(f"- {k}" for k in o.keep)
    outline = with_end_state(o.body) + (f"\n\n## 必须原样保留的字句\n{keep}" if keep else "")
    before = end_state(repo.outline(n - 1).body) if n - 1 in CHAPTERS else ""
    fixed = [("任务", TASKS[task]), ("全书骨架", repo.doc("skeleton.md")), ("风格守则", repo.doc("style.md")),
             ("本回大纲", outline),
             ("上一回结束时", before),
             ("证据", evidence_for(repo, n)), ("跨回线索", arcs_for(repo, n)),
             ("史料边界", history_for(repo, n)),
             ("时间线", repo.doc("timeline.md")), ("出场人物", cast)]
    tail = []
    if task in ("revise", "review"):
        tail.append(("本回现稿", repo.chapter(n)))
    if notes.strip():
        tail.append(("修订笔记", notes))
    optional = {"术语": repo.doc("glossary.md"), "时代语汇": repo.doc("vocab.md")}
    nb, pb = 3000, 6000

    def assemble():
        segs = fixed + [("前后回衔接", neighbors(repo, n, nb)), ("前八十回范文", parallels(repo, o.parallel, pb))]
        segs += list(optional.items()) + tail
        return [(k, scrub(v).strip()) for k, v in segs if v and v.strip()]

    segs = assemble()
    while sum(size(v) for _, v in segs) > limit:  # 超额时依次让出：语汇、术语、范文、衔接
        if optional:
            optional.pop(next(reversed(optional)))
        elif pb > 1500:
            pb = int(pb * 0.7)
        elif nb > 1000:
            nb = int(nb * 0.7)
        else:
            warn.append(f"上下文仍有 {sum(size(v) for _, v in segs)} 字，超过 {limit}")
            break
        segs = assemble()
    head = f"# 第{n}回 写作上下文\n\n{INTRO}"
    text = head + "\n\n" + "\n\n".join(f"## {k}\n\n{v}" for k, v in segs) + "\n"
    return Context(text, {k: size(v) for k, v in segs}, warn)


def build_span(repo: Repo, first: int, last: int, limit: int = SPAN_LIMIT) -> Context:
    """几回连读：给全书与段落层面的评审用，带全文，不带范文。"""
    if not (first in CHAPTERS and last in CHAPTERS and first < last):
        raise SystemExit(f"分段应在 81–100 之间且前小后大，收到 {first}-{last}")
    ns = range(first, last + 1)
    outlines = [repo.outline(n) for n in ns]
    cast, missing = cast_for(repo, list(dict.fromkeys(str(c) for o in outlines for c in o.cast)))
    warn = [f"大纲 cast 里这些人在 characters.md 中没有条目：{'、'.join(missing)}"] if missing else []
    arcs = "\n\n".join(dict.fromkeys(x for n in ns for x in arc_items(repo, n)))
    cards = []
    for o in outlines:
        parts = [f"## {h}\n{b}" for h, b in sections(with_end_state(o.body))
                 if h in ("时间", "人物", "回末状态") or h.startswith("保护锁")]
        cards.append(f"# {o.title}\n" + "\n\n".join(parts))
    before = end_state(repo.outline(first - 1).body) if first - 1 in CHAPTERS else ""
    optional = {"风格守则": repo.doc("style.md"), "出场人物": cast}
    fixed = [("全书骨架", repo.doc("skeleton.md")), ("跨回线索", arcs), ("时间线", repo.doc("timeline.md")), ("各回要点", "\n\n".join(cards)),
             (f"第{first - 1}回结束时", before), ("正文", "\n\n".join(repo.chapter(n) for n in ns))]

    def assemble():
        segs = [("任务", SPAN_TASK)] + list(optional.items()) + fixed
        return [(k, scrub(v).strip()) for k, v in segs if v and v.strip()]

    segs = assemble()
    while sum(size(v) for _, v in segs) > limit:
        if not optional:
            warn.append(f"上下文仍有 {sum(size(v) for _, v in segs)} 字，超过 {limit}；可把分段缩短")
            break
        optional.pop(next(iter(optional)))
        segs = assemble()
    text = f"# 第{first}至{last}回 通读上下文\n\n" + "\n\n".join(f"## {k}\n\n{v}" for k, v in segs) + "\n"
    return Context(text, {k: size(v) for k, v in segs}, warn)


def report(ctx: Context) -> None:
    total = sum(ctx.sizes.values())
    print(f"上下文共 {total} 字：" + "，".join(f"{k} {v}" for k, v in ctx.sizes.items()), file=sys.stderr)
    for w in ctx.notes:
        print(f"注意：{w}", file=sys.stderr)


__all__ = ["build", "build_span", "report", "TASKS", "LIMIT", "SPAN_LIMIT", "han_count"]
