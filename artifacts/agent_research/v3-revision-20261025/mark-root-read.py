"""Record declared reading in a later tool call after root inspected the full response.

Never batch an opinion display and this command in the same exec cell. These
declarations are not machine proof of reading. Retractions remain in the log.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
O=Path(__file__).resolve().parent
seen={json.loads(s)['registration'] for s in (O/'coordinator-notes-read.jsonl').read_text().splitlines()}
with (O/'coordinator-notes-read.jsonl').open('a') as f:
 for arg in sys.argv[1:]:
  n=int(arg);assert n not in seen,'already declared read'
  e=json.loads((O/f'registration-{n:03d}.json').read_bytes())
  f.write(json.dumps({'observed_utc':datetime.now(timezone.utc).isoformat(),'registration':n,'job':e['job_id'],'record':e['record'],'scope':'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR','basis':'DECLARED_ACTUAL_TOOL_READING_NOT_PROVEN','peer_credit':False,'authority_effect':'NONE'},ensure_ascii=False)+'\n');seen.add(n)
