"""Exercise native semantic modes and visible streamed growth in Chromium."""

import argparse
import json
import re
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--url", default="http://127.0.0.1:8769")
    args.add_argument("--output", default="/tmp/ds-workbench-browser")
    args.add_argument(
        "--live-lexical",
        action="store_true",
        help="Also exercise the configured live lexical provider",
    )
    options = args.parse_args()
    out = Path(options.output)
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1120},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(options.url)
        expect(page.locator("#result-status")).to_have_text("Complete derivation")
        # Parsing has finished, but playback starts with a single axiom and grows.
        assert page.locator("#timeline").input_value() == "0"
        assert page.locator(".tree-node").count() == 1
        assert page.locator("#speed").bounding_box()["width"] < 100
        assert "?Ty(Prop)" in page.locator("#node-panel").inner_text()
        expect(page.get_by_role("button", name="Pause derivation", exact=True)).to_be_enabled()
        page.screenshot(path=str(out / "axiom.png"), full_page=True)
        expect(page.locator("#timeline")).not_to_have_value("0", timeout=3000)
        assert page.locator(".tree-node").count() > 1
        page.get_by_role("button", name="Pause derivation", exact=True).click()
        frozen = page.locator("#timeline").input_value()
        page.wait_for_timeout(1000)
        assert page.locator("#timeline").input_value() == frozen
        page.screenshot(path=str(out / "growing.png"), full_page=True)

        # Make, traversal and decoration are separate calculus instructions.
        expect(page.locator('[data-mode="operations"]')).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="Go to axiom", exact=True).click()
        page.get_by_role("button", name="Next step", exact=True).click()
        assert page.locator(".tree-node").count() == 2
        assert page.locator(".tree-node.pointed").get_attribute("data-node") == "0"
        assert "make(↓1)" in page.locator("#operation-code").inner_text()
        assert "Pointer stays at 0" in page.locator("#pointer-transition").inner_text()
        assert "Created Tn(01)" in page.locator("#operation-change").inner_text()
        assert "IF" in page.locator("#operation-program").inner_text()
        assert page.locator(".program-line.executing").count() == 1
        page.screenshot(path=str(out / "make.png"), full_page=True)
        page.get_by_role("button", name="Next step", exact=True).click()
        assert page.locator(".tree-node").count() == 2
        assert page.locator(".tree-node.pointed").get_attribute("data-node") == "01"
        assert "0 → 01" in page.locator("#pointer-transition").inner_text()
        assert page.locator(".pointer-travel").count() == 1
        assert "go(" in page.locator(".program-line.executing").inner_text()
        page.screenshot(path=str(out / "go.png"), full_page=True)
        page.get_by_role("button", name="Next step", exact=True).click()
        assert "put(?Ty(" in page.locator("#operation-code").inner_text()
        assert "At 01: + ?Ty(" in page.locator("#operation-change").inner_text()
        page.get_by_role("button", name="Rules", exact=True).click()
        expect(page.locator('[data-mode="actions"]')).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="Operations", exact=True).click()

        def finish():
            expect(page.locator("#parse-button")).to_be_enabled(timeout=35000)
            page.get_by_role("tab", name="Action trace").click()
            page.locator("#action-list button").last.click()

        def sentence(text):
            page.locator("#sentence").fill(text)
            with page.expect_response("**/api/parse/stream"):
                page.locator("#parse-button").click()
            finish()

        finish()
        assert "Σ" in page.locator("#semantics").inner_text()
        assert "π₁" in page.locator("#semantics").inner_text()
        assert "Σ x:man. walk(x)" in page.locator("#normalized").inner_text()
        page.get_by_role("button", name="Copy formula", exact=True).click()
        assert "Σ" in page.evaluate("navigator.clipboard.readText()")
        with page.expect_download() as info:
            page.locator("#coq").click()
        assert "Definition meaning" in Path(info.value.path()).read_text()
        page.screenshot(path=str(out / "constructive.png"), full_page=True)
        # The lexical extension remains inspectable and can be switched off.
        page.locator("#lexical-settings > summary").click()
        page.locator("#advanced-settings").evaluate("element => element.open = true")
        sentence("a cat sleeps.")
        assert page.locator("#result-status").inner_text() == "Complete derivation"
        assert page.locator("#lexical-entries details").count() == 2
        page.locator("#lexical-entries summary").last.click()
        assert "lam(x,animal,sleep(x))" in page.locator("#lexical-entries pre").last.inner_text()
        assert "Σ x:cat. sleep(x)" in page.locator("#normalized").inner_text()
        page.screenshot(path=str(out / "lexical_expansion.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(out / "lexical_mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1120})
        page.locator("#lexical-mode").select_option("off")
        sentence("a cat sleeps.")
        assert page.locator("#diagnosis-title").inner_text() == "Missing lexical entry"
        page.locator("#lexical-mode").select_option("bundled")
        if options.live_lexical:
            page.locator("#lexical-mode").select_option("model")
            sentence("a cat purrs.")
            assert page.locator("#result-status").inner_text() == "Complete derivation"
            assert "purrs → intransitive" in page.locator("#lexical-entries").inner_text()
            page.locator("#lexical-entries summary").last.click()
            assert "model proposal" in page.locator("#lexical-entries").inner_text()
            assert re.search(
                r"Σ x:cat\. purr(?:_[a-z0-9_]+)?\(x\)", page.locator("#normalized").inner_text()
            )
            page.screenshot(path=str(out / "lexical_model.png"), full_page=True)
            sentence("a cat purrs.")
            assert page.locator("#lexical-status").inner_text() == "Cached model proposals"
            sentence("john believes that a man walks.")
            assert page.locator("#result-status").inner_text() == "Complete derivation"
            assert "believes → clausal" in page.locator("#lexical-entries").inner_text()
            assert re.search(
                r"believe(?:_[a-z0-9_]+)?\(john, Σ x:man\. walk\(x\)\)",
                page.locator("#normalized").inner_text(),
            )
            page.screenshot(path=str(out / "clausal_model.png"), full_page=True)
            page.locator("#lexical-mode").select_option("bundled")
        sentence("a man walks.")
        page.locator("#lexical-settings > summary").click()
        page.locator("#speed").select_option("200")
        page.get_by_role("button", name="Play derivation", exact=True).click()
        expect(page.locator("#timeline")).not_to_have_value("0", timeout=1500)
        page.get_by_role("button", name="Pause derivation", exact=True).click()
        sentence("every doctor examined a patient.")
        assert page.locator("#semantics").inner_text().startswith("Π")
        with page.expect_response("**/api/parse/stream"):
            page.locator("#scope").select_option("wide")
        finish()
        assert page.locator("#semantics").inner_text().startswith("Σ")
        sentence("john walks quickly.")
        assert "quickly(walk(john))" in page.locator("#semantics").inner_text()
        assert page.locator(".tree-edge.link").count() > 0
        sentence("john says that mary thinks that a man walks.")
        assert page.locator(".clause-node").count() == 2
        assert (
            "say(john, think(mary, Σ x:man. walk(x)))" in page.locator("#normalized").inner_text()
        )
        page.get_by_role("tab", name="Node inspector").click()
        page.locator(".clause-node").first.click()
        assert "Complement clause" in page.locator("#node-panel").inner_text()
        assert "Closed before combination" in page.locator("#node-panel").inner_text()
        assert "Ty(Content)" in page.locator(".clause-node .node-type").first.text_content()
        page.screenshot(path=str(out / "clause_embedding.png"), full_page=True)
        page.get_by_role("tab", name="Action trace").click()
        page.locator("#action-list button").filter(has_text="put(Ty(Content))").first.click()
        assert "close-complement" in page.locator("#operation-rule").inner_text()
        assert "put(Ty(Content))" in page.locator("#operation-code").inner_text()
        sentence("a stone shouts.")
        assert "Cannot apply a predicate of human to" in page.locator("#message").inner_text()
        assert page.locator("#result-status").inner_text() == "Stopped at a word"
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("classical")
        finish()
        assert "ε" in page.locator("#semantics").inner_text()
        assert page.locator(".tree-node").count() == 7
        assert "Ty(cn)" in page.locator('[data-node="000"] .node-type').text_content()
        assert "e → cn" in page.locator('[data-node="0001"] .node-type').text_content()
        assert "x0" in page.locator('[data-node="0000"] .node-formula').text_content()
        page.screenshot(path=str(out / "classical_cn.png"), full_page=True)
        assert not page.locator("#coq").is_visible()
        sentence("john thinks that a man walks.")
        assert "think(john, walk(ε x0:e. man(x0)))" in page.locator("#semantics").inner_text()
        assert page.locator(".clause-node .node-type").text_content() == "Ty(t)"
        assert "Ty(cn)" in page.locator('[data-node="01000"] .node-type').text_content()
        sentence("every man walks.")
        assert "τ" in page.locator("#semantics").inner_text()
        page.screenshot(path=str(out / "classical.png"), full_page=True)
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("ttr")
        finish()
        assert "know" in page.locator("#semantics").inner_text()
        sentence("does a man arrive?")
        assert page.locator("#result-status").inner_text() == "Complete derivation"
        sentence("a zzzunknown arrives")
        assert "not in this grammar" in page.locator("#message").inner_text()
        sentence("a man")
        assert page.locator("#result-status").inner_text() == "Partial derivation"
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("mltt")
        finish()
        # Dialect cases run through the same live action-calculus view.
        page.locator('[data-greek-example="cg-finite"]').click()
        finish()
        assert page.locator("#grammar").input_value() == "2026-cypriot-mltt"
        assert "know(speaker, him)" in page.locator("#semantics").inner_text()
        assert page.locator("#judgment-title").inner_text() == "Sourced placement pattern"
        page.locator('[data-environment="negation"]').click()
        page.locator('[data-greek-example="cg-neg"]').click()
        finish()
        assert "not(know(speaker, him))" in page.locator("#semantics").inner_text()
        # Switching semantics preserves the selected Greek dialect and sentence.
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("classical")
        finish()
        assert page.locator("#grammar").input_value() == "2026-cypriot-classical"
        page.locator('[data-greek-example="cg-neg-reverse"]').click()
        finish()
        assert page.locator("#diagnosis-title").inner_text() == "Placement constraint violated"
        assert page.locator("#lexicon-summary").inner_text() == "Every token has an entry"
        assert "Unlicensed" in page.locator("#judgment-title").inner_text()
        page.screenshot(path=str(out / "greek_constraint.png"), full_page=True)
        page.locator('[data-greek-example="pg-neg"]').click()
        finish()
        assert page.locator("#grammar").input_value() == "2026-pontic-classical"
        assert "¬(know(speaker, him))" in page.locator("#semantics").inner_text()
        page.locator('[data-history="cyprus"]').click()
        assert "wh-elements" in page.locator("#history-detail").inner_text()
        page.locator('[data-history="koine"]').click()
        page.locator(".corpus-counts summary").click()
        assert page.locator(".corpus-counts tbody tr").count() == 7
        page.locator("#greek-lab").screenshot(path=str(out / "greek_lab.png"))
        page.locator('[data-environment="imperative"]').click()
        page.locator('[data-greek-example="smg-imp"]').click()
        finish()
        assert "write(hearer, theme)" in page.locator("#semantics").inner_text()
        sentence("το ζουζουνίζει.")
        assert page.locator("#diagnosis-title").inner_text() == "Missing lexical entry"
        assert page.locator("#judgment-title").inner_text() == "Grammaticality not assessed"
        sentence("το τον ξέρω.")
        assert page.locator("#diagnosis-title").inner_text() == "No derivation · cause unassessed"
        assert page.locator("#judgment-title").inner_text() == "Grammaticality not assessed"
        sentence("τον")
        assert page.locator("#diagnosis-title").inner_text() == "Incomplete derivation"
        sentence("το γράφει.")
        assert page.locator("#result-status").inner_text() == "Complete derivation"
        assert page.locator("#judgment-title").inner_text() == "Grammaticality not assessed"
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("mltt")
        finish()
        with page.expect_response("**/api/parse/stream"):
            page.locator("#grammar").select_option("2026-english-mltt")
        finish()
        # Dialogue keeps one tree across turns and records real repair rollback.
        page.locator('[data-input-mode="dialogue"]').click()
        expect(page.locator("#dialogue-editor")).to_be_visible()
        page.locator('[data-dialogue-example="shared"]').click()
        finish()
        assert "like(john, mary)" in page.locator("#semantics").inner_text()
        assert page.locator(".transcript-turn").count() == 2
        page.locator('[data-dialogue-word="1"]').click()
        assert page.locator(".tree-node.pointed").get_attribute("data-node") == "010"
        assert "Turn 1 · A" in page.locator("#dialogue-now").inner_text()
        page.locator('[data-dialogue-word="2"]').click()
        assert "Turn 2 · B" in page.locator("#dialogue-now").inner_text()
        page.locator('[data-dialogue-example="other-repair"]').click()
        finish()
        assert "like(john, bill)" in page.locator("#semantics").inner_text()
        assert page.locator(".transcript-word.superseded").count() == 2
        assert "mary . → bill · B" in page.locator("#repair-history").inner_text()
        page.locator('[data-repair-step="before"]').click()
        assert "like(john, mary)" in page.locator("#semantics").inner_text()
        assert page.locator(".transcript-word.superseded").count() == 0
        page.locator('[data-repair-step="rollback"]').click()
        assert page.locator(".tree-node.pointed").get_attribute("data-node") == "010"
        assert "Restore the earlier tree" in page.locator("#operation-code").inner_text()
        assert "?Ty(object)" in page.locator('[data-node="010"] .node-type').text_content()
        page.screenshot(path=str(out / "dialogue_repair.png"), full_page=True)
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("classical")
        finish()
        assert "like(john, bill)" in page.locator("#semantics").inner_text()
        assert page.locator(".turn-text").last.input_value() == "sorry bill."
        page.locator('[data-dialogue-example="new-tree"]').click()
        finish()
        assert "like(john, mary)" in page.locator("#context-history").inner_text()
        assert "walk(bill)" in page.locator("#semantics").inner_text()
        page.locator("#context-history button").click()
        assert "like(john, mary)" in page.locator("#semantics").inner_text()
        # Missing repair context is not an unknown word or grammar judgment.
        page.locator('[data-dialogue-example="self-repair"]').click()
        finish()
        page.locator(".turn-text").fill("sorry bill.")
        page.locator("#parse-button").click()
        finish()
        assert page.locator("#diagnosis-title").inner_text() == "Missing repair context"
        assert page.locator("#judgment-title").inner_text() == "Grammaticality not assessed"
        page.locator('[data-dialogue-example="shared"]').click()
        finish()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(out / "dialogue_mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1120})
        with page.expect_response("**/api/parse/stream"):
            page.locator("#grammar").select_option("2026-cypriot-classical")
        finish()
        assert "not(know(speaker, him))" in page.locator("#semantics").inner_text()
        assert page.locator(".transcript-turn").count() == 2
        page.locator('[data-input-mode="sentence"]').click()
        with page.expect_response("**/api/parse/stream"):
            page.locator("#grammar").select_option("2026-english-classical")
        finish()
        with page.expect_response("**/api/parse/stream"):
            page.locator("#system").select_option("mltt")
        finish()
        page.get_by_role("button", name="Words", exact=True).click()
        page.get_by_role("button", name="Go to axiom", exact=True).click()
        assert page.locator(".tree-node").count() == 1
        page.get_by_role("button", name="Next step", exact=True).click()
        assert page.locator(".tree-node").count() > 1
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("tab", name="Node inspector").click()
        page.screenshot(path=str(out / "mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("#greek-lab").screenshot(path=str(out / "greek_mobile.png"))
        with page.expect_download() as info:
            page.locator("#export").click()
        data = json.loads(Path(info.value.path()).read_text())
        assert data["backend"] == "mltt" and data["complete"]
        assert not errors, errors
        for endpoint in ["/api/parse", "/api/parse/stream"]:
            response = context.request.post(
                options.url + endpoint, data={"sentence": "a", "grammar": "/tmp"}
            )
            assert response.status == 400
            response = context.request.post(
                options.url + endpoint,
                data={"sentence": "a", "grammar": "2015-english-ttr"},
                headers={"Origin": "https://example.com"},
            )
            assert response.status == 403
        browser.close()
    print(json.dumps({"browser": "passed", "console_errors": errors, "screenshots": str(out)}))


if __name__ == "__main__":
    main()
