"""Causal clauses must preserve both contents, modifiers, scope and DS checks."""
import shutil

import pytest

from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    reset_all_meta_bindings()
    def forbidden(*a, **kw):
        pytest.fail("Causal grammar tests must work without a model")
    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    yield
    reset_all_meta_bindings()


def parse(sentence, backend="mltt", language="english", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-{language}-{backend}",
                          "strict": True, **options}, _trace=False)


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("punctuation", ["", "."])
def test_reported_sentence_without_llm_preserves_reason_time_and_reference(backend, punctuation):
    result = parse("George opened the door because he came later" + punctuation, backend, lexical_mode="dictionary")
    assert result["complete"] and result["derivation"]["actions"]
    meaning = result["words"][-1]["normalized"]
    assert meaning.startswith("because(open_") and "later(come_" in meaning
    assert meaning.count("george") == 2 and "(him)" not in meaning
    assert any("him interpreted as george" in note for note in result["words"][-1]["context_assumptions"])
    assert all(e["source"] != "model" for e in result["lexical"]["entries"])
    assert not result["lexical"]["remaining"]
    assert any("L" in n["id"] for n in result["words"][-1]["nodes"])
    if backend == "mltt" and shutil.which("coqc"):
        assert "Parameter because : Type -> Type -> Prop." in result["coq"]
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,sentence,expected", [
    ("english", "John walks because Mary walks.", "because(walk(john), walk(mary))"),
    ("english", "Because Mary walks, John walks.", "because(walk(john), walk(mary))"),
    ("english", "John does not walk because Mary walks later.", "because(¬(walk(john)), later(walk(mary)))"),
    ("english", "John walks because Mary walks quickly.", "because(walk(john), quickly(walk(mary)))"),
    ("english", "Because Mary walks later, John walks today.", "because(today(walk(john)), later(walk(mary)))"),
    ("english", "John walks because Mary does not walk.", "because(walk(john), ¬(walk(mary)))"),
    ("smg", "Ο Γιώργος περπατάει επειδή η Μαρία περπατάει.", "because(walk(giorgos), walk(maria))"),
    ("smg", "Ο Γιώργος περπατάει διότι η Μαρία περπατάει αργότερα.", "because(walk(giorgos), later(walk(maria)))"),
    ("smg", "Επειδή η Μαρία περπατάει αργότερα, ο Γιώργος περπατάει σήμερα.", "because(today(walk(giorgos)), later(walk(maria)))"),
    ("smg", "Ο Γιώργος περπατάει επειδή δεν περπατάει η Μαρία.", "because(walk(giorgos), ¬(walk(maria)))"),
])
def test_clause_order_modifiers_and_negation(backend, language, sentence, expected):
    result = parse(sentence, backend, language)
    assert result["complete"], result["failure"]
    assert result["words"][-1]["normalized"] == expected
    assert all(not n["requirements"] for n in result["words"][-1]["nodes"])


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,sentence", [
    ("english", "John walks because."), ("english", "John walks because Mary."),
    ("english", "Because Mary walks."), ("english", "Because Mary walks, John."),
    ("english", "Because Mary walks John walks."), ("english", "Because, John walks."),
    ("english", "John walks because of Mary."), ("english", "John walks because because Mary walks."),
    ("smg", "Ο Γιώργος περπατάει επειδή."), ("smg", "Επειδή η Μαρία περπατάει."),
    ("smg", "Επειδή η Μαρία περπατάει, ο Γιώργος."),
])
def test_missing_arguments_and_unsupported_reason_forms_stay_incomplete(backend, language, sentence):
    result = parse(sentence, backend, language)
    assert not result["complete"], result["words"][-1]["normalized"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_both_quantified_contents_close_locally(backend):
    result = parse("A man walks because a dog walks later.", backend)
    assert result["complete"]
    meaning = result["words"][-1]["normalized"]
    if backend == "mltt":
        assert meaning == "because(Σ x:man. walk(x), Σ x:dog. later(walk(x)))"
        if shutil.which("coqc"):
            assert compile_coq(result["coq"], {}) == "passed"
    else:
        assert meaning.startswith("because(walk(ε ") and "later(walk(ε " in meaning


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_embedding_retains_two_causal_attachment_readings(backend):
    result = parse("John thinks Mary walks because Bill shouts.", backend, n_best=4)
    assert result["complete"]
    readings = {r["normalized"] for r in result["readings"]}
    assert "think(john, because(walk(mary), shout(bill)))" in readings
    assert "because(think(john, walk(mary)), shout(bill))" in readings
    assert all("because(" in m and "shout(bill)" in m for m in readings)


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_preposed_reason_modifiers_cannot_be_lost_during_alternative_search(backend):
    result = parse("Because Mary walks later, John walks today.", backend, n_best=6)
    assert result["complete"]
    assert result["readings"]
    for reading in result["readings"]:
        assert "later(walk(mary))" in reading["normalized"]
        assert "today(" in reading["normalized"] and "because(" in reading["normalized"]
        assert "today(walk(mary))" not in reading["normalized"]


def test_tree_replay_matches_the_causal_result():
    result = parse_request({"sentence": "John walks because Mary walks later.", "grammar": "2026-english-mltt"})
    assert result["complete"]
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    assert not any(frame["type_errors"] for frame in result["operations"])
    assert any(str(a).endswith("L") for frame in result["operations"] for a in frame.get("delta", {}).get("created", []))
    assert result["operations"][-1]["normalized"] == "because(walk(john), later(walk(mary)))"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_nested_causes_and_pps_are_not_erased(backend):
    nested = parse("John walks because Mary walks because Bill shouts.", backend, n_best=4)
    assert nested["complete"]
    assert {"because(walk(john), because(walk(mary), shout(bill)))",
            "because(because(walk(john), walk(mary)), shout(bill))"} <= {r["normalized"] for r in nested["readings"]}
    pp = parse("John walks because Mary walks in a park.", backend)
    assert pp["complete"] and "because(" in pp["words"][-1]["normalized"]
    assert "in_location(" in pp["words"][-1]["normalized"] and "walk(mary)" in pp["words"][-1]["normalized"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text", [
    ("english", "George opened the door because he came later. Because Mary walks, John walks today."),
    ("smg", "Ο Γιώργος περπατάει επειδή η Μαρία περπατάει αργότερα. Επειδή η Μαρία περπατάει, ο Γιώργος περπατάει σήμερα."),
])
def test_causal_paragraph_retains_each_sentence(backend, language, text):
    result = parse_request({"paragraph": text, "grammar": f"2026-{language}-{backend}",
                            "lexical_mode": "dictionary" if language == "english" else "corpus"})
    assert result["complete"] and len(result["sentences"]) == 2
    assert all(s["complete"] and "because(" in s["result"]["words"][-1]["normalized"] for s in result["sentences"])
