"""Check alternative playback with actual parser output from an ambiguous fixture."""

import argparse
import json
from pathlib import Path
import subprocess

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
import json, shutil, sys, tempfile
from pathlib import Path
from dylan import workbench_api
with tempfile.TemporaryDirectory() as temp:
    grammar = Path(temp) / "grammar"
    shutil.copytree(Path("src/dynamicsyntax/grammars") / ("2026-english-" + sys.argv[1]), grammar)
    with (grammar / "lexicon.txt").open("a") as out:
        out.write("bank proper john human\nbank proper mary human\n")
    config = workbench_api.configuration()
    config["grammars"].append(str(grammar))
    workbench_api.configuration = lambda: config
    print(json.dumps(workbench_api.parse_request({"grammar": str(grammar), "sentence": "bank shouts.",
                                                "n_best": 3, "reading_traces": True})))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8771")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-readings-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = {backend: json.loads(subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-c", FIXTURE, backend], cwd=ROOT,
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout) for backend in ("mltt", "classical")}
    relative_results = {backend: json.loads(subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-c",
         "import json,sys; from dylan.workbench_api import parse_request; "
         "print(json.dumps(parse_request({'grammar': '2026-english-' + sys.argv[1], "
         "'sentence': 'a man who mary knows walks.'})))", backend],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    ).stdout) for backend in ("mltt", "classical")}
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))

        def fixture_response(route):
            payload = route.request.post_data_json
            if payload.get("sentence") != "bank shouts.":
                route.continue_()
                return
            assert payload["n_best"] == 3 and payload["reading_traces"]
            backend = payload["grammar"].rsplit("-", 1)[-1]
            result = results[backend]
            # Only the fixture response is intercepted; UI assets and ordinary
            # examples use the running server. No lexical provider is called.
            start = {"event": "start", "initial": result["words"][0],
                     "tokens": result["tokens"], "sentence": result["sentence"],
                     "grammar": result["grammar"], "lexical": result["lexical"]}
            route.fulfill(content_type="application/x-ndjson", body="\n".join(
                json.dumps(event) for event in (start, {"event": "result", "result": result})
            ) + "\n")

        page.route("**/api/parse/stream", fixture_response)
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#lexical-settings > summary").click()
        page.locator("#advanced-settings").evaluate("element => element.open = true")
        page.locator("#lexical-mode").select_option("off")
        page.locator("#lexical-settings > summary").click()
        for backend in ("mltt", "classical"):
            if page.locator("#system").input_value() != backend:
                page.locator("#system").select_option(backend)
                expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            assert page.locator("#examples button").filter(has_text="a man who mary knows walks.").count() == 1
            page.locator("#n-best").select_option("1")
            page.locator("#sentence").fill("a man who mary knows walks.")
            page.locator("#parse-button").click()
            relative = relative_results[backend]
            assert relative["complete"]
            expect(page.locator("#parse-button")).to_be_enabled()
            if page.get_by_role("button", name="Pause derivation", exact=True).count():
                page.get_by_role("button", name="Pause derivation", exact=True).click()
            anchor = "000" if backend == "mltt" else "0000"
            root = anchor + "L"
            frames = relative["operations"]
            gap_step = next(i for i, frame in enumerate(frames) if frame["pointer"] == root + "*")
            merge_step = next(i for i, frame in enumerate(frames) if frame.get("rule") == "merge-relative")
            timeline = page.locator("#timeline")
            timeline.evaluate("(node, value) => { node.value = value; node.dispatchEvent(new Event('input')); }", gap_step)
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == root + "*"
            assert page.locator(".tree-edge.link").count() == 1
            page.screenshot(path=str(args.output / f"{backend}-relative-gap.png"), full_page=True)
            timeline.evaluate("(node, value) => { node.value = value; node.dispatchEvent(new Event('input')); }", merge_step)
            expect(page.locator("#operation-code")).to_contain_text("merge(")
            assert page.locator(f'[data-node="{root}*"]').count() == 0
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == root + "10"
            page.get_by_role("tab", name="Action trace").click()
            page.locator("#action-list button").last.click()
            expect(page.locator("#semantics")).to_have_text(relative["words"][-1]["semantics"])
            if backend == "classical":
                assert page.locator('[data-node="0001"]').count() == 1
                assert page.locator('[data-node="0000"]').count() == 1
            subject = page.locator(f'[data-node="{root}0"]').bounding_box()
            predicate = page.locator(f'[data-node="{root}1"]').bounding_box()
            assert subject["x"] + subject["width"] <= predicate["x"]
            page.screenshot(path=str(args.output / f"{backend}-relative-complete.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.locator("#n-best").select_option("3")
            expect(page.locator("#parse-button")).to_be_enabled()
            # The bundled grammar also has a real ambiguity: attachment of the
            # adverb to the matrix predicate or inside the complement.
            page.locator("#sentence").fill("john thinks that mary walks quickly.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator("#reading option")).to_have_count(2)
            assert "LINK" in page.locator("#reading option").first.inner_text()
            page.get_by_role("tab", name="Action trace").click()
            page.locator("#action-list button").last.click()
            first_meaning = page.locator("#semantics").inner_text()
            page.locator("#reading").select_option("1")
            page.get_by_role("button", name="Pause derivation", exact=True).click()
            page.locator("#action-list button").last.click()
            assert page.locator("#semantics").inner_text() != first_meaning
            assert page.locator(".tree-edge.link").count() > 0
            page.screenshot(path=str(args.output / f"{backend}-attachment.png"), full_page=True)
            page.locator("#sentence").fill("bank shouts.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator("#reading option")).to_have_count(2)
            expect(page.locator("#readings-summary")).to_contain_text("exhausted")
            page.locator("#reading").select_option("1")
            expect(page.locator("#timeline")).to_have_value("0")
            assert page.locator(".tree-node").count() == 1
            page.get_by_role("button", name="Pause derivation", exact=True).click()
            page.get_by_role("button", name="Next step", exact=True).click()
            assert page.locator(".tree-node").count() == 2
            expect(page.locator("#operation-code")).to_contain_text("make(")
            page.get_by_role("button", name="Next step", exact=True).click()
            expect(page.locator("#pointer-transition")).to_contain_text("0 → 01")
            page.get_by_role("tab", name="Action trace").click()
            page.locator("#action-list button").last.click()
            expect(page.locator("#semantics")).to_have_text("shout(mary)")
            if backend == "mltt":
                with page.expect_download() as download:
                    page.locator("#coq").click()
                assert "mary" in Path(download.value.path()).read_text()
            page.screenshot(path=str(args.output / f"{backend}-alternative.png"), full_page=True)
            page.locator("#reading").select_option("0")
            page.get_by_role("button", name="Pause derivation", exact=True).click()
            page.locator("#action-list button").last.click()
            expect(page.locator("#semantics")).to_have_text("shout(john)")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output / f"{backend}-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.locator("#grammar").select_option(f"2026-smg-{backend}")
            expect(page.locator("#parse-button")).to_be_enabled()
            assert page.locator("#examples button").filter(has_text="ο γιώργος, τον ξέρω.").count() == 1
            page.locator("#sentence").fill("o γiorγos xtipise to γiani.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            expect(page.locator("#reading option")).to_have_count(3)
            page.locator("#action-list button").last.click()
            assert page.locator('[data-node="0B"]').count() == 0
            page.locator("#reading").select_option("2")
            page.get_by_role("button", name="Pause derivation", exact=True).click()
            page.get_by_role("button", name="Next step", exact=True).click()
            expect(page.locator("#operation-code")).to_contain_text("make(")
            assert page.locator('[data-node="0B"]').count() == 1
            page.get_by_role("button", name="Next step", exact=True).click()
            assert page.locator(".tree-node.pointed").get_attribute("data-node") == "0B"
            page.screenshot(path=str(args.output / f"{backend}-topic-pointer.png"), full_page=True)
            page.locator("#action-list button").last.click()
            expect(page.locator("#semantics")).to_have_text("hit(giorgos, giannis)")
            assert page.locator(".tree-edge.link").count() == 1
            topic = page.locator('[data-node="0B"]').bounding_box()
            clause = page.locator('[data-node="0"]').bounding_box()
            assert topic["y"] < clause["y"]  # LINK runs from topic to clause.
            page.screenshot(path=str(args.output / f"{backend}-topic-complete.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(args.output / f"{backend}-topic-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1100})
        assert not errors, errors
        browser.close()
    print("Alternative playback, pointer movement, Coq export and mobile layout passed in both modes.")


if __name__ == "__main__":
    main()
