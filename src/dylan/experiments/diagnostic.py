"""Reproducible licensing diagnostics on hash-verified literature materials.

Run with --cache PATH [--fetch] --output PATH. The subprocess workers receive
only plain observations and an engine ID, never gold labels or region names.
The source surprisal predictions are preserved but are not scored as licensing.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from dylan.experiments.contracts import Observation, digest
from dylan.experiments.feature_engine import MODES, register
from dylan.experiments.literature import CACHE, syntaxgym
from dylan.experiments.registry import create_engine
from dylan.workbench_paths import WORKING_ROOT, data_path

PROTOCOL = "experiments/literature-diagnostic-v1.json"
CONDITIONS = {"match_sing": True, "match_plural": True,
              "mismatch_sing": False, "mismatch_plural": False}


def prepare(cache=CACHE, *, fetch=False):
    protocol_path = data_path(PROTOCOL)
    protocol = json.loads(protocol_path.read_text())
    items, sources, frame_signatures = [], [], {}
    for suite_id, selection in protocol["selection"].items():
        suite = syntaxgym(suite_id, cache, fetch=fetch)
        sources.append({k: suite[k] for k in ("source", "predictions", "critical_regions", "meta")})
        selected = {f["item_number"]: f for f in suite["families"]}
        if set(selected) != set(selection["items"]):
            raise ValueError("This protocol selects all source families; source IDs changed")
        for number in selection["items"]:
            family = selected[number]
            if {c["name"] for c in family["conditions"]} != set(CONDITIONS):
                raise ValueError("Unexpected condition inventory")
            signature = sorted({tuple(r["content"] for r in c["regions"] if r["number"] <= 5)
                                for c in family["conditions"]})
            if number in frame_signatures and frame_signatures[number] != signature:
                raise ValueError("The declared shared lexical frame differs across suites")
            frame_signatures[number] = signature
            for condition in family["conditions"]:
                items.append({
                    "id": family["id"] + "/" + condition["name"],
                    "family": family["id"], "suite": suite_id,
                    "shared_frame": f"lexical-frame:{number}",
                    "condition": condition["name"], "gold": CONDITIONS[condition["name"]],
                    "text": " ".join(r["content"] for r in condition["regions"] if r["content"]),
                    "regions": condition["regions"],
                    "critical_region": selection["critical_region"],
                })
    return {"schema": "literature.diagnostic.items.v1", "protocol": protocol,
            "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
            "sources": sources, "items": items, "items_sha256": digest(items)}


def compact(analysis):
    provenance = analysis.provenance
    # Non-derivation and search failure never earn credit on a negative item.
    rejection = provenance.get("rejections", [])
    explicit_conflict = any(
        r.get("unconstrained_derivation", {}).get("category") == "S"
        and any(c.get("enabled") and c.get("passes") is False for c in r.get("checks", []))
        for r in rejection)
    decision = True if analysis.status == "complete" and analysis.complete else (
        False if analysis.status == "constraint_rejection" and explicit_conflict else None)
    return {
        "status": analysis.status, "decision": decision,
        "meanings": list(analysis.meanings), "counters": analysis.counters,
        "failure": provenance.get("failure"),
        "provenance": {k: v for k, v in provenance.items()
                       if k.endswith("sha256") or k in {"mode", "processing", "max_words", "cell_cap", "tokenization"}},
        "derivations": provenance.get("analyses", [])[:1],
        "rejections": rejection[:1],
    }


def worker(payload):
    register()
    engine = create_engine(payload["engine"])
    results = []
    try:
        for text in payload["observations"]:
            try:
                results.append(compact(engine.analyse(
                    Observation(text, task="sentence"), trace=payload["engine"] in MODES)))
            except Exception as exc:
                results.append({"status": "execution_error", "decision": None,
                                "error": f"{type(exc).__name__}: {exc}"})
    finally:
        engine.close()
    return results


def run_engine(identifier, items, *, timeout=120):
    payload = {"engine": identifier, "observations": [i["text"] for i in items]}
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + environment.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "dylan.experiments.diagnostic", "--worker"], input=json.dumps(payload),
            capture_output=True, text=True, timeout=timeout, check=False, env=environment)
        if result.returncode:
            raise RuntimeError(f"Worker exited with code {result.returncode}: {result.stderr[-1200:]}")
        records = json.loads(result.stdout)
        if not isinstance(records, list) or len(records) != len(items):
            raise ValueError("Worker returned the wrong number of observations")
    except subprocess.TimeoutExpired:
        records = [{"status": "worker_timeout", "decision": None} for _ in items]
    except (OSError, ValueError, RuntimeError) as exc:
        records = [{"status": "worker_error", "decision": None, "error": str(exc)} for _ in items]
    return {item["id"]: record for item, record in zip(items, records, strict=True)}


def metrics(items, records):
    if set(records) != {i["id"] for i in items}:
        raise ValueError("Results must cover exactly the declared observation IDs")
    if any(r["decision"] is not None and type(r["decision"]) is not bool for r in records.values()):
        raise ValueError("Decisions must be booleans or unavailable")
    evaluable = [i for i in items if records[i["id"]]["decision"] is not None]
    families = defaultdict(list)
    for item in items:
        if type(item["gold"]) is not bool:
            raise ValueError("Gold licensing judgments must be booleans")
        families[item["family"]].append(item)
    if any(len(group) != 4 or {i["condition"] for i in group} != set(CONDITIONS) for group in families.values()):
        raise ValueError("Scoring requires all four source conditions in every family")
    covered = {fid for fid, group in families.items()
               if all(records[i["id"]]["decision"] is not None for i in group)}
    correct_families = {fid for fid in covered
                        if all(records[i["id"]]["decision"] == i["gold"] for i in families[fid])}

    def rate(group):
        return (sum(records[i["id"]]["decision"] == i["gold"] for i in group) / len(group)) if group else None

    return {
        "conditions": len(items), "evaluable_conditions": len(evaluable),
        "condition_accuracy": rate(evaluable),
        "positive_acceptance": rate([i for i in evaluable if i["gold"]]),
        "negative_rejection": rate([i for i in evaluable if not i["gold"]]),
        "families": len(families), "evaluable_families": len(covered),
        "correct_families": len(correct_families),
        "family_accuracy": len(correct_families) / len(covered) if covered else None,
        "covered_family_ids": sorted(covered),
        "statuses": dict(Counter(r["status"] for r in records.values())),
    }


def summarize(dataset, runs):
    items = dataset["items"]
    summary = {engine: {
        "overall": metrics(items, records),
        "suites": {suite: metrics([i for i in items if i["suite"] == suite],
                                 {i["id"]: records[i["id"]] for i in items if i["suite"] == suite})
                   for suite in dataset["protocol"]["selection"]}
    } for engine, records in runs.items()}
    intersections = {}
    for name, engines in (("all_configurations", list(runs)),
                          ("feature_ablations", [e for e in runs if e in MODES])):
        common = set.intersection(*(set(summary[e]["overall"]["covered_family_ids"]) for e in engines)) if engines else set()
        subset = [i for i in items if i["family"] in common]
        intersections[name] = {
            "family_ids": sorted(common), "families": len(common),
            "scores": {e: metrics(subset, {i["id"]: runs[e][i["id"]] for i in subset}) for e in engines},
        }
    return {"engines": summary, "intersections": intersections}


def source_fingerprint():
    root = WORKING_ROOT
    files = sorted([*root.glob("src/**/*.py"), *root.glob("src/dynamicsyntax/grammars/**/*.txt"),
                    *root.glob("src/dynamicsyntax/grammars/**/*.json")])
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                              text=True, capture_output=True, check=False).stdout.strip() or None
    return {"git_commit": revision, "source_manifest": manifest, "source_sha256": digest(manifest)}


def markdown(report):
    lines = [
        "# Agreement and reflexives: literature diagnostic",
        "",
        "Two published SyntaxGym suites; 38 four-condition item sets / 152 sentences / 19 shared lexical frames.",
        "This is a source-informed development licensing diagnostic. The original regional-surprisal predictions are unscored.",
        "",
        "| Configuration | Evaluable conditions | Evaluable families | Correct families | Condition accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, entry in report["summary"]["engines"].items():
        m = entry["overall"]
        score = "unavailable" if m["condition_accuracy"] is None else f'{m["condition_accuracy"]:.1%}'
        lines.append(f'| {name} | {m["evaluable_conditions"]}/{m["conditions"]} | '
                     f'{m["evaluable_families"]}/{m["families"]} | {m["correct_families"]} | {score} |')
    lines += [
        "", "Unknown words, unsupported structures and search limits receive no negative-item credit.",
        "The new feature configurations share one lexicon and application chart. Only the declared constraints/controller differ.",
        "",
        "## Interpretation",
        "",
        "The head configuration encodes subject-number and local reflexive-number dependencies explicitly. Its development score checks that implementation; it does not show that the dependencies were learned.",
        "An accept-all configuration can achieve 50% condition accuracy while passing zero complete families. The nearest-noun control tests the opposite controller in these distractor items.",
        "The original DS/CCG fragments are retained for coverage auditing. An empty shared family intersection prevents a matched architectural accuracy comparison.",
        "These examples do not test gender, general binding theory, normalized next-word probabilities or human reading times.",
        "",
        "## Reproduction",
        "",
        "Use python -m dylan.experiments.diagnostic --cache <pinned-source-cache> --output <directory>. Add --fetch to retrieve missing pinned source files.",
        f'Protocol SHA-256: {report["dataset"]["protocol_sha256"]}',
        f'Source SHA-256: {report["implementation"]["source_sha256"]}',
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--output", type=Path, default=WORKING_ROOT / "build/experiments/literature-diagnostic-v1")
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
        return
    dataset = prepare(args.cache, fetch=args.fetch)
    before = source_fingerprint()
    runs = {}
    for identifier in dataset["protocol"]["configurations"]:
        print(f"Evaluating {identifier} on {len(dataset['items'])} source conditions", flush=True)
        runs[identifier] = run_engine(identifier, dataset["items"])
    after = source_fingerprint()
    if before["source_sha256"] != after["source_sha256"]:
        raise RuntimeError("Implementation changed during the run; no mixed-version report written")
    report = {
        "schema": "literature.diagnostic.result.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset, "implementation": before, "runs": runs,
        "summary": summarize(dataset, runs),
        "original_surprisal_scores": None,
        "original_surprisal_unavailable_reason": "No engine supplies normalized next-word probabilities",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    (args.output / "report.md").write_text(markdown(report))
    from dylan.experiments.diagnostic_report import render

    (args.output / "report.html").write_text(render(report))
    print(args.output / "report.html")


if __name__ == "__main__":
    main()
