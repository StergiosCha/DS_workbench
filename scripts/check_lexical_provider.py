"""Opt-in live lexical evaluation; records proposals, not just parse success.

Run with server-side credentials and --model. Does not print credentials or URLs.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile

from dylan.workbench_api import parse_request
from dylan.workbench_environment import load_environment


def main():
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="/tmp/ds-lexical-provider.json")
    args = parser.parse_args()
    os.environ["DS_LEXICAL_MODEL"] = args.model
    cases = [
        ("a cat purrs.", True, {"purrs": "intransitive"}),
        ("john sneezes.", True, {"sneezes": "intransitive"}),
        ("john devours a sandwich.", True, {"devours": "transitive", "sandwich": "noun"}),
        ("john devours.", False, {"devours": "transitive"}),
        ("no kitten purrs.", False, {"kitten": "noun", "purrs": "intransitive"}),
        ("john believes that a man walks.", True, {"believes": "clausal"}),
    ]
    rows = []
    with tempfile.TemporaryDirectory(prefix="ds-lexical-eval-") as directory:
        os.environ["DS_LEXICAL_CACHE"] = str(Path(directory) / "proposals.sqlite3")
        for text, expected, frames in cases:
            result = parse_request(
                {"grammar": "2026-english-mltt", "sentence": text, "lexical_mode": "model"}
            )
            lexical = result["lexical"]
            chosen = {(e["surface"], e["template"]) for e in lexical["entries"]}
            passed = result["complete"] == expected and all(
                item in chosen for item in frames.items()
            )
            rows.append(
                {
                    "sentence": text,
                    "passed": passed,
                    "expected_complete": expected,
                    "complete": result["complete"],
                    "failure": result["failure"],
                    "meaning": result["words"][-1]["normalized"],
                    "lexical": lexical,
                    "elapsed_ms": result["elapsed_ms"],
                }
            )
            print(
                json.dumps(
                    {
                        "sentence": text,
                        "passed": passed,
                        "complete": result["complete"],
                        "status": lexical["status"],
                        "notices": lexical["notices"],
                        "elapsed_ms": result["elapsed_ms"],
                    }
                ),
                flush=True,
            )
    Path(args.output).write_text(json.dumps({"model": args.model, "cases": rows}, indent=2))
    print(
        f"{sum(row['passed'] for row in rows)}/{len(rows)} fixture checks passed; full proposals: {args.output}"
    )
    raise SystemExit(0 if all(row["passed"] for row in rows) else 1)


if __name__ == "__main__":
    main()
