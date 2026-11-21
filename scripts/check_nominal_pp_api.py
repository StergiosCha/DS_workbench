"""Verify nominal PP coverage on an actual service, without model credentials."""

import argparse
import json
from pathlib import Path
import ssl
from urllib.request import Request, urlopen

import certifi


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8827")
    ap.add_argument("--output", type=Path, default=Path("build/nominal-pp/api-checks.json"))
    args = ap.parse_args()
    cases = []
    for backend in ("mltt", "classical"):
        for sentence, complete, relation in [
            ("the man with a knife runs", True, "with_nominal"),
            ("a man with a knife runs", True, "with_nominal"),
            ("every man with a knife runs", True, "with_nominal"),
            ("a man with glasses runs", True, "with_nominal"),
            ("a woman in the park walks", True, "in_nominal"),
            ("a doctor at a library walks", True, "at_nominal"),
            ("john likes a book on a stone", True, "on_nominal"),
            ("a man near a woman walks", True, "near_nominal"),
            ("john walks with a knife", True, "with_accompaniment"),
            ("A person entered the room with glasses", True, None),
            ("a man with a knife", False, None),
            ("a man with a", False, None),
            ("a man with with a knife runs", False, None),
            ("a man with a glasses runs", False, None),
        ]:
            cases.append((f"2026-english-{backend}", sentence, complete, relation))
        cases += [(f"2026-smg-{backend}", "του με έδωσε", False, None),
                  (f"2026-smg-{backend}", "ο γιώργος περπατάει", True, None)]
    cases.append(("2015-english-ttr", "a man knows you.", True, None))
    outcomes = []
    tls = ssl.create_default_context(cafile=certifi.where())
    for grammar, sentence, expected, relation in cases:
        request = Request(args.url.rstrip("/") + "/api/parse",
                          data=json.dumps({"sentence": sentence, "grammar": grammar,
                                           "lexical_mode": "dictionary" if "english" in grammar and "ttr" not in grammar else "off",
                                           "allow_model_fallback": False}).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=60, context=tls) as response:
            result = json.load(response)
        final = result["words"][-1]
        relation_present = relation is None or any(
            relation in (node["formula"] or "") for node in final["nodes"])
        model_calls = result.get("lexical", {}).get("model_requests", 0)
        row = {"grammar": grammar, "sentence": sentence, "expected_complete": expected,
               "complete": result["complete"], "relation": relation,
               "relation_present": relation_present, "model_requests": model_calls,
               "meaning": final.get("normalized"), "context_assumptions": final.get("context_assumptions", []),
               "failure": result["failure"], "elapsed_ms": result.get("elapsed_ms")}
        row["passed"] = result["complete"] is expected and relation_present and model_calls == 0
        outcomes.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        {"url": args.url, "kind": "authored deployment regression cases; not independent linguistic gold",
         "cases": outcomes, "passed": sum(row["passed"] for row in outcomes),
         "total": len(outcomes)}, ensure_ascii=False, indent=2) + "\n")
    failed = [row for row in outcomes if not row["passed"]]
    assert not failed, failed
    print(f"{len(outcomes)} service checks passed; zero model calls.")


if __name__ == "__main__":
    main()
