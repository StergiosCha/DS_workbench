"""Live, uncached Jev comparison; never logs credentials or changes frozen benchmarks."""
import argparse
import json
import os
from pathlib import Path

from dylan.workbench_api import parse_request
from dylan.workbench_environment import load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-jev-comparison-live.json"))
parser.add_argument("--sentence", default="John lends a book to Mary.")
args = parser.parse_args()
load_environment()
os.environ.update(DS_DECISION_PROVIDER="openrouter", DS_EPHEMERAL_MODELS="1")
results = []
for backend in ("classical", "mltt"):
    result = parse_request({"sentence": args.sentence, "grammar": f"2026-english-{backend}",
                           "lexical_mode": "jev", "compare_jev": True})
    results.append(result)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    comparison = result["jev_comparison"]
    selection = result["lexical"]["selection"]
    print(json.dumps({"backend": backend, "sentence": args.sentence, "complete": result["complete"],
        "status": comparison["status"], "before": comparison["without_jev"]["meaning"],
        "after": comparison["with_jev"]["meaning"], "live_calls": comparison["live_calls"],
        "changes": comparison["changes"], "revisions": [r["status"] for r in selection["revisions"]]}, ensure_ascii=False), flush=True)
    assert comparison["same_inventory"]
    assert comparison["valid_decisions"], "No valid live Jev answer"
    assert result["complete"] and comparison["without_jev"]["complete"]
