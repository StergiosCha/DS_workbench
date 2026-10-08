"""Real BYOK browser checks; saves results/screenshots, never credentials."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from check_openrouter_browser import ready, connect, assert_private, load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8793")
parser.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-greek-evidence-browser"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
load_environment()
key = os.environ["OPENROUTER_API_KEY"]
expect.set_options(timeout=60000)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    ready(page, args.url)
    page.locator("#system").select_option("classical")
    page.locator("#grammar").select_option("2026-smg-classical")
    expect(page.locator("#greek-source-controls")).to_be_visible()
    expect(page.locator("#live-greek-sources")).to_be_disabled()
    expect(page.locator("#live-greek-sources")).not_to_be_checked()
    connect(page, key)
    page.locator("#openrouter-model").select_option(args.model)
    expect(page.locator("#live-greek-sources")).to_be_enabled()
    page.locator("#live-greek-sources").check()
    for backend in ("classical", "mltt"):
        page.locator("#system").select_option(backend)
        page.locator("#grammar").select_option("2026-smg-" + backend)
        page.locator("#lexical-mode").select_option("assisted")
        if backend == "mltt":
            page.locator('[data-input-mode="paragraph"]').click()
            page.locator("#paragraph").fill("Η ερευνήτρια περίμενε. Η Μαρία είναι εδώ.")
        else:
            page.locator("#sentence").fill("Η ερευνήτρια περίμενε.")
        with page.expect_request("**/api/parse/stream") as pending:
            page.locator("#parse-button").click()
        request = pending.value
        assert request.post_data_json["live_greek_sources"] is True
        assert request.post_data_json["greek_source_corpus"] == "ud_ud_greek-gud"
        assert request.headers.get("authorization") == f"Bearer {key}", "Missing BYOK credential"
        expect(page.locator("#parse-button")).to_be_enabled()
        result = page.evaluate("state.result")
        if backend == "mltt":
            paragraph = page.evaluate("state.paragraph")
            assert all(s["complete"] for s in paragraph["sentences"])
            (args.output / "paragraph.json").write_text(json.dumps(paragraph, ensure_ascii=False))
        serialized = json.dumps(result, ensure_ascii=False)
        assert key not in serialized
        (args.output / f"{backend}.json").write_text(serialized)
        assert result["complete"], (result["failure"], result["lexical"]["notices"])
        sources = result["lexical"]["live_sources"]
        assert {i["source"] for i in sources["items"]} == {"Svarna", "Triantafyllidis"}
        assert any(e.get("evidence_ids") for e in result["lexical"]["entries"] if e["source"] == "model")
        expect(page.locator("#live-source-report")).to_be_visible()
        page.locator("#live-source-words details").evaluate_all("nodes => nodes.forEach(node => node.open = true)")
        expect(page.locator("#live-source-words")).to_contain_text("Retrieved observations")
        expect(page.locator("#live-source-words")).to_contain_text("Model inferences")
        assert page.locator("#live-source-words blockquote").count() == len(sources["items"])
        page.locator("#live-source-report").screenshot(path=str(args.output / f"{backend}-evidence.png"))
        with page.expect_download() as download:
            page.locator("#export").click()
        exported = Path(download.value.path()).read_text()
        assert key not in exported and "evidence_ids" in exported and "live_sources" in exported
        print(json.dumps({"backend": backend, "complete": True, "observations": len(sources["items"]),
                          "model_calls": len(result["lexical"]["attempts"]), "elapsed_ms": paragraph["elapsed_ms"] if backend == "mltt" else result["elapsed_ms"]}), flush=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Mobile overflow"
    page.locator("#use-dictionaries").click()
    page.locator('[data-input-mode="sentence"]').click()
    expect(page.locator("#live-greek-sources")).to_be_disabled()
    page.locator("#sentence").fill("Η Μαρία είναι εδώ.")
    with page.expect_request("**/api/parse/stream") as pending:
        page.locator("#parse-button").click()
    assert not pending.value.post_data_json.get("live_greek_sources")
    assert "authorization" not in pending.value.headers
    expect(page.locator("#parse-button")).to_be_enabled()
    assert page.evaluate("state.result.complete")
    expect(page.locator("#live-source-report")).to_be_hidden()
    assert_private(page, key)
    assert not errors, errors
    browser.close()
