"""Check nominal attachment, witness binding and real failure boundaries."""

import shutil

import pytest

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def reset_bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(sentence, backend="mltt", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "lexical_mode": "off", **options})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence,relation", [
    ("the man with a knife runs.", "with_nominal"),
    ("a man with a knife runs.", "with_nominal"),
    ("every man with a knife runs.", "with_nominal"),
    ("a black dog with a book walks.", "with_nominal"),
    ("a woman in the park walks.", "in_nominal"),
    ("a doctor at a library walks.", "at_nominal"),
    ("a book on a stone arrives.", None),  # Nominal restriction cannot make a book human.
    ("a man near a woman walks.", "near_nominal"),
    ("john likes a book on a stone.", "on_nominal"),
    ("john thinks a man with a knife runs.", "with_nominal"),
    ("a man with a book in a library runs.", "with_nominal"),
    ("a man with glasses runs.", "with_nominal"),
])
def test_nominal_pp_coverage_and_meaning(backend, sentence, relation):
    result = run(sentence, backend)
    if relation is None:
        # The Constructive nominal hierarchy enforces this selection. Classical
        # e does not by itself enforce animacy; it is not an agreement test.
        if backend == "mltt":
            assert not result["complete"]
        return
    assert result["complete"], result["failure"]
    final = result["words"][-1]
    assert not final["type_errors"] and not final["semantic_error"]
    assert any(relation in (node["formula"] or "") for node in final["nodes"])
    assert all(not node["requirements"] for node in final["nodes"])
    assert any(edge["kind"] == "link" for edge in final["edges"])
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


def test_indefinite_head_and_complement_have_distinct_locally_bound_witnesses():
    result = run("a man with a knife runs.")
    assert result["words"][-1]["normalized"] == (
        "Σ x:(Σ n000:man. Σ x:knife. with_nominal(n000, x)). run(π₁(x))")
    assert "Parameter n000" not in result["coq"]
    with_state = next(frame for frame in result["words"] if frame["label"] == "with")
    assert with_state["pointer"] == "000L10"
    assert next(node for node in with_state["nodes"] if node["id"] == "01")["formula"] is None
    assert any("NOMINAL-PP" in req for node in with_state["nodes"] for req in node["requirements"])


def test_classical_nominal_restriction_precedes_choice():
    result = run("a man with a knife runs.", "classical")
    assert result["words"][-1]["normalized"] == (
        "run(ε x0:e. (man(x0) ∧ with_nominal(x0, ε x1:e. knife(x1))))")


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "a man with.", "a man with a.", "a man with a knife.",
    "a man with knife runs.", "with a knife runs.", "a man with with a knife runs.",
    "a man with a glasses runs.", "john reads with a knife.",
])
def test_missing_structure_is_not_erased(backend, sentence):
    result = run(sentence, backend)
    assert not result["complete"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("complement", ["a knife", "glasses", "mary", "a stone"])
def test_postverbal_accompaniment_accepts_objects_without_inventing_instrumentality(backend, complement):
    result = run(f"john walks with {complement}.", backend)
    assert result["complete"]
    meaning = result["words"][-1]["normalized"]
    assert "with_accompaniment" in meaning and "walk(john)" in meaning
    assert "with_companion" not in meaning and "with_instrument" not in meaning


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_object_attachment_and_predicate_attachment_are_distinct_readings(backend):
    result = run("john likes a man with a knife.", backend, n_best=4, reading_traces=True)
    assert result["complete"]
    meanings = [reading["normalized"] for reading in result["readings"]]
    assert any("with_nominal" in meaning for meaning in meanings)
    assert any("with_accompaniment" in meaning for meaning in meanings)


def test_experimental_mode_needs_no_model_to_parse_the_fixed_case(monkeypatch):
    from dylan import lexical_provider

    def forbidden(*args, **kwargs):
        pytest.fail("The maintained grammar should not ask a model for this sentence")

    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    result = run("the man with a knife runs", lexical_mode="assisted",
                 allow_model_fallback=True, experimental_rules=True)
    assert result["complete"] and result["experimental_grammar"]["baseline"]["complete"]
    assert result["experimental_grammar"]["attempts"] == []
