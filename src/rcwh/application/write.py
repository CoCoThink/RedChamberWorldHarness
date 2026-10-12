"""CLI adapter for research writing. Dry-run is the default, even with a key."""
from __future__ import annotations

import json
from pathlib import Path

from ..assets.paths import repository_path
from ..generation.records import binding, store
from ..generation.render import PromptRenderer, request_for
from ..generation.runner import AnthropicRunner, Budget, DEFAULT_MODEL, ReplayRunner
from ..generation.writing import diff_report, feedback_report, generate, load_draft, revision_prompt
from ..io import load_data
from .common import repo_root


def budget_for(args) -> Budget:
    return Budget(max_tokens=args.max_tokens, timeout_seconds=args.timeout,
                  max_retries=args.retries, max_requests=args.max_requests,
                  max_output_tokens=args.max_output_tokens, max_input_bytes=args.max_input_bytes)


def runner_for(args, root: Path):
    if args.replay:
        value = load_data(repository_path(root, args.replay))
        return ReplayRunner(value if isinstance(value, list) else [value])
    return AnthropicRunner(execute=args.execute, network_consent=args.network_consent)


def is_dry(args) -> bool:
    return args.dry_run or (not args.execute and not args.replay)


def preview(rendered: dict, budget: Budget, args) -> dict:
    request = request_for(rendered, budget, args.model, fallbacks=args.fallbacks)
    from ..candidate_reviews import canonical_bytes, digest
    if len(canonical_bytes(request)) > budget.max_input_bytes:
        raise ValueError("request exceeds input byte budget; no truncation performed")
    return {"status": "PASS", "mode": "DRY_RUN", "prompt_sha256": rendered["prompt_sha256"],
            "request_sha256": digest(canonical_bytes(request)), "request": request,
            "template": rendered["template"], "inputs": rendered["inputs"], "budget": budget.to_dict(),
            "budget_limitation": "Request/output/input-byte ceilings, not a currency or input-token ceiling; actual input usage is billed.",
            "authority_effect": "NONE"}


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.write_action == "diff":
            payload = diff_report(root, args.left, args.right)
        elif args.write_action == "draft":
            if not 1 <= args.samples <= 10:
                raise ValueError("samples must be between 1 and 10")
            budget = budget_for(args)
            budget.validate(args.samples, fallback=args.fallbacks)
            rendered = PromptRenderer(root).draft(args.package, args.chapter, route=args.route,
                                                 characters=args.characters, plan_path=args.plan,
                                                 previous_path=args.previous)
            if is_dry(args):
                payload = {**preview(rendered, budget, args), "samples": args.samples}
            else:
                runner = runner_for(args, root)
                results = []
                for _ in range(args.samples):
                    results.append(generate(root, runner, rendered, budget, chapter=args.chapter,
                                            model=args.model, route=args.route, fallbacks=args.fallbacks))
                payload = {"status": "PASS", "drafts": results, "authority_effect": "NONE"}
        elif args.write_action == "feedback":
            # Lexical/style/declared-state feedback runs offline by default.
            # Semantic API calls require explicit execute or replay fixtures.
            runner = None if is_dry(args) else runner_for(args, root)
            report = feedback_report(root, args.candidate, runner=runner, budget=budget_for(args),
                                     model=args.model, style_reference=args.style_reference,
                                     exclude_chapters=args.exclude_chapters, fallbacks=args.fallbacks)
            payload = {"status": "PASS", "report": report, "authority_effect": "NONE"}
            if args.dry_run:
                payload["mode"] = "DRY_RUN"
            else:
                payload["feedback"] = store(root, "data/writing/feedback", report)
        else:
            draft, _ = load_draft(root, args.candidate)
            rendered = revision_prompt(root, args.candidate, args.feedback, args.notes)
            budget = budget_for(args)
            if is_dry(args):
                payload = preview(rendered, budget, args)
            else:
                payload = generate(root, runner_for(args, root), rendered, budget, chapter=draft["chapter"],
                                   model=args.model, route=draft["route"], parent=binding(root, args.candidate),
                                   feedback=binding(root, args.feedback), fallbacks=args.fallbacks)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        payload = {"status": "FAIL", "findings": [str(exc)], "authority_effect": "NONE"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] == "FAIL" else 0


def add_commands(sub) -> None:
    parser = sub.add_parser("write", help="Research draft/feedback/revision; dry-run by default")
    commands = parser.add_subparsers(dest="write_action", required=True)
    draft = commands.add_parser("draft")
    draft.add_argument("package", help="Repository-relative frozen writing package")
    draft.add_argument("--chapter", type=int, required=True)
    draft.add_argument("--route", choices=["direct", "harness"], default="harness")
    draft.add_argument("--samples", type=int, default=1)
    draft.add_argument("--characters", type=int, default=6000)
    draft.add_argument("--plan")
    draft.add_argument("--previous", help="Repository prose to supply last three paragraphs")
    feedback = commands.add_parser("feedback")
    feedback.add_argument("candidate", help="Repository-relative immutable draft record, not bare prose")
    feedback.add_argument("--style-reference", action="store_true", help="Compute corpus distribution (may rebuild corpus)")
    feedback.add_argument("--exclude-chapters", nargs="*", type=int, default=[])
    revise = commands.add_parser("revise")
    revise.add_argument("candidate", help="Repository-relative immutable draft record")
    revise.add_argument("--feedback", required=True)
    revise.add_argument("--notes", help="Repository-relative editorial notes")
    diff = commands.add_parser("diff")
    diff.add_argument("left")
    diff.add_argument("right")
    for p in (draft, feedback, revise):
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--execute", action="store_true", help="Actually send model requests; requires separate network consent")
        p.add_argument("--network-consent", action="store_true", help="Confirm sending supplied materials and paying for this explicit budget")
        p.add_argument("--replay", help="Repository-relative JSON provider response fixture(s); offline")
        p.add_argument("--model", default=DEFAULT_MODEL)
        p.add_argument("--max-tokens", type=int, default=8192)
        p.add_argument("--timeout", type=float, default=120)
        p.add_argument("--retries", type=int, default=0)
        p.add_argument("--max-requests", type=int, default=1)
        p.add_argument("--max-output-tokens", type=int, default=8192)
        p.add_argument("--max-input-bytes", type=int, default=1000000)
    parser.set_defaults(func=command, fallbacks=False)
