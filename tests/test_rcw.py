import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rcw import check, context  # noqa: E402
from rcw.model import ModelError, extract_chapter  # noqa: E402
from rcw.repo import CHAPTERS, Repo, chapters_in, parse_span  # noqa: E402

TITLE = "第八十六回　潇湘馆泪尽芳魂逝　痴公子来迟旧梦空"
BODY86 = "紫鹃道：“姑娘醒了？”黛玉笑道：“你又来吵。”药吊子在炉上。宝玉道：“药不是还没吃么？再温一温。”\n\n" * 20


def make_repo(tmp_path: Path) -> Repo:
    (tmp_path / "book").mkdir()
    (tmp_path / "bible" / "outline").mkdir(parents=True)
    (tmp_path / "refs" / "front80").mkdir(parents=True)
    for n in CHAPTERS:
        title = TITLE if n == 86 else f"第{n}回　某某"
        body = BODY86 if n == 86 else f"第{n}回正文。袭人笑道：“好。”\n\n" * 30
        (tmp_path / "book" / f"ch{n:03d}.md").write_text(f"# {title}\n\n{body}", encoding="utf-8")
        cast = "[黛玉, 紫鹃, 宝玉]" if n == 86 else "[袭人]"
        keep = '\n  - "再温一温"' if n == 86 else " []"
        state = "- 谁知道了什么：紫鹃记下了药账" if n == 85 else "- 谁知道了什么："
        (tmp_path / "bible" / "outline" / f"ch{n:03d}.md").write_text(
            f"---\ntitle: {title}\ncast: {cast}\nparallel: [57]\nkeep:{keep}\n---\n\n# {title}\n\n## 人物\n\n大纲正文{n}\n\n"
            f"## 回末状态\n\n<!-- 说明 -->\n{state}\n- 钱与日子：\n\n## 本回设计\n\n场景{n}\n",
            encoding="utf-8")
    (tmp_path / "bible" / "characters.md").write_text(
        "# 人物\n\n## 黛玉（林黛玉）\n- 去世：第86回\n- 声口：尖。\n\n## 紫鹃\n- 声口：实。\n\n"
        "## 宝玉（贾宝玉）\n- 声口：爱问。\n\n## 袭人（花袭人）\n- 声口：劝。\n\n## 对白六条规则（全书通用）\n\n1. 先定对谁说。\n",
        encoding="utf-8")
    (tmp_path / "bible" / "style.md").write_text("# 风格守则\n\n见 `vocab.md`。\n", encoding="utf-8")
    (tmp_path / "bible" / "timeline.md").write_text("# 时间线\n\n| 86 | 黛玉夭亡 |\n", encoding="utf-8")
    (tmp_path / "bible" / "evidence.md").write_text(
        "# 证据与推演\n\n底线。\n\n## R01—R43\n\n| R | 节点 | 本稿落点 |\n|---|---|---|\n"
        "| R10 | 黛玉泪尽夭亡 | 85—86 |\n| R13 | 宝玉宝钗成夫妇 | 87 |\n", encoding="utf-8")
    (tmp_path / "bible" / "arcs.md").write_text(
        "# 跨回线索\n\n## 跨回接口总锁\n\n1. **84→87丧期缓冲**：不连续几日完成。\n2. **89→95经济降级**：逐步下降。\n\n"
        "## 跨回物件与母题\n\n### 药盒｜P1\n> 88：交接 → 89：带走\n", encoding="utf-8")
    (tmp_path / "refs" / "front80" / "ch057.md").write_text(
        "# 第57回\n\n叙述一段，没有对话。\n\n紫鹃笑道：“我是试你的。”宝玉道：“你试我？”\n", encoding="utf-8")
    (tmp_path / "refs" / "front80" / "ch080.md").write_text("# 第80回\n\n香菱病了。\n", encoding="utf-8")
    return Repo(tmp_path)


