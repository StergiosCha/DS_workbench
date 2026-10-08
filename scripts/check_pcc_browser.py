"""Verify PCC failure, prefix display and valid controls through the real DS API.

The optional-assistance check uses a fixture connection and an attested verb;
no model inference or real credential is required.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from check_openrouter_browser import assert_private, connect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8800")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-pcc-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=45000)
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()

        def parse(text, *, complete, assisted=False):
            page.locator("#sentence").fill(text)
            with page.expect_request("**/api/parse/stream") as pending:
                page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"] is complete
            assert ("authorization" in pending.value.headers) is assisted
            if complete:
                assert result["words"][-1]["requirement_count"] == 0
                assert all(n["fixed"] for n in result["words"][-1]["nodes"])
            else:
                page.locator("#result-evidence").evaluate("element => element.open = true")
                assert not result["ok"]
                assert result["failure"]["kind"] == "pcc_violation"
                assert result["failure"]["index"] == 1
                assert result["words"][-1]["label"] == text.split()[0]
                assert not any("PP" in n["id"] for f in result["words"] for n in f["nodes"])
                expect(page.locator("#diagnosis-title")).to_have_text("Person–Case Constraint (PCC)")
                expect(page.locator("#diagnosis-detail")).to_contain_text("same locally unfixed node")
                expect(page.locator("#message")).to_contain_text("cluster is blocked")
                expect(page.locator("#method-result-detail")).to_contain_text("incomplete")
            checks.append({"grammar": result["grammar"], "text": text, "complete": complete,
                           "assisted": assisted, "failure_kind": (result.get("failure") or {}).get("kind")})
            return result

        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-smg-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#use-dictionaries").click()
            for text in ("του με έδωσε", "του με έδωσε.", "της με έδωσε", "του σε έδωσε"):
                parse(text, complete=False)
            for text in ("του το έδωσε", "της τον έδωσε", "με αγαπά"):
                parse(text, complete=True)
            parse("του με έδωσε", complete=False)
            page.locator("#diagnostics").screenshot(path=str(args.output / f"{backend}-pcc.png"))
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported["failure"]["kind"] == "pcc_violation" and not exported["complete"]

        key = "fixture-pcc-secret"
        page.route("**/api/openrouter/connect", lambda route: route.fulfill(json={
            "connected": True, "models": [{"id": "fixture/pcc", "name": "Fixture model", "input_per_million": 0, "output_per_million": 0}],
            "default_model": "fixture/pcc", "jev": {"available": False},
        }))
        page.locator("#model-settings-button").click()
        connect(page, key)
        page.locator("#models-close").click()
        page.locator("#llm-enabled").check()
        for backend in ("classical", "mltt"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            result = parse("του με έδωσε", complete=False, assisted=True)
            assert result["lexical"]["attempts"] == []
            expect(page.locator("#method-usage")).to_contain_text("Analysis LLM · no request made")
        assert_private(page, key)
        page.locator("#use-dictionaries").click()
        page.locator('[data-input-mode="paragraph"]').click()
        page.locator("#paragraph").fill("του με έδωσε. του το έδωσε.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        paragraph = page.evaluate("state.paragraph")
        assert paragraph["coverage"]["complete"] == 1
        assert paragraph["sentences"][0]["result"]["failure"]["kind"] == "pcc_violation"
        assert paragraph["sentences"][1]["complete"]
        checks.append({"paragraph": "failed PCC sentence retained; valid following sentence completed"})
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#diagnostics").screenshot(path=str(args.output / "mobile-pcc.png"))
        assert not errors, errors
        browser.close()
    (args.output / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"Passed {len(checks)} PCC/browser cases, including both backends, LLM permission, exports and paragraph gaps.")


if __name__ == "__main__":
    main()
