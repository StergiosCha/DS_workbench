"""Log-only triage, with an explicit whitelist to avoid annotation leakage."""

from dylan.decision.questions.triage_v1 import questions


def triage_result(result, client):
    if result.get("cap_hit") or (result.get("failure") or {}).get("kind") not in {
        "unresolved_parse_failure", "construction_gap"
    }:
        return None
    # Do not send glosses, source judgments, expected outcomes or gold phenomena.
    state = {
        "grammar": result.get("grammar"), "sentence_id": result.get("id"),
        "surface": result.get("surface", result.get("sentence")),
        "stats": result.get("stats", {}),
        "lexical_coverage": result.get("diagnostics", {}).get("lexical_coverage", []),
    }
    record = client.decide(state, questions(), idea=9)
    if record is None:
        return None
    return {"model": record["model"], "stub": record["stub"],
            "answers": record["answers"], "gate": "unmeasured",
            "route": "human_review", "display": False,
            "chunk_id": record["chunk_id"], "question_set_hash": record["question_set_hash"]}
