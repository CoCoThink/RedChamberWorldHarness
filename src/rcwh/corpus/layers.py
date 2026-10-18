"""Font/color classification mapped exactly onto the unchanged PDF extraction."""
from __future__ import annotations

import re
from typing import Any

from ..assets import AssetError


def pdf_runs(document, page_number: int, expected: str, *, include_line_context: bool = False) -> list[dict[str, Any]]:
    runs, cursor, chunks = [], 0, []
    page = document[page_number - 1]
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            line_start, first_run = cursor, len(runs)
            for span in line["spans"]:
                text = span["text"]
                runs.append({"start": cursor, "end": cursor + len(text), "text": text,
                             "style": {"font": span["font"], "size": round(span["size"], 2), "color": span["color"]},
                             "bbox": list(span["bbox"])})
                chunks.append(text); cursor += len(text)
            if line["spans"]:
                runs.append({"start": cursor, "end": cursor + 1, "text": "\n", "style": runs[-1]["style"], "bbox": runs[-1]["bbox"]})
                chunks.append("\n"); cursor += 1
                if include_line_context:
                    context = {"start": line_start, "end": cursor,
                               "text": "".join(span["text"] for span in line["spans"]),
                               "bbox": list(line["bbox"]), "page_bbox": list(page.rect)}
                    for run in runs[first_run:]:
                        run["line"] = context
    if "".join(chunks) != expected:
        raise AssetError(f"PDF_STYLE_TEXT_MISMATCH: physical page {page_number}")
    return runs


def page_furniture_reason(run: dict, policy: dict) -> str | None:
    """Match only a declared complete line wholly inside a page-edge strip."""
    rules, line = policy.get("page_furniture"), run.get("line")
    if not rules or not line:
        return None
    _, page_top, _, page_bottom = line["page_bbox"]
    _, top, _, bottom = line["bbox"]
    height = page_bottom - page_top
    if height <= 0 or not page_top <= top <= bottom <= page_bottom:
        return None
    if not (bottom <= page_top + height * rules["top_band_fraction"] or
            top >= page_bottom - height * rules["bottom_band_fraction"]):
        return None
    text = line["text"].strip()
    if not text:
        return None
    if any(re.fullmatch(pattern, text) for pattern in rules["page_number_patterns"]):
        return "DECLARED_PAGE_NUMBER_LINE_IN_EDGE_STRIP"
    if text in rules["running_headers"]:
        return "DECLARED_RUNNING_HEADER_LINE_IN_EDGE_STRIP"
    return None


def classify(run: dict, policy: dict, *, variant: bool, appendix: bool, black_annotation: bool = False,
             schema_version: int = 1, line_in_scope: bool = False) -> tuple[str, str]:
    style, text = run["style"], run["text"]
    font, size, color = style["font"], style["size"], style["color"]
    if any(font.startswith(prefix) for prefix in policy["watermark_fonts"]):
        return "EDITORIAL", "WATERMARK_FONT"
    if color == 16777215:
        return "EDITORIAL", "INVISIBLE_TEXT"
    if schema_version == 2 and (appendix or variant) and line_in_scope:
        reason = page_furniture_reason(run, policy)
        if reason:
            return "EDITORIAL", reason
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
