"""Deterministic prompts from verified writing inputs; no prompt-side authority."""
from __future__ import annotations

from pathlib import Path

from ..assets import AssetCatalog
from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..evaluation.state import SceneStateAdapter
from ..io import load_data
from ..literary_inputs import LiteraryInputs
from .records import binding, bound_bytes
from .runner import Budget, DEFAULT_MODEL


class PromptRenderer:
    def __init__(self, root: Path):
        self.root = root.resolve()
        # Per invocation only: samples share one verified package/exemplar load.
        # No persistent corpus cache that could hide changed carrier bytes.
        self.packages: dict[str, dict] = {}

    def draft(self, package_path: str, chapter: int, *, route: str = "harness", characters: int = 6000,
              plan_path: str | None = None, previous_path: str | None = None) -> dict:
        if type(chapter) is not int or chapter < 1 or characters < 1:
            raise ValueError("chapter and target characters must be positive")
        if route not in {"harness", "direct"}:
            raise ValueError("unknown writing route")
        catalog = AssetCatalog.from_repo(self.root)
        if package_path not in self.packages:
            self.packages[package_path] = LiteraryInputs(catalog).package(package_path)
        report = self.packages[package_path]
        if report["status"] != "PASS":
            raise ValueError("writing package integrity failed: " + "; ".join(report["findings"]))
        package = report["package"]
        if package["chapter"] != chapter:
            raise ValueError("writing package chapter differs from requested chapter")
        manifest_path = catalog.resolve(report["exemplars"]["spec"]["manifest_ref"]).path.relative_to(self.root).as_posix()
        paths = {package_path, package["exemplar_set"]["path"], manifest_path}
        data = {"chapter": chapter, "target_characters": characters, "operation_scope": "RESEARCH",
                "package": package, "input_readiness": {"scope": report["scope"], "blockers": report["production_blockers"]},
                "world": {}, "plan": {}, "scenes": [], "previous_ending": None, "threads": None}
        for domain in ("world", "plan"):
            for ref in package[domain]:
                data[domain][ref["path"]] = load_data(repository_path(self.root, ref["path"]))
                paths.add(ref["path"])
        selected_plan = plan_path or f"data/planning/chapters/ch{chapter}.json"
        if plan_path or repository_path(self.root, selected_plan).exists():
            data["chapter_plan"] = load_data(repository_path(self.root, selected_plan))
            if data["chapter_plan"]["chapter"] != chapter:
                raise ValueError("chapter plan chapter mismatch")
            paths.add(selected_plan)
        # Agent overlays are advisory planning inputs, never silently substituted
        # for legacy executable scene contracts or independent semantic readings.
        data["agent_contracts"] = [value for value in data["plan"].values()
                                   if value.get("kind") == "AGENT_SCENE_CONTRACT"]
        scene_paths = []
        for path in sorted((self.root / "data/scenes").glob("*")):
            if path.suffix not in {".json", ".yaml", ".yml"}:
                continue
            relative = path.relative_to(self.root).as_posix()
            contract = load_data(repository_path(self.root, relative))
            if contract.get("chapter") == chapter:
                scene_paths.append((relative, contract))
        if not scene_paths:
            for item in data.get("chapter_plan", {}).get("scenes", []):
                relative = item["ref"]
                skeleton = load_data(repository_path(self.root, relative))
                if skeleton.get("chapter") != chapter:
                    raise ValueError("scene skeleton chapter mismatch")
                paths.add(relative)
                data["scenes"].append({"path": relative, "contract": skeleton, "entry": None,
                                       "unresolved": "DRAFT_SCENE_NO_EXECUTABLE_STATE_CONTRACT"})
            if not data["scenes"]:
                raise ValueError("no scene contracts or declared research skeletons for writing chapter")
        for relative, contract in sorted(scene_paths, key=lambda item: (item[1].get("order", 0), item[0])):
            paths.add(relative)
            data["scenes"].append({"path": relative, "contract": contract,
                                   "entry": SceneStateAdapter(self.root, contract).snapshot()})
        # Entry projection and knowledge guard dependencies are explicit bindings.
        for domain in ("project", "world", "knowledge", "objects"):
            for path in sorted((self.root / "data" / domain).rglob("*")):
                if path.is_file() and path.suffix in {".json", ".yaml", ".yml"}:
                    paths.add(path.relative_to(self.root).as_posix())
        hints = "data/planning/hints.json"
        if repository_path(self.root, hints).exists():
            data["threads"] = load_data(repository_path(self.root, hints))
            paths.add(hints)
        if previous_path:
            # Explicit context selection, not an accidental provider truncation.
            previous = repository_path(self.root, previous_path).read_text(encoding="utf-8")
            data["previous_ending"] = {"selection": "LAST_THREE_PARAGRAPHS", "text": "\n\n".join(previous.split("\n\n")[-3:])}
            paths.add(previous_path)
        data["exemplars"] = report["exemplars"]["segments"]
        from ..graph import ProvenanceGraph
        graph = ProvenanceGraph.from_repo(self.root)
        data["sources"] = [{"record": graph.sources[ref["source_ref"]], "verification": row}
                           for ref, row in zip(package["sources"], report["sources"], strict=True)]
        for path in sorted((self.root / "data/provenance/sources").glob("*.yaml")):
            paths.add(path.relative_to(self.root).as_posix())
        data["guidance"] = "Organize scene obligations and check entry/exit constraints before writing." if route == "harness" else "Write the supplied task directly."
        data["exemplar_dataset_ref"] = report["exemplars"]["spec"]["dataset_ref"]
        if "supplemental_source_sets" in report:
            data["supplemental_source_sets"] = report["supplemental_source_sets"]
            for selected in report["supplemental_source_sets"]:
                paths.update(selected["paths"])
        return self.render("author-v1", data, [binding(self.root, path) for path in sorted(paths)])

    def render(self, template_name: str, data: dict, inputs: list[dict]) -> dict:
        if template_name not in {"author-v1", "revise-v1", "revise-v2", "plan-draft-v1"}:
            raise ValueError("unknown generation template")
        path = f"data/writing/prompts/{template_name}.md"
        template = binding(self.root, path)
        system = bound_bytes(self.root, template).decode("utf-8")
        rendered = {"system": system, "messages": [{"role": "user", "content": canonical_bytes(data).decode()}]}
        return {**rendered, "prompt_sha256": digest(canonical_bytes(rendered)),
                "template": template, "inputs": inputs, "task": data}


def request_for(rendered: dict, budget: Budget, model: str = DEFAULT_MODEL, *, fallbacks: bool = False) -> dict:
    if fallbacks:
        raise ValueError("provider fallbacks are not enabled in this bounded runner")
    budget.validate()
    if not model or not model.startswith("claude-"):
        raise ValueError("an explicit Claude model ID is required")
    return {"model": model, "max_tokens": budget.max_tokens, "system": rendered["system"],
            "messages": rendered["messages"]}
