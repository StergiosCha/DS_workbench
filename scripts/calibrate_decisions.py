"""Collect real prefix decisions, query Jev once, replay offline, and report gates.

Only the query phase makes network calls. Corpus judgments, future words and
reference paths never leave the evaluation process. Existing responses are
reused; --per-group bounds requests for each grammar and decision family.
"""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import statistics

from dylan.corpus import CORPORA, read_rows
from dylan.decision.client import DecisionClient
from dylan.decision.evaluation import (
    answers_for_replay, check_manifest, decision_items, manifest, run_case,
    score_group, select_items, write_json,
)
from dylan.decision.gates import gate_path, qualifies
from dylan.decision.provider import settings
from dylan.workbench_environment import load_environment

DEFAULT_GRAMMARS = [f"2026-{language}-{backend}" for language in ("english", "smg")
                    for backend in ("classical", "mltt")]


def collect(args):
    seen, cases = set(), []
    for corpus in CORPORA:
        for row in read_rows(corpus):
            for grammar in sorted(set(row["grammars"]) & set(args.grammars)):
                identity = (grammar, row["surface"].strip().lower())
                if identity in seen:
                    continue
                seen.add(identity)
                cases.append({"id": f"{grammar}:{row['id']}", "grammar": grammar,
                              "surface": row["surface"], "source": row["source"]})
    for i, case in enumerate(cases):
        client = DecisionClient("stub", log_path=args.directory / "capture.jsonl")
        case["baseline"] = run_case(case, client)
        plain = run_case(case, None)
        case["stub_parity"] = (not ("error" in plain or "error" in case["baseline"])
                               and all(plain[key] == case["baseline"][key] for key in ("outcome", "stats")))
        if (i + 1) % 40 == 0:
            print(f"Captured {i + 1}/{len(cases)} cases", flush=True)
    dataset = {"manifest": manifest(args.grammars), "cases": cases, "items": decision_items(cases)}
    write_json(args.directory / "dataset.json", dataset)
    print(json.dumps({"cases": len(cases), "unique_decisions": len(dataset["items"]),
                      "stub_mismatches": sum(not c["stub_parity"] for c in cases)}), flush=True)


def query(args, dataset):
    config = settings()
    if not config["key"]:
        raise SystemExit("The configured decision provider has no key")
    items = select_items(dataset["items"], args.per_group)
    responses_path = args.responses or args.directory / "responses.json"
    responses = json.loads(responses_path.read_text()) if responses_path.exists() else {}
    pending = [item for item in items if item["cache_key"] not in responses]
    if any(i["provider"] != config["provider"] or i["requested_model"] != config["model"] for i in pending):
        raise SystemExit("Provider/model differs from the collection configuration; recollect")
    print(f"Querying {len(pending)} frozen states with {args.workers} workers", flush=True)

    def ask(item):
        client = DecisionClient("jev", log_path=args.directory / "requests" / f"{item['cache_key']}.jsonl")
        return item["cache_key"], client.decide(item["state"], item["questions"], idea=item["idea"],
                                               calibration=True, deterministic_order=item["deterministic_order"])

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(ask, item) for item in pending]
        for i, future in enumerate(as_completed(futures), 1):
            key, response = future.result()
            responses[key] = response
            write_json(responses_path, responses)
            if i % 20 == 0:
                print(f"Received {i}/{len(pending)} responses", flush=True)
    print(json.dumps({"responses": len(responses), "failed": sum(r["stub"] for r in responses.values()),
                      "cost_usd": sum(r.get("cost_usd") or 0 for r in responses.values())}), flush=True)


