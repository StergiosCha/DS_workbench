"""Workbench configuration and compact, honest decision summaries."""

from dylan.decision.client import DecisionClient
from dylan.decision.gates import measured_gate, evaluation_summary
from dylan.decision.provider import settings


def configuration(grammars):
    config = settings()
    return {
        "model": config["model"], "provider": config["provider"], "configured": bool(config["key"]),
        "grammars": {grammar: {"entry": measured_gate(grammar, 1, config["model"], config["provider"]),
                               "fanout": measured_gate(grammar, 2, config["model"], config["provider"]),
                               "evaluation": evaluation_summary(grammar, config["model"], config["provider"])} for grammar in grammars},
        "modes": ["off", "stub", "jev"],
        "description": "Jev orders existing choices using the prefix and tree; alternatives remain available.",
    }


def attach(parser, mode):
    if mode != "off":
        parser.decision_client = DecisionClient("stub" if mode == "stub" else "jev", runtime=mode == "jev")


def report(parser, mode):
    client = parser.decision_client
    records = client.records if client else []
    return {
        "mode": mode, "model": client.provider["model"] if client else settings()["model"],
        "provider": client.provider["provider"] if client else settings()["provider"],
        "active": any(r["action_taken"] == "runtime_ordering" for r in records),
        "live_calls": client.live_calls if client else 0,
        "latency_ms": round(sum(r["latency_ms"] for r in records), 3),
        "decisions": [{key: record.get(key) for key in (
            "idea", "word_index", "answers", "stub", "action_taken", "gate", "error", "cached",
        )} for record in records],
        "limits": "Priors break ties after the existing completion heuristics. Model ordering never removes candidates.",
    }
