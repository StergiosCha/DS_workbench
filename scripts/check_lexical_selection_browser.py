"""Exercise lexical preferences, cached parsing and pointer playback in both modes."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8772")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-lexical-selection-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(30000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#lexical-settings > summary").click()
        page.locator("#advanced-settings").evaluate("element => element.open = true")
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator('#lexical-mode option[value="jev"]')).to_be_enabled()
            expect(page.locator('#decision-mode option[value="jev"]')).to_be_disabled()
            page.locator("#lexical-mode").select_option("jev")
            expect(page.locator("#lexical-selection-description")).to_be_visible()
            page.locator("#n-best").select_option("3")
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#sentence").fill("john lends mary a book.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["sentence"] == "john lends mary a book." and result["complete"], result.get("failure")
            expect(page.locator("#lexical-selection")).to_be_visible()
            expect(page.locator("#lexical-selection-used")).to_contain_text("lends → lend_")
            expect(page.locator("#lexical-selection-decisions")).to_contain_text("cached")
            page.locator("#lexical-selection-decisions details").first.locator("summary").click()
            expect(page.locator("#lexical-selection-decisions")).to_contain_text("Prefix: john")
            expect(page.locator("#lexical-selection-decisions")).to_contain_text("Sense preference:")
            pause = page.get_by_role("button", name="Pause derivation", exact=True)
            if pause.count():
                pause.click()
            frames = result["operations"]
            step = next(i for i, frame in enumerate(frames) if frame["kind"] == "operation" and frame["label"].startswith("go("))
            page.locator("#timeline").evaluate("(node, value) => { node.value = value; node.dispatchEvent(new Event('input')); }", step)
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == frames[step]["pointer"]
            expect(page.locator("#operation-code")).to_contain_text("go(")
            page.screenshot(path=str(args.output / f"{backend}-lexical-pointer.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.set_viewport_size({"width": 1440, "height": 1100})
        assert not errors, errors
        browser.close()
    print("Jev vocabulary control, preferred/used distinction, cache and pointer playback passed in both modes.")


if __name__ == "__main__":
    main()
