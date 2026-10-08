"""Polar content, per-word speaker binding and context-dependent short answers."""
import shutil

import pytest

from dylan import lexical_provider
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


def dialogue(backend, turns, *, trace=False, lexical_mode="off"):
    return parse_request({"grammar": f"2026-english-{backend}", "lexical_mode": lexical_mode,
                          "dialogue": [{"speaker": speaker, "text": text, **options}
                                       for speaker, text, options in turns]}, _trace=trace)


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("lexical_mode", ["off", "dictionary"])
def test_reported_shared_question_is_verified_without_llm(backend, lexical_mode, monkeypatch):
    def no_model(*args, **kwargs):
        raise AssertionError("Closed-class dialogue rules must not call the model")
    monkeypatch.setattr(lexical_provider, "propose", no_model)
    r = dialogue(backend, [("A", "Did you burn", {}), ("B", "myself?", {}), ("A", "No", {})],
                 trace=True, lexical_mode=lexical_mode)
    assert r["complete"], r["failure"]
    assert r["tokens"] == ["did", "you", "burn", "myself", "?", "no"]
    assert r["words"][-1]["semantics"] == "¬(burn(speaker_B, speaker_B))"
    assert r["words"][-1]["active_words"] == [5]
    assert r["words"][-1]["speech_act"] == {
        "kind": "polarity_answer", "polarity": "no", "question_content": "burn(speaker_B, speaker_B)", "speaker": "A"}
    question, = r["context_trees"]
    assert question["complete"] and question["semantics"] == "burn(speaker_B, speaker_B)"
    assert question["speech_act"]["kind"] == "polar_question" and not question["speech_act"]["asserted"]
    assert question["reflexive_bindings"][0]["antecedent_label"] == "B"
    assert question["reflexive_bindings"][0]["subject_node"] == "00"
    assert all(t["boundary"] == "continue" for t in r["dialogue"])
    assert any(f["label"] == "Answer tree" for f in r["words"])
    assert any("¬" in f["label"] for f in r["operations"] if f["word_index"] == 5)
    assert all(not f["type_errors"] for f in r["operations"])
    assert any(f["reflexive_bindings"] and f["speaker"] == "B" for f in r["operations"])
    assert all(item["known"] for item in r["diagnostics"]["lexical_coverage"])
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(r["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("boundary,punctuation", [("continue", "?"), ("new_tree", "?"), ("continue", "")])
def test_positive_answer_and_reverse_person_shift(backend, boundary, punctuation):
    r = dialogue(backend, [("A", "Did I burn", {}), ("B", "yourself" + punctuation, {}),
                           ("A", "Yes.", {"boundary": boundary})])
    assert r["complete"], r["failure"]
    assert r["words"][-1]["semantics"] == "burn(speaker_A, speaker_A)"
    assert r["words"][-1]["speech_act"]["polarity"] == "yes"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("turns,token", [
    ([("A", "Did you burn myself?", {})], "myself"),
    ([("A", "Did you burn", {}), ("B", "yourself?", {})], "yourself"),
    ([("A", "Did I burn", {}), ("B", "myself?", {})], "myself"),
    ([("A", "Did John burn", {}), ("B", "No", {})], "no"),
    ([("A", "No.", {})], "no"),
    ([("A", "John walks.", {}), ("B", "No", {"boundary": "new_tree"})], "no"),
    ([("A", "Did John walk?", {}), ("B", "Mary walks.", {"boundary": "new_tree"}),
      ("A", "No", {"boundary": "new_tree"})], "no"),
])
def test_binding_and_answer_context_are_not_guessed(backend, turns, token):
    r = dialogue(backend, turns)
    assert not r["complete"]
    assert r["failure"]["token"] == token
    assert r["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence,expected", [
    ("Did John burn himself?", "burn(john, john)"),
    ("Does Mary burn herself?", "burn(mary, mary)"),
    ("John thinks that Mary burns herself.", "think(john, burn(mary, mary))"),
])
def test_local_binding_composes_with_questions_and_embedding(backend, sentence, expected):
    r = parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}"}, _trace=False)
    assert r["complete"], r["failure"]
    assert r["words"][-1]["semantics"] == expected


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence,token", [
    ("Did John burns himself?", "burns"), ("John burns herself.", "herself"),
    ("John thinks that Mary burns himself.", "himself"), ("Every woman burns himself.", "himself"),
    ("All people burn himself.", "himself"), ("We burn themselves.", "themselves"),
])
def test_bare_verb_locality_and_known_features_constrain_the_derivation(backend, sentence, token):
    r = parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}", "lexical_mode": "dictionary"}, _trace=False)
    assert not r["complete"] and r["failure"]["token"] == token


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("subject,reflexive", [("Every man", "himself"), ("A man", "himself"), ("All people", "themselves")])
def test_quantified_binding_stays_inside_its_scope_and_negative_answer(backend, subject, reflexive):
    r = dialogue(backend, [("A", f"Did {subject} burn {reflexive}?", {}), ("B", "No", {})], lexical_mode="dictionary")
    assert r["complete"], r["failure"]
    content = r["context_trees"][0]["normalized"]
    if backend == "classical" and subject != "All people":
        choice = "τ" if subject == "Every man" else "ε"
        assert content == f"burn({choice} x0:e. man(x0), {choice} x0:e. man(x0))"
    else:
        assert "burn(x, x)" in content
    assert r["words"][-1]["normalized"].startswith("¬")
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(r["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_repair_of_answer_preserves_the_question_and_original_no(backend):
    r = dialogue(backend, [("A", "Did you burn", {}), ("B", "myself?", {}), ("A", "No sorry Yes", {})], trace=True)
    assert r["complete"], r["failure"]
    assert len(r["context_trees"]) == 1
    assert r["words"][-1]["semantics"] == "burn(speaker_B, speaker_B)"
    assert r["tokens"][5:] == ["no", "sorry", "yes"]
    assert r["repairs"][0]["replaced"] == [5]
