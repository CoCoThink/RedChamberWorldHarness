"""读取 book/、bible/、refs/ 里的数据。格式出错时直接报出哪个文件。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CHAPTERS = range(81, 101)
HAN = re.compile(r"[一-鿿]")
QUOTE = re.compile(r"“[^”]*”")


def han_count(text: str) -> int:
    return len(HAN.findall(text))


def dialogue_share(text: str) -> float:
    total = han_count(text)
    return sum(han_count(q) for q in QUOTE.findall(text)) / total if total else 0.0


def sections(text: str, level: int = 2) -> list[tuple[str, str]]:
    """按 `## 标题` 切分，返回 [(标题, 正文)]；第一个标题之前的内容标题为空串。"""
    mark = "#" * level + " "
    out, head, buf = [], "", []
    for line in text.splitlines():
        if line.startswith(mark):
            out.append((head, "\n".join(buf).strip()))
            head, buf = line[len(mark):].strip(), []
        else:
            buf.append(line)
    out.append((head, "\n".join(buf).strip()))
    return [(h, b) for h, b in out if h or b]


def chapters_in(spec: str) -> set[int]:
    """从"85—86""87—100""89、92、99""86 → 87"之类的写法里取出 81–100 的回次。"""
    found: set[int] = set()
    for a, b in re.findall(r"(?<!\d)(\d{2,3})\s*[—–~-]\s*(\d{2,3})(?!\d)", spec):
        found.update(range(int(a), int(b) + 1))
    found.update(int(x) for x in re.findall(r"(?<!\d)(\d{2,3})(?!\d)", spec))
    return {n for n in found if n in CHAPTERS}


@dataclass
class Outline:
    chapter: int
    title: str
    cast: list[str]
    parallel: list
    keep: list[str]
    avoid: list[str]
    body: str


class Repo:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    @classmethod
    def find(cls, start: Path | str | None = None) -> "Repo":
        here = Path(start or Path.cwd()).resolve()
        for d in (here, *here.parents):
            if (d / "book").is_dir() and (d / "bible").is_dir():
                return cls(d)
        raise SystemExit("找不到仓库根目录（需要同时有 book/ 和 bible/）")

    def _read(self, *parts: str) -> str:
        p = self.root.joinpath(*parts)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def chapter_path(self, n: int) -> Path:
        return self.root / "book" / f"ch{n:03d}.md"

    def chapter(self, n: int) -> str:
        return self._read("book", f"ch{n:03d}.md")

    def front80(self, n: int) -> str:
        return self._read("refs", "front80", f"ch{n:03d}.md")

    def doc(self, name: str) -> str:
        return self._read("bible", name)

    def outline(self, n: int) -> Outline:
        name = f"bible/outline/ch{n:03d}.md"
        text = self._read("bible", "outline", f"ch{n:03d}.md")
        if not text:
            raise SystemExit(f"缺少 {name}")
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not m:
            raise SystemExit(f"{name} 开头缺少 --- frontmatter ---")
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as exc:
            raise SystemExit(f"{name} 的 frontmatter 不是合法 YAML：{exc}")
        return Outline(n, str(meta.get("title", "")), list(meta.get("cast") or []),
                       list(meta.get("parallel") or []), [str(k) for k in meta.get("keep") or []],
                       [str(a) for a in meta.get("avoid") or []], text[m.end():].strip())

    def characters(self) -> dict[str, str]:
        """{简称: 该人物整节文字}。标题写作"宝玉（贾宝玉）"时，简称和全称都能查到。"""
        out = {}
        for head, body in sections(self.doc("characters.md")):
            if not head or "规则" in head:
                continue
            entry = f"# {head}\n{body}"
            short, _, full = head.partition("（")
            out[short.strip()] = entry
            if full:
                out[full.rstrip("）").strip()] = entry
        return out

    def deaths(self) -> dict[str, int]:
        out = {}
        for head, body in sections(self.doc("characters.md")):
            m = re.search(r"去世：第(\d+)回", body)
            if m:
                short, _, full = head.partition("（")
                for name in (short.strip(), full.rstrip("）").strip()):
                    if name:
                        out[name] = int(m.group(1))
        return out
