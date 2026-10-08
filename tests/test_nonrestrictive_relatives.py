"""Sourced construction, authored probes; parser failures are not judgments."""
import shutil

import pytest

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    from dylan import lexical_provider
    def forbidden(*args, **kwargs):
        pytest.fail("The reviewed LINK construction needs no LLM")
    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(sentence, backend, **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "strict": True, **options})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence,expected", [
    ("John, who Mary knows, walks.", "(walk(john) ∧ know(mary, john))"),
    ("John, who walks, arrives.", "(arrive(john) ∧ walk(john))"),
    ("Mary knows John, who walks.", "(know(mary, john) ∧ walk(john))"),
    ("Mary knows John, who Bill knows.", "(know(mary, john) ∧ know(bill, john))"),
    ("John, who does not walk, arrives.", "(arrive(john) ∧ ¬(walk(john)))"),
    ("John, who walks, does not arrive.", "(¬(arrive(john)) ∧ walk(john))"),
    ("John, who walks quickly, arrives.", "(arrive(john) ∧ quickly(walk(john)))"),
    ("John, who Mary knows, walks quickly.", "(quickly(walk(john)) ∧ know(mary, john))"),
    ("John, who walks later, arrives today.", "(today(arrive(john)) ∧ later(walk(john)))"),
    ("John, who walks, knows Mary, who arrives.", "((know(john, mary) ∧ walk(john)) ∧ arrive(mary))"),
])
def test_assertion_identity_role_and_modifier_scope(backend, sentence, expected):
    result = run(sentence, backend)
    assert result["complete"] and result["cap_hit"] is None, result.get("failure")
    assert result["words"][-1]["normalized"] == expected
    assert not any(n["requirements"] for n in result["words"][-1]["nodes"])
    assert not any(o["type_errors"] for o in result["operations"])
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_local_indefinite_and_head_do_not_escape(backend):
    result = run("John, who knows a woman, walks.", backend)
    assert result["complete"]
    expected = ("(walk(john) ∧ Σ x:woman. know(john, x))" if backend == "mltt"
                else "(walk(john) ∧ know(john, ε x0:e. woman(x0)))")
    assert result["words"][-1]["normalized"] == expected
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("sentence", [
    "John, who Mary walks, arrives.",  # no argument gap
    "John, who Mary knows Bill, walks.",  # gap and an extra object
    "John, who knows, walks.",
    "John, who walks.",  # no matrix predicate
    "John, walks, arrives.",  # missing relativizer
    "John, that walks, arrives.",
    "John who walks arrives.",
    "John, who walks arrives.",  # missing closing delimiter
    "Every man, who walks, arrives.",  # quantified hosts deferred
    "A man, who walks, arrives.",
    "The man, who walks, arrives.",  # complex nominal hosts need a separate audit
    "John thinks Mary, who walks, arrives.",  # projection deferred
    "John, who Bill thinks Mary knows, walks.",  # nonlocal gap deferred
    "John, who Mary knows, walks because Bill shouts.",  # supplement projection deferred
    "Did John, who Mary knows, walk?",  # answer scope must not deny the supplement
])
def test_unresolved_or_unsupported_construction_cannot_pass(backend, sentence):
    result = run(sentence, backend)
    assert not result["complete"] and result["cap_hit"] is None
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_unfixed_copy_merge_inverse_link_and_separate_assertion_are_recorded(backend):
    result = run("John, who Mary knows, walks.", backend)
    operations = result["operations"]
    assert any(o.get("delta", {}).get("created") == ["00L"] for o in operations)
    assert any("00L*" in o.get("delta", {}).get("created", []) for o in operations)
    merge = [o for o in operations if o.get("rule") == "merge-relative"]
    assert len(merge) == 1 and merge[0]["pointer"] == "00L10"
    assert "00L*" in merge[0]["delta"]["removed"]
    assert any(o.get("pointer_before") == "00L" and o["pointer"] == "00" for o in operations)
    final = {n["id"]: n for n in result["words"][-1]["nodes"]}
    assert final["00"]["formula"] == final["00L10"]["formula"] == "john"
    assert final["00L"]["formula"] == "know(mary, john)"
    assert operations[-1]["nodes"] == result["words"][-1]["nodes"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_no_complete_analysis_can_discard_the_supplement(backend):
    result = run("John, who Mary knows, walks quickly.", backend, n_best=4)
    assert result["complete"]
    assert all(r["normalized"] == "(quickly(walk(john)) ∧ know(mary, john))" for r in result["readings"])
