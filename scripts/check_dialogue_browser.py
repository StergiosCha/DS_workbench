"""Exercise shared polar questions in the real UI, with no provider connection."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8792")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-dialogue-browser"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=60000)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url)
    expect(page.locator("#parse-button")).to_be_enabled()
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator('[data-input-mode="dialogue"]').click()
        page.locator('#lexical-settings').evaluate("el => el.open = true")
        page.locator("#advanced-settings").evaluate("element => element.open = true")
        page.locator("#lexical-mode").select_option("off")
        page.locator('[data-dialogue-example="shared-question"]').click()
        expect(page.locator("#parse-button")).to_be_enabled()
        page.evaluate("stop(); setIndex(frames().length - 1)")
        result = page.evaluate("state.result")
        assert result["complete"], result["failure"]
        assert result["words"][-1]["semantics"] == "¬(burn(speaker_B, speaker_B))"
        assert result["lexical"]["entries"] == []
        expect(page.locator("#method-result-title")).to_have_text("No LLM used")
        expect(page.locator("#speech-act")).to_contain_text("Negative answer")
        expect(page.locator("#context-history")).to_contain_text("question content")
        (args.output / f"{backend}-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = Path(download.value.path()).read_text()
        assert json.loads(exported)["context_trees"][0]["speech_act"]["kind"] == "polar_question"
        if backend == "mltt":
            with page.expect_download() as download:
                page.locator("#coq").click()
            assert "Definition meaning" in Path(download.value.path()).read_text()
        page.locator("#context-history button").click()
        expect(page.locator("#speech-act")).to_contain_text("Question content")
        expect(page.locator("#reflexive-binding")).to_contain_text("myself → local subject B")
        expect(page.locator("#semantics")).to_have_text("burn(speaker_B, speaker_B)")
        # Full combinator types remain visible in the tree; formulas can expand.
        if page.locator('.formula-toggle[aria-expanded="false"]').count():
            page.locator('.formula-toggle[aria-expanded="false"]').first.click()
        page.locator("#tree-stage").screenshot(path=str(args.output / f"{backend}-question.png"))
        page.evaluate("setIndex(frames().length - 1)")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#speech-act").scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / f"{backend}-mobile-answer.png"))
        page.set_viewport_size({"width": 1440, "height": 1050})
        # The wrong deictic reflexive must still fail when entered through the UI.
        page.get_by_label("Words for turn 2", exact=True).fill("yourself?")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert not page.evaluate("state.result.complete")
        assert page.evaluate("state.result.failure.token") == "yourself"
        print(f"{backend}: preset, shared binding, preserved question, negative answer, mobile and rejected mismatch passed", flush=True)
    assert not errors, errors
    browser.close()
