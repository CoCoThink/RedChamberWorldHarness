"""Capture native task_complete text unchanged; local rollout paths stay outside evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def capture(root, rollout_dir):
    directory = root / 'artifacts/scope-review-20261110'
    path = directory / 'execution.json'
    execution = json.loads(path.read_bytes())
    for rollout in sorted(rollout_dir.glob('*.jsonl')):
        with rollout.open() as stream:
            first = json.loads(next(stream))
            agent = first.get('payload', {}).get('agent_path')
            task = next((t for t in execution['tasks'] if any(
                a['agent_name'] == agent for a in t['attempts'])), None)
            if task is None:
                continue
            completions = []
            for number, line in enumerate(stream, 2):
                row = json.loads(line)
                payload = row.get('payload', {})
                if row.get('type') == 'event_msg' and payload.get('type') == 'task_complete':
                    completions.append((number, payload))
        attempts = [a for a in task['attempts'] if a['agent_name'] == agent]
        for attempt, (number, payload) in zip(attempts, completions):
            raw = payload['last_agent_message'].encode('utf-8')
            output = directory / 'opinions' / f"{task['id']}.a{attempt['number']}.json"
            if 'raw_output' in attempt:
                if output.read_bytes() != raw:
                    raise ValueError('refusing to replace an original submission')
                continue
            if output.exists() and output.read_bytes() != raw:
                raise ValueError('output path already contains different bytes')
            output.write_bytes(raw)
            attempt['raw_output'] = {'path': output.relative_to(root).as_posix(),
                                     'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            attempt['capture'] = {'source': 'LOCAL_NATIVE_ROLLOUT_TASK_COMPLETE',
                                  'rollout_filename': rollout.name, 'line': number,
                                  'completed_at': payload.get('completed_at')}
            if len(raw) > task['output_limit_bytes']:
                attempt['status'] = 'REJECTED'
                attempt['error'] = 'OUTPUT_LIMIT_EXCEEDED'
                task['status'] = 'RETRY_REQUIRED'
            else:
                # verify.py must subsequently validate identity, citations and scope.
                json.loads(raw)
                attempt['status'] = 'ACCEPTED'
                task['status'] = 'RECEIVED'
            print(task['id'], attempt['number'], len(raw), attempt['status'])
    path.write_text(json.dumps(execution, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollout-dir', required=True, type=Path)
    args = parser.parse_args()
    capture(Path(__file__).resolve().parents[2], args.rollout_dir)
