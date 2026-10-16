"""Real DS checks/reuse of an edited fixture proposal; no model calls."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8812")
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("/tmp/ds-workshop-browser"))
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    fixture = json.loads(a.fixture.read_text())
    expect.set_options(timeout=50000)
    errors = []
    requests = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))

        def seen(r):
            if "/api/parse" in r.url:
                assert "authorization" not in r.headers
                requests.append(r.post_data_json)

        page.on("request", seen)
        page.goto(a.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        page.evaluate('(result)=>receiveEvent({event:"result",result})', fixture)
        page.locator("#experimental-attempts > details > summary").first.click()
        page.get_by_role("button", name="Edit & keep rules").click()
        expect(page.locator("#grammar-workshop")).to_be_visible()
        page.locator("#pack-name").fill("Eyewear with user fixes")
        page.locator("#pack-notes").fill(
            "Reviewed fixture: change an equipment relation; no wearing inference."
        )
        page.locator("#pack-add-negative").click()
        page.locator("#pack-tests fieldset").last.locator("textarea").first.fill(
            "John walks with with glasses."
        )
        # A real user edit: change the relation symbol in declaration and action.
        declarations = page.locator("#pack-declarations fieldset")
        page.locator("#pack-declarations").locator("..").locator("summary").click()
        declarations.last.locator("input").first.fill("with_accessory")
        action = page.locator("#pack-rules fieldset").last.locator("textarea").last
        action.fill(action.input_value().replace("with_equipment", "with_accessory"))
        meaning = page.locator("#pack-tests fieldset").first.locator("textarea").last
        meaning.fill(meaning.input_value().replace("with_equipment", "with_accessory"))
        page.locator("#pack-check").click()
        expect(page.locator("#pack-check")).to_be_enabled()
        expect(page.locator("#pack-status")).to_contain_text("2/2 examples matched")
        assert requests[-1]["grammar_pack_check"] and requests[-1]["allow_model_fallback"] is False
        page.locator("#pack-save").click()
        expect(page.locator("#pack-status")).to_contain_text("Saved on this device")
        with page.expect_download() as d:
            page.locator("#pack-export").click()
        exported = json.loads(Path(d.value.path()).read_text())
        assert exported["check_report"]["all_matched"]
        assert "with_accessory" in json.dumps(exported["pack"])
        Path(a.output / "contribution.json").write_text(
            json.dumps(exported, ensure_ascii=False, indent=2) + "\n"
        )
        page.locator("#workshop-close").click()
        page.locator("#personal-enabled").check()
        page.locator("#sentence").fill("John walks with glasses.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#personal-report")).to_be_visible()
        expect(page.locator("#meaning-title")).to_contain_text("personal grammar")
        assert page.evaluate(
            'state.result.complete && state.result.words.at(-1).normalized.includes("with_accessory")'
        )
        expect(page.locator("#method-usage")).to_contain_text("Analysis LLM · off")
        assert requests[-1]["grammar_pack"]["name"] == "Eyewear with user fixes"
        page.reload()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#personal-enabled")).not_to_be_checked()
        page.locator("#personal-pack").select_option("0")
        page.locator("#personal-enabled").check()
        page.locator("#sentence").fill("Mary walks with glasses.")
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("state.result.complete")
        page.locator("#personal-enabled").uncheck()
        page.locator("#parse-button").click()
        expect(page.locator("#parse-button")).to_be_enabled()
        assert page.evaluate("!state.result.complete && !state.result.personal_grammar")
        page.locator("#grammar-workshop-open").click()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        assert page.locator("#grammar-workshop").evaluate("n=>n.scrollWidth<=n.clientWidth+1")
        page.locator("#grammar-workshop").screenshot(path=str(a.output / "mobile-workshop.png"))
        # A stale expected meaning must prevent a passing report after an edit.
        page.locator("#pack-tests fieldset").first.locator("textarea").last.fill("wrong meaning")
        page.locator("#pack-check").click()
        expect(page.locator("#pack-check")).to_be_enabled()
        expect(page.locator("#pack-status")).to_contain_text("1/2 examples matched")
        page.locator("#pack-delete").click()
        page.locator("#workshop-close").click()
        page.reload()
        expect(page.locator("#parse-button")).to_be_enabled()
        expect(page.locator("#personal-pack")).to_be_hidden()
        assert not errors, errors
        browser.close()
    (a.output / "checks.json").write_text(
        json.dumps(
            {
                "checks": [
                    "edit rules and declarations",
                    "positive/negative checks with real DS",
                    "persist and reuse after refresh",
                    "reuse on another sentence without a model",
                    "disable restores original grammar",
                    "export contribution with evidence",
                    "changed expectations invalidate a passing report",
                    "remove saved copy",
                    "mobile layout",
                ],
                "errors": errors,
            },
            indent=2,
        )
        + "\n"
    )
    print("9 grammar-workshop browser checks passed; no model calls.")


if __name__ == "__main__":
    main()