def evaluate(args, dataset):
    responses = json.loads((args.responses or args.directory / "responses.json").read_text())
    selected = select_items(dataset["items"], args.per_group)
    groups, comparisons = {}, []
    for idea in (1, 2):
        answers = answers_for_replay(dataset, responses, idea)
        totals = defaultdict(lambda: {"parity": True, "cases": 0, "baseline_backtracks": 0,
                                     "replay_backtracks": 0, "replay_hits": 0, "replay_misses": 0,
                                     "mismatches": [], "baseline_ms": 0, "replay_ms": 0})
        for i, case in enumerate(dataset["cases"]):
            client = DecisionClient("stub", recorded=answers, log_path=args.directory / f"replay-{idea}.jsonl")
            replay = run_case(case, client)
            baseline = case["baseline"]
            parity = (case["stub_parity"] and "error" not in replay
                      and baseline.get("outcome") == replay.get("outcome")
                      and replay["stats"]["pruned"] == 0 and not replay["stats"]["top_n_cuts"])
            total = totals[case["grammar"]]
            total["cases"] += 1
            total["parity"] &= parity
            if not parity:
                total["mismatches"].append(case["id"])
            for name, run in (("baseline", baseline), ("replay", replay)):
                total[f"{name}_backtracks"] += run.get("stats", {}).get("backtracks_ok", 0)
                total[f"{name}_ms"] += run.get("elapsed_ms", 0)
            total["replay_hits"] += sum(r.get("recorded", False) for r in replay["records"])
            total["replay_misses"] += sum(not r.get("recorded", False) and r["idea"] == idea for r in replay["records"])
            comparisons.append({"case": case["id"], "idea": idea, "parity": parity,
                                "outcome": replay.get("outcome"), "stats": replay.get("stats")})
            if (i + 1) % 80 == 0:
                print(f"Replayed family {idea}: {i + 1}/{len(dataset['cases'])}", flush=True)
        for grammar, total in totals.items():
            items = [x for x in selected if x["grammar"] == grammar and x["idea"] == idea]
            config = settings()
            metrics = {**score_group(items, responses), **total, "provider": config["provider"],
                       "model": config["model"], "grammar_hash": dataset["manifest"]["grammars"][grammar],
                       "family_hash": dataset["manifest"]["families"][str(idea)]}
            metrics["backtracks_reduced"] = metrics["replay_backtracks"] < metrics["baseline_backtracks"]
            metrics["eligible"] = qualifies(metrics, idea)
            groups[f"{grammar}:{idea}"] = metrics
    report = {"groups": groups, "comparisons": comparisons,
              "reference": "Retrospective primary-path agreement; no grammaticality labels or future input sent to Jev.",
              "limits": "Frozen-answer replay may encounter unqueried states, which retain normal order. Timings exclude network."}
    write_json(args.directory / "report.json", report)
    if args.summary:
        current = [responses[i["cache_key"]] for i in selected if i["cache_key"] in responses]
        latencies = sorted(r["latency_ms"] for r in current)
        config = settings()
        write_json(args.summary, {
            "model": config["model"], "provider": config["provider"],
            "cases": len(dataset["cases"]), "unique_states": len(dataset["items"]),
            "requests": len(current), "failed_requests": sum(r["stub"] for r in current),
            "cost_usd": sum(r.get("cost_usd") or 0 for r in current),
            "median_latency_ms": statistics.median(latencies) if latencies else None,
            "p95_latency_ms": latencies[int(.95 * (len(latencies) - 1))] if latencies else None,
            "manifest": dataset["manifest"], "groups": groups,
            "reference": report["reference"], "limits": report["limits"],
        })
    if args.install_gates:
        existing = json.loads(gate_path().read_text()) if gate_path().exists() else {}
        evaluation_path = gate_path().with_name("evaluation.json")
        evaluated = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else {}
        for key, metrics in groups.items():
            existing.pop(key, None)
            if metrics["eligible"]:
                existing[key] = metrics
        write_json(gate_path(), existing)
        write_json(evaluation_path, {**evaluated, **groups})
    for key, row in groups.items():
        print(json.dumps({"group": key, **{k: row[k] for k in (
            "n", "agreement", "gain", "parity", "baseline_backtracks", "replay_backtracks", "eligible")}}), flush=True)


def main():
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["collect", "query", "evaluate"])
    parser.add_argument("--directory", type=Path, default=Path("build/decision/calibration"))
    parser.add_argument("--grammars", nargs="+", default=DEFAULT_GRAMMARS)
    parser.add_argument("--per-group", type=int, default=40)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--install-gates", action="store_true")
    parser.add_argument("--summary", type=Path, help="Write aggregate evidence suitable for version control")
    parser.add_argument("--responses", type=Path, help="Use an archived response map for offline evaluation")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4 or not 1 <= args.per_group <= 100:
        parser.error("Use 1–4 workers and 1–100 samples per grammar/family")
    args.directory.mkdir(parents=True, exist_ok=True)
    if args.phase == "collect":
        collect(args)
    else:
        dataset = json.loads((args.directory / "dataset.json").read_text())
        check_manifest(dataset)
        (query if args.phase == "query" else evaluate)(args, dataset)


if __name__ == "__main__":
    main()
