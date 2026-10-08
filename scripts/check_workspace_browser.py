"""Verify workspace navigation, unchanged DS flows, model controls and mobile use.

Uses real DS responses and a fixture OpenRouter connection. Known vocabulary
needs no model inference; no real credentials or billed calls are required.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from check_openrouter_browser import connect, assert_private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8808")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-workspace-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=45000)
    checks, metrics, errors = [], {}, []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        requests = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: requests.append(r) if "/api/parse/stream" in r.url else None)
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()

        def pause():
            if page.locator("#play").get_attribute("aria-label") == "Pause derivation":
                page.locator("#play").click()

        def parse(text):
            page.locator("#sentence").fill(text)
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            pause()
            return page.evaluate("state.result")

        def tab(name):
            page.locator(f'[data-workspace="{name}"]').click()
            expect(page.locator(f'[data-workspace="{name}"]')).to_have_attribute("aria-selected", "true")

        pause()
        metrics["desktop_derivation_y"] = page.locator(".workbench").bounding_box()["y"] + page.evaluate("scrollY")
        assert metrics["desktop_derivation_y"] < 850
        expect(page.locator("#research")).to_be_hidden()
        expect(page.locator("#greek-lab")).to_be_hidden()
        expect(page.locator("#examples button")).to_have_count(3)
        page.locator("#all-examples").click()
        assert page.locator("#examples button").count() > 3
        page.locator("#all-examples").click()
        expect(page.locator("#examples button")).to_have_count(3)
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        page.evaluate("scrollTo(0,0)")
        page.screenshot(path=str(args.output / "desktop.png"))

        count, meaning = len(requests), page.evaluate("state.result.words.at(-1).semantics")
        tab("library")
        expect(page.locator("#library-count")).to_contain_text("53 of 53")
        page.locator("#library-query").fill("Kempson")
        assert 0 < page.locator(".library-card").count() < 53
        page.locator("#library-query").fill("zzzz-no-such-record")
        expect(page.locator("#library-results")).to_contain_text("No matching works")
        page.locator("#library-query").fill("")
        framework = page.locator('#library-framework option[value="ttr"]')
        assert framework.count() == 1
        page.locator("#library-framework").select_option("ttr")
        assert 0 < page.locator(".library-card").count() < 53
        page.locator("#library-query").fill("CL25")
        expect(page.locator(".library-card")).to_have_count(1)
        expect(page.locator(".library-card .library-meta").last).to_contain_text("TTR")
        page.locator("#library-query").fill("")
        page.locator("#library").screenshot(path=str(args.output / "library.png"))
        tab("research")
        expect(page.locator("#corpus-form")).to_be_visible()
        tab("greek-lab")
        expect(page.locator("#dialect-cards")).to_be_visible()
        page.locator('[data-workspace="greek-lab"]').focus()
        page.keyboard.press("ArrowRight")
        expect(page.locator('[data-workspace="library"]')).to_be_focused()
        tab("parse")
        assert len(requests) == count
        assert page.evaluate("state.result.words.at(-1).semantics") == meaning
        checks.append("Tabs and library filters preserve the parse and make no parse/model requests")

        tab("greek-lab")
        page.locator('[data-greek-example="smg-finite"]').click()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#parse-workspace")).to_be_visible()
        assert page.evaluate("state.result.complete")
        checks.append("Greek lab examples return to Parse and complete through DS")
        page.locator("#grammar").select_option("2026-english-mltt")
        expect(page.locator("#parse-button")).to_be_enabled()
        result = parse("John opens the door.")
        assert result["complete"]
        page.locator("#result-evidence > summary").click()
        assert page.locator(".lexical-word-group").count() > 0
        assert page.locator(".lexical-word-group").count() < len(result["lexical"]["entries"])
        page.locator(".lexical-word-group > summary").first.click()
        page.locator(".lexical-word-group[open] .lexical-entry > summary").first.click()
        expect(page.locator(".lexical-word-group[open] .lexical-entry[open] pre")).to_be_visible()
        checks.append("Candidates grouped by word; evidence and action programs remain inspectable")
        page.locator("#result-evidence > summary").click()
        result = parse("John glorped the door.")
        assert not result["complete"] and result["failure"]["kind"] == "lexicon_gap"
        page.locator("#inspect-failure").click()
        expect(page.locator("#diagnostics")).to_be_visible()
        expect(page.locator("#diagnosis-title")).to_have_text("Missing lexical entry")
        page.locator("#result-evidence > summary").click()
        parse("a man walks.")
        page.locator("#first").click() if page.locator("#first").is_enabled() else None
        page.locator("#next").click()
        page.locator("#zoom-in").click()
        view = page.locator("#tree").get_attribute("viewBox")
        page.locator("#next").click()
        assert page.locator("#tree").get_attribute("viewBox") == view
        expect(page.locator("#follow-tree")).not_to_be_checked()
        page.locator("#follow-tree").check()
        assert page.locator("#tree").get_attribute("viewBox") != view
        checks.append("Manual zoom persists between steps; Auto-fit restores following the tree")

        key = "fixture-workspace-secret"
        page.route("**/api/openrouter/connect", lambda route: route.fulfill(json={
            "connected": True, "models": [{"id": "fixture/workspace", "name": "Fixture model", "input_per_million": 0, "output_per_million": 0}],
            "default_model": "fixture/workspace", "jev": {"available": True, "model": "typesafe/jev-1.13-20260917"},
        }))
        count = len(requests)
        page.locator("#model-settings-button").click()
        expect(page.locator("#models-dialog")).to_be_visible()
        connect(page, key)
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        page.locator("#models-close").click()
        expect(page.locator("#model-settings-button")).to_be_focused()
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            for llm, jev in ((True, False), (True, True), (False, True), (False, False)):
                before = len(requests)
                page.locator("#llm-enabled").set_checked(llm)
                page.locator("#jev-enabled").set_checked(jev)
                assert len(requests) == before
                result = parse("John walks.")
                assert result["complete"]
                assert requests[-1].post_data_json["allow_model_fallback"] is llm
                assert ("authorization" in requests[-1].headers) is (llm or jev)
                expect(page.locator("#method-usage")).to_contain_text("Analysis LLM · " + ("no request made" if llm else "off"))
                expect(page.locator("#method-usage")).to_contain_text("Jev · " + ("no request made" if jev else "off"))
        page.locator("#model-settings-button").click()
        page.keyboard.press("Escape")
        expect(page.locator("#models-dialog")).to_be_hidden()
        checks.append("Model drawer and all LLM/Jev switch combinations preserve explicit permissions and usage counts")
        page.locator("#llm-enabled").check()
        page.locator("#jev-enabled").check()
        page.locator("#system").select_option("ttr")
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#llm-enabled")).not_to_be_checked()
        expect(page.locator("#jev-enabled")).not_to_be_checked()
        expect(page.locator("#llm-enabled")).to_be_disabled()
        assert "authorization" not in requests[-1].headers
        page.locator("#system").select_option("classical")
        expect(page.locator("#parse-button")).to_be_enabled()

        page.locator('[data-input-mode="paragraph"]').click()
        page.locator("#paragraph").fill("John walks. He knows Mary. She walks.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.paragraph.coverage.complete") == 3
        page.locator('[data-sentence-index="1"]').click()
        expect(page.locator('[data-mode="actions"]')).to_have_attribute("aria-pressed", "true")
        page.locator('[data-input-mode="dialogue"]').click()
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.result.complete")
        checks.append("Paragraph sentence playback and shared dialogue examples still complete")

        page.locator('[data-input-mode="sentence"]').click()
        parse("a man walks.")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#llm-enabled").check()
        page.locator("#jev-enabled").check()
        expect(page.locator("#llm-state")).to_have_text("ON · when needed")
        expect(page.locator("#jev-state")).to_have_text("ON")
        page.evaluate("scrollTo(0,0)")
        metrics["mobile_derivation_y"] = page.locator(".workbench").bounding_box()["y"]
        assert metrics["mobile_derivation_y"] < 1200
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        for id in ("first", "previous", "play", "next", "fit", "zoom-in", "zoom-out"):
            box = page.locator("#" + id).bounding_box()
            assert box["width"] >= 44 and box["height"] >= 44
        timeline = page.locator("#timeline").bounding_box()
        assert timeline["x"] >= 0 and timeline["x"] + timeline["width"] <= 390
        expect(page.locator("#inspector-drawer")).not_to_have_attribute("open", "")
        page.locator('.tree-node [role="button"]').first.focus()
        page.keyboard.press("Enter")
        expect(page.locator("#node-panel")).to_be_visible()
        expect(page.locator("#node-tab")).to_have_attribute("aria-selected", "true")
        assert page.locator(".semantics-panel").bounding_box()["y"] < page.locator("#inspector-drawer").bounding_box()["y"]
        page.evaluate("scrollTo(0,0)")
        page.screenshot(path=str(args.output / "mobile.png"))
        page.locator(".explorer").screenshot(path=str(args.output / "mobile-explorer.png"))
        assert_private(page, key)
        assert not errors, errors
        checks.append("Mobile playback targets, timeline bounds, formula placement and inspector disclosure checked")
        browser.close()
    (args.output / "checks.json").write_text(json.dumps({"checks": checks, "metrics": metrics}, indent=2))
    print(json.dumps({"checks": len(checks), "metrics": metrics}))


if __name__ == "__main__":
    main()
