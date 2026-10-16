"""Check Greek subject meaning in the real UI, with optional bounded live AI.

Never save keys, authorization headers or browser traces.
"""

import argparse
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dylan.workbench_environment import load_environment
from check_openrouter_browser import connect, assert_private


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8813")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--env-file", type=Path)
    ap.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    key = None
    if args.live:
        if not args.env_file:
            ap.error("--live requires --env-file")
        load_environment(args.env_file)
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise SystemExit("No OpenRouter key in the supplied environment.")
    rows, errors, requests = [], [], []
    expect.set_options(timeout=65000)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))

        def seen(request):
            if "/api/parse/stream" in request.url:
                requests.append(
                    {
                        "has_auth": "authorization" in request.headers,
                        "llm_allowed": request.post_data_json.get("allow_model_fallback"),
                    }
                )

        page.on("request", seen)
        page.goto(args.url)
        expect(page.locator("#parse-button")).to_be_enabled()
        if key:
            page.locator("#model-settings-button").click()
            connect(page, key)
            page.locator("#openrouter-model").select_option(args.model)
            page.locator("#models-close").click()
        cases = [
            ("ο μεγάλος άνθρωπος περπατάει", False, True, "overt"),
            ("περπατάει", False, True, "implicit"),
            (
                "ο μεγάλος ο κόκκινος ο άνθρωπος περπατάει",
                False,
                False,
                "polydefinite coverage gap",
            ),
            ("του με έδωσε", False, False, "PCC"),
        ]
        if args.live:
            cases.append(("ο μεγάλος άνθρωπος ήρθε", True, True, "overt"))
        for backend in ("mltt", "classical"):
            page.locator("#system").select_option(backend)
            page.locator("#grammar").select_option("2026-smg-" + backend)
            for sentence, ai, complete, kind in cases:
                page.locator("#llm-enabled").set_checked(ai)
                page.locator("#experimental-enabled").set_checked(False)
                page.locator("#sentence").fill(sentence)
                page.locator("#parse-button").click()
                expect(page.locator("#parse-button")).to_be_enabled()
                result = page.evaluate("state.result")
                final = result["words"][-1]
                row = {
                    "sentence": sentence,
                    "backend": backend,
                    "kind": kind,
                    "complete": result["complete"],
                    "meaning": final["normalized"],
                    "context_assumptions": final["context_assumptions"],
                    "failure": result["failure"],
                    "llm_on": ai,
                    "model_requests": len(result["lexical"].get("attempts", [])),
                    "usage": page.locator("#method-usage").inner_text(),
                }
                rows.append(row)
                args.output.write_text(
                    json.dumps(
                        {
                            "model": args.model if args.live else None,
                            "cases": rows,
                            "browser_errors": errors,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                )
                assert result["complete"] is complete, row
                assert requests[-1]["has_auth"] is ai and requests[-1]["llm_allowed"] is ai
                if kind == "overt":
                    subject = next(n for n in final["nodes"] if n["id"] == "00")
                    assert subject["formula"] not in {None, "pro", "U_pro"}, row
                    assert "pro" not in final["normalized"], row
                    assert "big" in final["normalized"] + str(final["context_assumptions"]), row
                elif kind == "implicit":
                    assert final["normalized"] == "walk(pro)", row
                elif kind == "PCC":
                    assert result["failure"]["kind"] == "pcc_violation", row
                else:
                    assert result["failure"]["token"] == "ο", row
                if not ai:
                    assert row["model_requests"] == 0
                print(
                    json.dumps(
                        {
                            k: row[k]
                            for k in (
                                "sentence",
                                "backend",
                                "complete",
                                "meaning",
                                "model_requests",
                            )
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        if key:
            assert_private(page, key)
        assert not errors, errors
        browser.close()
    print(f"{len(rows)} Greek subject and boundary browser checks passed.")


if __name__ == "__main__":
    main()
