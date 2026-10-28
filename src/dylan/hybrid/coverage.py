"""Full stimulus coverage with retained context, limits and matched-family accounting."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from dylan.hybrid.dataset import write_jsonl
from dylan.hybrid.traces import DSAdapter, digest


def stimulus_inventory(trials):
    inventory = defaultdict(set)
    for row in trials:
        for role in ("prime", "target"):
            inventory[row[role]].add(row["pos_" + role])
    return inventory


def audit(trials_path, bank_path, output, *, vocabulary="original"):
    output.mkdir(parents=True, exist_ok=True)
    trials = [json.loads(line) for line in trials_path.read_text().splitlines()]
    bank = json.loads(bank_path.read_text())
    inventory = stimulus_inventory(trials)
    adapter = DSAdapter(bank["grammar"], vocabulary=vocabulary)
    rows, traces = [], []
    try:
        if adapter.fingerprint != bank["grammar_sha256"]:
            raise ValueError("Context bank belongs to a different grammar")
        for index, (text, tags) in enumerate(sorted(inventory.items())):
            adapter.prepare(text)
            unknown = [w for w in text.split() if not adapter.parser.lexicon.lookup(w.lower())]
            attempts = []
            if not unknown:
                for context in bank["contexts"]:
                    probe = adapter.probe(text, left_context=context["text"], trace=False)
                    attempts.append({"context_id": context["id"], "status": probe["status"],
                                     "failure": probe["failure"], "search": probe["search"]})
                    if probe["status"] == "recognized_fragment":
                        detailed = adapter.probe(text, left_context=context["text"])
                        detailed["context_id"] = context["id"]
                        traces.append(detailed)
            supported = [a for a in attempts if a["status"] == "recognized_fragment"]
            status = "unsupported_lexicon" if unknown else "recognized_fragment" if supported else (
                "search_limit" if any(a["status"] == "search_limit" for a in attempts) else "no_analysis_in_context_bank")
            rows.append({"text": text, "pos_analyses": sorted(tags), "status": status,
                         "unknown": unknown, "attempts": attempts,
                         "successful_contexts": [a["context_id"] for a in supported],
                         "context_support_fraction": len(supported) / len(bank["contexts"])})
            if index % 100 == 0:
                print(f"Audited {index + 1}/{len(inventory)} unique strings", flush=True)
        by_text = {r["text"]: r for r in rows}
        families = defaultdict(set)
        for trial in trials:
            families[trial["family"]].update([trial["prime"], trial["target"]])
        matched = [f for f, texts in families.items() if all(by_text[t]["status"] == "recognized_fragment" for t in texts)]
        summary = {"schema": 1, "grammar": adapter.grammar, "grammar_sha256": adapter.fingerprint,
                   "context_bank_sha256": digest(bank), "strings": len(rows), "vocabulary": vocabulary,
                   "statuses": dict(Counter(r["status"] for r in rows)),
                   "families": len(families), "fully_supported_matched_families": matched,
                   "included_trials_in_matched_families": sum(r["included"] and r["family"] in matched for r in trials),
                   "interpretation": "Coverage of a bounded grammar/context bank; no grammaticality or probability-of-English claim"}
        write_jsonl(output / "coverage.jsonl", rows)
        write_jsonl(output / "traces.jsonl", traces)
        (output / "coverage-summary.json").write_text(json.dumps(summary, indent=2))
        return summary
    finally:
        adapter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("build/hybrid/data"))
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/audit"))
    parser.add_argument("--vocabulary", choices=["original", "dictionary"], default="original")
    args = parser.parse_args()
    print(json.dumps(audit(args.data / "trials.jsonl", args.data / "contexts.json", args.output,
                           vocabulary=args.vocabulary), indent=2))


if __name__ == "__main__":
    main()
