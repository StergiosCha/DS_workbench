"""Rule playback must expose DS computation without changing its outcome."""

import pytest

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.workbench_api import parse_request
from dylan.workbench_readings import RuleTraceBudget


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("grammar,text", [
    ("2026-english-classical", "a man walks."),
    ("2026-english-mltt", "a man walks."),
    ("2026-smg-classical", "της τον έδωσε."),
    ("2026-smg-mltt", "της τον έδωσε."),
    ("2015-english-ttr", "a man knows you."),
])
def test_rules_stream_between_words_and_end_at_the_same_tree(grammar, text):
    payload = {"grammar": grammar, "sentence": text,
               "lexical_mode": "corpus" if "smg" in grammar else "off"}
    plain = parse_request(payload, _trace=False)
    reset_all_meta_bindings()
    events = []
    result = parse_request(payload, events.append, _trace="actions")
    assert result["complete"] and plain["complete"]
    assert result["words"][-1]["nodes"] == plain["words"][-1]["nodes"]
    assert result["operations"] == []
    assert result["trace_level"] == "actions"
    rules = [f for f in result["actions"] if f["kind"] == "action"]
    assert {f["rule_kind"] for f in rules} >= {"lexical", "computational"}
    assert any(f["rule"] == "elimination" and f["delta"]["decorations"] for f in rules)
    assert next(i for i, f in enumerate(rules) if f["rule_kind"] == "computational") < max(i for i, f in enumerate(rules) if f["rule_kind"] == "lexical")
    assert [e["frame"] for e in events if e["event"] == "frame" and e["channel"] == "actions"] == result["actions"][1:]
    assert result["actions"][-1]["nodes"] == result["words"][-1]["nodes"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_assisted_rules_need_no_model_for_known_sentence(monkeypatch, backend):
    from dylan import lexical_provider
    def unexpected(*args, **kwargs):
        pytest.fail("Playback must not add a model request")
    monkeypatch.setattr(lexical_provider, "propose", unexpected)
    events = []
    result = parse_request({"grammar": f"2026-english-{backend}", "sentence": "a man walks.",
                            "lexical_mode": "assisted"}, events.append)
    assert result["complete"]
    assert result["lexical"]["attempts"] == []
    labels = [(f.get("rule_kind"), f["label"]) for f in result["actions"]]
    assert labels.index(("computational", "intro-pred")) < labels.index(("lexical", "a"))
    assert any(e["event"] == "frame" and e["frame"].get("rule_kind") == "computational" for e in events)


def test_snapshot_limit_is_an_explicit_jump_and_preserves_final_semantics():
    result = parse_request({"grammar": "2026-english-mltt", "sentence": "john walks."},
                           _trace="actions", _trace_budget=RuleTraceBudget(1))
    assert result["complete"] and result["trace_truncated"]
    assert result["actions"][-1]["kind"] == "trace_gap"
    assert result["actions"][-1]["normalized"] == "walk(john)"
    assert "budget" in result["trace_note"]
