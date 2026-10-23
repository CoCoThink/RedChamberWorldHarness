"""Run the existing serial custody helper for the frozen v2 rereview only."""
from pathlib import Path
import runpy
import sys

sys.argv.extend([
    '--plan', 'data/agent_release/research-81-100-v2/review-campaign-v1.json',
    '--out', 'artifacts/agent_research/review-campaign-20261021/rereview-v2',
    '--raw-directory', '/home/guan/rcwh-review-outputs-20261023-v2',
])
runpy.run_path(str(Path(__file__).with_name('native-control.py')), run_name='__main__')
