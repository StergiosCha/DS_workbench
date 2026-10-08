"""Distributive plurals require real quantifier derivations, not noun relabeling."""
import shutil
import subprocess

import pytest

from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.terms import parse_expr
from dylan.lexical_dictionary import candidates, is_plural_of
from dylan.workbench_api import parse_request

USER_TEXT = "A man opens the door and all people enter the room"


@pytest.fixture(autouse=True)
def clean_bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence", [
    USER_TEXT, "All children read a book.", "All black dogs walk.",
    "All the people enter the room.", "All the black dogs walk.",
    "John knows all people.", "John knows all the people.",
    "All women know all men.", "All sheep walk.",
])
def test_distributive_quantification_without_model_calls(backend, sentence, monkeypatch, tmp_path):
    def no_model(*args, **kwargs):
        raise AssertionError("This construction must run without any model call")
    monkeypatch.setattr(lexical_provider, "propose", no_model)
    result = parse_request({"paragraph": sentence, "grammar": f"2026-english-{backend}", "lexical_mode": "assisted"})
    assert result["complete"], result["sentences"][0]["failure"]
    parsed = result["sentences"][0]["result"]
    assert parsed["derivation"]["actions"]
    assert parsed["lexical"]["attempts"] == []
    meaning = parsed["words"][-1]["normalized"]
    assert ("∀" if backend == "classical" else "Π") in meaning
    if sentence == USER_TEXT:
        assert "∧" in meaning and "person_n00007846" in meaning
        assert "people_n" not in meaning
    if backend == "mltt" and shutil.which("coqc"):
        target = tmp_path / "Quantified.v"
        target.write_text(parsed["coq"])
        checked = subprocess.run(["coqc", str(target)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence", [
    "All person walks.", "All the person walks.", "A children walks.",
    "Every children walks.", "All the the children walk.", "All children.",
])
def test_plural_gate_does_not_accept_singular_or_missing_predicate(backend, sentence):
    result = parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}", "lexical_mode": "dictionary"}, _trace=False)
    assert not result["complete"]


def test_dictionary_people_are_individual_persons_and_keep_the_human_sort():
    entries, analyses = candidates("people")
    nouns = [e for e in entries if e["template"] in {"noun", "plural-noun"}]
    assert nouns and all(e["template"] == "plural-noun" and e["lemma"] == "person" for e in nouns)
    assert all(e["domains"] == ["human"] for e in nouns)
    assert any(a["inflection"] == "plural" for a in analyses)
    assert is_plural_of("people", "person") and is_plural_of("children", "child")
    assert not is_plural_of("people", "human")
    assert not is_plural_of("person", "person")


def test_classical_universal_is_capture_avoiding_and_round_trips():
    term = parse_expr("forall(x,e,implies(person(x),enter(x,y)))")
    assert "x" not in term.free() and "y" in term.free()
    changed = term.substitute("y", parse_expr("x"))
    assert changed.name != "x" and "x" in changed.free()
    assert parse_expr(changed.to_source()) == changed


def test_model_can_supply_a_plural_lexeme_with_an_individual_restrictor(monkeypatch):
    def provider(context, spec, **options):
        return {"entries": [{"surface": "glorps", "lemma": "glorp", "template": "plural-noun", "domains": ["object"],
                             "case": "none", "gender": "none", "person": "none", "number": "pl", "verb_form": "none",
                             "evidence": "Test novel count noun with regular plural morphology."}]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse_request({"sentence": "All glorps are here.", "grammar": "2026-english-mltt", "lexical_mode": "assisted"})
    assert result["complete"]
    assert "Π" in result["words"][-1]["normalized"]
    assert any(e["source"] == "model" and e["morphology"] == "plural" for e in result["lexical"]["entries"])


def test_unimplemented_closed_class_does_not_trigger_unrelated_model_calls(monkeypatch):
    def no_model(*args, **kwargs):
        raise AssertionError("A missing closed-class rule cannot be repaired by lexical proposals")
    monkeypatch.setattr(lexical_provider, "propose", no_model)
    result = parse_request({"paragraph": "Most zorbles enter the room. A man is here.", "grammar": "2026-english-mltt", "lexical_mode": "assisted"})
    assert not result["complete"]
    assert result["coverage"]["complete"] == 1
    first = result["sentences"][0]["result"]
    assert first["failure"]["token"] == "most"
    assert first["lexical"]["attempts"] == []
    assert any("no model retry" in n for n in first["lexical"]["notices"])


def test_rate_limit_stops_calls_for_the_remaining_paragraph(monkeypatch):
    calls = []
    def limited(*args, **kwargs):
        calls.append(1)
        raise lexical_provider.ProposalUnavailable("Lexical provider returned HTTP 429.")
    monkeypatch.setattr(lexical_provider, "propose", limited)
    result = parse_request({"paragraph": "A zorbler walks. A glorp is here. A man is here.", "grammar": "2026-english-mltt", "lexical_mode": "assisted"})
    assert len(calls) == 1
    assert result["coverage"]["complete"] == 1
    assert result["sentences"][0]["result"]["lexical"]["attempts"][0]["status"] == "unavailable"


def test_human_quantifier_does_not_weaken_selectional_types():
    result = parse_request({"sentence": "All stones sleep.", "grammar": "2026-english-mltt", "lexical_mode": "dictionary"}, _trace=False)
    assert not result["complete"]
