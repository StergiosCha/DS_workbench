"""PP arguments/modifiers compose through native DP and LINK actions."""

import shutil

import pytest

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(sentence, backend="mltt", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}",
                          "strict": True, **options})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "john reads a book in a library.", "john walks at a library.",
    "john walks in a park with mary.", "john walks quickly in a park.",
    "john walks in a park quickly.", "every man walks in every park.",
    "john relies on mary.", "john relies on every man.",
    "john does not rely on mary.",
    "john gives a book to mary in a library.",
])
def test_pp_composition_and_coq(sentence, backend):
    result = run(sentence, backend)
    assert result["complete"] and result["cap_hit"] is None
    assert not any(frame["type_errors"] for frame in result["operations"])
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    if result["coq"] and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "john walks in.", "john walks with.", "john relies.", "john relies mary.",
    "john relies in a park.", "john relies on.", "john relies on on mary.",
    "john reads in a library.", "john gives a book in a library.",
])
def test_missing_complements_and_wrong_markers_do_not_complete(sentence, backend):
    result = run(sentence, backend)
    assert not result["complete"] and result["cap_hit"] is None
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_pp_dp_structure_and_pointer_are_visible(backend):
    result = run("john reads a book in a library.", backend)
    nodes = {node["id"]: node for node in result["words"][-1]["nodes"]}
    assert "+PP" in nodes["01L1"]["labels"]
    assert nodes["01L10"]["formula"] and "library" in nodes["01L100"]["formula"]
    assert any(frame.get("pointer_before") == "01L1" and frame["pointer"] == "01L10"
               for frame in result["operations"])
    if backend == "classical":
        assert nodes["01L100"]["type"] == "cn"
        assert "01L1000" in nodes and "01L1001" in nodes
        assert "ε" in result["words"][-1]["normalized"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_matrix_and_embedded_pp_attachment_have_separate_readings(backend):
    result = run("john thinks mary walks in a park.", backend, n_best=3, reading_traces=True)
    assert len(result["readings"]) == 2 and result["reading_search"]["exhausted"]
    readings = [reading["normalized"] for reading in result["readings"]]
    assert any("think(john, walk(mary))" in meaning for meaning in readings)
    assert any("think(john," in meaning and "think(john, walk(mary))" not in meaning for meaning in readings)
    if backend == "mltt" and shutil.which("coqc"):
        for reading in result["readings"]:
            assert compile_coq(reading["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_negation_survives_pp_and_adverb_recomposition(backend):
    for tail in ("in a park", "quickly", "in a park quickly"):
        result = run(f"john does not walk {tail}.", backend)
        assert result["complete"] and result["words"][-1]["normalized"].startswith("¬")
        if backend == "mltt" and shutil.which("coqc"):
            assert compile_coq(result["coq"], {}) == "passed"


def test_companion_sort_and_quantified_locations():
    assert not run("john walks with a stone.")["complete"]
    assert run("every man walks in every park.")["words"][-1]["normalized"] == (
        "Π x:man. Π x2:park. in_location(x2, walk(x))")


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_selected_pp_template_preserves_new_verb_identity(monkeypatch, tmp_path, backend):
    from dylan import lexical_provider
    from dylan.lexical_expansion import proposal
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setattr(lexical_provider, "propose", lambda *args: (
        {"entries": [proposal("depends", "depend", "prepositional-on", ["human", "object"])]},
        {"provider": "fixture", "model": "fixture"}))
    result = run("john depends on mary.", backend, lexical_mode="model")
    assert result["complete"] and result["words"][-1]["normalized"] == "depend(john, mary)"
    assert not run("john depends in a park.", backend, lexical_mode="model")["complete"]
