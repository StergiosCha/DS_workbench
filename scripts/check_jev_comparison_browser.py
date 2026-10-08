"""Run the public Jev comparison with BYOK; save no credentials or network traces."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from check_openrouter_browser import ready, connect, assert_private, load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8794")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-jev-comparison-browser"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
load_environment()
key = os.environ["OPENROUTER_API_KEY"]
expect.set_options(timeout=60000)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    ready(page, args.url)
    page.locator("#system").select_option("classical")
    expect(page.locator("#parse-button")).to_be_enabled()
    page.locator("#jev-demo-button").click()
    previous_result = page.evaluate("state.result")
    page.locator("#jev-examples button").first.click()
    expect(page.locator("#sentence")).to_have_value("John lends a book to Mary.")
    expect(page.locator("#jev-run")).to_be_disabled()
    assert page.evaluate("state.result") == previous_result
    connect(page, key)
    page.locator("#openrouter-model").select_option("deepseek/deepseek-v4.1-flash")
    for backend in ("classical", "mltt"):
        page.locator("#use-dictionaries").click()
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        with page.expect_request("**/api/parse/stream") as pending:
            page.locator("#jev-examples button").first.click()
        request = pending.value
        assert request.post_data_json["compare_jev"] is True
        assert request.post_data_json["lexical_mode"] == "jev"
        assert request.post_data_json["decision_mode"] == "off"
        assert request.post_data_json["n_best"] == 1
        assert request.headers.get("authorization") == f"Bearer {key}"
        expect(page.locator("#parse-button")).to_be_enabled()
        result = page.evaluate("state.result")
        serialized = json.dumps(result, ensure_ascii=False)
        assert key not in serialized
        (args.output / f"{backend}.json").write_text(serialized)
        comparison = result["jev_comparison"]
        assert result["complete"] and comparison["without_jev"]["complete"]
        assert comparison["same_inventory"] and comparison["valid_decisions"]
        assert result["lexical"]["selection"]["model"] == "typesafe/jev-1.13-20260917"
        assert comparison["shared_model_candidates"] == 0
        expect(page.locator("#jev-impact")).to_be_visible()
        expect(page.locator("#jev-baseline")).to_contain_text("Complete DS derivation")
        expect(page.locator("#jev-preferred")).to_contain_text("Complete DS derivation")
        expect(page.locator("#jev-journey")).to_contain_text("john lends a book to mary")
        page.locator("#jev-impact").screenshot(path=str(args.output / f"{backend}-comparison.png"))
        page.locator("#lexical-selection-decisions details").evaluate_all("nodes => nodes.forEach(n => n.open = true)")
        assert page.locator(".jev-probability progress").count() >= 3
        expect(page.locator("#lexical-selection-decisions")).to_contain_text("Later words were not supplied")
        page.locator("#lexical-selection-decisions").screenshot(path=str(args.output / f"{backend}-probabilities.png"))
        revisions = page.locator("#jev-journey button")
        if revisions.count():
            revisions.first.click()
            frame = page.evaluate("frames()[state.index]")
            assert frame["kind"] == "backtrack" and frame["lexical_changes"]
            assert any(c["reason"] == "Jev preference validated by DS" for c in frame["lexical_changes"])
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = Path(download.value.path()).read_text()
        assert key not in exported and json.loads(exported)["jev_comparison"] == comparison
        assert_private(page, key)
        print(json.dumps({"backend": backend, "status": comparison["status"],
            "same_inventory": comparison["same_inventory"], "live_calls": comparison["live_calls"],
            "changes": [{"word": c["word"], "before": c["without_jev"]["symbol"], "after": c["with_jev"]["symbol"]} for c in comparison["changes"]],
            "revisions": result["lexical"]["selection"]["revisions"]}), flush=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile overflow"
    page.locator("#jev-impact").screenshot(path=str(args.output / "mobile-comparison.png"))
    page.locator("#use-dictionaries").click()
    page.locator("#sentence").fill("John walks.")
    page.locator("#parse-button").click()
    expect(page.locator("#parse-button")).to_be_enabled()
    expect(page.locator("#jev-impact")).to_be_hidden()
    assert page.evaluate("state.result.complete")
    assert not errors, errors
    browser.close()
print("Jev comparison browser checks passed: actual runs, probabilities, revision playback, exports, key privacy, mobile, off mode.")
