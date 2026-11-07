"""Exercise beta selection, source explanation, replay, limits and exit."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8794")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-conditional-beta-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=60000)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#try-conditional-beta").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#conditional-beta-notice")).to_be_visible()
        expect(page.locator("#system")).to_have_value("classical")
        expect(page.locator("#grammar")).to_have_value("2026-english-conditionals-beta-classical")
        for control in ("llm-enabled", "jev-enabled", "experimental-enabled"):
            expect(page.locator("#" + control)).not_to_be_checked()
            expect(page.locator("#" + control)).to_be_disabled()
        for mode in ("dialogue", "paragraph"):
            expect(page.locator(f'[data-input-mode="{mode}"]')).to_be_disabled()
        result = page.evaluate("state.result")
        assert result["complete"], result.get("failure")
        assert result["words"][-1]["conditional_beta"] == "fixed-situation-v1"
        page.locator("#conditional-beta-notice summary").click()
        expect(page.locator("#conditional-beta-source")).to_contain_text("Gregoromichelaki")
        page.evaluate("stop(); setIndex(frames().length - 1)")
        expect(page.locator("#semantics")).to_contain_text("τ")
        (args.output / "initial.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        page.locator("#sentence").fill("Mary laughs if John cries.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.result.complete")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#conditional-beta-notice").scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "beta-mobile.png"))
        page.locator("#sentence").fill("If John cries, Mary.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert not page.evaluate("state.result.complete")
        page.locator("#system").select_option("mltt")
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#conditional-beta-notice")).to_be_hidden()
        expect(page.locator('[data-input-mode="dialogue"]')).to_be_enabled()
        assert page.evaluate("state.result.complete")
        assert not errors, errors
        browser.close()
    print("Conditional beta: selection, both orders, replay, mobile, incomplete input and return to ordinary grammar passed.")


if __name__ == "__main__":
    main()
