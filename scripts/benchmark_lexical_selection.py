"""Benchmark lexical senses/frames separately from DS parse success; offline by default."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import statistics

from dynamicsyntax import icp
from dylan.decision.client import DecisionClient, content_hash, validate_answers
from dylan.decision.evaluation import write_json
from dylan.decision.questions.lexical_v1 import questions, options
from dylan.decision.provider import DIRECT_MODEL, OPENROUTER_MODEL
from dylan.lexical_dictionary import candidates
from dylan.lexical_expansion import validate_entries, _install
from dylan.lexical_selection import candidate_groups, THRESHOLD
from dylan.workbench_environment import load_environment


def build_item(case):
    parser = icp("2026-english-mltt", strict=True, top_n=0)
    try:
        entries, _ = candidates(case["word"])
        if not entries:
            raise ValueError(f"No dictionary candidates for {case['word']}; install the pinned WordNet dictionary first")
        compiled, theory = validate_entries({"entries": entries}, [case["word"]], parser.lexicon,
                                            parser.semantic_profile, max_entries=len(entries), max_analyses=len(entries))
        _install(parser, compiled, theory, {"source": "dictionary"})
        values, _ = candidate_groups(parser.lexicon.lookup_all(case["word"]))
        choices = options(values)
        for name, field, targets in (("sense", "sense_key", case["senses"]), ("frame", "template", case["frames"])):
            if not set(targets) <= {v[field] for v in choices[name].values()} | {"uncertain"}:
                raise ValueError(f"Reference missing from candidates for {case['id']}/{name}")
        state = {"grammar": "2026-english-mltt", "word": case["word"], "prefix": case["prefix"].split(),
                 "tree": {}, "speaker": "Dylan", "candidates": values}
        return {"id": case["id"], "state": state, "questions": questions(values), "reference": case}
    finally:
        parser.close()


def score(item, record):
    if (record["chunk_id"] != content_hash(item["state"])
            or record["question_set_hash"] != content_hash(item["questions"])):
        raise ValueError("Frozen response differs from the benchmark state/questions")
    if not record["stub"] and record["model"] != {
        "typesafe": DIRECT_MODEL, "openrouter": OPENROUTER_MODEL,
    }.get(record["provider"]):
        raise ValueError("Frozen response differs from the pinned provider/model")
    answers = validate_answers(record["answers"], item["questions"]) if not record["stub"] else {}
    choices = options(item["state"]["candidates"])
    result = {"id": item["id"], "word": item["state"]["word"], "failed": record["stub"]}
    for name, field, label in (("sense", "sense_key", "senses"), ("frame", "template", "frames")):
        answer = answers.get(name)
        candidates = choices[name]
        predicted = next(iter(candidates.values()))[field] if len(candidates) == 1 else "unavailable"
        if answer:
            selected = answer["choice"]
            predicted = candidates[selected][field] if selected in candidates and answer["probabilities"][selected] >= THRESHOLD else "uncertain"
        targets = item["reference"][label]
        result[name] = {"asked": name in item["questions"], "prediction": predicted, "targets": targets,
                        "correct": predicted in targets,
                        "dictionary_first_correct": next(iter(candidates.values()))[field] in targets}
    return result


def main():
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--responses", type=Path, default=Path("data/lexical-selection/responses.json"))
    parser.add_argument("--output", type=Path, default=Path("data/lexical-selection/results.json"))
    args = parser.parse_args()
    benchmark = json.loads(Path("data/lexical-selection/benchmark.json").read_text())
    items = [build_item(case) for case in benchmark["cases"]]
    records = json.loads(args.responses.read_text()) if args.responses.exists() else {}
    if args.live:
        def ask(item):
            client = DecisionClient("jev", log_path=Path("build/lexical-selection") / f"{item['id']}.jsonl")
            record = client.decide(item["state"], item["questions"], idea=6, calibration=True)
            return item["id"], {key: record.get(key) for key in (
                "model", "provider", "answers", "chunk_id", "question_set_hash", "stub", "latency_ms", "cost_usd", "error")}
        pending = [item for item in items if item["id"] not in records]
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(ask, item) for item in pending]
            for i, future in enumerate(as_completed(futures), 1):
                identity, record = future.result()
                records[identity] = record
                write_json(args.responses, records)
                print(f"Received {i}/{len(pending)} lexical responses", flush=True)
    if any(item["id"] not in records for item in items):
        raise SystemExit("Responses are missing; run explicitly with --live to measure them")
    rows = [score(item, records[item["id"]]) for item in items]
    metrics = {}
    for name in ("sense", "frame"):
        scored = [row[name] for row in rows if row[name]["asked"]]
        metrics[name] = {"asked": len(scored), "correct": sum(r["correct"] for r in scored),
                         "dictionary_first_correct": sum(r["dictionary_first_correct"] for r in scored)}
    report = {"scope": benchmark["scope"], "reference_source": benchmark["source"],
              "benchmark_hash": content_hash(benchmark), "threshold": THRESHOLD,
              "models": sorted({r["model"] for r in records.values() if not r["stub"]}),
              "cases": len(rows), "failed": sum(r["failed"] for r in rows), "metrics": metrics,
              "cost_usd": sum(r.get("cost_usd") or 0 for r in records.values()),
              "median_latency_ms": statistics.median(r["latency_ms"] for r in records.values()), "results": rows}
    write_json(args.output, report)
    print(json.dumps({k: report[k] for k in ("cases", "failed", "metrics", "cost_usd", "median_latency_ms")}))


if __name__ == "__main__":
    main()
