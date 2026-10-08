"""Check explicit model switches with real DS parses and a fixture connection.

No real credentials or billed model calls. Provider-call displays are also
checked with labelled response fixtures; actual fallback isolation is covered
by test_lexical_selection.py and test_jev_comparison.py.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from check_openrouter_browser import assert_private, connect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8798")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-ai-controls-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=30000)
    key = "fixture-switches-secret"
    connection = {
        "connected": True,
        "models": [{"id": "fixture/alpha", "name": "Fixture Alpha", "input_per_million": 0, "output_per_million": 0}],
        "default_model": "fixture/alpha",
        "jev": {"available": True, "model": "typesafe/jev-1.13-20260917", "name": "Jev 1.13"},
    }
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request) if "/api/parse/stream" in request.url else None)
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#ai-controls")).to_be_visible()
        expect(page.get_by_label("Use analysis LLM", exact=True)).to_be_visible()
        expect(page.get_by_label("Use Jev", exact=True)).to_be_visible()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        expect(page.locator("#llm-enabled")).to_be_disabled()
        expect(page.locator("#jev-enabled")).to_be_disabled()
        expect(page.locator("#lexical-settings")).not_to_have_attribute("open", "")
        assert "authorization" not in requests[-1].headers
        checks.append("No AI or credential sent on initial parse")

        page.route("**/api/openrouter/connect", lambda route: route.fulfill(json=connection))
        page.locator("#model-settings-button").click()
        connect(page, key)
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        expect(page.locator("#llm-enabled")).to_be_enabled()
        expect(page.locator("#jev-enabled")).to_be_enabled()
        expect(page.locator("#advanced-settings")).not_to_have_attribute("open", "")
        checks.append("Connecting enables the controls without switching on either model")

        def run(llm, jev):
            page.locator("#sentence").fill("John walks.")
            with page.expect_request("**/api/parse/stream") as pending:
                page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            request = pending.value
            body = request.post_data_json
            assert body["allow_model_fallback"] is llm
            assert body["decision_mode"] == "off"
            if llm or jev:
                assert request.headers.get("authorization") == f"Bearer {key}"
            else:
                assert "authorization" not in request.headers
            assert ("openrouter_model" in body) is llm
            assert body["lexical_mode"] == ("jev" if jev else "assisted" if llm else page.locator("#lexical-mode").input_value())
            result = page.evaluate("state.result")
            assert result["complete"], result.get("failure")
            expect(page.locator("#method-usage")).to_contain_text("DS parser · ran")
            expect(page.locator("#method-usage")).to_contain_text("Analysis LLM · " + ("no request made" if llm else "off"))
            expect(page.locator("#method-usage")).to_contain_text("Jev · " + ("no request made" if jev else "off"))
            assert not result["lexical"].get("model_requests", 0)
            checks.append(f"Real DS parse: {body['grammar']}, analysis LLM={llm}, Jev={jev}")
            return result

        for backend in ("mltt", "classical"):
            page.locator("#use-dictionaries").click()
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            run(False, False)
            count = len(requests)
            page.locator("#llm-enabled").focus()
            page.keyboard.press("Space")
            expect(page.locator("#llm-state")).to_have_text("ON · when needed")
            assert len(requests) == count, "Changing a switch must not start a parse"
            run(True, False)
            page.locator("#jev-enabled").check()
            expect(page.locator("#llm-help")).to_contain_text("missing words only")
            run(True, True)
            page.locator("#llm-enabled").uncheck()
            expect(page.locator("#method-mode")).to_contain_text("analysis LLM is off")
            baseline = run(False, True)
            page.locator("#jev-enabled").uncheck()
            expect(page.locator("#llm-enabled")).not_to_be_checked()

        # Recorded usage belongs to the result, not to subsequently edited controls.
        def displayed_usage(llm_calls, jev_calls, *, complete=True):
            result = deepcopy(baseline)
            result["complete"] = complete
            result["lexical"].update(model_requests=llm_calls, allow_model_fallback=bool(llm_calls))
            result["lexical"]["selection"]["live_calls"] = jev_calls
            page.evaluate("result => renderMethodResult(result)", result)
            return page.locator("#method-usage").inner_text()

        assert "Analysis LLM · 1 request" in displayed_usage(1, 3)
        expect(page.locator("#method-usage")).to_contain_text("Jev · 3 requests")
        page.locator("#llm-enabled").check()
        page.locator("#use-dictionaries").click()
        expect(page.locator("#method-usage")).to_contain_text("Jev · 3 requests")
        displayed_usage(0, 0, complete=False)
        expect(page.locator("#method-result-detail")).to_contain_text("incomplete")
        checks.append("Fixture counts remain separate and stay attached to their result")

        # The advanced controls and main switches must agree in both directions.
        page.locator("#advanced-settings > summary").click()
        page.locator("#lexical-mode").select_option("model")
        expect(page.locator("#llm-enabled")).to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        page.locator("#lexical-mode").select_option("jev")
        expect(page.locator("#llm-enabled")).to_be_checked()
        expect(page.locator("#jev-enabled")).to_be_checked()
        page.locator("#use-dictionaries").click()
        expect(page.locator("#decision-mode")).to_have_value("off")
        decision_config = page.evaluate("state.config.decision")
        page.evaluate("""() => {
            state.config.decision.grammars[$('grammar').value] = {entry: true};
            renderLexicalSettings();
        }""")
        page.locator("#decision-mode").select_option("jev")
        expect(page.locator("#jev-enabled")).to_be_checked()
        page.locator("#jev-enabled").uncheck()
        expect(page.locator("#decision-mode")).to_have_value("off")
        page.evaluate("config => { state.config.decision = config; renderLexicalSettings(); }", decision_config)
        page.evaluate("setBusy(true)")
        for control in ("llm-enabled", "jev-enabled", "jev-run", "compare-jev", "lexical-mode", "decision-mode"):
            expect(page.locator("#" + control)).to_be_disabled()
        page.evaluate("setBusy(false)")
        checks.append("Advanced strategy changes and Turn off all AI stay synchronized")

        page.locator("#llm-enabled").check()
        page.locator("#jev-enabled").check()
        page.locator("#grammar").select_option("2026-smg-classical")
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).to_be_disabled()
        page.locator("#llm-enabled").check()
        expect(page.locator("#lexical-mode")).to_have_value("assisted")
        page.locator('[data-input-mode="paragraph"]').click()
        expect(page.locator("#llm-enabled")).to_be_checked()
        page.locator('[data-input-mode="dialogue"]').click()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#llm-enabled")).to_be_disabled()
        page.locator('[data-input-mode="sentence"]').click()
        page.locator("#system").select_option("ttr")
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#llm-enabled")).to_be_disabled()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        assert "authorization" not in requests[-1].headers
        checks.append("Greek, dialogue, paragraph and TTR capability changes cannot leave hidden AI on")

        page.locator("#system").select_option("mltt")
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#llm-enabled").check()
        page.locator("#jev-enabled").check()
        page.locator("#openrouter-disconnect").click()
        for control in ("llm-enabled", "jev-enabled"):
            expect(page.locator("#" + control)).not_to_be_checked()
            expect(page.locator("#" + control)).to_be_disabled()
        assert_private(page, key)
        checks.append("Disconnect clears both switches; credentials stay out of state and storage")

        connect(page, key)
        page.locator("#llm-enabled").check()
        page.locator("#lexical-settings > summary").click()
        page.locator(".method-overview").screenshot(path=str(args.output / "desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator(".method-overview").screenshot(path=str(args.output / "mobile.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile overflow"
        page.reload()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        expect(page.locator("#openrouter-badge")).to_have_text("Not connected")
        assert not errors, errors
        checks.append("Desktop/mobile layout, keyboard control, refresh and console checks passed")
        browser.close()
    (args.output / "checks.json").write_text(json.dumps(checks, indent=2))
    print("\n".join(checks))


if __name__ == "__main__":
    main()
