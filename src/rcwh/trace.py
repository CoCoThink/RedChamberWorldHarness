from __future__ import annotations

from typing import Any


def _line(label: str, value: Any) -> str:
    return f"{label}: {value}"


def _append_implementations(out: list[str], implementations: list[dict[str, Any]]) -> None:
    out.append("")
    out.append("IMPLEMENTATIONS")
    if not implementations:
        out.append("- none")
        return
    for item in implementations:
        out.append(
            f"- {item['id']} [{item['status']}] ch{item['chapter']} {item['summary']}"
        )


def _append_axes(out: list[str], axes: list[dict[str, Any]]) -> None:
    out.append("")
    out.append("TITLE AXIS")
    if not axes:
        out.append("- none")
        return
    for axis in axes:
        out.append(f"- {axis['id']} [{axis['class']}] {axis['text']}")


def format_trace(payload: dict[str, Any]) -> str:
    kind = payload["type"]
    out: list[str] = []

    if kind == "source":
        source = payload["source"]
        out.extend([
            "SOURCE",
            _line("id", source["id"]),
            _line("type", source["type"]),
            _line("tier", source.get("tier")),
            _line("witness", source["witness"]),
            _line("title", source["title"]),
            _line("locator", source.get("locator")),
            _line("text", source.get("text")),
            "",
            "SUPPORTED CLAIMS",
        ])
        for claim in payload["claims"]:
            out.append(f"- {claim['id']} [{claim['status']}] {claim['statement']}")
        out.append("")
        out.append("DOWNSTREAM DECISIONS")
        for decision in payload["decisions"]:
            out.append(f"- {decision['id']} [{decision['status']}] {decision['statement']}")
        _append_axes(out, payload.get("title_axes", []))
        _append_implementations(out, payload.get("implementations", []))
        return "\n".join(out)

    if kind == "claim":
        claim = payload["claim"]
        out.extend([
            "CLAIM",
            _line("id", claim["id"]),
            _line("status", claim["status"]),
            _line("kind", claim["kind"]),
            _line("role", claim.get("role")),
            _line("modality", claim.get("modality")),
            _line("literal_targets", claim.get("literal_targets")),
            _line("t_axis", claim.get("t_axis")),
            _line("statement", claim["statement"]),
            "",
            "SUPPORTED BY",
        ])
        if payload["sources"]:
            for source in payload["sources"]:
                out.append(f"- {source['id']} ({source['type']}) {source['title']}")
                out.append(f"  text: {source['text']}")
        else:
            out.append("- none")
        out.append("")
        out.append("USED BY")
        for decision in payload["decisions"]:
            out.append(
                f"- {decision['id']} [{decision['status']}/{decision['constraint']}] "
                f"{decision['statement']}"
            )
        _append_axes(out, payload.get("title_axes", []))
        _append_implementations(out, payload.get("implementations", []))
        return "\n".join(out)

    if kind == "decision":
        decision = payload["decision"]
        out.extend([
            "DECISION",
            _line("id", decision["id"]),
            _line("status", decision["status"]),
            _line("constraint", payload["permission"]),
            _line("fully_source_backed", payload["fully_source_backed"]),
            _line("statement", decision["statement"]),
            "",
            "BASED ON CLAIMS",
        ])
        for claim in payload["claims"]:
            out.append(f"- {claim['id']} [{claim['status']}] {claim['statement']}")
        out.append("")
        out.append("TRACE TO SOURCES")
        if payload["sources"]:
            for source in payload["sources"]:
                out.append(f"- {source['id']} ({source['type']}) {source['title']}")
        else:
            out.append("- none")
        _append_axes(out, payload.get("title_axes", []))
        _append_implementations(out, payload.get("implementations", []))
        return "\n".join(out)

    if kind == "implementation":
        implementation = payload["implementation"]
        out.extend([
            "IMPLEMENTATION",
            _line("id", implementation["id"]),
            _line("status", implementation["status"]),
            _line("chapter", implementation["chapter"]),
            _line("summary", implementation["summary"]),
            _line("locator", implementation["locator"]),
            "",
            "DECISIONS",
        ])
        for decision in payload["decisions"]:
            out.append(
                f"- {decision['id']} [{decision['status']}/{decision['constraint']}] "
                f"{decision['statement']}"
            )
        out.append("")
        out.append("CLAIMS")
        for claim in payload["claims"]:
            out.append(f"- {claim['id']} [{claim['status']}] {claim['statement']}")
        out.append("")
        out.append("SOURCES")
        if payload["sources"]:
            for source in payload["sources"]:
                out.append(f"- {source['id']} ({source['type']}) {source['title']}")
        else:
            out.append("- none")
        _append_axes(out, payload.get("title_axes", []))
        return "\n".join(out)

    axis = payload["title_axis"]
    out.extend([
        "TITLE AXIS",
        _line("id", axis["id"]),
        _line("class", axis["class"]),
        _line("generated", axis["generated"]),
        _line("text", axis["text"]),
        _line("current_chapter", axis.get("current_chapter")),
        "",
        "CLAIMS",
    ])
    for claim in payload["claims"]:
        out.append(
            f"- {claim['id']} [{claim['status']}] role={claim.get('role')} "
            f"{claim['statement']}"
        )
    out.append("")
    out.append("SOURCES")
    for source in payload["sources"]:
        out.append(f"- {source['id']} [{source.get('tier')}] {source['title']}")
    out.append("")
    out.append("DECISIONS")
    for decision in payload["decisions"]:
        out.append(
            f"- {decision['id']} [{decision['status']}/{decision['constraint']}] "
            f"{decision['statement']}"
        )
    _append_implementations(out, payload.get("implementations", []))
    return "\n".join(out)
