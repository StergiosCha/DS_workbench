"""Live BYOK-equivalent bilingual checks. Never log credentials."""
import json
import os
from pathlib import Path
from dylan.workbench_environment import load_environment
from dylan.workbench_api import parse_request
from dylan.action.meta.element import reset_all_meta_bindings

load_environment()
os.environ['DS_LEXICAL_PROVIDER'] = 'openrouter'
os.environ['DS_LEXICAL_MODEL'] = os.getenv('DS_ASSISTED_TEST_MODEL', 'deepseek/deepseek-v4.1-flash')
os.environ['DS_EPHEMERAL_MODELS'] = '1'
cases = [
 ('english', 'The researcher examines a sample. She is in the laboratory and the technician is here. A student reads the report and writes a letter.'),
 ('smg', 'Η ερευνήτρια εξετάζει το δείγμα. Η Μαρία είναι στο εργαστήριο και ο γιατρός είναι εδώ. Ο φοιτητής διαβάζει την έκθεση.'),
]
rows = []
for language, paragraph in cases:
 for backend in ('classical', 'mltt'):
  reset_all_meta_bindings()
  result = parse_request({'paragraph': paragraph, 'grammar': f'2026-{language}-{backend}', 'lexical_mode': 'assisted'})
  rows.append(result)
  print(json.dumps({'language':language, 'backend':backend, 'coverage':result['coverage'], 'sentences':[{'text':s['text'],'complete':s['complete'],'failure':s['failure'],'meaning':s.get('result',{}).get('words',[{}])[-1].get('normalized'),'attempts':s.get('result',{}).get('lexical',{}).get('attempts')} for s in result['sentences']]},ensure_ascii=False),flush=True)
Path('/tmp/ds-assisted-live.json').write_text(json.dumps(rows,ensure_ascii=False))
