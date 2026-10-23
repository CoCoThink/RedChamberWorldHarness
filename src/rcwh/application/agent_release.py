"""CLI for isolated agent-reviewed research editions; no stable publication flags."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex

from ..workflow.agent_release import AgentRelease
from .common import repo_root


def _span(part: str) -> range:
    start, _, end = part.strip().partition("-")
    return range(int(start), int(end or start) + 1)


def cmd_agent_release(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.agent_release_command.startswith("review-"):
            from ..workflow import review_campaign
            if args.agent_release_command == "review-plan":
                payload = review_campaign.plan(root, args.request, args.out, batch_size=args.batch_size,
                    max_read_bytes=args.max_read_bytes, max_attempts=args.max_attempts)
            elif args.agent_release_command == "review-run":
                payload = review_campaign.run(root, args.plan, shlex.split(args.worker_command),
                    timeout=args.timeout, model_label=args.model_label)
            elif args.agent_release_command == "review-dispatch":
                payload = review_campaign.dispatch(root, args.plan, limit=args.limit, model_label=args.model_label)
            elif args.agent_release_command == "review-register":
                payload = review_campaign.submit(root, args.plan, args.job, args.opinion, origin=args.origin)
            elif args.agent_release_command == "review-fail":
                payload = review_campaign.fail(root, args.plan, args.job, reason=args.reason,
                    assignment_sha256=args.assignment_sha256, status_code=args.status_code, interrupted=args.interrupted)
            elif args.agent_release_command == "review-reopen":
                payload = review_campaign.reopen(root, args.plan, args.job, reason=args.reason)
            else:
                payload = review_campaign.status(root, args.plan)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return {"PASS": 0, "PENDING": 2, "FAIL": 1}[payload["status"]]
        release = AgentRelease(root)
        if args.agent_release_command == "prepare":
            from ..workflow.release_packets import prepare
            chapters = sorted({int(c) for part in args.chapters.split(",") for c in _span(part)})
            payload = prepare(root, args.edition, args.selection, chapters,
                              coordinator_session_id=args.coordinator_session_id,
                              max_book_read_bytes=args.max_book_read_bytes,
                              reuse_request_path=args.reuse_request)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.agent_release_command == "build":
            payload = release.build(args.request, allow_pending=args.allow_pending)
        else:
            payload = release.evaluate(args.request)
    except (KeyError, OSError, UnicodeError, TypeError, ValueError) as exc:
        payload = {"status": "FAIL", "scope": "AGENT_RESEARCH_RELEASE", "findings": [str(exc)],
                   "authority_effect": "NONE", "stable_active_effect": "NONE"}
    if getattr(args, "json", False) or args.agent_release_command == "prepare" or args.agent_release_command.startswith("review-"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"AGENT RESEARCH RELEASE: {payload['status']}")
        print("stable_active_effect: NONE")
        if "provenance" in payload:
            print(f"provenance: {payload['provenance']}")
        for finding in payload.get("findings", []):
            print(f"- {finding}")
        for pending in payload.get("pending", []):
            print(f"- pending: {pending}")
    return {"PASS": 0, "PENDING": 2, "FAIL": 1}[payload["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("agent-release", help="Isolated agent-only research release, never stable adoption")
    commands = parser.add_subparsers(dest="agent_release_command", required=True)
    for command in ("evaluate", "build"):
        child = commands.add_parser(command)
        child.add_argument("request", help="Repository-relative release request JSON/YAML")
        child.add_argument("--json", action="store_true")
        if command == "build":
            child.add_argument("--allow-pending", action="store_true", help="Emit staging manifest only; do not publish reviewed prose")
        child.set_defaults(func=cmd_agent_release)
    prepare = commands.add_parser("prepare", help="Write review packets, reading lists and a research request")
    prepare.add_argument("edition", help="Edition id (also the request id), e.g. research-81-100-pilot-v1")
    prepare.add_argument("--selection", required=True, help="Repository-relative chapter selection JSON")
    prepare.add_argument("--chapters", required=True, help="Chapters to review, e.g. 86,95,99 or 81-100")
    prepare.add_argument("--coordinator-session-id", required=True, help="Declared coordinator session (not a reviewer)")
    prepare.add_argument("--max-book-read-bytes", type=int, default=197 * 1024,
                         help="Maximum UTF-8 bytes per overlapping continuity segment")
    prepare.add_argument("--reuse-request", help="Reuse unchanged source/corpus contexts from this prior request")
    prepare.set_defaults(func=cmd_agent_release)
    campaign = commands.add_parser("review-plan", help="Prepare two readers per subject and per bounded continuity segment")
    campaign.add_argument("request")
    campaign.add_argument("--out", required=True, help="New immutable repository-relative campaign plan")
    campaign.add_argument("--batch-size", type=int, default=5, help="Maximum concurrent workers, 1..6")
    campaign.add_argument("--max-read-bytes", type=int, default=197 * 1024)
    campaign.add_argument("--max-attempts", type=int, default=3)
    campaign.set_defaults(func=cmd_agent_release)
    runner = commands.add_parser("review-run", help="Run a local JSON stdin/stdout reviewer adapter with retries")
    runner.add_argument("plan")
    runner.add_argument("--worker-command", required=True, help="Executable and args; no shell expansion")
    runner.add_argument("--timeout", type=float, default=600)
    runner.add_argument("--model-label", default="local worker (declared)")
    runner.set_defaults(func=cmd_agent_release)
    dispatch = commands.add_parser("review-dispatch", help="Export a bounded batch for subagents in the current agent environment")
    dispatch.add_argument("plan")
    dispatch.add_argument("--limit", type=int, help="Total active tasks; lower this to the available subagent slots")
    dispatch.add_argument("--model-label", default="agent environment reader (declared)")
    dispatch.set_defaults(func=cmd_agent_release)
    submit = commands.add_parser("review-register", help="Register an actual opinion against its exported assignment")
    submit.add_argument("plan")
    submit.add_argument("job")
    submit.add_argument("--opinion", required=True, help="Original returned AGENT_REVIEW_OPINION JSON file")
    submit.add_argument("--origin", required=True, help="Actual subagent session/task description")
    submit.set_defaults(func=cmd_agent_release)
    failure = commands.add_parser("review-fail", help="Record an actual subagent failure; allow bounded temporary retries")
    failure.add_argument("plan")
    failure.add_argument("job")
    failure.add_argument("--reason", required=True)
    failure.add_argument("--assignment-sha256", required=True, help="Exact assignment hash returned by dispatch")
    transport = failure.add_mutually_exclusive_group()
    transport.add_argument("--status-code", type=int, help="Transport status, e.g. 503")
    transport.add_argument("--interrupted", action="store_true", help="Agent was cancelled, timed out or lost")
    failure.set_defaults(func=cmd_agent_release)
    reopen = commands.add_parser("review-reopen", help="Request a genuine followup reading, preserving the old opinion")
    reopen.add_argument("plan")
    reopen.add_argument("job")
    reopen.add_argument("--reason", required=True)
    reopen.set_defaults(func=cmd_agent_release)
    inspect = commands.add_parser("review-status", help="Inspect bound campaign attempts and registrations")
    inspect.add_argument("plan")
    inspect.set_defaults(func=cmd_agent_release)
