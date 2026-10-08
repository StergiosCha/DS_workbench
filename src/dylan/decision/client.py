"""Pinned TypeSafe transport with neutral stubs and separately authorized calibration."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
import ssl
import time
from urllib import error, request

import certifi

from dylan.decision.log import append_jsonl
from dylan.decision.provider import DIRECT_MODEL, OPENROUTER_MODEL, settings

MODEL = DIRECT_MODEL


def content_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def uniform_answers(questions):
    answers = {}
    for key, question in questions.items():
        kind = question["type"]
        if kind == "noul":
            answers[key] = {"type": "noul", "noul": 0.5}
            continue
        criteria = question["criteria"]
        options = list(criteria) if kind == "choice" else list(map(str, range(len(criteria))))
        if len(options) < 2:
            raise ValueError("A decision needs at least two alternatives")
        value = {"type": kind, "probabilities": {o: 1 / len(options) for o in options}, "confidence": 0.0}
        if kind == "choice":
            value["choice"] = options[0]
        elif kind == "score":
            value.update(score=(len(options) - 1) / 2, legend=dict(zip(options, criteria)))
        else:
            raise ValueError(f"Unsupported primitive: {kind}")
        answers[key] = value
    return answers


def validate_answers(answers, questions):
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("Response question ids differ from the request")
    def probability(value):
        return type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1
    for key, question in questions.items():
        value = answers[key]
        if not isinstance(value, dict) or value.get("type") != question["type"]:
            raise ValueError("Response primitive differs from the request")
        if question["type"] == "noul":
            if not probability(value.get("noul")):
                raise ValueError("Invalid Noul probability")
            continue
        expected = set(question["criteria"]) if question["type"] == "choice" else set(map(str, range(len(question["criteria"]))))
        probs = value.get("probabilities", {})
        if (not isinstance(probs, dict) or set(probs) != expected or not all(probability(p) for p in probs.values())
                or not math.isclose(sum(probs.values()), 1, abs_tol=1e-5)
                or not probability(value.get("confidence"))):
            raise ValueError("Invalid decision distribution")
        if question["type"] == "choice" and (value.get("choice") not in expected
                or probs[value["choice"]] != max(probs.values())):
            raise ValueError("Invalid Choice selection")
        if question["type"] == "score":
            mean = sum(int(level) * prob for level, prob in probs.items())
            score = value.get("score")
            legend = {str(i): description for i, description in enumerate(question["criteria"])}
            if value.get("legend") != legend:
                raise ValueError("Invalid Score legend")
            if type(score) not in {int, float} or not math.isfinite(score) or not math.isclose(score, mean, abs_tol=1e-5):
                raise ValueError("Score differs from its probability-weighted mean")
    return answers


class DecisionClient:
    def __init__(self, mode=None, *, log_path=None, runtime=False, recorded=None, lexical=False):
        self.mode = mode or os.getenv("DS_DECISION_MODEL", "stub")
        if self.mode not in {"off", "stub", "jev", MODEL, OPENROUTER_MODEL}:
            raise ValueError("Decision mode must be off, stub, or the pinned model")
        self.provider = settings()
        if self.mode in {MODEL, OPENROUTER_MODEL}:
            # An explicit version must never silently select another vendor.
            if self.mode != self.provider["model"]:
                self.provider = {
                    "provider": "typesafe" if self.mode == MODEL else "openrouter",
                    "model": self.mode,
                    "endpoint": "https://api.typesafe.ai/v1/systemone" if self.mode == MODEL
                    else "https://openrouter.ai/api/v1/systemone",
                    "key": os.getenv("TYPESAFE_API_KEY" if self.mode == MODEL else "OPENROUTER_API_KEY", ""),
                }
        self.log_path = log_path or os.getenv("DS_JEV_LOG", ".ds-workbench/jev.jsonl")
        self.runtime = runtime
        self.lexical = lexical
        self.recorded = recorded or {}
        self.records = []
        self.cache = {}
        self.live_calls = 0

    def decide(self, state, questions, *, idea, calibration=False, deterministic_order=(), replay_context=None):
        """Return a log record; search ordering needs opt-in and a measured gate.

        The parser cannot activate live inference merely by setting an environment
        variable. Explicit lexical selection can request purpose 6 independently;
        the entry/tree search hooks still require their measured gates.
        """
        if self.mode == "off":
            return None
        start = time.perf_counter()
        answers = uniform_answers(questions)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(), "model": "stub",
            "requested_model": self.provider["model"], "provider": self.provider["provider"],
            "question_set_hash": content_hash(questions), "chunk_id": content_hash(state),
            "idea": idea, "grammar": state.get("grammar"), "sentence_id": state.get("sentence_id"),
            "word_index": state.get("word_index"), "candidate_ids": list(deterministic_order),
            "answers": answers, "action_taken": "none", "deterministic_order": list(deterministic_order),
            "stub": True, "input_tokens": 0, "state": state, "questions": questions,
        }
        record.update(replay_context or {})
        model = self.provider["model"]
        cache_key = content_hash([self.provider["provider"], model, idea, state, questions])
        record["cache_key"] = cache_key
        recorded = self.recorded.get(cache_key)
        if recorded is not None:
            record.update(answers=validate_answers(recorded, questions), model=model,
                          stub=False, action_taken="recorded_ordering", recorded=True)
        elif self.mode not in {"off", "stub"}:
            from dylan.decision.gates import measured_gate

            key = self.provider["key"]
            permitted = calibration or (self.runtime and (
                (self.lexical and idea == 6) or measured_gate(
                    state.get("grammar"), idea, model, self.provider["provider"])))
            if not permitted:
                record["gate"] = "unmeasured"
            elif not key:
                record["gate"] = "unmeasured_no_key"
            elif cache_key in self.cache:
                record.update(self.cache[cache_key], cached=True)
            elif not calibration and self.live_calls >= 8:
                record["gate"] = "request_budget"
            else:
                payload = {"model": model, "state": state, "questions": questions}
                req = request.Request(self.provider["endpoint"], data=json.dumps(payload).encode(), method="POST",
                                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                try:
                    self.live_calls += 1
                    with request.urlopen(req, timeout=15 if calibration else 2,
                                         context=ssl.create_default_context(cafile=certifi.where())) as response:
                        result = json.load(response)
                    if not isinstance(result, dict) or result.get("model") != model:
                        raise ValueError("Provider returned a different model version")
                    values = {"answers": validate_answers(result["answers"], questions), "model": result["model"],
                              "input_tokens": result.get("usage", {}).get("input_tokens", 0),
                              "cost_usd": result.get("usage", {}).get("cost"), "stub": False,
                              "action_taken": "calibration_only" if calibration else
                              "lexical_ordering" if self.lexical and idea == 6 else "runtime_ordering"}
                    record.update(values)
                    if not calibration:
                        self.cache[cache_key] = values
                except error.HTTPError as exc:
                    record["error"] = f"Decision provider returned HTTP {exc.code}; deterministic order retained"
                except (error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
                    record["error"] = "Decision request failed; deterministic order retained"
        record["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
        self.records.append(record)
        append_jsonl(self.log_path, record)
        return record
