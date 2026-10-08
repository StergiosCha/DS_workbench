"""Live OpenRouter + real browser checks of the hosted assisted path."""
import argparse
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dylan.workbench_environment import load_environment
from check_openrouter_browser import ready, connect, assert_private

parser=argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8778')
parser.add_argument('--output', type=Path, default=Path('/tmp/ds-assisted-browser'))
parser.add_argument('--clitics', action='store_true', help='Check the reported ditransitive clitic sentence and live lexical assistance')
parser.add_argument('--pps', action='store_true', help='Check bilingual destinations, similes and real lexical assistance')
parser.add_argument('--model', default='deepseek/deepseek-v4.1-flash')
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
load_environment();key=os.environ['OPENROUTER_API_KEY']
expect.set_options(timeout=60000)

def pps(page):
    def parse(text, name, complete=True):
        page.locator('#sentence').fill(text)
        with page.expect_request('**/api/parse/stream') as pending:
            page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        result = page.evaluate('state.result')
        serialized = json.dumps(result, ensure_ascii=False)
        assert key not in serialized
        (args.output / f'{name}.json').write_text(serialized)
        assert result['complete'] == complete, (name, result['failure'], result.get('lexical', {}).get('notices'))
        if complete:
            assert 'manner_like(' in result['words'][-1]['normalized']
            assert any('L' in n['id'] for n in result['words'][-1]['nodes'])
        return result, pending.value

    for backend in ('classical', 'mltt'):
        page.locator('#system').select_option(backend)
        page.locator('#grammar').select_option('2026-smg-' + backend)
        page.locator('#use-dictionaries').click()
        result, request = parse('Ο Γιώργος μπήκε στην πίστα σαν άγριο παγώνι,', backend + '-greek-offline')
        assert 'authorization' not in request.headers
        assert 'enter_goal(giorgos,' in result['words'][-1]['normalized']
        assert len(result['tokens']) == 9
        expect(page.locator('#method-result-title')).to_have_text('No LLM used')
        page.evaluate('stop(); setIndex(frames().length - 1)')
        page.locator('#tree-stage').screenshot(path=str(args.output / f'{backend}-greek-tree.png'))
        parse('Ο Γιώργος μπήκε στον πίστα σαν άγριο παγώνι.', backend + '-gender', False)
        page.locator('#grammar').select_option('2026-english-' + backend)
        page.locator('#use-dictionaries').click()
        for i, sentence in enumerate(('George walks onto the stage like a wild peacock.', 'George entered the room like a wild peacock.')):
            _, request = parse(sentence, f'{backend}-english-{i}')
            assert 'authorization' not in request.headers
        parse('George walks like a wild.', backend + '-missing-noun', False)
        page.locator('#pp-help').click()
        page.locator('[data-guide-language="smg"]').last.click()
        expect(page.locator('#parse-button')).to_be_enabled()
        assert page.locator('#grammar').input_value() == '2026-smg-' + backend
        assert page.evaluate('state.result.complete')
    connect(page, key)
    page.locator("#llm-enabled").check()
    page.locator('#openrouter-model').select_option(args.model)
    for backend in ('classical', 'mltt'):
        page.locator('#system').select_option(backend)
        for language, sentence in (
            ('smg', 'Ο Γιώργος όρμησε στην αυλή σαν ήρεμο λιοντάρι.'),
            ('english', 'Mary sauntered into the courtyard like a graceful gazelle.'),
        ):
            page.locator('#grammar').select_option(f'2026-{language}-{backend}')
            result, request = parse(sentence, f'{backend}-{language}-live')
            assert request.headers['authorization'] == f'Bearer {key}'
            assert request.post_data_json['openrouter_model'] == args.model
            assert result['lexical']['attempts']
            assert any(e['source'] == 'model' for e in result['lexical']['entries'])
            if language == 'smg':
                assert any(e['template'] == 'verb-prepositional-se' for e in result['lexical']['entries'])
            expect(page.locator('#method-result-title')).to_contain_text('LLM assistance')
            print(json.dumps({'backend':backend, 'language':language, 'complete':True, 'model_calls':len(result['lexical']['attempts'])}), flush=True)
    with page.expect_download() as download:
        page.locator('#export').click()
    assert key not in Path(download.value.path()).read_text()
    assert_private(page, key)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')

