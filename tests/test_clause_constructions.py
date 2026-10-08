"""Clause families, actual model-driven composition, and rejected hypotheses."""
from copy import deepcopy
import shutil

import pytest
from dynamicsyntax import icp
from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.construction_assistance import compile_proposals
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def parse(text, backend="mltt", language="english", **options):
    return parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}", "strict": True, **options}, _trace=False)


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("word,relation", [
    ("when", "when_clause"), ("whenever", "whenever_clause"),
    ("while", "while_clause"), ("before", "before_clause"),
    ("after", "after_clause"), ("since", "since_time"),
    ("until", "until_clause"), ("if", "condition"),
    ("unless", "unless_clause"), ("although", "concession"),
    ("though", "concession"), ("whereas", "contrast"),
])
def test_clause_family_preserves_order_and_distinct_relation_without_ai(monkeypatch, backend, word, relation):
    monkeypatch.setattr(lexical_provider, "propose", lambda *a, **k: pytest.fail("No model needed"))
    for text in [f"John walks {word} Mary walks later.", f"{word} Mary walks later, John walks."]:
        result = parse(text, backend)
        assert result["complete"], (text, result["failure"])
        assert result["words"][-1]["normalized"] == f"{relation}(walk(john), later(walk(mary)))"
        assert result["clause_constructions"][0]["relation"] == relation
        assert result["clause_constructions"][0]["surface"] == word
        assert all(not n["requirements"] for n in result["words"][-1]["nodes"])


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("word,relation", [
    ("όταν", "when_clause"), ("όποτε", "whenever_clause"),
    ("ενώ", "while_clause"), ("αφού", "after_clause"),
    ("αν", "condition"), ("εάν", "condition"),
    ("μολονότι", "concession"), ("παρότι", "concession"),
    ("ωσότου", "until_clause"),
])
def test_greek_clause_family(backend, word, relation):
    for text in [f"Ο Γιώργος περπατάει {word} η Μαρία περπατάει αργότερα.",
                 f"{word} η Μαρία περπατάει αργότερα, ο Γιώργος περπατάει."]:
        result = parse(text, backend, "smg")
        assert result["complete"], (text, result["failure"])
        assert result["words"][-1]["normalized"] == f"{relation}(walk(giorgos), later(walk(maria)))"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("text", ["John walks when.", "If Mary walks.", "Although Mary walks, John.",
    "John walks before Mary.", "John walks after walking.", "When Mary walks John walks.",
    "When does John walk?", "John walks because of Mary."])
