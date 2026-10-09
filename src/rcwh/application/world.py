from __future__ import annotations

import argparse
import json
from pathlib import Path
from ..literary_ecology import LiteraryEcologyRuntime, format_literary_ecology
from ..object_network import ObjectNetworkRuntime, format_object
from ..assets import AssetCatalog
from ..reconstruction import ReconstructionRegistry, format_reconstruction
from ..world import WorldRuntime, format_world
from .common import repo_root


def cmd_reconstruction(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = ReconstructionRegistry.from_repo(root)
    try:
        kind = args.reconstruction_command
        if kind == "summary":
            payload = registry.summary()
        elif kind == "chapter":
            payload = registry.chapter(args.key)
        elif kind == "r":
            payload = registry.r(args.key)
        elif kind == "p":
            payload = registry.p(args.key)
        elif kind == "timeline":
            payload = registry.timeline_at(args.key)
        elif kind == "state":
            payload = registry.state_at(args.key)
        elif kind == "jade":
            payload = registry.data["jade_logistics"]
        elif kind == "prison":
            payload = registry.data["prison_case"]
        elif kind == "legacy":
            payload = registry.legacy(args.key)
        elif kind == "cross":
            payload = registry.cross(args.key)
        else:
            raise KeyError(f"Unknown reconstruction command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_reconstruction(kind, payload))
    return 0

def cmd_world(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    world = WorldRuntime.from_repo(root)
    try:
        kind = args.world_command
        if kind == "summary":
            payload = world.summary()
        elif kind == "chapter":
            payload = world.chapter(args.chapter)
        elif kind == "character":
            payload = world.character_state(args.character_id, args.chapter)
        elif kind == "knowledge":
            payload = world.knowledge(args.character_id, args.chapter)
        elif kind == "location":
            payload = world.location(args.location_id)
        elif kind == "relation":
            payload = world.relation(args.relation_id, args.chapter)
        elif kind == "economy":
            payload = world.economy(args.chapter)
        else:
            raise KeyError(f"Unknown world command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_world(kind, payload))
    return 0

def cmd_object(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        objects = ObjectNetworkRuntime.from_repo(root)
        kind = args.object_command
        if kind == "summary":
            payload = objects.summary()
        elif kind == "get":
            payload = objects.snapshot(args.object_id, args.chapter)
        elif kind == "history":
            payload = objects.history(args.object_id)
        elif kind == "jade":
            payload = objects.jade(args.chapter)
        elif kind == "location":
            payload = objects.at_location(args.location, args.chapter)
        elif kind == "continuity":
            payload = objects.continuity_report()
        elif kind == "trace":
            migration_registry = AssetCatalog.from_repo(root)
            reconstruction = ReconstructionRegistry.from_repo(root)
            payload = objects.trace(args.object_id, migration_registry, reconstruction)
        else:
            raise KeyError(f"Unknown object command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_object(kind, payload))
    if kind == "continuity":
        return 0 if payload["status"] == "PASS" else 1
    return 0

def cmd_literary_ecology(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    ecology = LiteraryEcologyRuntime.from_repo(root)
    try:
        kind = args.literary_ecology_command
        if kind == "summary":
            payload = ecology.summary()
        elif kind == "dimension":
            payload = ecology.dimension(args.key)
        elif kind == "voice":
            payload = ecology.voice(args.key)
        elif kind == "technique":
            payload = ecology.technique(args.key)
        elif kind == "evidence":
            payload = ecology.evidence_node(args.key)
        elif kind == "chapter":
            payload = ecology.chapter(args.chapter)
        elif kind == "qingbang":
            payload = ecology.qingbang()
        elif kind == "ten-du-yin":
            payload = ecology.ten_du_yin()
        elif kind == "xu-zhuangzi":
            payload = ecology.xu_zhuangzi()
        elif kind == "daiyu":
            payload = ecology.daiyu_interfaces()
        elif kind == "g":
            payload = ecology.g(args.key)
        elif kind == "search":
            payload = ecology.search(args.term)
        elif kind == "trace":
            registry = AssetCatalog.from_repo(root)
            payload = ecology.trace(args.kind, args.key, registry)
        else:
            raise KeyError(f"Unknown literary-ecology command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literary_ecology(kind, payload))
    return 0


def add_commands(sub) -> None:
    p_recon = sub.add_parser("reconstruction")
    recon_sub = p_recon.add_subparsers(dest="reconstruction_command", required=True)
    p = recon_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_reconstruction)
    for name in ("chapter", "timeline", "state"):
        p = recon_sub.add_parser(name)
        p.add_argument("key", type=int)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)
    for name in ("r", "p", "legacy", "cross"):
        p = recon_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)
    for name in ("jade", "prison"):
        p = recon_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)

    p_world = sub.add_parser("world")
    world_sub = p_world.add_subparsers(dest="world_command", required=True)
    p = world_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("character")
    p.add_argument("character_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("knowledge")
    p.add_argument("character_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("location")
    p.add_argument("location_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("relation")
    p.add_argument("relation_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("economy")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)

    p_lit_ecology = sub.add_parser("literary-ecology")
    lit_ecology_sub = p_lit_ecology.add_subparsers(
        dest="literary_ecology_command", required=True
    )
    p = lit_ecology_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    for name in ("dimension", "voice", "technique", "evidence", "g"):
        p = lit_ecology_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    for name in ("qingbang", "ten-du-yin", "xu-zhuangzi", "daiyu"):
        p = lit_ecology_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("trace")
    p.add_argument(
        "kind",
        choices=[
            "dimension", "voice", "technique", "evidence", "g", "chapter",
            "qingbang", "ten_du_yin", "xu_zhuangzi"
        ],
    )
    p.add_argument("key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)

    p_object = sub.add_parser("object")
    object_sub = p_object.add_subparsers(dest="object_command", required=True)
    p = object_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("get")
    p.add_argument("object_id")
    p.add_argument("--chapter", type=int, help="Defaults to the last configured project chapter")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("history")
    p.add_argument("object_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("jade")
    p.add_argument("--chapter", type=int, help="Defaults to the last configured project chapter")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("location")
    p.add_argument("location")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("continuity")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("trace")
    p.add_argument("object_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
