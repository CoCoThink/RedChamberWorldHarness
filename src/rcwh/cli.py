"""Public CLI entry point; command handlers and parsers live in their domains."""
import argparse

from .application.common import repo_root
from .application.diagnostics import add_commands as add_diagnostics
from .application.pilot import add_commands as add_pilot
from .application.delivery import add_commands as add_delivery
from .application.foundation import add_foundation_commands
from .application.evidence import add_commands as add_evidence, cmd_validate, cmd_trace, cmd_literal, cmd_mechanism, cmd_open, cmd_regression, cmd_plock
from .application.evaluation import add_commands as add_evaluation, cmd_evaluate, cmd_semantic, cmd_literary_suite, cmd_literary_evaluate, cmd_historical_adapter, cmd_knowledge
from .application.planning import add_commands as add_planning, cmd_hypothesis, cmd_scenario, cmd_pareto, cmd_prewrite
from .application.research import add_commands as add_research, cmd_literary_stress, cmd_narrative_discourse, cmd_microdraft, cmd_blind_microdraft_review, cmd_revision_ablation
from .application.adoption import add_commands as add_adoption, cmd_competition, cmd_literary_production, cmd_implementation, cmd_promotion
from .application.world import add_commands as add_world, cmd_reconstruction, cmd_world, cmd_object, cmd_literary_ecology


def main() -> None:
    parser = argparse.ArgumentParser(prog="rcwh")
    parser.add_argument("--root", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    add_foundation_commands(sub, repo_root)
    add_diagnostics(sub)
    add_pilot(sub)
    add_delivery(sub)
    add_evidence(sub)
    add_evaluation(sub)
    add_planning(sub)
    add_research(sub)
    add_adoption(sub)
    add_world(sub)
    args = parser.parse_args()
    try:
        status = args.func(args)
    except (KeyError, OSError, ValueError) as exc:
        import json
        print(json.dumps({"status": "FAIL", "findings": [str(exc)]}, ensure_ascii=False))
        status = 1
    raise SystemExit(status)


if __name__ == "__main__":
    main()
