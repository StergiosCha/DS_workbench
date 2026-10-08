"""Frozen DS decision capture and offline replay, without linguistic judgments."""

from collections import defaultdict
import json
from pathlib import Path
import time

from dynamicsyntax import icp
from dynamicsyntax._parse import _active_path_edges
from dylan.action.lexical_action import LexicalAction
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import deadline
from dylan.decision.client import content_hash, validate_answers
from dylan.decision.gates import family_hash, grammar_hash
from dylan.decision.ranking import lexical_key
from dylan.decision.provider import settings
from dylan.nlp.types import utterance_from_text


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def run_case(case, client, *, enumerate_readings=False):
    """Label the primary successful path only after parsing has finished."""
    reset_all_meta_bindings()
    parser = icp(case["grammar"], top_n=0, strict=True)
    parser.decision_client = client
    started = time.perf_counter()
    try:
        with deadline(20):
            result = parser.parse(case["surface"])
            outcome = {"ok": result.ok, "complete": result.tree.is_complete(),
                       "semantics": str(result.semantics), "cap_hit": result.cap_hit}
            stats = result.stats.to_dict()
            winning = _active_path_edges(parser) if result.ok and result.tree.is_complete() else []
            by_parent = {edge.src.tuple_id: edge for edge in winning}
            records = list(client.records) if client else []
            tokens = [w.word for w in utterance_from_text("Dylan", case["surface"]).words]
            for record in records:
                edge = by_parent.get(record.get("replay_parent"))
                targets = []
                if edge is not None:
                    if record["idea"] == 2:
                        targets = [key for key, value in record["replay_edges"].items() if value == edge.edge_id]
                    else:
                        keys = {lexical_key(a) for a in edge.actions if isinstance(a, LexicalAction)}
                        targets = [key for key, value in record["replay_entries"].items() if value in keys]
                # Evaluation labels never go into record.state or its cache key.
                record["reference_choices"] = targets
                if targets:
                    prefix, word = record["state"]["tokens_so_far"], record["state"]["next_word"]
                    observed = prefix + ([word] if word is not None else [])
                    if tokens[:len(observed)] != observed:
                        raise ValueError("A labelled decision is not a prefix of its source input")
            readings = None
            if enumerate_readings and result.ok:
                from dylan.workbench_readings import collect_readings

                values, search = collect_readings(parser, result.tree, [], tokens, limit=32, max_candidates=200)
                readings = {"exhausted": search["exhausted"], "stop_reason": search["stop_reason"],
                            "meanings": sorted({v["normalized"] for v in values}),
                            "analyses": sorted({json.dumps([
                                v["strategies"], v["normalized"], sorted(
                                    (node["id"], sorted(node["labels"])) for node in v["tree"]["nodes"]
                                )], ensure_ascii=False) for v in values})}
            return {"outcome": outcome, "stats": stats, "records": records, "readings": readings,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
    except (TimeoutError, ValueError, TypeError, RuntimeError, RecursionError) as exc:
        return {"error": type(exc).__name__, "records": list(client.records) if client else []}
    finally:
        parser.close()


def manifest(grammars):
    return {"grammars": {g: grammar_hash(g) for g in sorted(grammars)},
            "families": {str(i): family_hash(i) for i in (1, 2)}, "top_n": 0}


def check_manifest(dataset):
    if dataset["manifest"] != manifest(dataset["manifest"]["grammars"]):
        raise ValueError("Grammar or decision code changed; collect a new frozen dataset")
    config = settings()
    if any(item["provider"] != config["provider"] or item["requested_model"] != config["model"]
           for item in dataset["items"]):
        raise ValueError("Select the captured provider/model before replaying this dataset")


def decision_items(cases):
    """Deduplicate exact observed states; retain conflicting reference paths."""
    items = {}
    for case in cases:
        if "error" in case["baseline"]:
            continue
        for record in case["baseline"]["records"]:
            key = record["cache_key"]
            if key not in items:
                items[key] = {k: record[k] for k in (
                    "cache_key", "state", "questions", "idea", "grammar", "provider",
                    "requested_model", "deterministic_order",
                )}
                items[key].update(reference_choices=set(), case_ids=set())
            items[key]["reference_choices"].update(record.get("reference_choices", []))
            items[key]["case_ids"].add(case["id"])
    for item in items.values():
        item["reference_choices"] = sorted(item["reference_choices"])
        item["case_ids"] = sorted(item["case_ids"])
    return list(items.values())


def select_items(items, per_group):
    groups = defaultdict(list)
    for item in items:
        if item["reference_choices"]:
            groups[(item["grammar"], item["idea"])].append(item)
    # Stable sampling independent of correctness, uncertainty and model answers.
    return [item for group in sorted(groups) for item in
            sorted(groups[group], key=lambda i: i["cache_key"])[:per_group]]


def answers_for_replay(dataset, responses, idea):
    answers = {}
    for item in dataset["items"]:
        response = responses.get(item["cache_key"])
        if item["idea"] != idea or not response or response.get("stub"):
            continue
        if (response.get("provider") != item["provider"]
                or response.get("model") != item["requested_model"]
                or response.get("question_set_hash") != content_hash(item["questions"])
                or response.get("chunk_id") != content_hash(item["state"])):
            raise ValueError("Recorded response does not match its frozen request")
        answers[item["cache_key"]] = validate_answers(response["answers"], item["questions"])
    return answers


def score_group(items, responses):
    scored, missing, ambiguous = [], 0, 0
    for item in items:
        targets = item["reference_choices"]
        if len(targets) != 1:
            ambiguous += bool(targets)
            continue
        response = responses.get(item["cache_key"])
        if not response or response.get("stub"):
            missing += 1
            continue
        answers = validate_answers(response["answers"], item["questions"])
        answer = next(iter(answers.values()))
        choice, probs = answer["choice"], answer["probabilities"]
        target = targets[0]
        order = sorted(probs, key=lambda key: -probs[key])
        scored.append({"hit": choice == target, "baseline_hit": item["deterministic_order"][0] == target,
                       "reciprocal_rank": 1 / (order.index(target) + 1),
                       "flat": max(probs.values()) < 0.4,
                       "brier": sum((p - (key == target)) ** 2 for key, p in probs.items())})
    n = len(scored)
    def mean(key):
        return sum(r[key] for r in scored) / n if n else 0
    return {"n": n, "missing": missing, "ambiguous": ambiguous,
            "agreement": mean("hit"), "baseline_agreement": mean("baseline_hit"),
            "gain": mean("hit") - mean("baseline_hit"), "mrr": mean("reciprocal_rank"),
            "brier": mean("brier"), "flat_rate": mean("flat")}
