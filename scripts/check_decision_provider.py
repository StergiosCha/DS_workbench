"""One bounded Jev connection check; never installs a runtime calibration gate."""

import json

from dylan.decision.client import DecisionClient
from dylan.decision.questions.entry_v1 import questions
from dylan.workbench_environment import load_environment


if __name__ == "__main__":
    load_environment()
    entries = [{"id": "e0", "template": "noun", "params": ["book", "object"]},
               {"id": "e1", "template": "transitive", "params": ["book", "human", "object"]}]
    state = {"grammar": "2026-english-mltt", "tokens_so_far": ["a"],
             "next_word": "book", "entries": entries,
             "tree": {"pointer": "000", "nodes": [{"address": "000", "labels": ["?Ty(CN)"]}]}}
    record = DecisionClient("jev", log_path="build/decision/provider-check.jsonl").decide(
        state, questions(entries), idea=1, calibration=True,
        deterministic_order=["e0", "e1"],
    )
    print(json.dumps({key: record.get(key) for key in ["provider", "model", "stub", "answers", "latency_ms", "cost_usd", "gate", "error"]}))
    raise SystemExit(0 if not record["stub"] else 1)
