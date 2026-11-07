"""Check the source-based laughter beta through the actual browser controls."""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8795")
    args = parser.parse_args()
    output = Path("/tmp/ds-laughter-beta-browser")
    output.mkdir(exist_ok=True)
    expect.set_options(timeout=60000)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#try-laughter-beta").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#laughter-beta-notice")).to_be_visible()
        expect(page.locator("#system")).to_have_value("ttr")
        expect(page.locator("#grammar")).to_have_value("2026-english-laughter-beta-ttr")
        assert page.evaluate("state.inputMode") == "dialogue"
        assert page.evaluate("state.result.complete")
        expect(page.locator("#semantics")).to_contain_text("laughable(e0)")
        for control in ("llm-enabled", "jev-enabled", "experimental-enabled"):
            expect(page.locator("#" + control)).not_to_be_checked()
            expect(page.locator("#" + control)).to_be_disabled()
        expect(page.locator('[data-input-mode="paragraph"]')).to_be_disabled()
        page.locator('[data-dialogue-example="laughter-mid-sentence"]').click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.result.complete")
        expect(page.locator("#semantics")).to_contain_text("laughable(x0)")
        page.locator('[data-input-mode="sentence"]').click()
        page.locator("#sentence").fill("John sees a telescope [laugh].")
        page.locator("#parse-options").evaluate("e => e.open = true")
        page.locator("#n-best").select_option("3")
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.result.readings.length") == 2
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#laughter-beta-notice summary").click()
        expect(page.locator("#laughter-beta-source")).to_contain_text("Howes")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#laughter-beta-notice").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "mobile.png"))
        page.locator("#sentence").fill("[laugh] John walks.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert not page.evaluate("state.result.complete")
        page.locator("#system").select_option("mltt")
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#laughter-beta-notice")).to_be_hidden()
        expect(page.locator('[data-input-mode="paragraph"]')).to_be_enabled()
        assert page.evaluate("state.result.complete")
        assert not errors, errors
        browser.close()
    print("Laughter beta: actual selection, dialogue, two readings, AI off, mobile, failure and exit passed.")


if __name__ == "__main__":
    main()
