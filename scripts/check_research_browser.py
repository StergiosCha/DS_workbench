"""Exercise corpus/dictionary lookup, real DS transfer, provenance and mobile layout."""

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright


def check_english(page, args):
    """Use the installed indexes and the real parser, without source fixtures."""
    page.locator("#research-language").select_option("en")
    expect(page.locator("#corpus-catalog-status")).to_contain_text("500 documents")
    page.locator("#corpus-search").click()
    expect(page.locator(".corpus-result")).to_have_count(20)
    first = page.evaluate("research.result.results[0]")
    assert first["metadata"]["tagged_source"]
    page.locator("#corpus-next").click()
    expect(page.locator("#corpus-page")).to_have_text("21–40")
    assert page.evaluate("research.result.results[0].fingerprint") != first["fingerprint"]
    page.locator("#corpus-previous").click()
    expect(page.locator("#corpus-page")).to_have_text("1–20")
    with page.expect_download() as pending:
        page.locator("#corpus-export").click()
    exported = json.loads(Path(pending.value.path()).read_text())
    assert exported["source"] == "Brown corpus" and exported["archive_sha256"]
    assert exported["results"][0]["metadata"]["line"]

    page.locator("#dictionary-search").click()
    expect(page.locator("#dictionary-status")).to_have_text("18 of 18 senses shown.")
    expect(page.locator(".dictionary-entry")).to_have_count(18)
    page.locator("#dictionary-query").fill("lends")
    page.locator("#dictionary-search").click()
    expect(page.locator("#dictionary-status")).to_have_text("3 of 3 senses shown.")
    assert page.locator(".wordnet-frames li").count() > 0
    assert "lend" in page.locator(".dictionary-entry summary").first.inner_text()
    page.locator("#dictionary-scope").select_option("entry")
    page.locator("#dictionary-query").fill("sloping land")
    page.locator("#dictionary-search").click()
    expect(page.locator(".dictionary-entry")).to_have_count(1)
    expect(page.locator(".dictionary-entry summary")).to_contain_text("bank")

    page.locator(".corpus-result").first.get_by_role("button", name="Select example →").click()
    expect(page.locator("#selected-corpus-grammar")).to_have_value("english")
    original = page.locator("#selected-corpus-text").input_value()
    passage_url = page.evaluate("research.selected.source_url")
    passage = page.request.get(args.url + passage_url).json()
    assert passage["observation"]["full_text"] == original
    # Explicit editing exercises successful analysis while preserving corpus evidence.
    page.locator("#selected-corpus-text").fill("john likes mary.")
    for backend in ("mltt", "classical", "ttr"):
        page.locator("#selected-corpus-system").select_option(backend)
        expected = "2015-english-ttr" if backend == "ttr" else f"2026-english-{backend}"
        page.locator("#selected-corpus-analyse").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        result = page.evaluate("state.result")
        assert result["complete"], result.get("failure")
        assert result["research_source"]["comparison_grammar"] == expected
        assert result["research_source"]["observation"]["full_text"] == original
        assert result["research_source"]["edited"]
        assert page.locator("#decision-mode").input_value() == "off"
        assert page.locator("#lexical-mode").input_value() != "model"
    with page.expect_download() as pending:
        page.locator("#export").click()
    result = json.loads(Path(pending.value.path()).read_text())
    assert result["research_source"]["comparison_grammar"] == "2015-english-ttr"
    (args.output / "english-ttr-observation.json").write_text(
        json.dumps(result["research_source"], indent=2)
    )
    # Reparse under a manually changed grammar: record the actual comparison.
    page.locator("#system").select_option("classical")
    page.locator("#grammar").select_option("2026-english-classical")
    page.locator("#sentence").fill("john likes mary.")
    page.locator("#parse-button").click()
    expect(page.locator("#parse-button")).to_be_enabled()
    assert (
        page.evaluate("state.result.research_source.comparison_grammar") == "2026-english-classical"
    )

    page.locator("#corpus-register").select_option("news")
    page.locator("#corpus-kind").select_option("regex")
    page.locator("#corpus-query").fill(r"\bbank\b")
    page.locator("#corpus-search").click()
    expect(page.locator("#corpus-search")).to_be_enabled()
    results = page.evaluate("research.result.results")
    assert results and all(row["register"] == "news" for row in results)

    page.locator("#corpus-db").select_option("gutenberg")
    expect(page.locator("#corpus-catalog-status")).to_contain_text("18 documents")
    page.locator("#corpus-filter").select_option("austen-emma.txt")
    page.locator("#corpus-kind").select_option("words")
    page.locator("#corpus-query").fill("Emma")
    page.locator("#corpus-search").click()
    expect(page.locator(".corpus-result")).to_have_count(20)
    row = page.evaluate("research.result.results[0]")
    assert row["metadata"]["end"] > row["metadata"]["start"]
    assert row["metadata"]["encoding"] == "latin-1"
    assert row["metadata"]["sentence_model"]["punkt_parameters"]
    page.locator("#dictionary-query").fill("bank")
    page.locator("#dictionary-scope").select_option("headword")
    page.locator("#dictionary-search").click()
    expect(page.locator(".dictionary-entry")).to_have_count(18)
    page.locator(".dictionary-entry summary").first.click()
    page.locator("#research").screenshot(path=str(args.output / "english-corpus-dictionary.png"))

    # A language change clears the old source's results and comparison controls.
    page.locator("#research-language").select_option("el")
    expect(page.locator("#dictionary-title")).to_have_text("Triantafyllidis dictionary")
    expect(page.locator(".corpus-result")).to_have_count(0)
    expect(page.locator("#research-selection")).to_be_hidden()
    page.locator("#research-language").select_option("en")
    expect(page.locator("#corpus-catalog-status")).to_contain_text("500 documents")
    page.locator("#corpus-search").click()
    expect(page.locator(".corpus-result")).to_have_count(20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8773")
    parser.add_argument("--live", action="store_true", help="Also query the real public sources")
    parser.add_argument(
        "--english", action="store_true", help="Also check installed Brown/Gutenberg and WordNet"
    )
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-research-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(40000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        row = {
            "full_text": "ιξέρω τον.",
            "corpus": "grdd_cypriot",
            "register": "dialectal",
            "mode": "written",
            "year": "",
            "metadata": '{"dialect":"Cypriot"}',
            "fingerprint": "fixture",
        }

        def sources(route):
            url = urlsplit(route.request.url)
            params = parse_qs(url.query)
            path = url.path.rsplit("/", 1)[-1]
            status = 200
            if path == "corpora":
                data = {
                    "db": params["db"][0],
                    "stats": [
                        {"corpus": c, "register": "dialectal", "mode": "written"}
                        for c in ("grdd_cypriot", "grdd_pontic", "grdd_cretan")
                    ],
                }
            elif path == "dictionary":
                q = params["q"][0]
                if q == "error":
                    status, data = 502, {"error": "Dictionary temporarily unavailable."}
                else:
                    entries = (
                        []
                        if q == "unknown"
                        else [
                            {
                                "headword": "λέξη",
                                "text": "<img src=x onerror=alert(1)> A quoted source string.",
                                "url": "https://www.greek-language.gr/#1_42",
                            }
                        ]
                    )
                    data = {
                        "entries": entries,
                        "total": len(entries),
                        "has_more": False,
                        "attribution": "Dictionary fixture",
                        "note": "Published entry text.",
                    }
            else:
                q, offset = params["q"][0], int(params.get("offset", [0])[0])
                if q == "error":
                    status, data = 502, {"error": "Svarna temporarily unavailable."}
                else:
                    results = (
                        []
                        if q == "empty"
                        else [{**row, "corpus": params.get("corpus", [row["corpus"]])[0]}]
                    )
                    data = {
                        "source": "Svarna",
                        "source_url": "https://greek-corpus-workbench.wonderfulhill-e1c9f1a0.westeurope.azurecontainerapps.io/api/search?q=test",
                        "fetched_at": "2026-10-01T00:00:00Z",
                        "db": "dialectal",
                        "query": q,
                        "kind": params.get("kind", ["words"])[0],
                        "filters": {},
                        "results": results,
                        "total": 21 if results else 0,
                        "offset": offset,
                        "limit": 20,
                        "total_is_exact": True,
                        "has_more": offset == 0 and bool(results),
                        "note": "Matching sentences.",
                    }
            route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

        page.route("**/api/research/**", sources)
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.locator("#research").scroll_into_view_if_needed()
        expect(page.locator("#corpus-filter")).to_be_enabled()
        page.locator("#corpus-filter").select_option("grdd_cypriot")
        page.locator("#corpus-search").click()
        expect(page.locator(".corpus-result")).to_have_count(1)
        page.locator("#corpus-next").click()
        expect(page.locator("#corpus-page")).to_have_text("21–21")
        page.locator("#corpus-previous").click()
        expect(page.locator("#corpus-page")).to_have_text("1–1")
        # A selected corpus word becomes an explicit dictionary query.
        page.locator(".corpus-text").evaluate(
            "node => { const range = document.createRange(); range.selectNodeContents(node); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); }"
        )
        page.get_by_role("button", name="Look up selected word", exact=True).click()
        expect(page.locator("#dictionary-query")).to_have_value(row["full_text"])
        expect(page.locator(".dictionary-entry")).to_have_count(1)
        page.get_by_role("button", name="Select example →", exact=True).click()
        expect(page.locator("#selected-corpus-grammar")).to_have_value("cypriot")

        for backend in ("mltt", "classical"):
            page.locator("#selected-corpus-system").select_option(backend)
            page.locator("#selected-corpus-analyse").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["complete"], result.get("failure")
            assert result["research_source"]["observation"]["full_text"] == row["full_text"]
            assert result["research_source"]["comparison_grammar"] == f"2026-cypriot-{backend}"
            assert not result["research_source"]["edited"]
            expect(page.locator("#research-provenance")).to_contain_text("original text")

        page.locator("#selected-corpus-text").fill("εν τον ιξέρω.")
        page.locator("#selected-corpus-analyse").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        with page.expect_download() as pending:
            page.locator("#export").click()
        downloaded = json.loads(Path(pending.value.path()).read_text())
        assert downloaded["research_source"]["edited"]
        assert downloaded["research_source"]["observation"]["full_text"] == row["full_text"]
        page.locator("#selected-corpus-text").fill("λέξη " * 45)
        expect(page.locator("#selected-corpus-analyse")).to_be_disabled()
        page.locator("#selected-corpus-reset").click()
        expect(page.locator("#selected-corpus-text")).to_have_value(row["full_text"])

        page.locator("#corpus-filter").select_option("grdd_cretan")
        page.locator("#corpus-search").click()
        expect(page.locator(".corpus-result")).to_have_count(1)
        page.get_by_role("button", name="Select example →", exact=True).click()
        expect(page.locator("#selected-corpus-grammar")).to_have_value("")
        expect(page.locator("#selected-corpus-analyse")).to_be_disabled()

        for query, expected in [("empty", "No matching"), ("error", "temporarily unavailable")]:
            page.locator("#corpus-query").fill(query)
            page.locator("#corpus-search").click()
            expect(page.locator("#corpus-status")).to_contain_text(expected)
            expect(page.locator(".corpus-result")).to_have_count(0)

        page.locator("#dictionary-search").click()
        expect(page.locator(".dictionary-entry")).to_have_count(1)
        expect(page.locator(".dictionary-text")).to_contain_text("<img src=x")
        assert page.locator("#dictionary-results img").count() == 0
        for query, expected in [
            ("unknown", "No entry found"),
            ("error", "temporarily unavailable"),
        ]:
            page.locator("#dictionary-query").fill(query)
            page.locator("#dictionary-search").click()
            expect(page.locator("#dictionary-status")).to_contain_text(expected)

        # A new manually entered sentence must not inherit an unrelated source.
        page.locator("#sentence").fill("εν τον ιξέρω")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert "research_source" not in page.evaluate("state.result")
        expect(page.locator("#research-provenance")).to_be_hidden()

        if args.live:
            page.unroute("**/api/research/**", sources)
            page.reload()
            expect(page.locator("#parse-button")).to_be_enabled()
            page.locator("#research").scroll_into_view_if_needed()
            expect(page.locator("#corpus-filter")).to_be_enabled()
            page.locator("#corpus-filter").select_option("grdd_pontic")
            page.locator("#corpus-search").click()
            expect(page.locator(".corpus-result").first).to_be_visible()
            page.locator("#dictionary-search").click()
            expect(page.locator(".dictionary-entry")).to_have_count(1)
            expect(page.locator(".dictionary-entry summary")).to_have_text("δίνω")
            page.locator(".corpus-result").first.get_by_role(
                "button", name="Select example →"
            ).click()
            page.evaluate("stop()")
            page.locator("#research").screenshot(
                path=str(args.output / "live-corpus-dictionary.png")
            )
            # Check genuine source transfer even when the fragment cannot parse it.
            page.locator("#selected-corpus-analyse").click()
            expect(page.locator("#parse-button")).to_be_enabled()
            result = page.evaluate("state.result")
            assert result["research_source"]["source"] == "Svarna"
            assert result["sentence"] == result["research_source"]["analysed_text"]
            (args.output / "live-observation.json").write_text(
                json.dumps(
                    {
                        "source": result["research_source"],
                        "complete": result["complete"],
                        "failure": result.get("failure"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        if args.english:
            page.unroute("**/api/research/**", sources)
            check_english(page, args)

        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#research").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("#research").screenshot(path=str(args.output / "mobile-research.png"))
        assert not errors, errors
        browser.close()
    print(
        "Corpus/dictionary UI, DS transfer, provenance/export, source errors and mobile layout passed."
    )


if __name__ == "__main__":
    main()
