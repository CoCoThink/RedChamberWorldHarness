"""Retain the actual evaluation and normal-build outcome, including refusal."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import subprocess
import sys

from rcwh.workflow.agent_release import AgentRelease
from rcwh.generation.records import binding

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REQUEST = 'data/agent_release/research-81-100-v5/request.json'


def main():
    report = AgentRelease(R).evaluate(REQUEST)
    if report['status'] == 'FAIL' or report['findings']:
        raise ValueError('integrity failures must be fixed before delivery')
    paths = [O / 'final-release-evaluation.json', O / 'normal-build-attempt.json']
    if any(p.exists() for p in paths):
        raise ValueError('actual evidence already exists; refusing overwrite')
    command = [sys.executable, '-m', 'rcwh.cli', 'agent-release', 'build', REQUEST, '--json']
    result = subprocess.run(command, cwd=R, env={**os.environ, 'PYTHONPATH': str(R / 'src')},
                            text=True, capture_output=True)
    edition = R / report['output']['directory']
    paths[0].write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    receipt = {'kind': 'ACTUAL_NORMAL_RESEARCH_BUILD_ATTEMPT',
               'observed_utc': datetime.now(timezone.utc).isoformat(),
               'command': command, 'workdir': str(R), 'allow_pending': False,
               'request': binding(R, REQUEST), 'release_status': report['status'],
               'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
               'refused': result.returncode != 0, 'edition_directory_exists': edition.exists(),
               'authority_effect': 'NONE', 'P9_credit': False}
    paths[1].write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    messages = result.stdout + '\n' + result.stderr
    if report['status'] == 'PENDING':
        if result.returncode == 0 or 'only explicit pending staging is allowed' not in messages or edition.exists():
            raise ValueError('unresolved normal build must refuse and publish no edition files; captured receipt retained')
    elif result.returncode != 0 or json.loads(result.stdout)['status'] != 'PASS':
        raise ValueError('normal PASS build failed; captured receipt retained')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
