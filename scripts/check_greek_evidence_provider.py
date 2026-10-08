"""Bounded live source/model smoke checks. Credentials are never logged."""
import argparse
import json
import os
from pathlib import Path
import time

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.greek_lexical_evidence import Evidence
from dylan.workbench_api import parse_request
from dylan.workbench_environment import load_environment

parser = argparse.ArgumentParser()
parser.add_argument("--sources-only", action="store_true")
parser.add_argument("--model", default="deepseek/deepseek-v4.1-flash")
parser.add_argument("--output", type=Path, default=Path("/tmp/ds-greek-evidence-live.json"))
args = parser.parse_args()
if args.sources_only:
    result = Evidence().collect(["γέρος", "κοίταζε", "περίμενε", "παρατηρεί"], [], deadline=time.monotonic() + 15)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result["words"], ensure_ascii=False))
else:
    load_environment()
    os.environ.update(DS_LEXICAL_PROVIDER="openrouter", DS_LEXICAL_MODEL=args.model, DS_EPHEMERAL_MODELS="1")
    results = []
    for backend in ("classical", "mltt"):
        reset_all_meta_bindings()
        result = parse_request({"grammar": f"2026-smg-{backend}", "lexical_mode": "assisted",
            "live_greek_sources": True, "sentence": "Η ερευνήτρια είναι εδώ."}, _trace=False)
        results.append(result)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        lexical = result["lexical"]
        print(json.dumps({"backend": backend, "complete": result["complete"], "elapsed_ms": result["elapsed_ms"],
            "calls": len(lexical["attempts"]), "sources": lexical["live_sources"]["words"],
            "candidates": [{k: e.get(k) for k in ("surface", "lemma", "template", "evidence_ids")} for e in lexical["entries"] if e["source"] == "model"],
            "notices": lexical["notices"]}, ensure_ascii=False), flush=True)
        assert result["complete"], result["failure"]
        assert lexical["attempts"]
        assert lexical["live_sources"]["items"], "Live sources supplied no observations"
        assert any(e.get("evidence_ids") for e in lexical["entries"] if e["source"] == "model"), "Model did not cite retrieved evidence"
