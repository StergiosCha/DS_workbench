"""Opt-in live BYOK checks: real UI switches, model calls and DS outcomes.

Reads an existing project environment; never saves keys, headers or browser traces.
Each case is tested with AI off, analysis LLM on, and analysis LLM + Jev on.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from dylan.workbench_environment import load_environment
from check_openrouter_browser import connect, assert_private


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', default='http://127.0.0.1:8812')
    ap.add_argument('--env-file', type=Path, required=True)
    ap.add_argument('--model', default='deepseek/deepseek-v4.1-flash')
    ap.add_argument('--output', type=Path, default=Path('/tmp/ds-vocabulary-switches.json'))
    ap.add_argument('--live', action='store_true', help='Required: allows bounded billed model requests')
    ap.add_argument('--experimental', action='store_true', help='Enable experimental grammar proposals whenever the LLM is on')
    ap.add_argument('--backend', action='append', choices=['mltt','classical'])
    ap.add_argument('--llm-only', action='store_true', help='Only test LLM on / Jev off')
    ap.add_argument('--sentence', action='append', help='Test these exact sentences instead of the two reported failures')
    args = ap.parse_args()
    if not args.live:
        ap.error('--live is required to exercise an actual provider')
    load_environment(args.env_file)
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('An OpenRouter key is required in the supplied project environment.')
    cases = args.sentence or ['the person entered the room randomly', 'A person entered the room with glasses']
    rows, errors, requests = [], [], []
    expect.set_options(timeout=65000)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        def request_seen(request):
            if '/api/parse/stream' in request.url:
                body = request.post_data_json
                requests.append({'mode':body.get('lexical_mode'), 'llm_allowed':body.get('allow_model_fallback'),
                                 'has_auth':'authorization' in request.headers, 'experimental':body.get('experimental_rules',False)})
        page.on('request', request_seen)
        page.goto(args.url)
        expect(page.locator('#parse-button')).to_be_enabled()
        page.locator('#model-settings-button').click()
        connect(page, key)
        page.locator('#openrouter-model').select_option(args.model)
        page.locator('#models-close').click()
        for backend in (args.backend or ('mltt', 'classical')):
            if page.locator('#system').input_value() != backend:
                page.locator('#system').select_option(backend)
                expect(page.locator('#parse-button')).to_be_enabled()
            for sentence in cases:
                for llm, jev in (((True,False),) if args.llm_only else ((False,False), (True,False), (True,True))):
                    before = len(requests)
                    page.locator('#llm-enabled').set_checked(llm)
                    page.locator('#jev-enabled').set_checked(jev)
                    page.locator('#experimental-enabled').set_checked(args.experimental and llm)
                    assert len(requests) == before, 'Toggling must not make a parse/model request'
                    page.locator('#sentence').fill(sentence)
                    page.locator('#parse-button').click()
                    expect(page.locator('#parse-button')).to_be_enabled()
                    result = page.evaluate('state.result')
                    lexical = result['lexical']
                    assert requests[-1]['llm_allowed'] is llm
                    assert requests[-1]['experimental'] is (args.experimental and llm)
                    assert requests[-1]['has_auth'] is (llm or jev)
                    assert requests[-1]['mode'] == ('jev' if jev else 'assisted' if llm else 'dictionary')
                    usage = page.locator('#method-usage').inner_text()
                    entry = {'sentence':sentence, 'backend':backend, 'llm_on':llm, 'jev_on':jev,
                             'payload':requests[-1], 'complete':result['complete'], 'failure':result.get('failure'),
                             'meaning':result['words'][-1].get('normalized'), 'usage':usage,
                             'model_requests':len(result['experimental_grammar']['attempts']) if 'experimental_grammar' in result else len(lexical.get('attempts',[])) if lexical['mode']=='assisted' else lexical.get('model_requests',0),
                             'attempts':lexical.get('attempts',[]), 'notices':lexical.get('notices',[]),
                             'entries':[{k:e.get(k) for k in ('surface','lemma','template','symbol','domains','source','model')} for e in lexical.get('entries',[])],
                             'jev_requests':lexical.get('selection',{}).get('live_calls',0)}
                    if 'experimental_grammar' in result:
                        entry['experimental_grammar'] = result['experimental_grammar']
                        expect(page.locator('#experimental-report')).to_be_visible()
                        if result['experimental_grammar']['used']:
                            expect(page.locator('#meaning-title')).to_contain_text('experimental grammar')
                    rows.append(entry)
                    args.output.write_text(json.dumps({'model':args.model,'cases':rows,'browser_errors':errors},indent=2,ensure_ascii=False)+'\n')
                    print(json.dumps({k:entry[k] for k in ('sentence','backend','llm_on','jev_on','complete','model_requests','jev_requests','usage')},ensure_ascii=False),flush=True)
                    if not llm:
                        assert entry['model_requests'] == 0
            assert_private(page,key)
            page.locator('#llm-enabled').uncheck()
            page.locator('#jev-enabled').uncheck()
        assert not errors, errors
        browser.close()
    print(f'{len(rows)} real browser parses recorded in {args.output}; outcomes are recorded, not forced to success.')

if __name__ == '__main__':
    main()