def test_missing_clauses_or_other_uses_of_same_word_do_not_complete(backend, text):
    assert not parse(text, backend)["complete"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_composed_relations_preserve_subordinate_negation_and_modification(backend):
    result = parse("John walks when Mary does not walk because Bill shouts later.", backend, n_best=4)
    assert result["complete"]
    readings = {r["normalized"] for r in result["readings"]}
    assert "when_clause(walk(john), because(¬(walk(mary)), later(shout(bill))))" in readings
    assert all("when_clause(" in r and "because(" in r and "¬(walk(mary))" in r and "later(shout(bill))" in r for r in readings)


def test_constructive_local_contents_and_coq():
    result = parse("A man walks if a dog walks.")
    assert result["complete"]
    assert result["words"][-1]["normalized"] == "condition(Σ x:man. walk(x), Σ x:dog. walk(x))"
    assert "Parameter condition : Type -> Type -> Prop." in result["coq"]
    if shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text,word,relation", [
    ("english", "John walks since Mary walks.", "since", "because"),
    ("smg", "Ο Γιώργος περπατάει ενώ η Μαρία περπατάει.", "ενώ", "contrast"),
])
def test_llm_selects_relation_then_ds_composes_it(monkeypatch, backend, language, text, word, relation):
    baseline = parse(text, backend, language)
    assert baseline["complete"] and not baseline["words"][-1]["normalized"].startswith(relation + "(")
    calls = []
    def provider(context, spec, **options):
        assert context["task"] == "finite_clause_constructions"
        assert context["backend"] == backend and word in context["requested"]
        assert relation in context["relations"] and options["instruction"]
        calls.append(context)
        return {"constructions": [{"surface": word, "relation": relation, "evidence": "Controlled sense-selection fixture."}]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse(text, backend, language, lexical_mode="assisted")
    assert result["complete"] and len(calls) == 1
    assert result["words"][-1]["normalized"].startswith(relation + "(")
    assert result["clause_constructions"][0]["relation"] == relation
    assert result["lexical"]["constructions"][0]["alternatives_retained"] > 0
    assert result["lexical"]["constructions"][0]["added_programs"] == 0


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_llm_instantiates_a_new_connective_on_failure(monkeypatch, backend):
    text = "John walks provided Mary walks."
    assert not parse(text, backend, lexical_mode="dictionary")["complete"]
    calls = []
    def provider(context, spec, **options):
        calls.append(context)
        if context.get("task") == "finite_clause_constructions":
            assert context["failure"] and context["failure"]["token"] == "provided"
            return {"constructions": [{"surface": "provided", "relation": "condition", "evidence": "Provided introduces a finite condition here."}]}, {"provider": "fixture", "model": "fixture"}
        return {"entries": []}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse(text, backend, lexical_mode="assisted")
    assert result["complete"], result["failure"]
    assert result["words"][-1]["normalized"] == "condition(walk(john), walk(mary))"
    assert [a["complete"] for a in result["assistance"]["derivation_attempts"]] == [False, True]
    assert result["lexical"]["constructions"][0]["added_programs"] >= 2


@pytest.mark.parametrize("bad", [
    {"surface": "since", "relation": "condition", "evidence": "Wrong lexical meaning"},
    {"surface": "since", "relation": "eval(arbitrary)", "evidence": "Injected program"},
    {"surface": "the", "relation": "because", "evidence": "Article cannot become conjunction"},
    {"surface": "since", "relation": "because", "evidence": "Extra program", "program": "do_nothing"},
])
def test_rejected_model_batch_cannot_change_grammar(bad):
    parser = icp("2026-english-mltt")
    try:
        before = {w: list(a) for w, a in parser.lexicon.items()}
        theory = deepcopy(parser.semantic_profile)
        with pytest.raises(ValueError):
            compile_proposals(parser, {"constructions": [bad]}, ["since", "the"], "en")
        assert dict(parser.lexicon) == before and parser.semantic_profile == theory
    finally:
        parser.close()


def test_provider_outage_leaves_all_grammar_alternatives(monkeypatch):
    def provider(*a, **k):
        raise lexical_provider.ProposalUnavailable("Fixture outage")
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse("John walks since Mary walks.", lexical_mode="assisted")
    assert result["complete"] and result["clause_constructions"][0]["relation"] == "since_time"
    assert result["lexical"]["attempts"][0]["status"] == "unavailable"


def test_preferences_do_not_leak_across_paragraph_sentences(monkeypatch):
    def provider(context, spec, **options):
        return {"constructions": [{"surface": "since", "relation": "because", "evidence": "Fixture reason."}] if "later" in context["tokens"] else []}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse_request({"paragraph": "John walks since Mary walks later. John walks since Mary walks.", "grammar": "2026-english-mltt", "lexical_mode": "assisted"})
    assert result["complete"]
    assert [s["result"]["clause_constructions"][0]["relation"] for s in result["sentences"]] == ["because", "since_time"]


def test_repeated_ambiguous_word_does_not_receive_one_global_model_choice(monkeypatch):
    monkeypatch.setattr(lexical_provider, "propose", lambda *a, **k: pytest.fail("No global choice for two occurrences"))
    result = parse("John walks since Mary walks since Bill shouts.", lexical_mode="assisted")
    assert result["complete"] and len(result["clause_constructions"]) == 2


def test_missing_greek_connective_can_be_proposed_in_first_vocabulary_request(monkeypatch):
    calls = []
    def provider(context, spec, **options):
        calls.append(context)
        assert "καθότι" in context["construction_requested"]
        assert "constructions" in spec["required"]
        return {"entries": [], "constructions": [{"surface": "καθότι", "relation": "because", "evidence": "A causal finite-clause marker."}]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse("Ο Γιώργος περπατάει καθότι η Μαρία περπατάει.", language="smg", lexical_mode="assisted")
    assert result["complete"] and len(calls) == 1
    assert result["words"][-1]["normalized"] == "because(walk(giorgos), walk(maria))"
    assert result["lexical"]["attempts"][0]["kind"] == "vocabulary_and_construction"
    assert result["lexical"]["constructions"][0]["added_programs"] == 3


def test_invalid_combined_batch_cannot_install_either_half(monkeypatch):
    from dylan.assisted_parsing import Assistance
    def provider(*args, **kwargs):
        return {"entries": [], "constructions": [{"surface": "whilst", "relation": "while_clause", "evidence": "Temporal overlap."}],
                "program": "unreviewed effect"}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    parser = icp("2026-english-mltt")
    try:
        before = dict(parser.lexicon)
        helper = Assistance(parser, "2026-english-mltt", ["whilst"], calls=1)
        assert not helper.propose(["whilst"], ["whilst"])
        assert dict(parser.lexicon) == before and not helper.constructions
    finally:
        parser.close()
