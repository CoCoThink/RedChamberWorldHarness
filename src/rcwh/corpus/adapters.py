"""Format adapters preserve characters and expose physical / markup origins."""
from __future__ import annotations

import html
from html.parser import HTMLParser
import io
from pathlib import PurePosixPath
import posixpath
from typing import Any
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from ..assets import AssetError
from ..assets.transactions import digest


def unit(reference: str, text: str, nodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"unit_ref": reference, "text": text, "text_sha256": digest(text.encode("utf-8")), "nodes": nodes}


class MarkupText(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.chunks: list[str] = []
        self.nodes: list[dict[str, Any]] = []
        self.length = 0
        self.stack: list[tuple[str, str, dict[str, int]]] = [("", "", {})]
        self.line_starts = [0]
        self.line_starts.extend(i + 1 for i, char in enumerate(source) if char == "\n")

    def source_offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def emit(self, text: str, raw_length: int, kind: str) -> None:
        if any(tag in {"head", "script", "style", "template"} for tag, _, _ in self.stack):
            return
        if not text:
            return
        start = self.source_offset()
        self.nodes.append({
            "start": self.length, "end": self.length + len(text),
            "origin": {"dom_path": self.stack[-1][1] or "/", "raw_start": start, "raw_end": start + raw_length, "kind": kind},
        })
        self.chunks.append(text)
        self.length += len(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        siblings = self.stack[-1][2]
        siblings[tag] = siblings.get(tag, 0) + 1
        path = f"{self.stack[-1][1]}/{tag}[{siblings[tag]}]"
        if tag == "br":
            self.emit("\n", len(self.get_starttag_text()), "BR_TO_LF")
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, path, {}))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        self.emit(data, len(data), "TEXT")

    def handle_entityref(self, name: str) -> None:
        raw = f"&{name};"
        # HTML permits some references without a semicolon; record the actual range.
        size = len(raw) if self.source.startswith(raw, self.source_offset()) else len(raw) - 1
        self.emit(html.unescape(self.source[self.source_offset():self.source_offset() + size]), size, "ENTITY")

    def handle_charref(self, name: str) -> None:
        raw = f"&#{name};"
        size = len(raw) if self.source.startswith(raw, self.source_offset()) else len(raw) - 1
        self.emit(html.unescape(self.source[self.source_offset():self.source_offset() + size]), size, "ENTITY")


def markup_unit(reference: str, raw: bytes) -> dict[str, Any]:
    source = raw.decode("utf-8")
    parser = MarkupText(source)
    parser.feed(source)
    parser.close()
    return unit(reference, "".join(parser.chunks), parser.nodes)


def zip_path(name: str) -> str:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name or str(path) != name:
        raise AssetError(f"UNSAFE_EPUB_MEMBER: {name}")
    return name


def epub_units(raw: bytes) -> list[dict[str, Any]]:
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
            if len(names) != len(set(names)):
                raise AssetError("DUPLICATE_EPUB_MEMBER")
            for name in names:
                zip_path(name)
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            roots = [element for element in container.iter() if element.tag.rsplit("}", 1)[-1] == "rootfile"]
            if len(roots) != 1:
                raise AssetError("AMBIGUOUS_EPUB_PACKAGE")
            opf_path = zip_path(roots[0].attrib["full-path"])
            package = ET.fromstring(archive.read(opf_path))
            items = {}
            spine = None
            for element in package:
                tag = element.tag.rsplit("}", 1)[-1]
                if tag == "manifest":
                    for item in element:
                        if item.attrib["id"] in items:
                            raise AssetError("DUPLICATE_EPUB_ITEM_ID")
                        items[item.attrib["id"]] = item.attrib
                elif tag == "spine":
                    if spine is not None:
                        raise AssetError("AMBIGUOUS_EPUB_SPINE")
                    spine = element
            if spine is None:
                raise AssetError("MISSING_EPUB_SPINE")
            result = []
            seen = set()
            for entry in spine:
                item = items[entry.attrib["idref"]]
                url = urlsplit(item["href"])
                if url.scheme or url.netloc or url.query or url.fragment:
                    raise AssetError("EXTERNAL_OR_FRAGMENT_EPUB_ITEM")
                href = unquote(url.path)
                if href.startswith("/") or "\\" in href:
                    raise AssetError("UNSAFE_EPUB_ITEM")
                path = zip_path(posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), href)))
                if path in seen:
                    raise AssetError("DUPLICATE_EPUB_SPINE_ITEM")
                if item.get("media-type") != "application/xhtml+xml":
                    raise AssetError(f"UNSUPPORTED_EPUB_ITEM_TYPE: {item.get('media-type')}")
                seen.add(path)
                result.append(markup_unit(f"epub:{path}", archive.read(path)))
            return result
    except (BadZipFile, ET.ParseError, KeyError, RuntimeError) as exc:
        raise AssetError(f"INVALID_EPUB: {exc}") from exc


def extract_units(raw: bytes, config: dict[str, Any]) -> list[dict[str, Any]]:
    format_name = config["format"]
    try:
        if format_name == "TEXT":
            text = raw.decode("utf-8")
            result = [unit("text:1", text, [{"start": 0, "end": len(text), "origin": {"raw_start": 0, "raw_end": len(text)}}])]
        elif format_name == "HTML":
            result = [markup_unit("html:1", raw)]
        elif format_name == "EPUB":
            result = epub_units(raw)
        elif format_name == "PDF":
            import pymupdf
            try:
                with pymupdf.open(stream=raw, filetype="pdf") as document:
                    if document.needs_pass:
                        raise AssetError("ENCRYPTED_PDF")
                    pages = config.get("pdf_pages", list(range(1, len(document) + 1)))
                    if any(page > len(document) for page in pages):
                        raise AssetError("PDF_PAGE_OUT_OF_RANGE")
                    result = []
                    for number in pages:
                        text = document[number - 1].get_text("text", sort=False)
                        result.append(unit(f"pdf:page:{number}", text, [{
                            "start": 0, "end": len(text), "origin": {"pdf_page": number},
                        }]))
            except pymupdf.FileDataError as exc:
                raise AssetError(f"INVALID_PDF: {exc}") from exc
        else:
            raise AssetError(f"UNSUPPORTED_FORMAT: {format_name}")
    except UnicodeDecodeError as exc:
        raise AssetError(f"INVALID_UTF8: {exc}") from exc
    if not result or not any(item["text"].strip() for item in result):
        raise AssetError("NO_EXTRACTABLE_TEXT")
    return result
