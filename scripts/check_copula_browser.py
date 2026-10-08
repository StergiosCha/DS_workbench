"""Verify the reported first-person copula sentence through the real browser API."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8775")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-copula-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=40000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#lexical-settings").evaluate("element => element.open = true")
            page.locator("#advanced-settings").evaluate("element => element.open = true")
            page.locator("#lexical-mode").select_option("dictionary")
            page.locator("#sentence").fill("I am an asshole")
            with page.expect_request("**/api/parse/stream") as pending:
                page.locator("#parse-button").click()
            assert "authorization" not in pending.value.headers
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"] and result["failure"] is None
            assert result["grammar"] == f"2026-english-{backend}"
            assert "asshole_n09815188" in result["words"][-1]["normalized"]
            assert all(token["known"] for token in result["diagnostics"]["lexical_coverage"])
            expect(page.locator("#lexical-entries")).to_contain_text("WordNet")
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported["complete"] and exported["sentence"] == "I am an asshole"
            (args.output / f"{backend}-result.json").write_text(
                json.dumps(exported, ensure_ascii=False, indent=2)
            )
            page.locator("#lexical-report").screenshot(
                path=str(args.output / f"{backend}-vocabulary.png")
            )
            print(
                json.dumps(
                    {
                        "backend": backend,
                        "complete": result["complete"],
                        "meaning": result["words"][-1]["normalized"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            page.locator("#grammar").select_option(f"2026-smg-{backend}")
            expect(page.locator("#lexical-mode")).to_have_value("corpus")
            page.locator("#sentence").fill("Είμαι πολύ μαλάκας")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            assert page.evaluate("state.result.complete")
            page.locator('[data-input-mode="paragraph"]').click()
            expect(page.locator("#paragraph-baseline")).to_contain_text("0/6 English paragraphs")
            greek = "Η επιτροπή εγκρίνει την πρόταση. Εγώ σε ξέρω. Διαβάζω το βιβλίο."
            page.locator("#paragraph").fill(greek)
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            paragraph = page.evaluate("state.paragraph")
            assert paragraph["complete"] and paragraph["coverage"]["complete"] == 3, paragraph["coverage"]
            expect(page.locator("#paragraph-summary")).to_contain_text("3 / 3")
            page.locator('[data-sentence-index="2"]').click()
            assert page.evaluate("state.result.sentence") == "Διαβάζω το βιβλίο."
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = json.loads(Path(download.value.path()).read_text())
            assert exported["kind"] == "paragraph" and exported["paragraph"] == greek
            if backend == "mltt":
                with page.expect_download() as download:
                    page.locator("#coq").click()
                assert "Definition meaning" in Path(download.value.path()).read_text()
            page.locator("#grammar").select_option(f"2026-english-{backend}")
            page.locator("#paragraph").fill("John walks. Glorp. He knows Mary.")
            page.locator("#parse-button").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            paragraph = page.evaluate("state.paragraph")
            assert not paragraph["complete"] and paragraph["coverage"]["complete"] == 2
            expect(page.locator("#paragraph-summary")).to_contain_text("2 / 3")
            page.locator('[data-sentence-index="2"]').click()
            assert page.evaluate("state.result.words.at(-1).normalized") == "know(john, mary)"
            expect(page.locator("#paragraph-sentences")).to_contain_text("Context excludes failed sentence 2")
            page.locator("#paragraph-results").screenshot(path=str(args.output / f"{backend}-paragraph.png"))
            page.locator('[data-input-mode="sentence"]').click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-input-mode="paragraph"]').click()
        page.locator("#lexical-settings").evaluate("element => element.open = false")
        page.locator(".composer").screenshot(path=str(args.output / "mobile-composer.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    main()
