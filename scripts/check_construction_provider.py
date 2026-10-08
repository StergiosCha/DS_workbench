"""Real model proposals followed by actual DS, without saving credentials."""
import argparse
import json
import os
from pathlib import Path

from dylan.workbench_environment import load_environment
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.workbench_api import parse_request

args = argparse.ArgumentParser()
args.add_argument("--output", type=Path, default=Path("/tmp/ds-construction-live.json"))
args = args.parse_args()
load_environment()
os.environ["DS_LEXICAL_PROVIDER"] = "openrouter"
os.environ["DS_LEXICAL_MODEL"] = os.getenv("DS_ASSISTED_TEST_MODEL", "deepseek/deepseek-v4.1-flash")
os.environ["DS_EPHEMERAL_MODELS"] = "1"
rows = []
for backend in ("classical", "mltt"):
    for language, text, relation in [
        ("english", "John walks provided Mary walks.", "condition"),
        ("smg", "Ο Γιώργος περπατάει καθότι η Μαρία περπατάει.", "because"),
        ("english", "John walks since Mary walks.", None),
    ]:
        reset_all_meta_bindings()
        result = parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}", "lexical_mode": "assisted"}, _trace=False)
        row = {"text": text, "backend": backend, "complete": result["complete"], "failure": result["failure"],
               "meaning": result["words"][-1]["normalized"], "used": result["clause_constructions"],
               "proposals": result["lexical"]["constructions"], "attempts": result["lexical"]["attempts"],
               "derivation_attempts": result["assistance"]["derivation_attempts"]}
        rows.append(row)
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: row[k] for k in ("text", "backend", "complete", "meaning", "used")}, ensure_ascii=False), flush=True)
        assert result["complete"], row
        if relation:
            assert row["meaning"].startswith(relation + "("), row
            assert row["proposals"] and row["proposals"][0]["added_programs"] >= 2, row
        else:
            assert any(a["kind"] == "construction" for a in row["attempts"]), row
assert os.environ["OPENROUTER_API_KEY"] not in args.output.read_text()
print("Live construction checks passed; ambiguous since is recorded without assuming one correct reading.")
