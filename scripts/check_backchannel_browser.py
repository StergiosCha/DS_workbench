"""Check the local feedback preset, playback, and incomplete-unit contrast."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8793")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-backchannel-browser"))
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
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator('[data-input-mode="dialogue"]').click()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        page.locator('[data-dialogue-example="backchannel"]').click()
        expect(page.locator("#parse-button")).to_be_enabled()
        page.evaluate("stop(); setIndex(frames().length - 1)")
        result = page.evaluate("state.result")
        assert result["complete"], result["failure"]
        assert len(result["words"][-1]["feedback_events"]) == 1
        expect(page.locator("#feedback-events")).to_contain_text('B: “mhm”')
        expect(page.locator("#feedback-events")).to_contain_text("Tn(00) to Tn(0)")
        expect(page.locator("#feedback-events")).to_contain_text("Howes & Eshghi")
        page.evaluate("setIndex(0)")
        expect(page.locator("#feedback-events")).to_be_hidden()
        page.evaluate("setIndex(frames().length - 1)")
        (args.output / f"{backend}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#feedback-events").scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / f"{backend}.png"))
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.get_by_label("Words for turn 1", exact=True).fill("the")
        page.get_by_label("Words for turn 3", exact=True).fill("man walks.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert not page.evaluate("state.result.complete")
        assert page.evaluate("state.result.failure.token") == "mhm"
        expect(page.locator("#feedback-events")).to_be_hidden()
        print(f"{backend}: feedback preset, playback, mobile and missing-unit contrast passed", flush=True)
    assert not errors, errors
    browser.close()