def test_chapters_in():
    assert chapters_in("85—86") == {85, 86}
    assert chapters_in("89、92、99") == {89, 92, 99}
    assert chapters_in("86 → 87—100") == set(range(86, 101))
    assert chapters_in("第45回") == set()


def test_context_selects_relevant_material(tmp_path):
    ctx = context.build(make_repo(tmp_path), 86, "revise", "把哭声再收一收。")
    t = ctx.text
    assert "## 任务" in t and "## 修订笔记" in t and "把哭声再收一收" in t
    assert "### 紫鹃" in t and "袭人（花袭人）" not in t          # 只放本回出场人物
    assert "R10" in t and "R13" not in t                           # 只放落点涉及本回的证据
    assert "丧期缓冲" in t and "经济降级" not in t and "药盒" not in t
    assert "### 上一回结尾" in t and "### 下一回开头" in t
    assert "我是试你的" in t                                       # 范文取对话最密的段落
    assert "必须原样保留的字句\n- 再温一温" in t
    assert ".md" not in t and not re.search(r"[0-9a-f]{40}", t)    # 不把文件名、哈希交给模型


def test_end_state_carries_forward_only_when_filled(tmp_path):
    repo = make_repo(tmp_path)
    t86 = context.build(repo, 86, "revise").text
    assert "## 上一回结束时" in t86 and "紫鹃记下了药账" in t86   # 第85回填了，进第86回上下文
    assert "回末状态" not in t86 and "<!--" not in t86              # 第86回自己没填，整节不出现
    assert "上一回结束时" not in context.build(repo, 87, "revise").text


def test_span_context(tmp_path):
    assert parse_span("86") == (86, 86) and parse_span("84-88") == (84, 88) and parse_span("84—88") == (84, 88)
    ctx = context.build_span(make_repo(tmp_path), 84, 88)
    t = ctx.text
    assert "## 正文" in t and TITLE in t and "第88回正文" in t and "第89回正文" not in t
    assert "丧期缓冲" in t and "药盒" in t and "经济降级" not in t   # 跨回线索取各回之并
    assert "紫鹃记下了药账" in t and "场景86" not in t               # 要点只取时间、人物、回末状态、保护锁
    assert ".md" not in t


def test_context_trims_to_limit(tmp_path):
    repo = make_repo(tmp_path)
    full = context.build(repo, 86, "revise")
    limit = sum(full.sizes.values()) - 50
    small = context.build(repo, 86, "revise", limit=limit)
    assert sum(small.sizes.values()) <= limit or small.notes


def test_check_flags_problems(tmp_path):
    repo = make_repo(tmp_path)
    assert not any("再温一温" in w for w in check.check_chapter(repo, 86))
    bad = f"# {TITLE}\n\n" + BODY86.replace("再温一温", "热一热") + "共3碗。\n"
    warns = check.check_chapter(repo, 86, bad)
    assert any("缺少必须保留的字句：再温一温" in w for w in warns)
    assert any("阿拉伯数字" in w for w in warns)
    later = "# 第87回　某某\n\n" + "黛玉笑道：“你来了。”\n\n" * 30
    assert any("黛玉已于第86回去世" in w for w in check.check_chapter(repo, 87, later))


def test_extract_chapter():
    original = f"# {TITLE}\n\n" + BODY86
    reply = "好的，修订如下：\n\n" + original
    assert extract_chapter(reply, original).startswith(f"# {TITLE}")
    with pytest.raises(ModelError):
        extract_chapter(f"# {TITLE}\n\n太短。", original)
    with pytest.raises(ModelError):
        extract_chapter("没有回目", original)


@pytest.mark.skipif(not (ROOT / "bible" / "outline").is_dir(), reason="仓库里没有 bible/")
def test_real_repo_builds_every_chapter():
    repo = Repo(ROOT)
    for n in CHAPTERS:
        ctx = context.build(repo, n, "revise")
        assert sum(ctx.sizes.values()) <= context.LIMIT, n
        assert ".md" not in ctx.text, n
        check.check_chapter(repo, n)
