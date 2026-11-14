"""Exercise the generated, offline literature report with Chromium."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path,
                        default=Path("build/experiments/literature-diagnostic-v1/report.html"))
    args = parser.parse_args()
    report = args.report.resolve()
    output = report.parent / "browser"
    output.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1000}, accept_downloads=True)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(report.as_uri())
        assert page.locator("#scores tr").count() == 9
        assert page.locator("#conditions .condition").count() == 4
        assert page.locator("#conditions .pass").count() == 4
        assert page.locator("#conditions .critical").count() == 4
        page.select_option("#engine", "ccg-feature-nearest-v1")
        assert page.locator("#conditions .fail").count() == 4
        page.select_option("#engine", "ds-english-v1")
        assert page.locator("#conditions .unavailable").count() == 4
        page.select_option("#suite", "reflexive_prep_masc")
        page.select_option("#family", "reflexive_prep_masc:19")
        page.select_option("#engine", "ccg-feature-no-binding-v1")
        assert page.locator("#conditions .pass").count() == 2
        assert page.locator("#conditions .fail").count() == 2
        assert "Constraint disabled." in page.locator("#conditions").inner_text()
        page.select_option("#engine", "ccg-feature-head-v1")
        assert page.locator("#conditions .pass").count() == 4
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        with page.expect_download() as download:
            page.click("#download")
        download.value.save_as(str(output / "download.json"))
        downloaded = json.loads((output / "download.json").read_text())
        assert len(downloaded["dataset"]["items"]) == 152
        assert downloaded["original_surprisal_scores"] is None
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print("Passed: nine configurations, family/suite filters, constraints, unavailable scores, JSON download, mobile layout.")


if __name__ == "__main__":
    main()
