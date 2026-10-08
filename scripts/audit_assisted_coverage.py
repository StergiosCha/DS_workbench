"""Run a fixed development probe with real providers; retain every failure."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from dylan.workbench_environment import load_environment

load_environment()
os.environ['DS_LEXICAL_PROVIDER'] = 'openrouter'
os.environ['DS_LEXICAL_MODEL'] = os.getenv('DS_ASSISTED_TEST_MODEL', 'deepseek/deepseek-v4.1-flash')
os.environ['DS_EPHEMERAL_MODELS'] = '1'
sample = json.loads(Path('data/coverage/open-text-probe.json').read_text())
def run(task):
    passage, backend = task
    payload = {'paragraph':passage['text'], 'grammar':f"2026-{passage['language']}-{backend}", 'lexical_mode':'assisted'}
    try:
        worker = subprocess.run([sys.executable, '-m', 'dylan.workbench_api'], input=json.dumps(payload), text=True, capture_output=True, timeout=58)
        result = json.loads(worker.stdout)
        row = {'id':passage['id'], 'backend':backend, 'language':passage['language'], 'coverage':result['coverage'], 'elapsed_ms':result['elapsed_ms'], 'sentences':[{'text':s['text'],'complete':s['complete'],'failure':s['failure'],'meaning':s.get('result',{}).get('words',[{}])[-1].get('normalized'),'attempts':s.get('result',{}).get('lexical',{}).get('attempts',[])} for s in result['sentences']]}
    except (ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        row = {'id':passage['id'], 'backend':backend, 'language':passage['language'], 'coverage':{'complete':0,'total':3,'all_complete':False}, 'error':str(exc)}
    print(json.dumps({k:v for k,v in row.items() if k!='sentences'},ensure_ascii=False),flush=True)
    return row
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(run, [(p,b) for p in sample['passages'] for b in ('classical','mltt')]))
summary={}
for language in ('english','smg'):
    for backend in ('classical','mltt'):
        selected=[r for r in rows if r['language']==language and r['backend']==backend]
        summary[f'{language}-{backend}']={'complete_passages':sum(r['coverage']['all_complete'] for r in selected),'passages':len(selected),'complete_sentences':sum(r['coverage']['complete'] for r in selected),'sentences':sum(r['coverage']['total'] for r in selected)}
Path('data/coverage/open-text-results.json').write_text(json.dumps({'sample':'open-text-probe.json','model':os.environ['DS_LEXICAL_MODEL'],'note':sample['selection'],'summary':summary,'results':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
