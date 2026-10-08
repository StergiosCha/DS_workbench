"""Verify real PP trees and cached Jev revision playback through the local server."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8772")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-pp-revision-browser"))
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
            page.locator("#lexical-mode").select_option("off")
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#sentence").fill("john reads a book in a library.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"] and result["sentence"] == "john reads a book in a library."
            pause = page.get_by_role("button", name="Pause derivation", exact=True)
            if pause.count():
                pause.click()
            step = next(i for i, f in enumerate(result["operations"]) if f["pointer"] == "01L10")
            page.locator("#timeline").evaluate("(node, value) => { node.value = value; node.dispatchEvent(new Event('input')); }", step)
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == "01L10"
            assert page.locator(".tree-edge.link").count() == 1
            page.screenshot(path=str(args.output / f"{backend}-pp-pointer.png"), full_page=True)
            page.get_by_role("tab", name="Action trace").click()
            page.locator("#action-list button").last.click()
            expect(page.locator("#semantics")).to_have_text(result["words"][-1]["semantics"])
            if backend == "classical":
                assert page.locator('[data-node="01L1000"]').count() == 1
                assert page.locator('[data-node="01L1001"]').count() == 1
            page.locator("#lexical-mode").select_option("jev")
            page.locator("#n-best").select_option("3")
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#sentence").fill("john lends a book to mary.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"] and "lend_vhho02324182" in result["words"][-1]["normalized"]
            change = page.locator("#lexical-path-updates .lexical-entry").filter(has_text="Jev preference validated by DS")
            expect(change).to_have_count(1)
            change.get_by_role("button", name="Watch this revision").click()
            expect(page.locator("#operation-rule")).to_have_text("Revise an earlier interpretation")
            expect(page.locator("#operation-change")).to_contain_text("lend_vhho02324182")
            frame = page.evaluate("current()")
            assert frame["kind"] == "backtrack" and frame["word_index"] == 5
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == frame["pointer"]
            page.get_by_role("button", name="Next step", exact=True).click()
            assert page.evaluate("current().kind") in {"operation", "word", "action", "grouped"}
            page.screenshot(path=str(args.output / f"{backend}-revision.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.set_viewport_size({"width": 1440, "height": 1100})
        assert not errors, errors
        browser.close()
    print("PP DP structure, LINK/pointer steps, live-answer revision playback and mobile width passed in both modes.")


if __name__ == "__main__":
    main()
