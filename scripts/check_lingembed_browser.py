"""Exercise both local applications, origin-bound transfer, imports and encodings."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbench", default="http://127.0.0.1:8770")
    parser.add_argument("--viewer", default="http://127.0.0.1:8781/workbench.html")
    parser.add_argument("--output", type=Path, default=Path("build/lingembed/browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        errors = []
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        page = context.new_page()
        page.goto(args.workbench + "/experiments.html")
        expect(page.locator("#connection")).to_contain_text("workers ready")
        expect(page.locator("#open-lingembed")).to_be_visible()
        expect(page.locator("#open-lingembed")).to_be_disabled()
        page.get_by_text("LingEmbed connection", exact=True).click()
        page.fill("#lingembed-url", args.viewer)
        page.click("#run-pair")
        expect(page.locator("#run-status")).to_contain_text("Comparison ready", timeout=50000)
        cards = page.locator(".run-grid > article")
        assert cards.count() == 2
        expect(page.locator("#open-lingembed")).to_be_enabled()
        assert page.locator("#lingembed-analysis option").count() == 4
        assert "Target" in page.locator("#lingembed-analysis option:checked").inner_text()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        expect(page.locator("#open-lingembed")).to_be_visible()
        page.set_viewport_size({"width": 1440, "height": 1000})
        with page.expect_popup() as popup:
            page.click("#open-lingembed")
        viewer = popup.value
        expect(page.locator("#lingembed-status")).to_have_text("Analysis opened in LingEmbed.")
        expect(viewer.locator("#engine")).to_have_text("ds-english-v1")
        assert not viewer.url.split("#")[-1].startswith("bridge=")
        viewer.locator("#tokens button").last.click()
        expect(viewer.locator("#binding-result")).to_contain_text("Decoded node and edge records match")
        viewer.locator("#overlap").fill("1")
        expect(viewer.locator("#binding-result")).to_contain_text("Full record reconstruction fails")
        with viewer.expect_download() as download:
            viewer.click("#download-diagnostic")
        download.value.save_as(args.output / "encoding-check.json")
        diagnostic = json.loads((args.output / "encoding-check.json").read_text())
        assert diagnostic["binding"]["ties"] > 1
        assert diagnostic["geometry"]["maxError"] == 0
        viewer.locator("#overlap").fill("0")
        viewer.screenshot(path=str(args.output / "ds-desktop.png"), full_page=True)
        viewer.set_viewport_size({"width": 390, "height": 844})
        assert viewer.evaluate("document.documentElement.scrollWidth <= innerWidth")
        viewer.screenshot(path=str(args.output / "ds-mobile.png"), full_page=True)

        # File import is independent of the popup connection and needs no server-side write.
        with page.expect_download() as download:
            cards.nth(1).locator(".download-lingembed").last.click()
        download.value.save_as(args.output / "ccg-export.json")
        exported = json.loads((args.output / "ccg-export.json").read_text())
        viewer.locator("#import-file").set_input_files(args.output / "ccg-export.json")
        expect(viewer.locator("#engine")).to_have_text("ccg-incremental-v1")
        assert viewer.locator("#alternative option").count() == 2
        viewer.select_option("#alternative", "1")
        expect(viewer.locator("#node-detail")).to_contain_text(">T")
        viewer.click("#next")
        expect(viewer.locator("#prefix")).to_contain_text("token 2")
        viewer.screenshot(path=str(args.output / "ccg-mobile.png"), full_page=True)
        assert viewer.evaluate("document.documentElement.scrollWidth <= innerWidth")

        # A message from the same page, without the exact opener/channel, cannot replace the analysis.
        viewer.evaluate("window.postMessage({type:'lingembed:analysis',channel:'forged',analysis:{}},location.origin)")
        expect(viewer.locator("#engine")).to_have_text("ccg-incremental-v1")
        invalid = json.loads(json.dumps(exported))
        invalid["frames"][0]["observed"].append("future")
        viewer.locator("#import-file").set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": json.dumps(invalid).encode()})
        expect(viewer.locator("#import-status")).to_contain_text("Import rejected")
        expect(viewer.locator("#engine")).to_have_text("ccg-incremental-v1")

        # Strings from imports are displayed literally, including hostile markup.
        hostile = json.loads(json.dumps(exported))
        hostile["frames"][0]["structures"][0]["nodes"][0]["label"] = '<img src=x onerror="window.injected=true">'
        viewer.locator("#import-file").set_input_files({"name": "text.json", "mimeType": "application/json", "buffer": json.dumps(hostile).encode()})
        expect(viewer.locator("#node-detail")).to_contain_text("<img")
        assert not viewer.evaluate("Boolean(window.injected)")
        for example in ("ds-greek", "ccg-english", "ds-english"):
            viewer.click(f'[data-example="{example}"]')
            expected = "ds-greek-v1" if example == "ds-greek" else "ccg-incremental-v1" if example == "ccg-english" else "ds-english-v1"
            expect(viewer.locator("#engine")).to_have_text(expected)
        assert not errors, errors
        browser.close()
    print(json.dumps({"status": "passed", "checks": ["native DS popup transfer", "CCG file import", "prefix replay", "typed records", "geometry", "role interference", "mobile", "invalid import", "literal text rendering", "bundled examples"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
