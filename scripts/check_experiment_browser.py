"""Exercise independent configurations, report rendering, rehearsal and API boundaries."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8770")
    parser.add_argument("--output", type=Path, default=Path("build/experiments/browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width":1440, "height":1000}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/experiments.html")
        expect(page.locator("#connection")).to_contain_text("workers ready")
        assert page.locator("#configurations article").count() == 2
        assert "864 simulated targets" in page.locator("#report").inner_text()
        assert "NO · diagnostic only" in page.locator("#report").inner_text()
        page.click("#run-pair")
        expect(page.locator("#run-status")).to_contain_text("Comparison ready", timeout=50000)
        assert page.locator(".run-grid > article").count() == 2
        assert "DS tree" in page.locator("#results").inner_text()
        assert "CCG categories" in page.locator("#results").inner_text()
        page.locator(".run-grid > article").nth(1).locator(".step-buttons button").first.click()
        assert "After “mary”" in page.locator("#results").inner_text()
        with page.expect_download() as download:
            page.click("#download")
        download.value.save_as(args.output / "comparison.json")
        initial = json.loads((args.output / "comparison.json").read_text())
        assert all(r["events"][-1]["analysis"]["supported"] for r in initial["runs"])
        card = page.locator("#configurations article").nth(1)
        card.locator('[name="memory"]').select_option("none-v1")
        page.select_option("#study-lag", "2")
        page.click("#run-study")
        expect(page.locator("#run-status")).to_contain_text("Comparison ready", timeout=50000)
        assert page.locator(".run-grid > article").nth(1).locator(".event").count() == 4
        assert "Activation before update: 0.0000" in page.locator(".run-grid > article").nth(1).inner_text()
        page.screenshot(path=str(args.output / "configurations.png"), full_page=True)
        page.set_viewport_size({"width":390, "height":844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(args.output / "mobile.png"), full_page=True)
        invalid = page.request.post(args.url + "/api/experiments/run", data={"configurations":[{}], "prime":"John", "target":"Mary", "task":[]})
        assert invalid.status == 400
        invalid_config = page.request.post(args.url + "/api/experiments/run", data={"configurations":[{"grammar":"arbitrary-module"}]})
        assert invalid_config.status == 400
        bad_origin = page.request.post(args.url + "/api/experiments/run", data={}, headers={"Origin":"https://elsewhere.invalid"})
        assert bad_origin.status == 403
        too_large = page.request.post(args.url + "/api/experiments/run", data="x"*17000)
        assert too_large.status == 400
        assert page.request.get(args.url + "/api/experiments/schedule?participant=-1").status == 400
        assert page.request.get(args.url + "/api/experiments/unknown").status == 404
        page.goto(args.url + "/experiment-task.html")
        page.click("#start")
        expect(page.locator("#task-stage")).to_be_visible()
        for _ in range(5):
            page.click("#reveal")
            expect(page.locator("#possible")).to_be_enabled()
            page.click("#possible")
        with page.expect_download() as download:
            page.click("#save")
        download.value.save_as(args.output / "rehearsal-0.json")
        saved = json.loads((args.output / "rehearsal-0.json").read_text())
        assert saved["data_kind"] == "rehearsal" and len(saved["events"]) == 5
        assert all(e["rt_ms"] > 0 for e in saved["events"])
        page.screenshot(path=str(args.output / "task.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        browser.close()
    print(json.dumps({"status":"passed", "checks":["independent states", "memory swap", "synthetic report", "mobile", "API validation", "local rehearsal export"], "output":str(args.output)}))


if __name__ == "__main__":
    main()
