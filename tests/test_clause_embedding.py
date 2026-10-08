"""Recursive finite complements, local witness closure and actual DS operations."""

from pathlib import Path
import shutil
import subprocess

import pytest

from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.semantics import parse_semantic_type, subtype
from dylan.formula.mltt.terms import name
from dylan.lexical_expansion import proposal, validate_entries
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    reset_all_meta_bindings()
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "lexical.sqlite3"))
    yield
    reset_all_meta_bindings()


def parse(text, backend="mltt", **options):
    return parse_request({"sentence": text, "grammar": f"2026-english-{backend}", **options})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize(
    "text,expected,depth",
    [
        ("john thinks that mary walks.", "think(john, walk(mary))", 1),
        ("john thinks mary walks.", "think(john, walk(mary))", 1),
        ("john says that mary thinks that bill shouts.", "say(john, think(mary, shout(bill)))", 2),
        (
            "john thinks mary says bill thinks john walks.",
            "think(john, say(mary, think(bill, walk(john))))",
            3,
        ),
    ],
)
def test_recursive_composition(backend, text, expected, depth):
    result = parse(text, backend)
    assert result["complete"] and result["ok"]
    final = result["words"][-1]
    assert final["normalized"] == expected
    assert len(final["nodes"]) == 3 + 4 * depth
    clauses = [n for n in final["nodes"] if n["clause"]]
    assert len(clauses) == depth
    assert all(n["clause_closed"] and not n["requirements"] for n in clauses)
    assert all(n["type"] == ("Content" if backend == "mltt" else "t") for n in clauses)
    assert not any(f["type_errors"] for f in result["operations"])
    assert all(f["backend"] == backend for f in result["words"])


def compile_meaning(result, directory):
    coqc = shutil.which("coqc")
    if coqc:
        target = Path(directory) / "Embedded.v"
        target.write_text(result["coq"])
        check = subprocess.run([coqc, str(target)], capture_output=True, text=True, timeout=15)
        assert check.returncode == 0, check.stderr


@pytest.mark.parametrize(
    "text,expected",
    [
        ("john thinks that a man walks.", "think(john, Σ x:man. walk(x))"),
        ("a man thinks that a dog walks.", "Σ x:man. think(x, Σ x:dog. walk(x))"),
        (
            "john thinks that every doctor examined a patient.",
            "think(john, Π x:doctor. Σ x1:patient. examine(x, x1))",
        ),
        (
            "john thinks that mary says that a dog walks.",
            "think(john, say(mary, Σ x:dog. walk(x)))",
        ),
    ],
)
def test_constructive_closure_is_local_and_typechecks(text, expected, tmp_path):
    result = parse(text)
    assert result["complete"]
    assert result["words"][-1]["normalized"] == expected
    assert "Parameter think : human -> Type -> Prop." in result["coq"]
    assert "ε" not in result["words"][-1]["normalized"]
    compile_meaning(result, tmp_path)


def test_wide_scope_stays_inside_its_complement(tmp_path):
    result = parse("john thinks that every doctor examined a patient.", scope="wide")
    assert result["complete"]
    assert (
        result["words"][-1]["normalized"] == "think(john, Σ x:patient. Π x1:doctor. examine(x1, x))"
    )
    compile_meaning(result, tmp_path)


