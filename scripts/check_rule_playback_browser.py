"""Check visible computational steps using real DS; no model calls or real keys."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from check_openrouter_browser import connect, assert_private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8808")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-rule-playback"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=45000)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()

        def inspect(label):
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator('[data-mode="actions"]')).to_have_attribute("aria-pressed", "true")
            if page.locator("#play").get_attribute("aria-label") == "Pause derivation":
                page.locator("#play").click()
            page.locator("#trace-tab").click()
            computational = page.locator("#action-list button").filter(has=page.locator(".rule-kind.computational"))
            assert computational.count() > 0
            computational.first.click()
            expect(page.locator("#operation-kind")).to_have_text("Computational rule")
            expect(page.locator("#operation-detail")).to_be_visible()
            assert page.locator("#operation-change").inner_text()
            assert page.locator("#tree .tree-node").count() > 1
            assert "word" in page.locator("#rule-progress").inner_text()
            page.locator("#action-list button").filter(has=page.locator(".rule-kind.lexical")).first.click()
            expect(page.locator("#operation-kind")).to_have_text("Lexical rule")
            page.locator("#next").click()
            current = page.evaluate("current()")
            assert current["nodes"]
            computational.first.click()
            page.locator(".tree-column").screenshot(path=str(args.output / f"{label}.png"))
            checks.append({"case": label, "computational_steps": computational.count(), "mode": page.evaluate("state.mode")})

        inspect("plain")
        page.locator('[data-mode="operations"]').click()
        page.locator("#first").click()
        page.locator("#next").click()
        expect(page.locator("#operation-kind")).to_have_text("Computational rule")
        expect(page.locator("#operation-program")).to_contain_text("IF")

        key = "fixture-rule-playback"
        page.route("**/api/openrouter/connect", lambda route: route.fulfill(json={
            "connected": True, "models": [{"id": "fixture/rules", "name": "Fixture", "input_per_million": 0, "output_per_million": 0}],
            "default_model": "fixture/rules", "jev": {"available": False},
        }))
        page.locator("#model-settings-button").click()
        connect(page, key)
        page.locator("#llm-enabled").check()
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#sentence").fill("a man walks.")
            page.locator("#parse-button").click()
            inspect(f"assisted-{backend}")
            assert page.evaluate("state.result.lexical.attempts.length") == 0
            expect(page.locator('[data-mode="operations"]')).to_be_disabled()
            expect(page.locator("#rule-progress")).to_contain_text("DS attempt 1")

        page.locator("#use-dictionaries").click()
        page.locator('[data-input-mode="paragraph"]').click()
        page.locator("#paragraph").fill("John walks. He knows Mary. She walks.")
        page.locator("#parse-button").click()
        inspect("paragraph-english")
        assert page.evaluate("state.paragraph.coverage.complete") == 3
        page.locator('[data-sentence-index="1"]').click()
        inspect("paragraph-second")
        expect(page.locator("#rule-progress")).to_contain_text("Sentence 2")
        page.locator("#grammar").select_option("2026-smg-classical")
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#paragraph").fill("της τον έδωσε. με αγαπά.")
        page.locator("#parse-button").click()
        inspect("paragraph-greek")
        assert page.evaluate("state.paragraph.coverage.complete") == 2
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        expect(page.locator("#operation-kind")).to_be_visible()
        page.locator(".tree-column").screenshot(path=str(args.output / "mobile.png"))
        assert_private(page, key)
        assert not errors, errors
        browser.close()
    (args.output / "checks.json").write_text(json.dumps(checks, indent=2))
    print(f"Passed {len(checks)} rule-playback cases, operation inspection and mobile layout.")


if __name__ == "__main__":
    main()
