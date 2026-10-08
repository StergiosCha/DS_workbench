"""Check the no-AI guide/examples and the user's GPT-4o plural paragraph flow."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dylan.workbench_environment import load_environment
from check_openrouter_browser import ready, connect, assert_private

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8790')
parser.add_argument('--output', type=Path, default=Path('/tmp/ds-plural-browser'))
args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
load_environment(); key = os.environ['OPENROUTER_API_KEY']
expect.set_options(timeout=60000)
text = 'A man opens the door and all people enter the room'

def check_tree_labels(page):
    page.evaluate('stop(); setIndex(frames().length - 1)')
    issues = page.evaluate('''() => {
        const issues = [], boxes = [];
        for (const group of document.querySelectorAll('.tree-node')) {
            const id = group.dataset.node, node = current().nodes.find(n => n.id === id);
            const label = group.querySelector('.node-type');
            const raw = node.type || node.required_type;
            // The legacy TTR serializer uses > for the displayed function arrow.
            const pretty = raw?.replaceAll('>', ' → ');
            const expected = raw ? `${node.type ? '' : '?'}Ty(${pretty})` : null;
            if (expected && label.textContent !== expected) issues.push(`Truncated type at ${id}: ${label.textContent}`);
            const box = group.querySelector('.node-box').getBBox(), text = label.getBBox();
            if (text.x < box.x || text.y < box.y || text.x + text.width > box.x + box.width || text.y + text.height > box.y + box.height) issues.push(`Type outside node ${id}`);
            const rect = group.querySelector('.node-box').getBoundingClientRect();
            for (const previous of boxes) {
                if (rect.left < previous.right - 1 && rect.right > previous.left + 1 && rect.top < previous.bottom - 1 && rect.bottom > previous.top + 1) issues.push(`Overlapping nodes ${id}/${previous.id}`);
            }
            boxes.push({id, left:rect.left, right:rect.right, top:rect.top, bottom:rect.bottom});
        }
        return issues;
    }''')
    assert not issues, issues

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1440, 'height':1050})
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    ready(page, args.url)
    expect(page.locator('.method-overview')).to_be_visible()
    expect(page.locator('#method-mode')).to_contain_text('No lexical model requests')
    page.locator('#method-help').click()
    expect(page.locator('#help-dialog')).to_contain_text('Without an LLM')
    expect(page.locator('#help-dialog')).to_contain_text('Your selected LLM')
    expect(page.locator('#help-dialog')).to_contain_text('Jev preferences')
    page.locator('#guide-semantics > summary').click()
    expect(page.locator('#guide-semantics')).to_contain_text('record types')
    page.locator('#help-close').click()
    for backend in ('mltt', 'classical'):
        page.locator('#system').select_option(backend)
        expect(page.locator('#parse-button')).to_be_enabled()
        for sentence in ('john relies on mary.', 'john gives a book to mary.',
                         'john walks in a park.', 'a man is in a park.',
                         'john thinks mary walks in a park.'):
            page.locator('#pp-help').click()
            expect(page.locator('#guide-pps')).to_contain_text('Modifier via LINK')
            with page.expect_request('**/api/parse/stream') as pending:
                page.locator(f'[data-guide-example="{sentence}"]').click()
            expect(page.locator('#parse-button')).to_be_enabled()
            assert 'authorization' not in pending.value.headers
            assert pending.value.post_data_json['lexical_mode'] == 'dictionary'
            assert pending.value.post_data_json['decision_mode'] == 'off'
            result = page.evaluate('state.result')
            assert result['complete'], (backend, sentence, result.get('failure'))
            expect(page.locator('#method-result-title')).to_have_text('No LLM used')
            check_tree_labels(page)
            if 'thinks' in sentence:
                assert len(result['readings']) == 2
            if sentence == 'john walks in a park.':
                assert any('L' in n['id'] and '+PP' in n['labels'] for n in result['words'][-1]['nodes'])
    page.locator('[data-input-mode="paragraph"]').click()
    page.locator('#paragraph').fill(text)
    with page.expect_request('**/api/parse/stream') as pending:
        page.locator('#parse-button').click()
    expect(page.locator('#parse-button')).to_be_enabled()
    assert 'authorization' not in pending.value.headers
    assert page.evaluate('state.paragraph.complete')
    expect(page.locator('#method-result-title')).to_have_text('No LLM used')
    connect(page, key)
    page.locator("#llm-enabled").check()
    expect(page.locator('#method-mode')).to_contain_text('your selected model')
    page.locator('#lexical-mode').select_option('jev')
    page.locator('#use-dictionaries').click()
    expect(page.locator('#lexical-mode')).to_have_value('dictionary')
    expect(page.locator('#decision-mode')).to_have_value('off')
    expect(page.locator('#openrouter-badge')).to_have_text('Connected')
    with page.expect_request('**/api/parse/stream') as pending:
        page.locator('#parse-button').click()
    expect(page.locator('#parse-button')).to_be_enabled()
    assert 'authorization' not in pending.value.headers
    assert page.evaluate('state.paragraph.complete')
    page.locator('#lexical-mode').select_option('assisted')
    page.locator('#openrouter-model').select_option('openai/gpt-4o')
    page.locator('[data-input-mode="paragraph"]').click()
    for backend in ('mltt', 'classical'):
        page.locator('#system').select_option(backend)
        page.locator('#grammar').select_option('2026-english-' + backend)
        page.locator('#paragraph').fill(text)
        with page.expect_request('**/api/parse/stream') as request:
            page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        assert request.value.headers['authorization'] == f'Bearer {key}'
        assert json.loads(request.value.post_data)['openrouter_model'] == 'openai/gpt-4o'
        result = page.evaluate('state.paragraph')
        assert result['complete'] and result['coverage']['complete'] == 1
        parsed = result['sentences'][0]['result']
        assert parsed['lexical']['attempts'] == []
        assert parsed['assistance']['verified'] and parsed['derivation']['actions']
        expect(page.locator('#paragraph-summary')).to_contain_text('1 / 1')
        expect(page.locator('#lexical-status')).to_contain_text('no model call')
        expect(page.locator('#method-result-title')).to_have_text('No model request made')
        expect(page.locator('#semantics')).to_contain_text('Π' if backend == 'mltt' else '∀')
        check_tree_labels(page)
        if backend == 'mltt':
            expect(page.locator('[data-node="011"] .node-type')).to_have_text('Ty(object → human → Prop)')
            assert page.locator('[data-node="0L00"] .node-type tspan').count() > 1
            page.locator('#tree-stage').screenshot(path=str(args.output / 'complete-types.png'))
        with page.expect_download() as download: page.locator('#export').click()
        raw = Path(download.value.path()).read_text(); assert key not in raw
        (args.output / f'{backend}.json').write_text(raw)
        if backend == 'mltt':
            with page.expect_download() as download: page.locator('#coq').click()
            target = args.output / 'Meaning.v'; target.write_text(Path(download.value.path()).read_text())
            if shutil.which('coqc'):
                checked = subprocess.run(['coqc', str(target)], text=True, capture_output=True, timeout=15)
                assert checked.returncode == 0, checked.stderr
        page.locator('#lexical-report').evaluate('el => el.open = false')
        page.screenshot(path=str(args.output / f'{backend}.png'), full_page=True)
        print(json.dumps({'backend':backend, 'complete':True, 'model_calls':0, 'meaning':parsed['words'][-1]['normalized']}, ensure_ascii=False), flush=True)
    assert_private(page, key)
    page.locator('[data-input-mode="sentence"]').click()
    page.locator('#grammar').select_option('2026-smg-classical')
    expect(page.locator('#parse-button')).to_be_enabled()
    page.locator('#use-dictionaries').click()
    expect(page.locator('#lexical-mode')).to_have_value('corpus')
    expect(page.locator('#method-mode')).to_contain_text('No lexical model requests')
    expect(page.locator('#use-dictionaries')).to_have_text('Use corpus lexicon only')
    page.locator('#system').select_option('ttr')
    expect(page.locator('#parse-button')).to_be_enabled()
    expect(page.locator('#use-dictionaries')).to_have_text('Use original lexicon only')
    expect(page.locator('#method-mode')).to_contain_text('original grammar lexicon')
    page.set_viewport_size({'width':390, 'height':844})
    check_tree_labels(page)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.locator('#pp-help').click()
    assert page.locator('#help-dialog').evaluate('el => el.scrollWidth <= el.clientWidth + 1')
    page.screenshot(path=str(args.output / 'guide-mobile.png'))
    assert not errors, errors
    browser.close()
