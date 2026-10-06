from __future__ import annotations

from typing import Any


def _line(label: str, value: Any) -> str:
    return f"{label}: {value}"


def format_trace(payload: dict[str, Any]) -> str:
    kind = payload["type"]
    out: list[str] = []

    if kind == "source":
        source = payload["source"]
        out.extend([
            "SOURCE",
            _line("id", source["id"]),
            _line("type", source["type"]),
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
        return "\n".join(out)

    if kind == "claim":
        claim = payload["claim"]
        out.extend([
            "CLAIM",
            _line("id", claim["id"]),
            _line("status", claim["status"]),
            _line("kind", claim["kind"]),
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
            out.append(f"- {decision['id']} [{decision['status']}] {decision['statement']}")
        return "\n".join(out)

    decision = payload["decision"]
    out.extend([
        "DECISION",
        _line("id", decision["id"]),
        _line("status", decision["status"]),
        _line("permission", payload["permission"]),
        _line("evidence_proven", payload["evidence_proven"]),
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
    if decision.get("implementation_refs"):
        out.append("")
        out.append("IMPLEMENTED BY")
        for ref in decision["implementation_refs"]:
            out.append(f"- {ref}")
    return "\n".join(out)
