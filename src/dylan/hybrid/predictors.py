"""Frozen representational predictors built from observed trial histories only."""

from collections import defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path

from dylan.hybrid.constituency import fragments
from dylan.hybrid.traces import SequenceMemory


def ngrams(tokens, n):
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def overlap(first, second):
    first, second = set(first), set(second)
    return len(first & second) / max(1, len(first | second))


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.


def log_count(value):
    return math.log1p(float(value)) if value not in {None, "", "NA"} else 0.


def lexical_features(stimulus, length):
    if not stimulus:
        raise ValueError("No published stimulus metadata")
    key = "four" if length == 4 else "tri1" if "tri1" in stimulus else "tri"
    return {"string_frequency": log_count(stimulus.get(key)),
            "unigram_frequency": mean(log_count(stimulus.get(f"uni{i}")) for i in range(1, length + 1)),
            "bigram_frequency": mean(log_count(stimulus.get(f"bi{i}")) for i in range(1, length))}


def load_traces(path):
    actions, states = defaultdict(set), defaultdict(set)
    if not path.exists():
        return actions, states
    for line in path.read_text().splitlines():
        record = json.loads(line)
        # Structural projections are explicitly lossy features, not claims that
        # lexical programs with different predicates are equivalent actions.
        sequence = []
        for frame in record["frames"]:
            if frame["context"]:
                continue
            for edge in frame["selected_actions"]:
                for program in edge["programs"]:
                    label = program["template"] or program["name"]
                    sequence.append(f"{program['class']}:{label}")
            pending = tuple(sorted(p["requirement"] for p in frame["after"]["pending"]))
            states[record["text"]].add((frame["after"]["pointer"], *pending))
        actions[record["text"]].update(ngrams(sequence, 2) + ngrams(sequence, 3))
    return actions, states


def build(data: Path, audit: Path):
    trials = [json.loads(line) for line in (data / "trials.jsonl").read_text().splitlines()]
    observations = [json.loads(line) for line in (data / "observations.jsonl").read_text().splitlines()]
    stimuli = [json.loads(line) for line in (data / "stimuli.jsonl").read_text().splitlines()]
    lookup = {(int(s["study"]), str(int(float(s["itemId"]))), s["string"]): s for s in stimuli}
    bank = json.loads((data / "contexts.json").read_text())
    contexts = tuple(tuple(c["pos"]) for c in bank["contexts"])
    frequencies = json.loads((data / "pos-frequencies.json").read_text())["counts"]
    ds_actions, ds_states = load_traces(audit / "traces.jsonl")

    @lru_cache(maxsize=4096)
    def trees(pos):
        return {("tree", feature) for context in contexts
                for feature in fragments(tuple(pos.split()), context)["features"]}

    grouped = defaultdict(list)
    for event in observations:
        grouped[(event["study"], event["subject"])].append(event)
    recency = {}
    for events in grouped.values():
        memories = {key: SequenceMemory(.8) for key in ["lexical", "pos2", "pos3", "tree", "action", "state"]}
        for event in sorted(events, key=lambda e: e["order"]):
            sequences = {
                "lexical": ngrams(event["text"].split(), 1),
                "pos2": ngrams(event["pos"].split(), 2), "pos3": ngrams(event["pos"].split(), 3),
                "tree": trees(event["pos"]), "action": ds_actions[event["text"]], "state": ds_states[event["text"]]}
            recency[event["id"]] = {f"{key}_recency": mean(math.log1p(memories[key].activation(s)) for s in seqs)
                                     for key, seqs in sequences.items()}
            for key, seqs in sequences.items():
                memories[key].observe(seqs)
    records = []
    for trial in trials:
        if not trial["history_verified"]:
            continue
        prime = lookup[(trial["study"], trial["item_id"], trial["source_prime"])]
        target = lookup[(trial["study"], trial["item_id"], trial["source_target"])]
        features = {}
        for role, source in (("prime", prime), ("target", target)):
            text = trial[role]
            features.update({f"{role}_{name}": value for name, value in lexical_features(source, len(text.split())).items()})
            features[f"{role}_characters"] = len(text.replace(" ", ""))
            features[f"{role}_words"] = len(text.split())
        similarity = "simil_" + "".join(x[0] for x in trial["pattern"].split("_")) if trial["study"] == 4 else "simil"
        features["semantic_similarity"] = float(prime.get(similarity) or 0)
        features["trial_order"] = trial["target_order"]
        features["lexical_overlap"] = overlap(trial["prime"].split(), trial["target"].split())
        features["constituent_condition"] = float(str(trial.get("constituent")).lower() in {"true", "1", "constituent"})
        for n in (2, 3):
            features[f"pos{n}_overlap"] = overlap(ngrams(trial["pos_prime"].split(), n), ngrams(trial["pos_target"].split(), n))
            features[f"pos{n}_frequency"] = mean(math.log1p(frequencies[str(n)].get(" ".join(g), 0))
                                                  for g in ngrams(trial["pos_target"].split(), n))
        features["tree_overlap"] = overlap(trees(trial["pos_prime"]), trees(trial["pos_target"]))
        features["action_overlap"] = overlap(ds_actions[trial["prime"]], ds_actions[trial["target"]])
        features["state_overlap"] = overlap(ds_states[trial["prime"]], ds_states[trial["target"]])
        event_id = f"s{trial['study']}:p{trial['subject']}:t{trial['target_order']}"
        features.update(recency[event_id])
        records.append({**trial, "features": features})
    return records
