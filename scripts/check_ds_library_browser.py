"""Check offline DS-library filtering, evidence boundaries and layout."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "docs/research/library"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-library-browser"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    papers = json.loads((LIBRARY / "papers.json").read_text())["papers"]
    discovery = json.loads((LIBRARY / "discovery.json").read_text())["candidates"]
    checks = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, network = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: network.append(request.url) if request.url.startswith(("https:", "http:")) else None)
        page.goto((LIBRARY / "index.html").as_uri())
        expect(page.locator("#papers article")).to_have_count(len(papers))
        checks.append("All selected works load from a local file without a server")
        page.screenshot(path=str(args.output / "desktop.png"))
        page.locator("#search").fill("PCC")
        expect(page.locator("#papers article")).to_have_count(2)
        page.locator("#C10 .related > summary").click()
        pcc_card = page.locator('#C10 [data-analysis="smg-pcc-acc12"]')
        expect(pcc_card).to_contain_text("του με έδωσε")
        expect(pcc_card).to_contain_text("No equivalent Greek dialect suite")
        expect(pcc_card).to_contain_text("User-supplied regression, not a source quotation")
        checks.append("PCC search exposes precise source cards and separate backend/example status")
        page.locator("#clear").click()
        page.locator("#category").select_option("C09")
        page.locator("#framework").select_option("classical")
        page.locator("#language").select_option("Standard Modern Greek")
        matching = [p for p in papers if "C09" in p["tags"]["categories"]
                    and "classical" in p["tags"]["frameworks"]
                    and "Standard Modern Greek" in p["tags"]["languages"]]
        expect(page.locator("#papers article")).to_have_count(len(matching))
        expect(page.locator("#C10")).to_be_visible()
        expect(page.locator("#CK11")).to_be_visible()
        checks.append("Topic, semantic framework and variety filters combine")
        page.locator("#clear").click()
        page.locator("#framework").select_option("constructive")
        expect(page.locator("#papers article")).to_have_count(1)
        expect(page.locator("#C25")).to_be_visible()
        page.locator("#clear").click()
        page.locator("#framework").select_option("ttr")
        expect(page.locator("#ECH13")).to_be_visible()
        expect(page.locator("#EPH13")).to_have_count(0)
        checks.append("Source-framework filters distinguish Constructive and the two induction studies")
        page.locator("#clear").click()
        page.locator("aside details > summary").click()
        page.locator("#framework").select_option("ttr")
        page.locator("#integration").select_option("ttr_ds")
        expect(page.locator("#papers article")).to_have_count(1)
        expect(page.locator("#CL25")).to_be_visible()
        page.locator("#CL25 .related > summary").click()
        expect(page.locator("#CL25 .analysis")).to_contain_text("does not implement the proposed TTR encoding of parsing itself")
        checks.append("TTR-DS recasting stays distinct from DS–TTR meanings and current app capabilities")
        page.locator("#clear").click()
        page.locator("#mechanism").select_option("link")
        expect(page.locator("#CKM05")).to_be_visible()
        expect(page.locator("#OH26")).to_have_count(0)
        page.locator("#clear").click()
        page.locator("#review").select_option("citation_only")
        expected = sum(p["review"]["status"] == "citation_only" for p in papers)
        expect(page.locator("#papers article")).to_have_count(expected)
        expect(page.locator("#KMW01")).to_be_visible()
        expect(page.locator("#CKM05")).to_have_count(0)
        checks.append("Mechanism and reading-status filters preserve unknown/unread distinctions")
        page.locator("#clear").click()
        page.locator("#search").fill("eph13")
        expect(page.locator("#papers article")).to_have_count(1)
        expect(page.locator("#EPH13")).to_be_visible()
        page.locator("#search").fill("<script>unmatched-library-query</script>")
        expect(page.locator("#empty")).to_be_visible()
        expect(page.locator("#papers article")).to_have_count(0)
        checks.append("Exact IDs, clear and empty search behave consistently")
        page.locator("#clear").click()
        pending = sum(c["screening"] == "needs_screening" for c in discovery)
        expect(page.locator("#discovery-count")).to_contain_text(f"{pending} need screening")
        page.locator(".discovery summary").click()
        expect(page.locator("#discovery li")).to_have_count(len(discovery))
        expect(page.locator("#discovery")).to_contain_text("excluded")
        expect(page.locator("#papers article")).to_have_count(len(papers))
        checks.append("Discovery candidates and exclusions remain outside selected-work counts")
        for filename in ("ds-library.bib", "ds-library.csl.json"):
            expect(page.locator(f'nav a[href="{filename}"]')).to_have_attribute("download", "")
            assert (LIBRARY / filename).is_file()
        checks.append("Both citation-export links reference generated files")
        page.locator("#search").fill("C10")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#C10").scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "mobile.png"))
        page.locator("#C10 .related > summary").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        checks.append("Mobile record and expanded analysis fit without horizontal overflow")
        assert not errors, errors
        assert not network, network
        checks.append("No browser errors, tracking or external network requests")
        browser.close()
    (args.output / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(f"Passed {len(checks)} offline library checks.")


if __name__ == "__main__":
    main()
