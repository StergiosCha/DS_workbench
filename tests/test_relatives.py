"""Restrictive LINK fixtures: specified parser behavior, not sourced judgments."""

import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(sentence, backend="mltt", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "strict": True, **options})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence,mltt,classical", [
    ("a man who walks arrives.",
     "Σ x:(Σ r000:man. walk(r000)). arrive(π₁(x))",
     "arrive(ε x0:e. (man(x0) ∧ walk(x0)))"),
    ("a man who mary knows walks.",
     "Σ x:(Σ r000:man. know(mary, r000)). walk(π₁(x))",
     "walk(ε x0:e. (man(x0) ∧ know(mary, x0)))"),
    ("john knows a man who walks.",
     "Σ x:(Σ r0100:man. walk(r0100)). know(john, π₁(x))",
     "know(john, ε x0:e. (man(x0) ∧ walk(x0)))"),
    ("john knows a man who mary knows.",
     "Σ x:(Σ r0100:man. know(mary, r0100)). know(john, π₁(x))",
     "know(john, ε x0:e. (man(x0) ∧ know(mary, x0)))"),
    ("a dog which walks walks.",
     "Σ x:(Σ r000:dog. walk(r000)). walk(π₁(x))",
     "walk(ε x0:e. (dog(x0) ∧ walk(x0)))"),
    ("a man that walks arrives.",
     "Σ x:(Σ r000:man. walk(r000)). arrive(π₁(x))",
     "arrive(ε x0:e. (man(x0) ∧ walk(x0)))"),
    ("every man who walks arrives.",
     "Π x:(Σ r000:man. walk(r000)). arrive(π₁(x))",
     "arrive(τ x0:e. (man(x0) ∧ walk(x0)))"),
    ("john knows every man who walks.",
     "Π x1:(Σ r0100:man. walk(r0100)). know(john, π₁(x1))",
     "know(john, τ x0:e. (man(x0) ∧ walk(x0)))"),
    ("a black dog which walks walks.",
     "Σ x:(Σ r000:(Σ x:dog. black(x)). walk(π₁(r000))). walk(π₁(π₁(x)))",
     "walk(ε x0:e. ((dog(x0) ∧ black(x0)) ∧ walk(x0)))"),
    ("a man who knows a woman walks.",
     "Σ x:(Σ r000:man. Σ x:woman. know(r000, x)). walk(π₁(x))",
     "walk(ε x0:e. (man(x0) ∧ know(x0, ε x1:e. woman(x1))))"),
    ("a man who does not walk arrives.",
     "Σ x:(Σ r000:man. ¬(walk(r000))). arrive(π₁(x))",
     "arrive(ε x0:e. (man(x0) ∧ ¬(walk(x0))))"),
    ("john thinks that a man who walks arrives.",
     "think(john, Σ x:(Σ r01000:man. walk(r01000)). arrive(π₁(x)))",
     "think(john, arrive(ε x0:e. (man(x0) ∧ walk(x0))))"),
    ("a man who knows a woman who walks arrives.",
     "Σ x:(Σ r000:man. Σ x:(Σ r000L100:woman. walk(r000L100)). know(r000, π₁(x))). arrive(π₁(x))",
     "arrive(ε x0:e. (man(x0) ∧ know(x0, ε x1:e. (woman(x1) ∧ walk(x1)))))"),
])
def test_relative_meanings_and_coq(backend, sentence, mltt, classical):
    result = run(sentence, backend)
    assert result["ok"] and result["complete"] and result["cap_hit"] is None
    assert result["words"][-1]["normalized"] == (mltt if backend == "mltt" else classical)
    assert not any(frame["type_errors"] for frame in result["operations"])
    assert all(not node["requirements"] for node in result["words"][-1]["nodes"])
    if backend == "mltt":
        assert "ε" not in mltt and "τ" not in mltt
        assert "Parameter r0" not in result["coq"]  # The head copy is bound, not declared.
        if shutil.which("coqc"):
            assert compile_coq(result["coq"], {}) == "passed"
    else:
        assert result["coq"] is None


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "who walks arrives.",
    "a man who knows walks.",
    "a man who mary knows.",
    "a man who mary walks arrives.",
    "a man who mary knows bill walks.",
    "a man who walks mary arrives.",
    "a man who john thinks mary knows walks.",
    "a man who walks who shouts arrives.",
])
def test_relative_gap_controls(backend, sentence):
    # The last two are unsupported extraction/stacking, not judgments of
    # ungrammatical English. Keep all failure judgments unassessed in the UI.
    result = run(sentence, backend)
    assert not result["ok"] and not result["complete"] and result["cap_hit"] is None
    assert all(item["known"] for item in result["diagnostics"]["lexical_coverage"])
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("prefix", ["a man who", "a man who mary", "a man who knows"])
def test_unresolved_relative_stays_partial(backend, prefix):
    partial = run(prefix, backend)
    assert partial["ok"] and not partial["complete"]
    assert any("REL-CLOSED" in req for n in partial["words"][-1]["nodes"]
               for req in n["requirements"])
    stopped = run(prefix + ".", backend)
    assert not stopped["ok"] and stopped["failure"]["token"] == "."


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("object_gap", [False, True])
def test_object_relative_uses_merge_and_each_pointer_operation_is_replayable(backend, object_gap):
    result = run("a man who mary knows walks." if object_gap else "a man who walks arrives.", backend)
    anchor = "000" if backend == "mltt" else "0000"
    root = anchor + "L"
    site = root + ("10" if object_gap else "0")
    operations = result["operations"]
    assert any(o["label"] == r"make(\/L)" and o["delta"]["created"] == [root]
               for o in operations if "delta" in o)
    assert any(o.get("pointer_before") == anchor and o["pointer"] == root for o in operations)
    assert any(o["label"] == r"make(\/*)" and o["delta"]["created"] == [root + "*"]
               for o in operations if "delta" in o)
    merged = [o for o in operations if o.get("rule") == "merge-relative"]
    assert len(merged) == 1 and merged[0]["pointer"] == site
    assert root + "*" in merged[0]["delta"]["removed"]
    final = {n["id"]: n for n in result["words"][-1]["nodes"]}
    assert root + "*" not in final and final[site]["formula"].startswith(("r0", "x0"))
    assert {"source": anchor, "target": root, "kind": "link", "path": "L"} in result["words"][-1]["edges"]
    assert operations[-1]["nodes"] == result["words"][-1]["nodes"]
    assert not any(o.get("trace_note") for o in operations)
    if backend == "classical":
        assert final["00"]["type"] == "e"
        assert final["001"]["type"] == "cn → e"
        assert final["000"]["type"] == "cn"
        assert final["0000"]["type"] == "e" and final["0000"]["formula"] == "x0"
        assert final["0001"]["type"] == "e → cn"


