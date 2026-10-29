"""Versioned study definitions, counterbalancing, coverage and observation replay."""

import argparse
from collections import Counter
import json
from pathlib import Path
import random

from dylan.experiments.contracts import Observation, digest
from dylan.experiments.host import Session, cues
from dylan.experiments.memory import Memory
from dylan.experiments.registry import create_engine, catalog


def prototype():
    families = []
    names = ("John", "Mary", "Bill", "George")
    # Hand-declared words in the two maintained fragments. Selection uses no
    # human response or priming estimate. These are unreviewed design seeds.
    nouns = ("book", "dog", "stone", "library", "park", "peacock")
    for i, subject in enumerate(names):
        for j, noun in enumerate(nouns):
            other, prime_noun = names[(i + 1) % len(names)], nouns[(j + 1) % len(nouns)]
            target = {"text": f"likes the {noun}", "left_context": subject, "task": "fragment"}
            families.append({"id": f"f{i * len(nouns) + j:02d}", "target": target,
                "conditions": {
                    "matched": {"text": f"likes a {prime_noun}", "left_context": other, "task": "fragment"},
                    "shifted_boundary": {"text": f"the {prime_noun}", "left_context": f"{other} likes", "task": "fragment"}},
                "annotation_status": "author_constructed_requires_independent_review"})
    return {"schema": 1, "id": "contextual-fragment-memory-v1", "date": "2026-10-29", "seed": 20261029,
        "status": "computational_design_pilot_no_new_human_data", "task": "contextual_fragment_decision",
        "question": "Do memory and grammar configurations yield distinguishable predictions under shared observations?",
        "scope": "Boundary/length/POS differences covary; not a clean test of structure versus POS priming",
        "families": families, "lags": [0, 2],
        "fillers": [{"text": "walks", "left_context": "John", "task": "sentence"},
                    {"text": "arrives", "left_context": "Mary", "task": "sentence"}],
        "grammars": ["ds-english-v1", "ccg-incremental-v1", "ccg-application-v1"],
        "memories": ["none-v1", "count-v1", "exponential-v1"],
        "measurements": ["lognormal-v1", "shifted-lognormal-v1"],
        "representation": "native", "decay": .8,
        "primary_split": "new participants; item families remain shared",
        "counterbalance": "four cyclic lists cross prime condition and intervening lag; order randomized per participant",
        "human_collection": "Independent stimulus review and prospective protocol approval are outstanding; local task is a rehearsal",
        "instructions": "Read the context, then decide whether the displayed continuation can occur after it. Some continuations may be unfinished.",
        "limitations": ["Small declared grammars", "Unreviewed authored stimuli", "Grammar-native cues are different projections",
                        "A grammatical derivation is not a human judgment", "Default RT coefficients are illustrative",
                        "All authored items are intended positive; independently reviewed negative controls are needed before a decision experiment"]}


def validate_study(study):
    if not isinstance(study, dict) or study.get("schema") != 1 or not 1 <= len(study.get("families", [])) <= 200:
        raise ValueError("Invalid bounded study schema")
    identities = []
    for family in study["families"]:
        identities.append(family["id"])
        Observation(**family["target"])
        if set(family["conditions"]) != {"matched", "shifted_boundary"}:
            raise ValueError("This study version requires its two declared conditions")
        for value in family["conditions"].values():
            Observation(**value)
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate family identifier")
    for filler in study["fillers"]:
        Observation(**filler)
    if study["lags"] != [0, 2] or len(study["fillers"]) < 2:
        raise ValueError("This protocol has fixed zero/two-filler lag conditions")
    return study


def schedule(study, participant):
    validate_study(study)
    if type(participant) is not int or not 0 <= participant < 100000:
        raise ValueError("Participant code must be an integer in [0, 100000)")
    rng = random.Random(study["seed"] + participant)
    order = list(enumerate(study["families"]))
    rng.shuffle(order)
    events = []
    for index, family in order:
        cell = (participant + index) % 4
        condition, lag = ("matched" if cell % 2 == 0 else "shifted_boundary"), study["lags"][cell // 2]
        base = {"family": family["id"], "condition": condition, "lag": lag}
        events.append({**base, "role": "prime", "observation": family["conditions"][condition]})
        for filler in study["fillers"][:lag]:
            events.append({**base, "role": "filler", "observation": filler})
        events.append({**base, "role": "target", "observation": family["target"]})
    return {"study_id": study["id"], "study_sha256": digest(study), "participant": participant,
            "list": participant % 4, "events": [{**event, "order": i} for i, event in enumerate(events)]}


def inventory(study):
    values = {}
    for family in study["families"]:
        for observation in [family["target"], *family["conditions"].values()]:
            values[digest(observation)] = observation
    for observation in study["fillers"]:
        values[digest(observation)] = observation
    return values


def prepare(study, *, grammars=None):
    validate_study(study)
    results, coverage = {}, {}
    observations = inventory(study)
    for grammar in grammars or study["grammars"]:
        engine = create_engine(grammar)
        try:
            analyses = {key: engine.analyse(Observation(**value), trace=False) for key, value in observations.items()}
        finally:
            engine.close()
        supported_families = []
        for family in study["families"]:
            required = [family["target"], *family["conditions"].values(), *study["fillers"]]
            if all(analyses[digest(value)].supported for value in required):
                supported_families.append(family["id"])
        coverage[grammar] = {"observations": len(analyses), "statuses": dict(Counter(a.status for a in analyses.values())),
                             "supported_families": supported_families,
                             "failures": [{"observation": observations[k], "status": a.status}
                                          for k, a in analyses.items() if not a.supported]}
        results[grammar] = analyses
    common = sorted(set.intersection(*(set(c["supported_families"]) for c in coverage.values())))
    return results, {"grammars": coverage, "common_families": common,
                     "criterion": "Every prime alternative, target and intervening filler must be supported"}


def replay_schedule(study, participant, config, analyses):
    memory = Memory(config.memory, config.decay)
    rows = []
    for event in schedule(study, participant)["events"]:
        analysis = analyses[digest(event["observation"])]
        values = cues(analysis, config.representation)
        activation = memory.activation(values) if values is not None else None
        if event["role"] == "target":
            rows.append({"participant": participant, "family": event["family"], "condition": event["condition"],
                         "lag": event["lag"], "order": event["order"], "activation": activation,
                         "supported": analysis.supported})
        memory.observe(values or ())
    return rows


def interactive_demo(study, config, family_id, condition, lag):
    family = next((f for f in study["families"] if f["id"] == family_id), None)
    if family is None or condition not in family["conditions"] or lag not in study["lags"]:
        raise ValueError("Unknown study family or condition")
    session = Session(config)
    try:
        for value in [family["conditions"][condition], *study["fillers"][:lag], family["target"]]:
            session.observe(Observation(**value))
        return {"study_id": study["id"], "configuration": config.to_dict(), "events": session.events,
                "scope": "Illustrative unfitted predictions; no human response used"}
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/experiments/pilot"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    study = prototype()
    (args.output / "study.json").write_text(json.dumps(study, ensure_ascii=False, indent=2))
    _, coverage = prepare(study, grammars=[*study["grammars"], "ccg-original-v1"])
    (args.output / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
    (args.output / "catalog.json").write_text(json.dumps(catalog(), indent=2))
    print(json.dumps({"output": str(args.output), "coverage": {g: len(c["supported_families"]) for g, c in coverage["grammars"].items()}}))


if __name__ == "__main__":
    main()