def test_classical_embedded_dps_keep_cn_and_choice_terms():
    result = parse("a man thinks that every doctor examined a patient.", "classical")
    assert result["complete"]
    assert (
        result["words"][-1]["normalized"]
        == "think(ε x0:e. man(x0), examine(τ x1:e. doctor(x1), ε x2:e. patient(x2)))"
    )
    assert sum(n["type"] == "cn" for n in result["words"][-1]["nodes"]) == 3
    assert result["coq"] is None


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "text",
    ["john thinks", "john thinks that", "john thinks that mary", "john says mary thinks that"],
)
def test_missing_complement_is_a_partial_tree_until_punctuation(backend, text):
    partial = parse(text, backend)
    assert partial["ok"] and not partial["complete"] and partial["failure"] is None
    assert any(n["clause"] and not n["clause_closed"] for n in partial["words"][-1]["nodes"])
    stopped = parse(text + ".", backend)
    assert not stopped["ok"] and not stopped["complete"]
    assert stopped["failure"]["token"] == "."
    assert stopped["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "text",
    [
        "that john walks.",
        "john walks that mary walks.",
        "john thinks that that mary walks.",
        "john thinks that a dog.",
    ],
)
def test_complementizer_requires_a_selected_clause(backend, text):
    result = parse(text, backend)
    assert not result["complete"]
    assert all(item["known"] for item in result["diagnostics"]["lexical_coverage"])
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_embedded_type_failure_and_unknown_word_stay_distinct():
    typed = parse("john thinks that a stone shouts.")
    assert typed["failure"]["kind"] == "semantic_type_mismatch"
    missing = parse("john thinks that a zzzunknown walks.")
    assert missing["failure"]["kind"] == "lexicon_gap"
    assert missing["failure"]["token"] == "zzzunknown"


def test_clause_growth_and_closure_are_visible_operations():
    result = parse("john thinks that mary walks.")
    first = next(w for w in result["words"] if w["label"] == "thinks")
    clause = next(n for n in first["nodes"] if n["clause"])
    assert clause["id"] == "010" and not clause["clause_closed"]
    operations = result["operations"]
    assert any(o.get("pointer_before") == "01" and o["pointer"] == "010" for o in operations)
    assert any(o["label"] == "delete(?+COMP)" and o.get("rule") == "that" for o in operations)
    closure = [o for o in operations if o.get("rule") == "close-complement"]
    assert any(o["label"] == "put(Ty(Content))" for o in closure)
    assert any(o["label"] == "delete(?+CLOSED)" for o in closure)
    assert any(o["label"] == "put(+CLOSED)" for o in closure)


def test_content_is_not_a_nominal_subtype_or_np_slot():
    assert not subtype(name("Content"), name("object"), {})
    assert not parse_semantic_type("mltt:object").accepts_requirement(
        parse_semantic_type("mltt:Content")
    )


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_model_can_instantiate_the_new_frame_without_writing_actions(
    monkeypatch, backend, tmp_path
):
    monkeypatch.setattr(
        lexical_provider,
        "propose",
        lambda *args: (
            {
                "entries": [
                    proposal("believes", "believe", "clausal", ["human"]),
                ]
            },
            {"model": "fixture", "provider": "fixture"},
        ),
    )
    result = parse("john believes that a man walks.", backend, lexical_mode="model")
    assert result["complete"]
    assert result["lexical"]["entries"][0]["template"] == "clausal"
    assert result["words"][-1]["normalized"].startswith("believe(john,")
    if backend == "mltt":
        assert "Parameter believe : human -> Type -> Prop." in result["coq"]
        compile_meaning(result, tmp_path)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_a_second_speaker_can_supply_the_complement(backend):
    result = parse_request(
        {
            "grammar": f"2026-english-{backend}",
            "dialogue": [
                {"speaker": "A", "text": "john thinks", "boundary": "continue"},
                {"speaker": "B", "text": "that mary walks.", "boundary": "continue"},
            ],
        }
    )
    assert result["complete"]
    assert result["words"][-1]["normalized"] == "think(john, walk(mary))"


@pytest.mark.parametrize("lemma,symbol", [("think", "think"), ("believe", "think")])
def test_template_reuse_cannot_replace_believe_with_think(lemma, symbol):
    from dynamicsyntax import icp

    parser = icp("2026-english-mltt")
    try:
        with pytest.raises(ValueError, match="lemma"):
            validate_entries(
                {"entries": [proposal("believes", lemma, "clausal", ["human"], symbol=symbol)]},
                ["believes"],
                parser.lexicon,
                parser.semantic_profile,
            )
        assert "believes" not in parser.lexicon
    finally:
        parser.close()
