"""Check measured search status and local decision recording in the workbench."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8772")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-decision-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#lexical-settings > summary").click()
        page.locator("#advanced-settings").evaluate("element => element.open = true")
        page.locator("#lexical-mode").select_option("off")
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator("#decision-status")).to_contain_text("no search benefit")
            expect(page.locator('#decision-mode option[value="jev"]')).to_be_disabled()
            page.locator("#decision-mode").select_option("stub")
            page.locator("#sentence").fill("john gives mary a book.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator("#decision-report")).to_be_visible()
            expect(page.locator("#decision-summary")).to_contain_text("local recording")
            assert not page.locator("#decision-summary").inner_text().startswith("0 choices")
            page.screenshot(path=str(args.output / f"{backend}-decisions.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print("Measured status, disabled unhelpful preferences and local recording passed in both modes.")


if __name__ == "__main__":
    main()
