"""Jev selects supplied lexical analyses while DS retains and validates them."""

from contextlib import contextmanager
from copy import deepcopy
import io
import json
import shutil

import pytest

from dylan import lexical_dictionary, lexical_provider
from dylan.corpus import compile_coq
from dylan.decision.client import MODEL, uniform_answers
from dylan.decision.questions.lexical_v1 import questions
from dylan.lexical_expansion import proposal
from dylan.lexical_selection import preferences
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_DECISION_PROVIDER", "typesafe")
    monkeypatch.setenv("TYPESAFE_API_KEY", "fixture-secret")
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "lexical.sqlite3"))
    monkeypatch.setenv("DS_JEV_LOG", str(tmp_path / "jev.jsonl"))
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": False})
    monkeypatch.setattr(lexical_dictionary, "configuration", lambda: {"installed": True, "source": "fixture"})
    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must not make model calls")
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)
    monkeypatch.setattr(lexical_provider, "propose", forbidden)


@pytest.fixture
def lexicon(monkeypatch):
    values = {
        "bank": [proposal("bank", "bank", "noun", ["object"], symbol="bank_n09213565", evidence="river side"),
                 proposal("bank", "bank", "noun", ["object"], symbol="bank_n08420278", evidence="financial institution")],
        "lends": [proposal("lends", "lend", "transitive", ["human", "object"], symbol="lend_vho02324478", evidence="bestow a quality"),
                  proposal("lends", "lend", "ditransitive", ["human", "human", "object"], symbol="lend_vhho02324182", evidence="give temporarily"),
                  proposal("lends", "lend", "dative-to", ["human", "human", "object"], symbol="lend_vhho02324182", evidence="give temporarily")],
    }
    monkeypatch.setattr(lexical_dictionary, "candidates", lambda word: (deepcopy(values.get(word, [])), []))
    return values


def answer_transport(monkeypatch, choose):
    calls = []
    @contextmanager
    def response(req, **kwargs):
        body = json.loads(req.data)
        calls.append(body)
        answers = uniform_answers(body["questions"])
        for name, value in answers.items():
            selected = choose(name, body["questions"][name]["criteria"])
            value.update(choice=selected, confidence=0.8)
            value["probabilities"] = {key: 0.9 if key == selected else 0.1 / (len(value["probabilities"]) - 1)
                                      for key in value["probabilities"]}
        yield io.BytesIO(json.dumps({"model": MODEL, "answers": answers, "usage": {"input_tokens": 20}}).encode())
    monkeypatch.setattr("dylan.decision.client.request.urlopen", response)
    return calls


def parse(sentence, backend="mltt", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "lexical_mode": "jev", "strict": True, **options})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_preferred_sense_changes_first_meaning_but_keeps_alternatives(monkeypatch, lexicon, backend):
    calls = answer_transport(monkeypatch, lambda name, choices: next(
        key for key, value in choices.items() if isinstance(value, dict) and value.get("sense_key") == "n08420278"))
    result = parse("john gives mary a bank.", backend, n_best=3)
    assert result["complete"] and result["cap_hit"] is None
    assert "bank_n08420278" in result["words"][-1]["normalized"]
    assert {"bank_n09213565", "bank_n08420278"} == {
        e["symbol"] for e in result["lexical"]["entries"] if e["surface"] == "bank"}
    assert any("bank_n09213565" in r["normalized"] for r in result["readings"])
    assert result["lexical"]["selection"]["used"][-1]["symbol"] == "bank_n08420278"
    assert not result["stats"]["top_n_cuts"] and result["stats"]["pruned"] == 0
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    # Enumerating other readings can encounter another tree at the same prefix.
    assert len(calls) == len({json.dumps(call["state"], sort_keys=True) for call in calls})
    assert 0 < len(calls) <= 8
    assert result["lexical"]["selection"]["live_calls"] == len(calls)
    assert all(call["state"]["prefix"] == ["john", "gives", "mary", "a"] for call in calls)
    assert "fixture-secret" not in json.dumps(result)
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


