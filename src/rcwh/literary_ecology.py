from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .contracts import unique_index, project_chapters, coverage_errors, validate_plan_constraints


@dataclass
class LiteraryEcologyRuntime:
    chapter_scope: tuple[int, ...]
    data: dict[str, Any]
    dimensions: dict[str, dict[str, Any]]
    dimensions_by_key: dict[str, dict[str, Any]]
    voices: dict[str, dict[str, Any]]
    techniques: dict[str, dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    g_layer: dict[str, dict[str, Any]]
    author_rhyme: dict[int, dict[str, Any]]
    post80_text: dict[int, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryEcologyRuntime":
        data = load_data(root / "data" / "literary_ecology" / "m5.json") or {}
        dims = unique_index(data.get('dimensions', []), 'id')
        return cls(
            chapter_scope=project_chapters(root),
            data=data,
            dimensions=dims,
            dimensions_by_key=unique_index(data.get('dimensions', []), 'key'),
            voices=unique_index(data.get('voice_profiles', []), 'id'),
            techniques=unique_index(data.get('techniques', []), 'id'),
            evidence=unique_index(data.get('evidence_nodes', []), 'id'),
            g_layer=unique_index(data.get('g_layer_decisions', []), 'id'),
            author_rhyme=unique_index(data.get('author_rhyme_chapters', []), 'chapter'),
            post80_text=unique_index(data.get('post80_text_ecology', []), 'chapter'),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "dimensions": len(self.dimensions),
            "voice_profiles": len(self.voices),
            "techniques": len(self.techniques),
            "evidence_nodes": len(self.evidence),
            "g_layer_decisions": len(self.g_layer),
            "post80_chapters": len(self.post80_text),
            "author_rhyme_chapters": len(self.author_rhyme),
            "source_documents": len(self.data.get("sources", {})),
        }

    def dimension(self, key: str) -> dict[str, Any]:
        if key in self.dimensions:
            return self.dimensions[key]
        if key in self.dimensions_by_key:
            return self.dimensions_by_key[key]
        raise KeyError(f"Unknown literary-ecology dimension: {key}")

    def voice(self, character_id: str) -> dict[str, Any]:
        if character_id not in self.voices:
            raise KeyError(f"Unknown voice profile: {character_id}")
        return self.voices[character_id]

    def technique(self, key: str) -> dict[str, Any]:
        if key in self.techniques:
            return self.techniques[key]
        for item in self.techniques.values():
            if item["name"] == key:
                return item
        raise KeyError(f"Unknown technique: {key}")

    def evidence_node(self, node_id: str) -> dict[str, Any]:
        if node_id not in self.evidence:
            raise KeyError(f"Unknown literary evidence node: {node_id}")
        return self.evidence[node_id]

    def chapter(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.post80_text:
            raise KeyError(f"Literary Ecology chapter query covers 81..100: {chapter}")
        return {
            "chapter": chapter,
            "text_ecology": self.post80_text[chapter],
            "author_rhyme": self.author_rhyme[chapter],
        }

    def qingbang(self) -> dict[str, Any]:
        return self.data["qingbang"]

    def ten_du_yin(self) -> dict[str, Any]:
        return self.data["ten_du_yin"]

    def xu_zhuangzi(self) -> dict[str, Any]:
        return self.data["xu_zhuangzi"]

    def daiyu_interfaces(self) -> list[dict[str, Any]]:
        return self.data["daiyu_text_interfaces"]

    def g(self, g_id: str) -> dict[str, Any]:
        if g_id not in self.g_layer:
            raise KeyError(f"Unknown G-layer decision: {g_id}")
        return self.g_layer[g_id]

    def search(self, term: str) -> dict[str, Any]:
        needle = term.casefold()
        hits: list[dict[str, Any]] = []
        collections = [
            ("dimension", list(self.dimensions.values()), "id"),
            ("voice", list(self.voices.values()), "id"),
            ("technique", list(self.techniques.values()), "id"),
            ("evidence", list(self.evidence.values()), "id"),
            ("g", list(self.g_layer.values()), "id"),
            ("chapter_text", list(self.post80_text.values()), "chapter"),
            ("author_rhyme", list(self.author_rhyme.values()), "chapter"),
            ("daiyu_interface", self.data.get("daiyu_text_interfaces", []), "interface_id"),
        ]
        for kind, items, key_name in collections:
            for item in items:
                if needle in _flatten_text(item).casefold():
                    hits.append({
                        "kind": kind,
                        "key": item.get(key_name),
                        "summary": _short_summary(item),
                        "source_refs": _source_refs(item),
                    })
        for kind, key in [
            ("qingbang", "qingbang"),
            ("ten_du_yin", "ten_du_yin"),
            ("xu_zhuangzi", "xu_zhuangzi"),
        ]:
            item = self.data.get(key, {})
            if needle in _flatten_text(item).casefold():
                hits.append({
                    "kind": kind,
                    "key": key,
                    "summary": _short_summary(item),
                    "source_refs": _source_refs(item),
                })
        return {"term": term, "count": len(hits), "hits": hits[:100]}

    def trace(self, kind: str, key: str, catalog: Any) -> dict[str, Any]:
        item = self._resolve(kind, key)
        refs = _source_refs(item)
        resolved = []
        for ref in refs:
            if not ref.startswith("asset:"):
                resolved.append({"ref": ref, "kind": "non_asset_ref"})
                continue
            doc = catalog.assets.get(ref)
            if doc is None:
                resolved.append({"ref": ref, "kind": "missing_asset"})
                continue
            resolved.append({"ref": ref, "kind": "asset", **catalog.resolve(ref).summary()})
        return {
            "kind": kind,
            "key": key,
            "node": item,
            "resolved_sources": resolved,
            "trace_complete": bool(resolved) and all(x["kind"] == "asset" for x in resolved if x["ref"].startswith("asset:")),
        }

    def validate_integrity(self, catalog: Any) -> list[str]:
        errors: list[str] = []
        if not self.dimensions or not self.voices or not self.techniques:
            errors.append("literary dimensions, voices and techniques must be nonempty")
        errors.extend(coverage_errors(self.post80_text, self.chapter_scope, "literary chapter ecology"))
        errors.extend(coverage_errors(self.author_rhyme, self.chapter_scope, "author-rhyme chapters"))
        source_docs = self.data.get("sources", {})
        if not source_docs:
            errors.append("literary source bindings must be nonempty")
        for ref, source in source_docs.items():
            doc = catalog.assets.get(ref)
            if doc is None:
                errors.append(f"M5 source is not registered: {ref}")
            elif doc["sha256"] != source["sha256"]:
                errors.append(f"M5 source SHA mismatch: {ref}")

        for node in self._all_source_nodes():
            for ref in _source_refs(node):
                if ref.startswith("asset:") and ref not in catalog.assets:
                    errors.append(f"M5 node references unregistered document {ref}")

        q = self.data.get("qingbang", {})
        if q.get("formal_title_status") != "OPEN":
            errors.append("Qingbang formal title must remain OPEN")
        literals = {(x.get("character_id"), x.get("literal")) for x in q.get("known_evaluations", [])}
        if literals != {("baoyu", "情不情"), ("daiyu", "情情")}:
            errors.append("Only the two known Qingbang evaluation literals may be hard-coded")
        if q.get("level_system", {}).get("complete_rosters_locked"):
            errors.append("Qingbang complete rosters may not be locked")
        if q.get("level_system", {}).get("total_sixty_locked"):
            errors.append("Qingbang total-sixty model may not be locked")

        ten = self.data.get("ten_du_yin", {})
        if ten.get("existence") != "A_LOCKED":
            errors.append("Ten Duyin title existence must remain A-locked")
        if ten.get("author_status") != "OPEN_EVIDENCE_C_WORKING":
            errors.append("Ten Duyin author must remain evidence-OPEN/current-C-working")
        if ten.get("post80") == "LOCKED":
            errors.append("Ten Duyin may not hard-lock an 80+ placement")

        xz = self.data.get("xu_zhuangzi", {})
        if xz.get("future_baoyu_sight") != "OPEN":
            errors.append("Baoyu's later sight of Xu Zhuangzi must remain OPEN")
        if xz.get("not_seen_is_future_step") != "LOCKED":
            errors.append("Xu Zhuangzi 'not seen is a future step' must remain locked")

        errors.extend(validate_plan_constraints(catalog, "literary_ecology", {
            "g_layer": self.g_layer,
            "author_rhyme": self.author_rhyme,
            "author_rhyme_b_chapters": sorted(ch for ch, item in self.author_rhyme.items()
                                             if item["winner"].startswith("B")),
        }))

        return errors

    def _resolve(self, kind: str, key: str) -> Any:
        if kind == "dimension":
            return self.dimension(key)
        if kind == "voice":
            return self.voice(key)
        if kind == "technique":
            return self.technique(key)
        if kind == "evidence":
            return self.evidence_node(key)
        if kind == "g":
            return self.g(key)
        if kind == "chapter":
            return self.chapter(int(key))
        if kind == "qingbang":
            return self.qingbang()
        if kind == "ten_du_yin":
            return self.ten_du_yin()
        if kind == "xu_zhuangzi":
            return self.xu_zhuangzi()
        raise KeyError(f"Unknown literary-ecology trace kind: {kind}")

    def _all_source_nodes(self) -> list[Any]:
        nodes: list[Any] = []
        nodes.extend(self.dimensions.values())
        nodes.extend(self.voices.values())
        nodes.extend(self.techniques.values())
        nodes.extend(self.evidence.values())
        nodes.extend(self.g_layer.values())
        nodes.extend(self.author_rhyme.values())
        nodes.extend(self.post80_text.values())
        nodes.extend(self.data.get("daiyu_text_interfaces", []))
        nodes.extend([
            self.data.get("qingbang", {}),
            self.data.get("ten_du_yin", {}),
            self.data.get("xu_zhuangzi", {}),
        ])
        return nodes


def _source_refs(item: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(item, dict):
        if isinstance(item.get("source_ref"), str):
            refs.append(item["source_ref"])
        if isinstance(item.get("source_refs"), list):
            refs.extend(str(x) for x in item["source_refs"])
        for value in item.values():
            if isinstance(value, (dict, list)):
                for ref in _source_refs(value):
                    if ref not in refs:
                        refs.append(ref)
    elif isinstance(item, list):
        for value in item:
            for ref in _source_refs(value):
                if ref not in refs:
                    refs.append(ref)
    return list(dict.fromkeys(refs))


def _flatten_text(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(_flatten_text(v) for v in item.values())
    if isinstance(item, list):
        return " ".join(_flatten_text(v) for v in item)
    return "" if item is None else str(item)


def _short_summary(item: dict[str, Any]) -> str:
    for key in ("name", "principle", "decision", "texts", "locked", "function", "mode", "voice"):
        value = item.get(key)
        if value:
            return str(value)[:220]
    return _flatten_text(item)[:220]


def format_literary_ecology(kind: str, payload: Any) -> str:
    if kind == "summary":
        return "\n".join([
            "LITERARY ECOLOGY M5",
            f"dimensions: {payload['dimensions']}",
            f"voice_profiles: {payload['voice_profiles']}",
            f"techniques: {payload['techniques']}",
            f"evidence_nodes: {payload['evidence_nodes']}",
            f"post80_chapters: {payload['post80_chapters']}",
            f"source_documents: {payload['source_documents']}",
        ])
    if kind == "voice":
        return "\n".join([
            f"VOICE {payload['id']} / {payload['name']}",
            f"density: {payload['utterance_density']}",
            f"reference_chapters: {', '.join(payload['reference_chapters'])}",
            f"voice: {payload['voice']}",
            f"relation_shift: {payload['relation_shift']}",
            f"post80_forbidden: {payload['post80_forbidden']}",
        ])
    if kind == "chapter":
        t = payload["text_ecology"]
        r = payload["author_rhyme"]
        return "\n".join([
            f"LITERARY ECOLOGY CH{payload['chapter']}",
            f"texts: {t['texts']}",
            f"text_voice: {t['voice']}",
            f"function: {t['function']}",
            f"assessment: {t['assessment']}",
            f"author_rhyme: {r['winner']} / {r['mode']}",
            f"ending_anchor: {r['ending_anchor']}",
        ])
    if kind == "search":
        lines = [f"SEARCH {payload['term']}: {payload['count']} hits"]
        lines.extend(f"- {x['kind']}:{x['key']} | {x['summary']}" for x in payload["hits"])
        return "\n".join(lines)
    return _flatten_text(payload)
