import json
from pathlib import Path

from ..delivery import BundleDelivery
from .common import repo_root


def command(args):
    root = Path(args.root).resolve() if args.root else repo_root()
    service = BundleDelivery(root)
    if args.delivery_action == "summary": payload = service.summary()
    elif args.delivery_action == "materialize": payload = service.materialize(args.bundle, Path(args.destination))
    else: payload = service.attachments(Path(args.destination))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def add_commands(sub):
    parser = sub.add_parser("delivery")
    commands = parser.add_subparsers(dest="delivery_action", required=True)
    commands.add_parser("summary")
    materialize = commands.add_parser("materialize")
    materialize.add_argument("bundle")
    materialize.add_argument("destination")
    attachments = commands.add_parser("attachments")
    attachments.add_argument("destination")
    parser.set_defaults(func=command)
