"""Source-based local feedback contrasts; native adaptations of HE21 Fig. 6."""
import pytest

from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    reset_all_meta_bindings()
    monkeypatch.setattr(lexical_provider, "propose", lambda *a, **k: pytest.fail("No model needed"))
    yield
    reset_all_meta_bindings()


def parse(parts, backend, **options):
    return parse_request({"grammar": f"2026-english-{backend}",
                          "dialogue": [{"speaker": "B" if i == 1 else "A", "text": p}
                                       for i, p in enumerate(parts)], **options})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("noun", ["John", "the man", "a man"])
def test_feedback_compiles_nominal_then_sentence_continues(backend, noun):
    result = parse([noun, "mhm", "walks."], backend)
    assert result["complete"], result["failure"]
    baseline = parse_request({"grammar": f"2026-english-{backend}", "sentence": noun + " walks."})
    assert result["words"][-1]["normalized"] == baseline["words"][-1]["normalized"]
    feedback = next(f for f in result["words"] if f["label"] == "mhm")
    assert not feedback["complete"] and feedback["requirement_count"] > 0
    event, = feedback["feedback_events"]
    assert event["node"] == "00" and event["pointer_after"] == "0"
    assert event["speaker"] == "B" and event["word"] == "mhm"
    assert not event["clause_complete"]
    assert len(result["words"][-1]["feedback_events"]) == 1
    assert result["context_trees"] == []
    assert all(not f["type_errors"] for f in result["operations"])
    assert any(f["kind"] == "operation" and f["word_index"] == len(noun.split())
               and f["feedback_events"] for f in result["operations"])
    if noun != "John":
        # Feedback waits for determiner/noun composition; it is not discarded
        # as an unknown word, nor attached just to the noun's CN leaf.
        assert event["type"] not in {"CN", "cn"}
        assert any(f["label"] == "elimination" and f["word_index"] == len(noun.split())
                   for f in result["actions"])


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("parts", [["mhm"], ["the", "mhm", "man walks."],
    ["John likes", "mhm", "Mary."], ["John gives a book to", "mm", "Mary."]])
def test_unfinished_unit_does_not_license_local_feedback(backend, parts):
    result = parse(parts, backend)
    assert not result["complete"] and result["failure"]["token"] in {"mhm", "mm"}
    assert all(not f["feedback_events"] for f in result["words"])
    assert all(w["known"] for w in result["diagnostics"]["lexical_coverage"])
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("clause", ["John walks.", "John likes Mary", "a man likes a woman"])
def test_two_complete_sisters_compile_before_feedback(backend, clause):
    result = parse([clause, "mm"], backend)
    assert result["complete"], result["failure"]
    event, = result["words"][-1]["feedback_events"]
    assert event["node"] == event["pointer_after"] == "0"
    assert event["clause_complete"]
    assert result["words"][-1]["speech_act"] is None


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_feedback_does_not_answer_or_assert_a_question(backend):
    result = parse(["Did John walk?", "mhm", "No"], backend)
    assert result["complete"], result["failure"]
    question, = result["context_trees"]
    assert question["feedback_events"][0]["content"] == "walk(john)"
    assert question["speech_act"]["kind"] == "polar_question"
    assert not question["speech_act"]["asserted"]
    assert result["words"][-1]["semantics"] == "¬(walk(john))"
    assert result["words"][-1]["feedback_events"] == []


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_repair_keeps_feedback_on_the_retained_subject(backend):
    result = parse(["John", "mhm", "likes Mary sorry Bill."], backend)
    assert result["complete"], result["failure"]
    assert result["words"][-1]["normalized"] == "like(john, bill)"
    event, = result["words"][-1]["feedback_events"]
    assert event["content"] == "john"


def test_streamed_feedback_frames_equal_returned_frames():
    events = []
    result = parse_request({"grammar": "2026-english-mltt", "dialogue": [
        {"speaker": "A", "text": "the man"}, {"speaker": "B", "text": "mhm"},
        {"speaker": "A", "text": "walks."}]}, on_event=events.append)
    for channel in ("words", "actions", "operations"):
        streamed = [events[0]["initial"]] + [e["frame"] for e in events
                     if e.get("event") == "frame" and e["channel"] == channel]
        assert streamed == result[channel]
