"""Check clause families and visible, live construction assistance in the UI."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from check_openrouter_browser import ready, connect, assert_private, load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8796")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-construction-browser"))
parser.add_argument("--live", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=65000)


def run(page, text):
    page.locator("#sentence").fill(text)
    page.locator("#parse-button").click()
    expect(page.locator("#parse-button")).to_be_enabled()
    return page.evaluate("state.result")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors, rows = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    ready(page, args.url)
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#grammar").select_option(f"2026-english-{backend}")
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#use-dictionaries").click()
        for text, symbol in [("When George opened the door, Mary entered the room.", "when_clause"),
                             ("If Bill shouts, John walks because Mary walks.", "condition")]:
            result = run(page, text)
            assert result["complete"] and result["words"][-1]["normalized"].startswith(symbol + "(")
            expect(page.locator("#construction-summary")).to_contain_text("without a construction model request")
            expect(page.locator("#construction-used")).to_contain_text(symbol.replace("_", " "))
            rows.append({"backend": backend, "text": text, "meaning": result["words"][-1]["normalized"], "used": result["clause_constructions"]})
        page.locator("#grammar").select_option(f"2026-smg-{backend}")
        expect(page.locator("#parse-button")).to_be_enabled()
        result = run(page, "Ο Γιώργος περπατάει παρότι η Μαρία περπατάει αργότερα.")
        assert result["complete"] and result["words"][-1]["normalized"] == "concession(walk(giorgos), later(walk(maria)))"
        rows.append({"backend": backend, "text": result["sentence"], "meaning": result["words"][-1]["normalized"]})
    page.locator("#grammar").select_option("2026-english-mltt")
    expect(page.locator("#parse-button")).to_be_enabled()
    assert not run(page, "John walks when.")["complete"]
    if args.live:
        load_environment()
        key = os.environ["OPENROUTER_API_KEY"]
        connect(page, key)
        page.locator("#openrouter-model").select_option(os.getenv("DS_ASSISTED_TEST_MODEL", "deepseek/deepseek-v4.1-flash"))
        page.locator("#lexical-mode").select_option("assisted")
        result = run(page, "John walks provided Mary walks.")
        assert result["complete"] and result["words"][-1]["normalized"] == "condition(walk(john), walk(mary))"
        expect(page.locator("#construction-proposals")).to_contain_text("Model proposed: provided")
        expect(page.locator("#construction-used")).to_contain_text("DS used: “provided” → condition")
        page.locator("#construction-proposals details").first.locator("summary").click()
        expect(page.locator("#construction-proposals pre").first).to_be_visible()
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = Path(download.value.path()).read_text()
        assert key not in exported and json.loads(exported)["clause_constructions"][0]["relation"] == "condition"
        (args.output / "live-provided.json").write_text(exported)
        assert_private(page, key)
        page.locator("#construction-report").screenshot(path=str(args.output / "construction-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile overflow"
        page.locator("#construction-report").screenshot(path=str(args.output / "construction-mobile.png"))
    assert not errors, errors
    (args.output / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    browser.close()
print("Browser checks passed: clause families, two backends, both languages, failures" + (", live construction proposal, actual DS choice, exports and mobile." if args.live else "."))
