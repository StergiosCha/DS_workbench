"""Verify source-based supplemental relatives through the actual workbench UI."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from check_openrouter_browser import ready

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8797")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-nonrestrictive-browser"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=60000)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    ready(page, args.url)
    records = []
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#grammar").select_option(f"2026-english-{backend}")
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#use-dictionaries").click()
        for sentence, expected in [
            ("John, who Mary knows, walks.", "(walk(john) ∧ know(mary, john))"),
            ("John, who walks quickly, arrives.", "(arrive(john) ∧ quickly(walk(john)))"),
            ("Mary knows John, who walks.", "(know(mary, john) ∧ walk(john))"),
            ("John, who Mary walks, arrives.", None),
        ]:
            page.locator("#sentence").fill(sentence)
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"] == (expected is not None), result.get("failure")
            if expected is not None:
                assert result["words"][-1]["normalized"] == expected
                assert any("L" in n["id"] for n in result["words"][-1]["nodes"])
                page.locator("#show-final").click()
                expect(page.locator("#semantic-status")).to_have_text("COMPLETE TREE")
                expect(page.locator("#semantics")).to_contain_text("∧")
                with page.expect_download() as download:
                    page.locator("#export").click()
                exported = json.loads(Path(download.value.path()).read_text())
                assert exported["words"][-1]["normalized"] == expected
                if sentence.startswith("John, who Mary knows"):
                    page.locator(".semantics-panel").screenshot(path=str(args.output / f"{backend}-meaning.png"))
                    (args.output / f"{backend}-derivation.json").write_text(json.dumps(exported, ensure_ascii=False))
            records.append({"backend": backend, "sentence": sentence, "complete": result["complete"],
                            "meaning": result["words"][-1]["normalized"]})
    assert not errors, errors
    (args.output / "results.json").write_text(json.dumps({"url": args.url, "checks": records,
                                                         "browser_errors": errors}, indent=2))
    browser.close()
print(json.dumps({"checks": len(records), "url": args.url, "output": str(args.output)}))
