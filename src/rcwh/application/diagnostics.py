"""Prose observations, character coverage and focused corpus audit material."""
import json
from pathlib import Path

from ..evaluation.characters import CharacterProfiles
from ..evaluation.corpus_focus import focus_report
from ..evaluation.continuity import continuity_report, impact_report
from ..evaluation.style import style_diagnostics
from ..evaluation.style_reference import reference_profile
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.diagnostic == "style":
            dataset_ref = getattr(args, "reference", None)
            reference = reference_profile(root, dataset_ref) if dataset_ref else None
            payload = style_diagnostics(Path(args.text).read_bytes().decode(),
                                        [Path(p).read_bytes().decode() for p in args.poetry], reference=reference)
        elif args.diagnostic == "characters":
            profiles = CharacterProfiles(root)
            payload = profiles.profile(args.character) if args.character else profiles.summary()
        elif args.diagnostic == "continuity":
            payload = continuity_report(root, args.chapter)
        elif args.diagnostic == "impact":
            payload = impact_report(root, args.target)
        else:
            payload = focus_report(root)
    except (KeyError, OSError, ValueError) as exc:
        payload = {"status": "FAIL", "findings": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("status") == "FAIL" else 2 if payload.get("status") == "PENDING" else 0


def add_commands(sub) -> None:
    parser = sub.add_parser("diagnostics")
    choices = parser.add_subparsers(dest="diagnostic", required=True)
    style = choices.add_parser("style")
    style.add_argument("text")
    style.add_argument("--poetry", nargs="*", default=[])
    style.add_argument("--reference", help="exploratory corpus dataset_ref (not a literary gate)")
    characters = choices.add_parser("characters")
    characters.add_argument("--character")
    choices.add_parser("corpus-focus")
    continuity = choices.add_parser("continuity")
    continuity.add_argument("--chapter", type=int)
    impact = choices.add_parser("impact")
    impact.add_argument("target", help="canonical character.* or object.* state target")
    parser.set_defaults(func=command)
