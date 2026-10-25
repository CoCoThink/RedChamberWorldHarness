"""Record a real committed clone reproduction, without claiming final CI."""
from pathlib import Path
import json
import subprocess
from rcwh.generation.records import binding

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
    payload = json.loads((O / 'payload-commit.json').read_bytes())
    assert head == payload['commit']
    report = json.loads((O / 'committed-clone-verification.json').read_bytes())
    assert report['status'] == report['release_status'] == report['cloned_build']['status'] == report['cloned_build']['release_status'] == 'PASS'
    reproduction = report['cloned_build']['committed_release']
    assert reproduction['status'] == 'PASS' and reproduction['book'] == 'EXACT_BYTES'
    assert reproduction['manifest'] == 'EXACT_EXCEPT_NAMED_RUNTIME_OBSERVATIONS'
    index = json.loads((O / 'human-final-release-index.json').read_bytes())
    for key in ('request', 'manifest', 'book'):
        assert index[key] == binding(R, index[key]['path'])
    manifest = json.loads((R / index['manifest']['path']).read_bytes())
    assert report['request_sha256'] == manifest['request_sha256']
    assert report['cloned_build']['text'] == manifest['output']['text']
    result = {'status': 'PASS', 'scope': 'ACTUAL_COMMITTED_PAYLOAD_CLONE_REPRODUCTION',
              'tested_commit': head,
              'verification': binding(R, (O / 'committed-clone-verification.json').relative_to(R).as_posix()),
              'verification_tool': binding(R, 'tools/verify_agent_release.py'),
              'clone_build_allow_pending_argument': True, 'clone_release_status': 'PASS',
              'committed_book': reproduction['book'], 'manifest_comparison': reproduction['manifest'],
              'runtime_observation_paths': reproduction['runtime_observation_paths'],
              **{k: index[k] for k in ('request', 'manifest', 'book')},
              'final_head_ci': 'MUST_BE_VERIFIED_AFTER_FINAL_PUSH_NOT_CLAIMED_HERE',
              'authority_effect': 'NONE', 'P9_credit': False}
    target = O / 'committed-clone-custody.json'
    assert not target.exists()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
