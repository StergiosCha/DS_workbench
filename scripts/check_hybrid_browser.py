"""Exercise the research UI against a running local ds-workbench server.

Requires Playwright and Chromium. No live model requests are made.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8769")
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/hybrid.html")
        expect(page.locator("#connection")).to_contain_text("worker ready", timeout=15000)
        results = []
        for index in range(9):
            page.select_option("#example", str(index))
            page.click("#build")
            expect(page.locator("#analysis-status")).to_have_text("Analysis ready", timeout=50000)
            result = page.locator("#analysis-result").inner_text()
            assert result.strip()
            results.append({"example": index, "rendered": True})
            if index == 1:
                assert "Valence requirements are satisfied" in result
                page.locator(".step-buttons button").nth(1).click()
                assert 'After “likes”' in page.locator("#step-title").inner_text()
                assert "Requirements remain open" in page.locator("#lfg-panel").inner_text()
                page.screenshot(path=str(args.output / "english-prefix.png"), full_page=True)
            if index == 3:
                assert "complete" in result and "Nominal descriptions unify" in result
                page.screenshot(path=str(args.output / "greek-polydefinite.png"), full_page=True)
            if index == 5:
                assert "No unique type meet" in result
            if index == 7:
                assert '"operation": "Move"' in result
        page.click("#tab-evidence")
        assert "26,962" in page.locator("#evidence-intro").inner_text()
        assert page.locator("#matched-table tbody tr").count() == 5
        page.select_option("#cohort", "ds_matched")
        assert "unavailable" in page.locator("#comparison-note").inner_text()
        page.select_option("#regime", "participant")
        assert "rank deficient" in page.locator("#comparison-table").inner_text()
        page.screenshot(path=str(args.output / "evidence.png"), full_page=True)
        page.click("#tab-assistance")
        page.click("#rank")
        expect(page.locator("#assist-status")).to_have_text("Result ready", timeout=50000)
        assert "stub" in page.locator("#assistance-result").inner_text()
        page.set_viewport_size({"width": 390, "height": 844})
        page.click("#tab-analysis")
        page.screenshot(path=str(args.output / "mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        bad_origin = page.request.post(args.url + "/api/hybrid/analyse", data={"text": "John"}, headers={"Origin": "https://elsewhere.invalid"})
        assert bad_origin.status == 403
        bad_payload = page.request.post(args.url + "/api/hybrid/analyse", data={"text": "John", "complete": "false"})
        assert bad_payload.status == 400
        assert not errors, errors
        browser.close()
    report = {"examples": results, "mobile_overflow": False, "javascript_errors": errors,
              "origin_rejected": True, "invalid_payload_rejected": True, "live_models": False}
    (args.output / "checks.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
