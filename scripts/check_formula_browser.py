"""Check formula expansion against real parser results, without any model calls."""
import argparse
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8791')
parser.add_argument('--output', type=Path, default=Path('/tmp/ds-formula-browser'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=60000)


def check_geometry(page):
    errors = page.evaluate('''() => {
        const errors = [], boxes = [];
        for (const group of document.querySelectorAll('.tree-node')) {
            const id = group.dataset.node, box = group.querySelector('.node-box').getBBox();
            for (const label of group.querySelectorAll('.node-type, .node-formula, .formula-toggle')) {
                const b = label.getBBox();
                if (b.x < box.x || b.y < box.y || b.x + b.width > box.x + box.width || b.y + b.height > box.y + box.height) errors.push(`Overflow at ${id}: ${label.getAttribute('class')}`);
            }
            const rect = group.querySelector('.node-box').getBoundingClientRect();
            for (const old of boxes) if (rect.left < old.right - 1 && rect.right > old.left + 1 && rect.top < old.bottom - 1 && rect.bottom > old.top + 1) errors.push(`Overlapping boxes ${id}/${old.id}`);
            boxes.push({id, left:rect.left, right:rect.right, top:rect.top, bottom:rect.bottom});
        }
        return errors;
    }''')
    assert not errors, errors


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1440,'height':1050})
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if '/api/parse' in request.url else None)
    page.goto(args.url)
    expect(page.locator('#parse-button')).to_be_enabled()
    for backend in ('mltt', 'classical', 'ttr'):
        page.locator('#system').select_option(backend)
        expect(page.locator('#parse-button')).to_be_enabled()
        if backend != 'ttr':
            page.locator('#grammar').select_option('2026-smg-' + backend)
            expect(page.locator('#parse-button')).to_be_enabled()
            page.locator('#sentence').fill('της τον έδωσε.')
            page.locator('#parse-button').click()
            expect(page.locator('#parse-button')).to_be_enabled()
        else:
            page.locator('#sentence').fill('a man knows you.')
            page.locator('#parse-button').click()
            expect(page.locator('#parse-button')).to_be_enabled()
        page.evaluate('stop(); setIndex(frames().length - 1)')
        assert page.evaluate('state.result.complete')
        if backend == 'ttr':
            result = page.evaluate('state.result')
            meaning = result['words'][-1]['semantics']
            subject = re.search(r'subj\([^,]+, (\w+)\)', meaning).group(1)
            obj = re.search(r'obj\([^,]+, (\w+)\)', meaning).group(1)
            assert subject != obj, meaning
            assert f'man({subject})' in meaning and f'{obj}==you : e' in meaning
            displayed = page.locator('#semantics').inner_text()
            assert re.sub(r'[\s|]+', '', displayed) == re.sub(r'[\s|]+', '', meaning)
            expect(page.locator('#method-result-title')).to_have_text('No LLM used')
            with page.expect_download() as download:
                page.locator('#export').click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported['words'][-1]['semantics'] == meaning
            (args.output / 'ttr-referents.json').write_text(json.dumps(result, indent=2))
        node = page.evaluate('current().nodes.filter(n => n.formula && n.formula.startsWith("λ") && n.formula.length > 25).sort((a,b) => b.formula.length - a.formula.length)[0] || current().nodes.find(n => n.formula && n.formula.length > 25)')
        assert node, backend
        selector = f'[data-formula-toggle="{node["id"]}"]'
        formula = page.locator(f'[data-node="{node["id"]}"] .node-formula')
        button = page.locator(selector)
        before = page.evaluate('JSON.stringify(state.result)')
        count = len(requests)
        assert formula.text_content().endswith('…')
        button.click()
        expect(button).to_have_attribute('aria-expanded', 'true')
        expect(formula).to_have_text(node['formula'])
        assert page.evaluate('state.timer') is None
        assert page.locator(selector).evaluate('el => el === document.activeElement')
        assert page.evaluate('JSON.stringify(state.result)') == before
        assert len(requests) == count
        check_geometry(page)
        page.locator('#tree-stage').screenshot(path=str(args.output / f'{backend}-expanded.png'))
        button.press('Enter')
        expect(button).to_have_attribute('aria-expanded', 'false')
        assert formula.text_content().endswith('…')
        button.press('Space')
        expect(button).to_have_attribute('aria-expanded', 'true')
        expect(formula).to_have_text(node['formula'])
        # Several independently expanded nodes must also keep their contents.
        while page.locator('.formula-toggle[aria-expanded="false"]').count():
            page.locator('.formula-toggle[aria-expanded="false"]').first.click()
        check_geometry(page)
        if backend == 'mltt':
            page.set_viewport_size({'width':390,'height':844})
            check_geometry(page)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.screenshot(path=str(args.output / 'mobile-expanded.png'))
            button.click()
            expect(button).to_have_attribute('aria-expanded', 'false')
            page.set_viewport_size({'width':1440,'height':1050})
        page.locator('#parse-button').click()
        expect(page.locator('#parse-button')).to_be_enabled()
        page.evaluate('stop(); setIndex(frames().length - 1)')
        expect(page.locator('.formula-toggle[aria-expanded="true"]')).to_have_count(0)
        print(f'{backend}: exact full formula, collapse, keyboard, layout and no parser requests passed', flush=True)
    assert not errors, errors
    browser.close()
