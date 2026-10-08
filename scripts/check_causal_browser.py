"""Check causal meanings and final-result/playback distinction in a real browser."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from check_openrouter_browser import ready, connect, assert_private, load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8795")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-causal-browser"))
parser.add_argument("--live", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=60000)
EXACT = "George opened the door because he came later"


def run(page, sentence):
    page.locator("#sentence").fill(sentence)
    page.locator("#parse-button").click()
    expect(page.locator("#parse-button")).to_be_enabled()
    return page.evaluate("state.result")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    ready(page, args.url)
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#grammar").select_option(f"2026-english-{backend}")
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#use-dictionaries").click()
        result = run(page, EXACT)
        assert result["complete"] and "later(come_" in result["words"][-1]["normalized"]
        assert result["words"][-1]["normalized"].count("george") == 2
        assert result["lexical"]["mode"] == "dictionary"
        page.evaluate("setIndex(5)")
        expect(page.locator("#playback-status-text")).to_contain_text("The whole input has a complete derivation")
        expect(page.locator("#playback-status-text")).to_contain_text("Viewing an earlier tree")
        expect(page.locator("#semantic-status")).to_contain_text("FINAL DERIVATION COMPLETE")
        page.locator("#show-final").click()
        assert page.evaluate("state.index === frames().length - 1 && state.timer === null")
        expect(page.locator("#semantic-status")).to_have_text("COMPLETE TREE")
        expect(page.locator("#semantics")).to_contain_text("because(")
        expect(page.locator("#semantics")).to_contain_text("later(")
        expect(page.locator("#semantic-note")).to_contain_text("him interpreted as george")
        page.locator(".semantics-panel").screenshot(path=str(args.output / f"{backend}-meaning.png"))
        page.locator("#playback-status").screenshot(path=str(args.output / f"{backend}-status.png"))
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = json.loads(Path(download.value.path()).read_text())
        assert exported["words"][-1]["normalized"] == result["words"][-1]["normalized"]
        (args.output / f"{backend}.json").write_text(json.dumps(exported, ensure_ascii=False))
        page.locator("#grammar").select_option(f"2026-smg-{backend}")
        expect(page.locator("#parse-button")).to_be_enabled()
        greek = run(page, "Επειδή η Μαρία περπατάει αργότερα, ο Γιώργος περπατάει σήμερα.")
        assert greek["complete"] and greek["words"][-1]["normalized"] == "because(today(walk(giorgos)), later(walk(maria)))"
        print(json.dumps({"backend": backend, "exact_complete": result["complete"], "meaning": result["words"][-1]["normalized"], "greek_complete": greek["complete"]}), flush=True)
    page.locator("#grammar").select_option("2026-english-mltt")
    expect(page.locator("#parse-button")).to_be_enabled()
    failed = run(page, "John walks because.")
    assert not failed["complete"]
    page.evaluate("setIndex(frames().length - 1)")
    expect(page.locator("#playback-status-text")).to_contain_text("The whole input is incomplete")
    assert "FINAL DERIVATION COMPLETE" not in page.locator("#semantic-status").inner_text()
    run(page, EXACT)
    page.evaluate("setIndex(5)")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile overflow"
    page.locator("#playback-status").screenshot(path=str(args.output / "mobile-playback.png"))
    page.locator("#show-final").click()
    if args.live:
        load_environment()
        key = os.environ["OPENROUTER_API_KEY"]
        connect(page, key)
        page.locator("#lexical-mode").select_option("jev")
        result = run(page, EXACT)
        assert result["complete"] and result["jev_comparison"]["without_jev"]["complete"]
        assert result["jev_comparison"]["same_inventory"] and result["jev_comparison"]["valid_decisions"]
        assert "because(" in result["words"][-1]["normalized"] and "later(" in result["words"][-1]["normalized"]
        assert_private(page, key)
        text = json.dumps(result, ensure_ascii=False)
        assert key not in text
        (args.output / "jev-exact.json").write_text(text)
        print("Live Jev exact-sentence comparison passed.", flush=True)
    assert not errors, errors
    browser.close()
print("Causal browser checks passed: exact sentence, English/Greek, both backends, playback/final status, missing reason, exports and mobile.")
