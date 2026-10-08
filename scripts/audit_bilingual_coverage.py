"""Report actual DS completion on everyday Greek/English probes; never call models."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(case):
    language, family, sentence, backend = case
    grammar = f"2026-{'english' if language == 'en' else 'smg'}-{backend}"
    payload = {"sentence": sentence, "grammar": grammar, "lexical_mode": "dictionary" if language == "en" else "off"}
    record = {"language": language, "family": family, "sentence": sentence, "grammar": grammar}
    try:
        worker = subprocess.run([sys.executable, "-m", "dylan.workbench_api"], input=json.dumps(payload), text=True, capture_output=True, timeout=15, cwd=ROOT, env={**os.environ, "DS_EPHEMERAL_MODELS": "1"})
        result = json.loads(worker.stdout)
        record.update(complete=result.get("complete", False), failure=result.get("failure") or result.get("error"), missing=[row["token"] for row in result.get("diagnostics", {}).get("lexical_coverage", []) if not row["known"]], meaning=result.get("words", [{}])[-1].get("normalized"))
    except (subprocess.TimeoutExpired, ValueError):
        record.update(complete=False, failure="worker_limit", missing=[], meaning=None)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-bilingual-coverage.json"))
    args = parser.parse_args()
    probes = json.loads((ROOT / "data/coverage/everyday-bilingual.json").read_text())
    cases = [(language, family, sentence, backend) for language in ("en", "el") for family, sentence in probes[language] for backend in ("classical", "mltt")]
    with ThreadPoolExecutor(4) as workers:
        rows = list(workers.map(run, cases))
    summary = {language: {backend: {"complete": sum(row["complete"] for row in rows if row["language"] == language and row["grammar"].endswith(backend)), "total": len(probes[language])} for backend in ("classical", "mltt")} for language in ("en", "el")}
    args.output.write_text(json.dumps({"description": probes["description"], "summary": summary, "results": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
