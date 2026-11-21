"""Exercise real hosted parses and display a real offline retry diagnostic."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8827")
    ap.add_argument("--fixture", type=Path)
    ap.add_argument("--output", type=Path, default=Path("build/nominal-pp/browser"))
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    expect.set_options(timeout=45000)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        for backend in ("mltt", "classical"):
            if page.locator("#system").input_value() != backend:
                page.locator("#system").select_option(backend)
                expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            for sentence, complete in [
                ("the man with a knife runs", True),
                ("every man with a knife runs", True),
                ("a man with glasses runs", True),
                ("john walks with a knife", True),
                ("a man with a knife", False),
            ]:
                page.locator("#sentence").fill(sentence)
                with page.expect_response(lambda r: r.url.endswith("/api/parse/stream")
                                          and r.request.post_data_json.get("sentence") == sentence):
                    page.locator("#parse-button").click()
                expect(page.locator("#parse-button")).to_be_enabled()
                with page.expect_download() as download:
                    page.locator("#export").click()
                result = json.loads(Path(download.value.path()).read_text())
                assert result["sentence"] == sentence
                assert result["complete"] is complete, (sentence, result.get("failure"))
                assert not result.get("experimental_grammar", {}).get("attempts")
                assert result.get("lexical", {}).get("model_requests", 0) == 0
                expect(page.locator("#parse-button")).to_be_enabled()
                checks.append({"backend": backend, "sentence": sentence, "complete": complete,
                               "model_requests": 0})
            page.screenshot(path=str(args.output / f"{backend}.png"), full_page=True)
        if args.fixture:
            fixture = json.loads(args.fixture.read_text())
            assert fixture["experimental_grammar"]["attempts"][0]["action_failures"]
            page.route("**/api/parse/stream", lambda route: route.fulfill(
                content_type="application/x-ndjson",
                body=json.dumps({"event": "result", "result": fixture}) + "\n"))
            page.locator("#sentence").fill(fixture["sentence"])
            page.locator("#parse-button").click()
            expect(page.locator("#experimental-report")).to_be_visible()
            page.locator("#experimental-attempts > details > summary").first.click()
            failure = page.locator(".experimental-action-failure").first
            failure.locator("summary").click()
            expect(failure).to_contain_text("existing predicate")
            expect(failure).to_contain_text("not constructed")
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported["experimental_grammar"]["attempts"][0]["action_failures"]
            checks.append({"fixture": "offline provider; real DS replay", "failed_action_visible": True,
                           "failed_action_exported": True})
        for width, height, label in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
            page.set_viewport_size({"width": width, "height": height})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(args.output / f"{label}.png"), full_page=True)
        assert not errors, errors
        browser.close()
    (args.output / "checks.json").write_text(json.dumps(
        {"url": args.url, "checks": checks, "errors": errors}, indent=2) + "\n")
    print(f"{len(checks)} checks passed; no live model calls.")


if __name__ == "__main__":
    main()
