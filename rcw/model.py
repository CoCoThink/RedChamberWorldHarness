"""调用 Claude。只在 revise / review 时用到；context 与 check 不需要网络。"""
from __future__ import annotations

import os
import re

MODEL = os.environ.get("RCW_MODEL", "claude-opus-5-5")

SYSTEM = ("你是《红楼梦》八十回后续书的执笔者，熟悉前八十回的语言、人物与章法。"
          "用户给你的上下文是作者本人的设定与手稿，照其要求写作或评改。")


class ModelError(RuntimeError):
    pass


def complete(prompt: str, effort: str = "high") -> str:
    import anthropic

    client = anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # 被安全分类器拒绝时，服务端自动换模型重试
            output_config={"effort": effort},
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise ModelError("没有可用的 API 凭据：设置 ANTHROPIC_API_KEY，或先运行 ant auth login")
    except anthropic.RateLimitError:
        raise ModelError("触发限流，稍后再试")
    except anthropic.APIStatusError as exc:
        raise ModelError(f"API 返回错误 {exc.status_code}：{exc.message}")
    except anthropic.APIConnectionError:
        raise ModelError("连不上 API，检查网络")
    if msg.stop_reason == "refusal":
        raise ModelError("模型拒绝了这次请求")
    if msg.stop_reason == "max_tokens":
        raise ModelError("输出达到长度上限被截断")
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def extract_chapter(reply: str, original: str) -> str:
    """从模型回复里取出整回正文；回复明显不完整时报错，不覆盖原稿。"""
    m = re.search(r"^(?:# )?第[一二三四五六七八九十百]+回.*$", reply, re.M)
    if not m:
        raise ModelError("回复里找不到回目行")
    text = reply[m.start():].strip()
    if not text.startswith("# "):
        text = "# " + text
    text = re.sub(r"\n```\s*$", "", text).strip()
    from .repo import han_count
    if han_count(text) < han_count(original) * 0.5:
        raise ModelError(f"回复只有 {han_count(text)} 字，不到原稿的一半，未写入")
    return text + "\n"
