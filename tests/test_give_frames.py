"""Give-family argument order, mandatory preposition and quantified composition."""

import shutil

import pytest

from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.lexical_expansion import proposal
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    reset_all_meta_bindings()
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "lexical.sqlite3"))
    yield
    reset_all_meta_bindings()


def run(sentence, backend, **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "strict": True, **options})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "john gives mary a book.", "john gives a book to mary.",
    "john gave mary a book.", "john gave a book to mary.",
    "john give mary a book.", "john give a book to mary.",
])
def test_give_alternation_preserves_roles(backend, sentence):
    # Agreement and tense are separate work: bare give is still accepted in
    # finite position by this fragment, exactly as bare walk was before it.
    result = run(sentence, backend)
    assert result["complete"] and result["ok"] and result["cap_hit"] is None
    assert result["words"][-1]["normalized"] == (
        "Σ x:book. give(john, mary, x)" if backend == "mltt"
        else "give(john, mary, ε x0:e. book(x0))"
    )
    assert not result["stats"]["top_n_cuts"]
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "john gives mary.", "john gives a book.", "john gives a book to.",
    "john gives mary to a book.", "john gives a book to to mary.",
    "john gives mary a book a book.", "john does not gives mary a book.",
])
def test_give_argument_and_preposition_controls(backend, sentence):
    result = run(sentence, backend)
    # Classical e typing cannot distinguish a book from a recipient; this
    # specific role-order control is a constructive selectional check.
    if sentence == "john gives mary to a book." and backend == "classical":
        assert result["complete"]
    else:
        assert not result["complete"]
    assert result["cap_hit"] is None
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("sentence,expected", [
    ("every man gives every woman every book.",
     "Π x:man. Π x1:woman. Π x2:book. give(x, x1, x2)"),
    ("john gives every book to every woman.",
     "Π x1:book. Π x2:woman. give(john, x2, x1)"),
    ("john does not give mary a book.", "¬(Σ x:book. give(john, mary, x))"),
    ("john does not give a book to mary.", "¬(Σ x:book. give(john, mary, x))"),
    ("a man who gives mary a book walks.",
     "Σ x:(Σ r000:man. Σ x:book. give(r000, mary, x)). walk(π₁(x))"),
])
def test_give_quantifiers_negation_and_relative_scope(sentence, expected):
    result = run(sentence, "mltt")
    assert result["complete"] and result["words"][-1]["normalized"] == expected
    assert not any(frame["type_errors"] for frame in result["operations"])
    if shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_recipient_and_theme_are_distinct_visible_argument_nodes(backend):
    result = run("john gives mary a book.", backend)
    nodes = {node["id"]: node for node in result["words"][-1]["nodes"]}
    assert nodes["010"]["formula"] == "mary"
    assert nodes["0110"]["formula"] != "mary"
    assert "give" in nodes["0111"]["formula"]
    assert any(frame.get("pointer_before") == "011" and frame["pointer"] == "0110"
               for frame in result["operations"])
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_model_reuses_give_frame_without_replacing_lexical_meaning(monkeypatch, backend):
    monkeypatch.setattr(lexical_provider, "propose", lambda *args: (
        {"entries": [proposal("lends", "lend", frame, ["human", "human", "object"])
                     for frame in ["ditransitive", "dative-to"]]},
        {"model": "fixture", "provider": "fixture"},
    ))
    for sentence in ["john lends mary a book.", "john lends a book to mary."]:
        result = run(sentence, backend, lexical_mode="model")
        assert result["complete"]
        meaning = result["words"][-1]["normalized"]
        assert "lend(john, mary," in meaning and "give(" not in meaning
        if backend == "mltt" and shutil.which("coqc"):
            assert compile_coq(result["coq"], {}) == "passed"
