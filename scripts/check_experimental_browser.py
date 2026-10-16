"""Check experimental controls and inspectable results, without billed calls.

The supplied fixture must be a real DS result generated with a fixture provider;
this checks browser wiring/display, not live model capability.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from check_openrouter_browser import connect, assert_private


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', default='http://127.0.0.1:8812')
    ap.add_argument('--fixture', type=Path, required=True)
    ap.add_argument('--output', type=Path, default=Path('/tmp/ds-experimental-browser'))
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = json.loads(args.fixture.read_text())
    assert result['complete'] and result['experimental_grammar']['used']
    expect.set_options(timeout=45000)
    errors, requests, checks = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator('#parse-button')).to_be_enabled()
        exp = page.locator('#experimental-enabled')
        expect(exp).not_to_be_checked()
        expect(exp).to_be_disabled()
        page.route('**/api/openrouter/connect', lambda route: route.fulfill(json={
            'connected':True, 'models':[{'id':'fixture/grammar','name':'Fixture grammar','input_per_million':0,'output_per_million':0}],
            'default_model':'fixture/grammar', 'jev':{'available':True,'model':'typesafe/jev-1.13-20260917','name':'Jev 1.13'}}))
        page.locator('#model-settings-button').click()
        key = 'fixture-experimental-secret'
        connect(page, key)
        page.locator('#models-close').click()
        expect(exp).to_be_enabled()
        expect(exp).not_to_be_checked()
        expect(page.locator('#llm-enabled')).not_to_be_checked()
        def respond(route):
            body = route.request.post_data_json
            requests.append(body)
            if not body['experimental_rules']:
                assert body['allow_model_fallback'] is False
                assert 'authorization' not in route.request.headers
                route.continue_()
                return
            assert body['experimental_rules'] and body['allow_model_fallback']
            assert key not in route.request.post_data
            route.fulfill(content_type='application/x-ndjson', body=json.dumps({'event':'result','result':result})+'\n')
        page.route('**/api/parse/stream', respond)
        exp.check()
        expect(page.locator('#llm-enabled')).to_be_checked()
        expect(page.locator('#n-best')).to_be_disabled()
        page.locator('#jev-enabled').check()
        expect(page.locator('#llm-help')).to_contain_text('including when Jev is on')
        assert not requests
        page.locator('#sentence').fill(result['sentence'])
        page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        assert requests[-1]['lexical_mode']=='jev'
        expect(page.locator('#experimental-report')).to_be_visible()
        expect(page.locator('#experimental-title')).to_have_text('Complete under experimental grammar')
        expect(page.locator('#meaning-title')).to_contain_text('experimental grammar')
        expect(page.locator('#diagnosis-title')).to_have_text('Complete under experimental grammar')
        page.locator('#experimental-attempts > details > summary').first.click()
        expect(page.locator('#experimental-attempts')).to_contain_text('selected by DS')
        expect(page.locator('#experimental-attempts pre').first).to_be_visible()
        page.locator('#experimental-report').screenshot(path=str(args.output/'rules.png'))
        with page.expect_download() as download:
            page.locator('#export').click()
        exported = Path(download.value.path()).read_text()
        assert key not in exported
        assert json.loads(exported)['experimental_grammar']['rules']==result['experimental_grammar']['rules']
        checks.append('Separate opt-in, LLM enablement, Jev combination, experimental completion label, programs and JSON export')
        page.locator('#focus-derivation').click()
        expect(page.locator('#experimental-report')).to_be_visible()
        expect(page.locator('#focus-usage')).to_contain_text('Analysis LLM')
        page.keyboard.press('Escape')
        expect(page.locator('.composer')).to_be_visible()
        assert len(requests)==1
        checks.append('Focus preserves experimental provenance without a new request')
        for width,height,label in [(1440,1000,'desktop'),(390,844,'mobile')]:
            page.set_viewport_size({'width':width,'height':height})
            page.locator('#ai-controls').scroll_into_view_if_needed()
            expect(exp).to_be_visible()
            box=exp.bounding_box()
            assert box['width']>=18 and box['height']>=18
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.locator('#ai-controls').screenshot(path=str(args.output/f'{label}-controls.png'))
        checks.append('Visible desktop/mobile controls without horizontal overflow')
        page.locator('#use-dictionaries').click()
        expect(exp).not_to_be_checked()
        expect(page.locator('#llm-enabled')).not_to_be_checked()
        expect(page.locator('#jev-enabled')).not_to_be_checked()
        exp.check()
        page.locator('#llm-enabled').uncheck()
        expect(exp).not_to_be_checked()
        exp.check()
        page.locator('[data-input-mode="paragraph"]').click()
        expect(exp).not_to_be_checked()
        expect(exp).to_be_disabled()
        page.locator('[data-input-mode="sentence"]').click()
        expect(exp).to_be_enabled()
        exp.check()
        page.locator('#system').select_option('ttr')
        expect(page.locator('#parse-button')).to_be_enabled()
        expect(exp).not_to_be_checked()
        expect(exp).to_be_disabled()
        assert len(requests)==2  # Selecting another semantic system runs its built-in example.
        assert_private(page,key)
        checks.append('All-off and LLM-off disable proposals; paragraphs and TTR disable the control; toggles make no request')
        assert not errors, errors
        browser.close()
    (args.output/'checks.json').write_text(json.dumps({'checks':checks,'errors':errors},indent=2)+'\n')
    print(f'{len(checks)} experimental browser checks passed; fixture provider, real DS result.')


if __name__=='__main__':
    main()