def clitics(page):
    def parse(text, name, complete=True):
        page.locator('#sentence').fill(text)
        with page.expect_request('**/api/parse/stream') as request:
            page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        result = page.evaluate('state.result')
        serialized = json.dumps(result, ensure_ascii=False)
        assert key not in serialized
        (args.output / f'{name}.json').write_text(serialized)
        assert result['complete'] == complete, (name, result['failure'], result.get('lexical',{}).get('notices'))
        assert result['tokens'] == text.lower().replace('.', ' .').split()
        return result, request.value

    for backend in ('classical', 'mltt'):
        page.locator('#system').select_option(backend)
        page.locator('#grammar').select_option('2026-smg-' + backend)
        page.locator('#use-dictionaries').click()
        result, request = parse('Της το έδωσε', backend + '-corpus')
        assert 'authorization' not in request.headers
        assert result['words'][-1]['normalized'] == 'el_dino_863958_v3(pro, theme, her)'
        assert result['completion_search']['stop_reason'] == 'complete'
        expect(page.locator('#method-result-title')).to_have_text('No LLM used')
        page.evaluate('stop(); setIndex(frames().length - 1)')
        expect(page.locator('#semantics')).to_contain_text('(pro, theme, her)')
        page.locator('#tree-stage').screenshot(path=str(args.output / f'{backend}-tree.png'))
        parse('Το της έδωσε', backend + '-wrong-order', False)
        parse('Της με έδωσε', backend + '-pcc', False)
    connect(page, key)
    page.locator("#llm-enabled").check()
    page.locator('#openrouter-model').select_option(args.model)
    for backend in ('classical', 'mltt'):
        page.locator('#system').select_option(backend)
        page.locator('#grammar').select_option('2026-smg-' + backend)
        result, request = parse('Της το έδωσε', backend + '-assisted')
        assert request.headers['authorization'] == f'Bearer {key}'
        assert request.post_data_json['openrouter_model'] == args.model
        assert result['lexical']['attempts'] == []
        expect(page.locator('#method-result-title')).to_have_text('No model request made')
        result, _ = parse('Της το χάρισε', backend + '-model')
        assert result['words'][-1]['normalized'].endswith('(pro, theme, her)')
        assert any(e['source'] == 'model' and e['template'] == 'verb-ditransitive' for e in result['lexical']['entries'])
        expect(page.locator('#method-result-title')).to_contain_text('LLM assistance')
        with page.expect_download() as download:
            page.locator('#export').click()
        assert key not in Path(download.value.path()).read_text()
        print(json.dumps({'backend': backend, 'reported_sentence_complete': True, 'reported_sentence_model_calls': 0, 'novel_verb_model_calls': len(result['lexical']['attempts'])}), flush=True)
    assert_private(page, key)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')

with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    ready(page,args.url)
    if args.pps:
        pps(page)
        assert not errors, errors
        browser.close()
        raise SystemExit(0)
    if args.clitics:
        clitics(page)
        assert not errors, errors
        browser.close()
        raise SystemExit(0)
    connect(page,key)
    page.locator("#llm-enabled").check()
    expect(page.locator('#lexical-mode')).to_have_value('assisted')
    page.locator('#openrouter-model').select_option(args.model)
    for backend in ('mltt','classical'):
        page.locator('#system').select_option(backend)
        page.locator('#grammar').select_option('2026-english-'+backend)
        page.locator('#sentence').fill('A man is here.')
        with page.expect_request('**/api/parse/stream') as request:
            page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        assert request.value.headers['authorization']==f'Bearer {key}'
        assert page.evaluate('state.result.complete')
        expect(page.locator('#semantics')).to_contain_text('here')
        assert page.evaluate('state.mode')=='words'
        page.locator('#grammar').select_option('2026-smg-'+backend)
        expect(page.locator('#lexical-mode')).to_have_value('assisted')
        page.locator('[data-input-mode="paragraph"]').click()
        page.locator('#paragraph').fill('Η ερευνήτρια εξετάζει το δείγμα. Η Μαρία είναι στο εργαστήριο και ο γιατρός είναι εδώ.')
        page.locator('#parse-button').click();expect(page.locator('#parse-button')).to_be_enabled()
        result=page.evaluate('state.paragraph')
        # Retain actual failures as well as successes to diagnose provider variation.
        diagnostic=json.dumps(result,ensure_ascii=False);assert key not in diagnostic
        (args.output/f'{backend}-result.json').write_text(diagnostic)
        if result['coverage']['complete'] != 2:
            print(json.dumps({'backend':backend,'failures':[{'status':s['status'],'failure':s.get('failure'),'notices':s.get('result',{}).get('lexical',{}).get('notices',[])} for s in result['sentences']]},ensure_ascii=False),flush=True)
        assert result['coverage']['complete']==2, result['coverage']
        assert any(e['source']=='model' for s in result['sentences'] for e in s['result']['lexical']['entries'])
        expect(page.locator('#method-result-title')).to_contain_text('LLM assistance')
        expect(page.locator('#method-result-detail')).to_contain_text('shared across this paragraph')
        expect(page.locator('#paragraph-summary')).to_contain_text('2 / 2')
        with page.expect_download() as download:page.locator('#export').click()
        raw=Path(download.value.path()).read_text();assert key not in raw
        (args.output/f'{backend}.json').write_text(raw)
        page.locator('#paragraph-results').screenshot(path=str(args.output/f'{backend}.png'))
        print(json.dumps({'backend':backend,'complete':result['coverage']['complete'],'total':result['coverage']['total']}),flush=True)
        page.locator('[data-input-mode="sentence"]').click()
    assert_private(page,key)
    page.set_viewport_size({'width':390,'height':844});page.locator('[data-input-mode="paragraph"]').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert not errors,errors
    browser.close()
