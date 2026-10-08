"""Exercise BYOK in a real browser; --live makes two small billed vocabulary calls.

Credentials are read from the existing local environment, never printed or saved.
Browser traces/network archives are deliberately not recorded.
"""

import argparse
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dylan.workbench_environment import load_environment  # noqa: E402


def ready(page, url):
    page.goto(url)
    expect(page.locator("#parse-button")).to_be_enabled(timeout=60000)
    page.locator("#lexical-settings").evaluate("element => element.open = true")
    page.locator("#advanced-settings").evaluate("element => element.open = true")
    expect(page.locator("#openrouter-panel")).to_be_visible()


def connect(page, key):
    page.locator("#openrouter-key").fill(key)
    page.locator("#openrouter-connect").click()
    expect(page.locator("#openrouter-badge")).to_have_text("Connected", timeout=35000)
    expect(page.locator("#openrouter-key")).to_have_value("")


def assert_private(page, key):
    exposed = page.evaluate("""() => JSON.stringify({
        local: {...localStorage}, session: {...sessionStorage}, state,
        html: document.documentElement.outerHTML, cookies: document.cookie
    })""")
    assert key not in exposed, "Credential appeared in browser state, storage or DOM"


def analyse(page, sentence, model, key, output):
    page.locator("#openrouter-model").select_option(model)
    page.locator("#lexical-mode").select_option("model")
    page.locator("#sentence").fill(sentence)
    with page.expect_request("**/api/parse/stream") as pending:
        page.locator("#parse-button").click()
    request = pending.value
    assert request.headers.get("authorization") == f"Bearer {key}", "Missing per-request credential"
    assert key not in request.url and key not in request.post_data, (
        "Credential leaked into URL or body"
    )
    assert request.post_data_json["openrouter_model"] == model
    expect(page.locator("#parse-button")).to_be_enabled(timeout=45000)
    with page.expect_download() as download:
        page.locator("#export").click()
    text = Path(download.value.path()).read_text()
    assert key not in text, "Credential appeared in export"
    result = json.loads(text)
    assert result.get("complete"), "The native DS derivation did not complete"
    assert_private(page, key)
    output.write_text(text)
    return result


def fixtures(browser, args):
    context = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    data = {
        "connected": True,
        "models": [
            {
                "id": "fixture/alpha",
                "name": "Alpha",
                "input_per_million": 0.4,
                "output_per_million": 1.6,
            },
            {"id": "fixture/beta", "name": "Beta", "input_per_million": 0, "output_per_million": 0},
        ],
        "default_model": "fixture/alpha",
        "jev": {"available": True, "model": "typesafe/jev-1.13-20260917", "name": "Jev 1.13"},
    }
    ready(page, args.url)
    expect(page.locator('#lexical-mode option[value="model"]')).to_be_disabled()
    page.route(
        "**/api/openrouter/connect",
        lambda route: route.fulfill(status=401, json={"error": "OpenRouter rejected this key."}),
    )
    page.locator("#openrouter-key").fill("fixture-invalid-secret")
    page.locator("#openrouter-connect").click()
    expect(page.locator("#openrouter-status")).to_contain_text("rejected")
    expect(page.locator('#lexical-mode option[value="model"]')).to_be_disabled()
    page.unroute("**/api/openrouter/connect")
    page.route("**/api/openrouter/connect", lambda route: route.fulfill(json=data))
    key = "fixture-visitor-secret"
    connect(page, key)
    expect(page.locator("#openrouter-price")).to_contain_text("$0.4 input / $1.6 output")
    expect(page.locator('#lexical-mode option[value="jev"]')).to_be_enabled()
    page.locator("#openrouter-filter").fill("Beta")
    page.locator("#openrouter-model").select_option("fixture/beta")
    expect(page.locator("#openrouter-price")).to_contain_text("$0 input / $0 output")
    analyse(page, "john likes mary.", "fixture/beta", key, args.output / "fixture-export.json")
    page.locator("#openrouter-panel").screenshot(path=str(args.output / "connection-desktop.png"))

    # A second tab does not inherit the first tab's connection.
    second = context.new_page()
    ready(second, args.url)
    expect(second.locator("#openrouter-badge")).to_have_text("Not connected")
    expect(second.locator('#lexical-mode option[value="model"]')).to_be_disabled()
    second.close()
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#openrouter-panel").scroll_into_view_if_needed()
    page.locator("#openrouter-panel").screenshot(path=str(args.output / "connection-mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
        "Mobile page overflows horizontally"
    )
    page.locator("#openrouter-disconnect").click()
    expect(page.locator("#openrouter-badge")).to_have_text("Not connected")
    expect(page.locator('#lexical-mode option[value="model"]')).to_be_disabled()
    assert page.locator("#lexical-mode").input_value() not in {"model", "jev"}
    assert_private(page, key)
    connect(page, key)
    page.reload()
    expect(page.locator("#parse-button")).to_be_enabled(timeout=45000)
    expect(page.locator("#openrouter-badge")).to_have_text("Not connected")
    expect(page.locator('#lexical-mode option[value="model"]')).to_be_disabled()
    assert_private(page, key)
    assert not errors, "Browser JavaScript raised an error"
    context.close()
    print(
        "Browser fixtures passed: key errors, model choice, per-request auth, exports, tab isolation, disconnect, refresh, mobile.",
        flush=True,
    )


def live(browser, args):
    load_environment()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit(
            "Live check requires OPENROUTER_API_KEY in the existing local environment."
        )
    context = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = context.new_page()
    ready(page, args.url)
    connect(page, key)
    print(page.locator("#openrouter-status").inner_text(), flush=True)
    results = []
    for index, model in enumerate(("openai/gpt-4.1-mini", "deepseek/deepseek-v4.1-flash")):
        result = analyse(
            page, "john sneezes.", model, key, args.output / f"live-model-{index}.json"
        )
        entries = result["lexical"]["entries"]
        assert any(
            entry["surface"] == "sneezes" and entry["source"] == "model" for entry in entries
        ), "No actual model proposal was installed"
        assert model in json.dumps(result["lexical"]), "Selected model provenance was not recorded"
        results.append(
            {
                "model": model,
                "complete": result["complete"],
                "status": result["lexical"]["status"],
                "elapsed_ms": result["elapsed_ms"],
            }
        )
        print(json.dumps(results[-1]), flush=True)
    page.locator("#openrouter-panel").screenshot(path=str(args.output / "live-connected.png"))
    page.locator("#openrouter-disconnect").click()
    assert_private(page, key)
    context.close()
    (args.output / "live-summary.json").write_text(json.dumps(results, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8775")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-openrouter-browser"))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expect.set_options(timeout=20000)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        fixtures(browser, args)
        if args.live:
            live(browser, args)
        browser.close()


if __name__ == "__main__":
    main()
