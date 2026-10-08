"""Real DS runs isolate Jev's intervention, including failure and shared fallback."""
from contextlib import contextmanager
from copy import deepcopy
import io
import json

import pytest

from dylan import lexical_dictionary, lexical_provider
from dylan.decision.client import MODEL, uniform_answers
from dylan.lexical_expansion import proposal
from dylan.workbench_api import parse_request


@pytest.fixture
def environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_DECISION_PROVIDER", "typesafe")
    monkeypatch.setenv("TYPESAFE_API_KEY", "fixture-secret")
    monkeypatch.setenv("DS_EPHEMERAL_MODELS", "1")
    monkeypatch.setenv("DS_JEV_LOG", str(tmp_path / "jev.jsonl"))
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": False})
    monkeypatch.setattr(lexical_dictionary, "configuration", lambda: {"installed": True, "source": "fixture"})
    entries = [proposal("bank", "bank", "noun", ["object"], symbol="bank_n09213565", evidence="river side"),
               proposal("bank", "bank", "noun", ["object"], symbol="bank_n08420278", evidence="financial institution")]
    lookups = []
    def candidates(word):
        lookups.append(word)
        return (deepcopy(entries) if word == "bank" else []), []
    monkeypatch.setattr(lexical_dictionary, "candidates", candidates)
    calls = []
    @contextmanager
    def transport(req, **kwargs):
        body = json.loads(req.data)
        calls.append(body)
        answers = uniform_answers(body["questions"])
        for name, value in answers.items():
            selected = next(k for k, v in body["questions"][name]["criteria"].items()
                            if isinstance(v, dict) and v.get("sense_key") == "n08420278")
            value.update(choice=selected, confidence=.8)
            value["probabilities"] = {k: .9 if k == selected else .05 for k in value["probabilities"]}
        yield io.BytesIO(json.dumps({"model": MODEL, "answers": answers, "usage": {"cost": .0001}}).encode())
    monkeypatch.setattr("dylan.decision.client.request.urlopen", transport)
    return calls, lookups


def parse(backend="classical", **options):
    return parse_request({"sentence": "John gives Mary a bank.", "grammar": f"2026-english-{backend}",
                          "lexical_mode": "jev", "compare_jev": True, "strict": True, **options})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_two_actual_derivations_show_changed_sense_with_identical_inventory(environment, backend):
    calls, lookups = environment
    result = parse(backend)
    comparison = result["jev_comparison"]
    baseline, preferred = comparison["without_jev"], comparison["with_jev"]
    assert baseline["complete"] and preferred["complete"] and result["complete"]
    assert baseline["derivation"]["actions"] and preferred["derivation"]["actions"]
    assert "bank_n09213565" in baseline["meaning"]
    assert "bank_n08420278" in preferred["meaning"]
    assert comparison["same_inventory"] and baseline["inventory_hash"] == preferred["inventory_hash"]
    assert comparison["status"] == "changed"
    assert comparison["changes"][0]["word"] == "bank" and comparison["changes"][0]["index"] == 4
    assert len(result["lexical"]["entries"]) == 2 and lookups.count("bank") == 1
    assert len(calls) == comparison["live_calls"] == 1  # No Jev request in the baseline.
    assert calls[0]["state"]["prefix"] == ["john", "gives", "mary", "a"]
    assert calls[0]["state"]["word"] == "bank" and "sentence" not in calls[0]["state"]
    assert "fixture-secret" not in json.dumps(result)
    decision = result["lexical"]["selection"]["decisions"][0]
    assert decision["questions"] == calls[0]["questions"]
    assert sum(decision["answers"]["sense"]["probabilities"].values()) == pytest.approx(1)
    assert decision["cost_usd"] == .0001
    assert result["decision"]["mode"] == "off"
    if backend == "mltt":
        assert "bank_n08420278" in result["coq"]


def test_comparison_keeps_jev_on_and_model_fallback_off(environment, monkeypatch):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "propose", lambda *args: pytest.fail("Analysis LLM is off"))
    changed = parse(allow_model_fallback=False)
    assert changed["complete"] and changed["jev_comparison"]["live_calls"] > 0
    assert changed["lexical"]["allow_model_fallback"] is False
    missing = parse(sentence="Zephira walks.", allow_model_fallback=False)
    assert not missing["complete"]
    assert missing["lexical"]["model_requests"] == 0
    assert missing["jev_comparison"]["shared_model_candidates"] == 0


