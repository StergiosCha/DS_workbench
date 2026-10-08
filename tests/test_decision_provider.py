"""Native OpenRouter transport, credential isolation and neutral fallbacks."""

from contextlib import contextmanager
import io
import json
from urllib.error import HTTPError

import pytest

from dylan.decision.client import DecisionClient, uniform_answers
from dylan.decision.provider import DIRECT_MODEL, OPENROUTER_MODEL, settings
from dylan.decision.questions.entry_v1 import questions
from dylan.decision.workbench import configuration
from dylan import lexical_provider


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for name in ("DS_DECISION_PROVIDER", "DS_DECISION_MODEL", "OPENROUTER_API_KEY",
                 "TYPESAFE_API_KEY", "DS_LEXICAL_PROVIDER", "DS_LEXICAL_MODEL",
                 "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT",
                 "OPENAI_API_KEY", "DS_LEXICAL_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Live inference is forbidden in the test suite")
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)
    monkeypatch.setattr(lexical_provider, "urlopen", forbidden)


def test_openrouter_key_routes_to_native_jev_not_chat(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-fixture")
    monkeypatch.setenv("TYPESAFE_API_KEY", "different-direct-fixture")
    qs = questions([{"id": "e0", "template": "noun", "params": ["book"]}])
    state = {"grammar": "2026-english-mltt", "tokens_so_far": ["a"], "next_word": "book"}
    calls = []

    @contextmanager
    def response(req, **kwargs):
        assert req.full_url == "https://openrouter.ai/api/v1/systemone"
        assert req.get_header("Authorization") == "Bearer openrouter-fixture"
        body = json.loads(req.data)
        assert body == {"model": OPENROUTER_MODEL, "state": state, "questions": qs}
        assert kwargs["timeout"] == 15
        calls.append(body)
        yield io.StringIO(json.dumps({"model": OPENROUTER_MODEL, "answers": uniform_answers(qs),
                                     "usage": {"input_tokens": 123, "cost": 0.00001}}))

    monkeypatch.setattr("dylan.decision.client.request.urlopen", response)
    client = DecisionClient("jev", log_path=tmp_path / "audit.jsonl")
    record = client.decide(state, qs, idea=1, calibration=True)
    assert len(calls) == 1 and not record["stub"]
    assert record["provider"] == "openrouter" and record["model"] == OPENROUTER_MODEL
    assert record["cost_usd"] == 0.00001 and record["action_taken"] == "calibration_only"
    public = json.dumps([record, configuration(["2026-english-mltt"])])
    assert "openrouter-fixture" not in public and "different-direct-fixture" not in public


def test_explicit_provider_never_borrows_another_providers_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-fixture")
    monkeypatch.setenv("DS_DECISION_PROVIDER", "typesafe")
    assert settings()["key"] == "" and settings()["model"] == DIRECT_MODEL
    assert DecisionClient(OPENROUTER_MODEL).provider["key"] == "openrouter-fixture"
    monkeypatch.setenv("DS_DECISION_PROVIDER", "invalid")
    with pytest.raises(ValueError, match="DS_DECISION_PROVIDER"):
        settings()


@pytest.mark.parametrize("failure", ["http", "version", "answers"])
def test_provider_failures_preserve_deterministic_order_and_redact(monkeypatch, tmp_path, failure):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-fixture")
    qs = questions([{"id": "e0", "template": "noun", "params": []}])

    @contextmanager
    def response(req, **kwargs):
        if failure == "http":
            raise HTTPError(req.full_url, 401, "secret-fixture", {}, io.BytesIO(b"secret-fixture"))
        yield io.StringIO(json.dumps({"model": "other-model" if failure == "version" else OPENROUTER_MODEL,
                                     "answers": {} if failure == "answers" else uniform_answers(qs)}))

    monkeypatch.setattr("dylan.decision.client.request.urlopen", response)
    record = DecisionClient("jev", log_path=tmp_path / "audit.jsonl").decide(
        {}, qs, idea=1, calibration=True, deterministic_order=["e0"],
    )
    assert record["stub"] and record["action_taken"] == "none"
    assert record["deterministic_order"] == ["e0"] and record["error"]
    assert "secret-fixture" not in json.dumps(record)


def test_openrouter_key_does_not_enable_uncalibrated_ordering(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-fixture")
    monkeypatch.setenv("DS_DECISION_GATES", str(tmp_path / "absent.json"))
    client = DecisionClient("jev", runtime=True, log_path=tmp_path / "audit.jsonl")
    qs = questions([{"id": "e0", "template": "noun", "params": []}])
    record = client.decide({"grammar": "2026-english-mltt"}, qs, idea=1)
    assert record["stub"] and record["gate"] == "unmeasured" and client.live_calls == 0


def test_lexical_model_uses_same_openrouter_key_and_json_schema(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-fixture")
    monkeypatch.setenv("DS_LEXICAL_PROVIDER", "openrouter")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://old-azure.example")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "old-azure-fixture")
    schema = {"type": "object", "properties": {}, "additionalProperties": False}

    @contextmanager
    def response(req, **kwargs):
        assert req.full_url == "https://openrouter.ai/api/v1/chat/completions"
        assert req.get_header("Authorization") == "Bearer openrouter-fixture"
        body = json.loads(req.data)
        assert body["model"] == "deepseek/deepseek-v4.1-flash"
        assert body["response_format"]["json_schema"]["schema"] == schema
        assert body["reasoning"] == {"enabled": False}
        yield io.BytesIO(json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}).encode())

    monkeypatch.setattr(lexical_provider, "urlopen", response)
    result, provider = lexical_provider.propose({}, schema)
    assert result == {} and provider["provider"] == "OpenRouter"
    assert "openrouter-fixture" not in json.dumps(lexical_provider.configuration())
    monkeypatch.setenv("DS_LEXICAL_PROVIDER", "openai")
    assert lexical_provider.settings()["key"] == ""


def test_gateway_keepalives_cannot_extend_lexical_read_forever(monkeypatch):
    class Keepalive:
        def read1(self, size):
            return b" "
    ticks = iter([0, 1, 14, 16])
    monkeypatch.setattr(lexical_provider.time, "monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError):
        lexical_provider._read_response(Keepalive(), deadline=15)


def test_lexical_response_size_limit_is_preserved():
    with pytest.raises(lexical_provider.ProposalUnavailable, match="exceeded"):
        lexical_provider._read_response(io.BytesIO(b" " * 65537), deadline=float("inf"))
