"""Count every sentence and every full passage, including errors/timeouts."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

from dylan.paragraph_workbench import sentence_spans


def run(case):
    passage, backend = case
    language = passage["language"]
    grammar = f"2026-{'english' if language == 'en' else 'smg'}-{backend}"
    payload = {"paragraph": passage["text"], "grammar": grammar, "lexical_mode": "dictionary" if language == "en" else "corpus"}
    row = {"id": passage["id"], "language": language, "grammar": grammar, "text_sha256": passage["text_sha256"]}
    try:
        worker = subprocess.run([sys.executable, "-m", "dylan.workbench_api"], input=json.dumps(payload), text=True, capture_output=True, timeout=30,
            env={**os.environ, "DS_EPHEMERAL_MODELS": "1"})
        result = json.loads(worker.stdout)
        if "error" in result:
            raise ValueError(result["error"])
        row.update(complete=result["complete"], coverage=result["coverage"], elapsed_ms=result["elapsed_ms"],
            sentences=[{"text": s["text"], "status": s["status"], "complete": s["complete"], "failure": s["failure"],
                "context_gaps": s["context_gaps"], "missing": [t["token"] for t in s.get("result", {}).get("diagnostics", {}).get("lexical_coverage", []) if not t["known"]],
                "meaning": s.get("result", {}).get("words", [{}])[-1].get("normalized")} for s in result["sentences"]])
    except (ValueError, subprocess.TimeoutExpired) as exc:
        count = len(sentence_spans(passage["text"], language))
        row.update(complete=False, coverage={"complete": 0, "total": count, "failed": count, "all_complete": False}, error=str(exc))
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/coverage/unseen-passages.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/ds-paragraph-coverage.json"))
    args = parser.parse_args()
    sample = json.loads(args.sample.read_text())
    with ThreadPoolExecutor(4) as workers:
        rows = list(workers.map(run, [(p, b) for p in sample["passages"] for b in ("classical", "mltt")]))
    summary = {}
    for language in ("en", "el"):
        for backend in ("classical", "mltt"):
            selected = [r for r in rows if r["language"] == language and r["grammar"].endswith(backend)]
            summary[f"{language}-{backend}"] = {"complete_passages": sum(r["complete"] for r in selected), "passages": len(selected),
                "complete_sentences": sum(r["coverage"]["complete"] for r in selected), "sentences": sum(r["coverage"]["total"] for r in selected),
                "failure_kinds": dict(Counter(s["failure"]["kind"] for r in selected for s in r.get("sentences", []) if s["failure"]))}
    args.output.write_text(json.dumps({"sample": str(args.sample), "seed": sample["seed"], "summary": summary, "results": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