@pytest.mark.parametrize("mode", ["uncertain", "timeout", "invalid", "missing_key"])
def test_no_reliable_preference_does_not_fabricate_a_change(environment, monkeypatch, mode):
    if mode == "missing_key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    else:
        @contextmanager
        def unavailable(req, **kwargs):
            if mode == "timeout":
                raise TimeoutError("fixture timeout")
            answers = uniform_answers(json.loads(req.data)["questions"])
            for value in answers.values():
                value["choice"] = "uncertain"
            yield io.BytesIO(json.dumps({"model": MODEL, "answers": answers if mode == "uncertain" else {}}).encode())
        monkeypatch.setattr("dylan.decision.client.request.urlopen", unavailable)
    result = parse()
    comparison = result["jev_comparison"]
    assert result["complete"] and comparison["without_jev"]["complete"]
    assert comparison["same_inventory"] and comparison["changes"] == []
    assert comparison["without_jev"]["meaning"] == comparison["with_jev"]["meaning"]
    assert comparison["status"] == ("same" if mode == "uncertain" else "no_model_answer")


def test_unknown_word_proposal_is_shared_once_not_regenerated(environment, monkeypatch):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    proposals = []
    def propose(context, schema):
        proposals.append(context)
        return {"entries": [proposal("zephira", "zephira", "proper", ["human"], evidence="name")]}, {"provider": "fixture", "model": "small"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = parse(sentence="Zephira walks.")
    comparison = result["jev_comparison"]
    assert len(proposals) == 1 and proposals[0]["tokens"] == ["zephira"]
    assert result["complete"] and comparison["without_jev"]["complete"]
    assert comparison["same_inventory"] and comparison["shared_model_candidates"] == 1
    assert comparison["without_jev"]["meaning"] == comparison["with_jev"]["meaning"]
    assert comparison["status"] == "no_model_answer"  # No sense ambiguity; fallback is not Jev.


def test_incomplete_baseline_is_reported_as_inconclusive(environment):
    result = parse(sentence="John gives Mary a bank unknowableword.")
    assert not result["complete"] and result["jev_comparison"]["status"] == "inconclusive"
    assert result["jev_comparison"]["without_jev"]["failure"]["token"] == "unknowableword"


def test_baseline_timeout_preserves_primary_jev_parse(environment, monkeypatch):
    from dylan import workbench_api
    from dylan.paragraph_workbench import SentenceDeadline
    original = workbench_api.parse_request
    def timed_out(payload, *args, **kwargs):
        if kwargs.get("_setup") and kwargs.get("_trace") is False:
            raise SentenceDeadline("fixture baseline timeout")
        return original(payload, *args, **kwargs)
    monkeypatch.setattr(workbench_api, "parse_request", timed_out)
    result = parse()
    comparison = result["jev_comparison"]
    assert result["complete"] and comparison["status"] == "inconclusive"
    assert comparison["without_jev"]["failure"]["kind"] == "comparison_limit"
    assert "bank_n08420278" in comparison["with_jev"]["meaning"]


@pytest.mark.parametrize("options", [
    {"compare_jev": "true"}, {"lexical_mode": "dictionary"}, {"grammar": "2026-smg-classical"},
    {"grammar": "2026-english-ttr"}, {"decision_mode": "jev"}, {"n_best": 3},
    {"paragraph": "John walks."},
    {"dialogue": [{"speaker": "A", "text": "John walks.", "boundary": "continue"}]},
])
def test_unsupported_comparison_rejected_before_model_requests(environment, options):
    with pytest.raises(ValueError):
        parse(**options)
    assert not environment[0]


def test_interleaved_backends_do_not_share_bindings_or_mutate_original_grammar(environment):
    first = parse("classical")
    constructive = parse("mltt")
    second = parse("classical")
    for result in (first, constructive, second):
        assert result["complete"] and result["jev_comparison"]["same_inventory"]
    assert first["jev_comparison"]["without_jev"]["meaning"] == second["jev_comparison"]["without_jev"]["meaning"]
    original = parse_request({"grammar": "2026-english-classical", "sentence": "John walks.",
                              "_setup": {"programs": "untrusted"}})
    assert original["complete"] and "jev_comparison" not in original