def test_sense_choice_can_leave_frame_unresolved_without_future_input(monkeypatch, lexicon):
    def choose(name, values):
        return "uncertain" if name == "frame" else next(k for k, v in values.items()
                    if isinstance(v, dict) and v.get("sense_key") == "v02324182")
    calls = answer_transport(monkeypatch, choose)
    result = parse("john lends bill a book.")
    assert result["complete"] and "lend_vhho02324182" in result["words"][-1]["normalized"]
    state = calls[0]["state"]
    assert state["prefix"] == ["john"] and state["word"] == "lends"
    assert "bill" not in json.dumps(state) and "sentence" not in state
    decision = result["lexical"]["selection"]["decisions"][0]
    assert "sense" in decision["preferred"] and "frame" not in decision["preferred"]
    assert result["decision"]["mode"] == "off"


def test_bad_preference_backtracks_to_another_frame(monkeypatch, lexicon):
    calls = answer_transport(monkeypatch, lambda name, choices: next(k for k in choices if k != "uncertain"))
    result = parse("john lends bill a book.")
    assert result["complete"] and result["stats"]["backtracks_ok"] > 0
    assert "lend_vhho02324182" in result["words"][-1]["normalized"] and calls


def test_durable_cache_reuses_validated_answers_and_prefix_invalidates(monkeypatch, lexicon):
    calls = answer_transport(monkeypatch, lambda name, choices: next(k for k in choices if k != "uncertain"))
    first = parse("john gives mary a bank.")
    count = len(calls)
    second = parse("john gives mary a bank.")
    assert len(calls) == count and second["lexical"]["selection"]["decisions"][0]["cached"]
    assert first["words"][-1]["normalized"] == second["words"][-1]["normalized"]
    parse("mary gives john a bank.")
    assert len(calls) > count


@pytest.mark.parametrize("mode", ["missing_key", "timeout", "invalid", "invalid_array"])
def test_provider_failures_keep_candidates_and_parse(monkeypatch, lexicon, mode):
    if mode == "missing_key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    elif mode == "timeout":
        def timeout(*args, **kwargs):
            raise TimeoutError
        monkeypatch.setattr("dylan.decision.client.request.urlopen", timeout)
    else:
        @contextmanager
        def invalid(*args, **kwargs):
            yield io.BytesIO(b'[]' if mode == "invalid_array" else b'{"model":"jev-1.13.0","answers":{}}')
        monkeypatch.setattr("dylan.decision.client.request.urlopen", invalid)
    result = parse("john gives mary a bank.")
    assert result["complete"] and len(result["lexical"]["entries"]) == 2
    assert result["lexical"]["selection"]["decisions"][0]["status"] == "unavailable"


