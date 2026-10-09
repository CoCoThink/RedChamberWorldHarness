"""Font/color classification mapped exactly onto the unchanged PDF extraction."""
from __future__ import annotations

import re
from typing import Any

from ..assets import AssetError


def pdf_runs(document, page_number: int, expected: str) -> list[dict[str, Any]]:
    runs, cursor, chunks = [], 0, []
    page = document[page_number - 1]
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"]
                runs.append({"start": cursor, "end": cursor + len(text), "text": text,
                             "style": {"font": span["font"], "size": round(span["size"], 2), "color": span["color"]},
                             "bbox": list(span["bbox"])})
                chunks.append(text); cursor += len(text)
            if line["spans"]:
                runs.append({"start": cursor, "end": cursor + 1, "text": "\n", "style": runs[-1]["style"], "bbox": runs[-1]["bbox"]})
                chunks.append("\n"); cursor += 1
    if "".join(chunks) != expected:
        raise AssetError(f"PDF_STYLE_TEXT_MISMATCH: physical page {page_number}")
    return runs


def classify(run: dict, policy: dict, *, variant: bool, appendix: bool, black_annotation: bool = False) -> tuple[str, str]:
    style, text = run["style"], run["text"]
    font, size, color = style["font"], style["size"], style["color"]
    if any(font.startswith(prefix) for prefix in policy["watermark_fonts"]):
        return "EDITORIAL", "WATERMARK_FONT"
    if color == 16777215:
        return "EDITORIAL", "INVISIBLE_TEXT"
    if appendix:
        return "APPENDIX", "DECLARED_APPENDIX_SCOPE"
    if variant:
        return "VARIANT", "DECLARED_ALTERNATE_CHAPTER_SCOPE"
    if re.fullmatch(r"[甲己庚戚蒙列杨辰][眉侧夹]?", text.strip()) and font.startswith("00-"):
        return "ZHIPI", "WITNESS_LABEL_GLYPH"
    if color in policy["annotation_colors"] and any(font.startswith(prefix) for prefix in policy["annotation_fonts"]):
        return "ZHIPI", "DECLARED_ANNOTATION_COLOR"
    if black_annotation and "KaiTi" in font:
        return "ZHIPI", "BLACK_COMMENT_FOLLOWS_WITNESS_LABEL"
    low, high = policy["main_size_range"]
    if color == policy["main_color"] and low <= size <= high and font in policy["main_fonts"]:
        return "MAIN_TEXT", "DECLARED_MAIN_FONT_SIZE_COLOR"
    if color == policy["main_color"] and (size < low or size > high):
        return "EDITORIAL", "HEADER_FOOTNOTE_TITLE_OR_COLLATION_MARKER"
    if not text.strip():
        return "EDITORIAL", "LAYOUT_WHITESPACE"
    return "UNCLASSIFIED", "UNRECOGNIZED_TYPOGRAPHY"