@pytest.mark.parametrize("sentence", ["every black dog walks.", "every black dog which walks walks."])
def test_universal_refinement_projects_the_entity_before_predication(sentence):
    result = run(sentence)
    assert result["complete"] and "walk(π₁(" in result["words"][-1]["normalized"]
    if shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


def test_subject_relative_refines_cn_and_compiles():
    result = parse("a man who knows a woman walks.", "2026-english-mltt", strict=True)
    assert result.ok and result.tree.is_complete()
    # Neither head copies nor local indefinite witnesses escape their binders.
    assert not any(n.startswith(("r0", "p0")) for n in result.semantics.term.free())
    if shutil.which("coqc"):
        assert compile_coq(result.semantics.to_coq(), {}) == "passed"


def test_unknown_relative_word_and_semantic_mismatch_remain_distinct():
    unknown = run("a man who zzzunknown arrives.")
    assert unknown["failure"]["kind"] == "lexicon_gap"
    typed = run("a stone who shouts walks.")
    assert typed["failure"]["kind"] == "semantic_type_mismatch"
    assert typed["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_another_speaker_can_complete_the_relative(backend):
    result = parse_request({"grammar": f"2026-english-{backend}", "dialogue": [
        {"speaker": "A", "text": "a man who mary", "boundary": "continue"},
        {"speaker": "B", "text": "knows walks.", "boundary": "continue"},
    ]})
    assert result["complete"]
    assert "know(mary," in result["words"][-1]["normalized"]