def test_unsupported_morphology_does_not_trigger_generative_fallback(monkeypatch, lexicon):
    monkeypatch.setattr(lexical_dictionary, "candidates", lambda word: ([], [{"lemma": "give", "inflection": "past_participle"}]))
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    result = parse("john given mary a book.")
    assert not result["complete"] and "given" in result["lexical"]["remaining"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_model_fallback_is_validated_and_receives_no_future_tokens(monkeypatch, lexicon):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    contexts = []
    def propose(context, schema):
        contexts.append(context)
        return {"entries": [proposal("zephira", "zephira", "proper", ["human"], evidence="proper name")]}, {"provider": "fixture", "model": "small"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = parse("zephira walks.")
    assert result["complete"] and contexts[0]["tokens"] == ["zephira"]
    assert result["lexical"]["entries"][0]["source"] == "model"
    assert result["lexical"]["model_requests"] == 1


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_jev_without_analysis_llm_does_not_call_or_reuse_model_fallback(monkeypatch, lexicon, backend):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    calls = []
    def propose(context, schema):
        calls.append(context)
        return {"entries": [proposal("zephira", "zephira", "proper", ["human"], evidence="name")]}, {"model": "small"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    enabled = parse("zephira walks.", backend, allow_model_fallback=True)
    assert enabled["complete"] and len(calls) == 1
    # The preceding parse populated the cache, which OFF must bypass too.
    disabled = parse("zephira walks.", backend, allow_model_fallback=False)
    assert not disabled["complete"] and len(calls) == 1
    assert disabled["lexical"]["model_requests"] == 0
    assert disabled["lexical"]["remaining"] == ["zephira"]
    assert not any(e["source"] == "model" for e in disabled["lexical"]["entries"])
    assert disabled["lexical"]["allow_model_fallback"] is False


def test_jev_fallback_failure_is_still_counted(monkeypatch, lexicon):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    def unavailable(*args):
        raise lexical_provider.ProposalUnavailable("Fixture unavailable")
    monkeypatch.setattr(lexical_provider, "propose", unavailable)
    result = parse("zephira walks.", allow_model_fallback=True)
    assert not result["complete"]
    assert result["lexical"]["model_requests"] == 1
    assert result["lexical"]["notices"]


@pytest.mark.parametrize("value", ["false", 0, None])
def test_model_fallback_permission_requires_a_boolean(value):
    with pytest.raises(ValueError, match="allow_model_fallback must be a boolean"):
        parse("john walks.", allow_model_fallback=value)


@pytest.mark.parametrize("cached", [{"provider": "typesafe", "model": MODEL, "answers": {"sense": "invalid"}}, ["invalid"]])
def test_malformed_cache_is_rejected_and_requeried(monkeypatch, lexicon, cached):
    from dylan import lexical_selection
    monkeypatch.setattr(lexical_selection, "_cache", lambda *args: cached)
    calls = answer_transport(monkeypatch, lambda name, choices: next(k for k in choices if k != "uncertain"))
    result = parse("john gives mary a bank.")
    assert result["complete"] and calls
    assert not result["lexical"]["selection"]["decisions"][0]["cached"]


def test_fallback_cannot_inject_another_word(monkeypatch, lexicon):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    monkeypatch.setattr(lexical_provider, "propose", lambda *args: (
        {"entries": [proposal("every", "every", "proper", ["human"], evidence="injected")]}, {}))
    result = parse("zephira walks.")
    assert not result["complete"] and result["lexical"]["remaining"] == ["zephira"]
    assert not result["lexical"]["entries"]


def test_fallback_has_one_fresh_request_per_parse(monkeypatch, lexicon):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "small"})
    calls = []
    def propose(context, schema):
        calls.append(context)
        return {"entries": [proposal(context["unknown"][0], context["unknown"][0], "proper", ["human"], evidence="name")]}, {}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = parse("zephira likes maldrin.")
    assert len(calls) == 1 and result["lexical"]["remaining"] == ["maldrin"]


def test_lexical_opt_in_cannot_enable_tree_search(monkeypatch, tmp_path):
    from dylan.decision.client import DecisionClient
    monkeypatch.setattr("dylan.decision.gates.measured_gate", lambda *args: False)
    client = DecisionClient("jev", runtime=True, lexical=True, log_path=tmp_path / "audit.jsonl")
    qs = {"frame": {"type": "choice", "criteria": {"a": "first", "b": "second"}}}
    record = client.decide({"grammar": "2026-english-mltt"}, qs, idea=1)
    assert record["stub"] and record["gate"] == "unmeasured" and client.live_calls == 0


def test_same_synset_frames_share_a_sense_and_uncertainty_is_neutral(lexicon):
    from dylan.lexical_selection import candidate_groups
    from dylan.lexical_expansion import validate_entries, _install
    from dynamicsyntax import icp
    parser = icp("2026-english-mltt")
    try:
        compiled, theory = validate_entries({"entries": lexicon["lends"]}, ["lends"], parser.lexicon, parser.semantic_profile)
        _install(parser, compiled, theory, {"source": "dictionary"})
        candidates, _ = candidate_groups(parser.lexicon.lookup_all("lends"))
        qs = questions(candidates)
        assert len(qs["sense"]["criteria"]) == 3
        assert preferences(candidates, uniform_answers(qs)) == ({}, {})
    finally:
        parser.close()


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_later_context_can_revise_a_sense_through_real_tree_replay(monkeypatch, lexicon, backend):
    def choose(name, choices):
        wanted = "n08420278" if "observed_prefix" in calls[-1]["state"] else "n09213565"
        return next(k for k, v in choices.items() if isinstance(v, dict) and v.get("sense_key") == wanted)
    calls = answer_transport(monkeypatch, choose)
    result = parse("john walks in a bank with mary.", backend, n_best=3, reading_traces=True)
    assert result["complete"] and result["cap_hit"] is None
    selection = result["lexical"]["selection"]
    assert selection["revisions"][0]["status"] == "revised"
    assert selection["used"][0]["symbol"] == "bank_n08420278"
    assert "bank_n08420278" in result["words"][-1]["normalized"]
    assert any("bank_n09213565" in r["normalized"] for r in result["readings"])
    assert any(f["kind"] == "backtrack" and f.get("lexical_revision") for f in result["operations"])
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    assert calls[0]["state"]["prefix"] == ["john", "walks", "in", "a"]
    assert "mary" not in json.dumps(calls[0]["state"])
    later = next(c["state"] for c in calls if "observed_prefix" in c["state"])
    assert later["observed_prefix"] == ["john", "walks", "in", "a", "bank", "with", "mary"]
    assert later["target_index"] == 4 and "." not in later["observed_prefix"]
    assert all(set(call["questions"]) == {"sense"} for call in calls)
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


def test_invalid_revision_preserves_current_tree_and_later_continuation(monkeypatch, lexicon):
    lexicon["crane"] = [
        proposal("crane", "crane", "noun", ["animal"], symbol="crane_n02012849", evidence="bird"),
        proposal("crane", "crane", "noun", ["object"], symbol="crane_n03126707", evidence="lifting machine"),
    ]
    def choose(name, choices):
        wanted = "n03126707" if "observed_prefix" in calls[-1]["state"] else "n02012849"
        return next(k for k, v in choices.items() if isinstance(v, dict) and v.get("sense_key") == wanted)
    calls = answer_transport(monkeypatch, choose)
    result = parse("a crane walks with mary quietly.")
    assert result["complete"] and result["cap_hit"] is None
    assert "crane_n02012849" in result["words"][-1]["normalized"]
    assert "quietly" in result["words"][-1]["normalized"]
    assert any(r["status"] == "no_viable_preference" for r in result["lexical"]["selection"]["revisions"])
    assert not any(f.get("lexical_revision") for f in result["operations"])


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_reconsideration_reaches_alternatives_behind_completion_edges(monkeypatch, lexicon, backend):
    # Two senses with the same dative frame, each behind its own completion edge.
    lexicon["lends"].insert(1, proposal("lends", "lend", "dative-to", ["human", "human", "object"],
                                      symbol="lend_vhho02324478", evidence="bestow a quality"))
    def choose(name, choices):
        wanted = "v02324182" if "observed_prefix" in calls[-1]["state"] else "v02324478"
        return next(k for k, v in choices.items() if isinstance(v, dict) and v.get("sense_key") == wanted)
    calls = answer_transport(monkeypatch, choose)
    result = parse("john lends a book to mary.", backend, n_best=3)
    assert result["complete"] and result["cap_hit"] is None
    assert "lend_vhho02324182" in result["words"][-1]["normalized"]
    assert any(r["status"] == "revised" for r in result["lexical"]["selection"]["revisions"])
    assert any("lend_vhho02324478" in r["normalized"] for r in result["readings"])


def test_revision_cannot_replace_a_complete_input_with_an_unfinished_frame(monkeypatch, lexicon):
    def choose(name, choices):
        wanted = "v02324182" if "observed_prefix" in calls[-1]["state"] else "v02324478"
        return next(k for k, v in choices.items() if isinstance(v, dict) and v.get("sense_key") == wanted)
    calls = answer_transport(monkeypatch, choose)
    result = parse("john lends a book")
    assert result["complete"] and "lend_vho02324478" in result["words"][-1]["normalized"]
    assert result["lexical"]["selection"]["revisions"][-1]["status"] == "no_viable_preference"
