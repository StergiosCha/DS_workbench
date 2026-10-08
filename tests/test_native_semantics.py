"""Native DS composition: no TTR translation, sound application and growing trees."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from dynamicsyntax import parse
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.semantics import (
    SemanticFormula,
    SemanticType,
    apply_semantics,
    parse_semantic_formula,
    parse_semantic_type,
    subtype,
)
from dylan.formula.mltt.terms import parse_expr, name
from dylan.workbench_api import configuration, parse_request


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(sentence, backend="mltt", scope="narrow"):
    return parse_request(
        {"sentence": sentence, "grammar": f"2026-english-{backend}", "scope": scope}
    )


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_native_grammars_are_strictly_valid(backend):
    path = Path(__file__).parents[1] / "src/dynamicsyntax/grammars" / f"2026-english-{backend}"
    grammar = Grammar(path, strict=True)
    assert {
        "intro-pred",
        "elimination",
        "close-complement",
        "zero-complementizer",
    } <= grammar.keys()
    assert Lexicon(path, strict=True).lookup("walks")


@pytest.mark.parametrize(
    "sentence,expected",
    [
        ("a man walks.", "Σ x:man. walk(x)"),
        ("every man walks.", "Π x:man. walk(x)"),
        ("every doctor examined a patient.", "Π x:doctor. Σ x1:patient. examine(x, x1)"),
        ("a black dog walks.", "Σ x:(Σ x:dog. black(x)). walk(π₁(x))"),
        ("john walks quickly.", "quickly(walk(john))"),
        ("bill shouts.", "shout(bill)"),
    ],
)
def test_constructive_composition_and_real_coq_export(sentence, expected, tmp_path):
    r = run(sentence)
    assert r["complete"] and r["ok"]
    assert r["words"][-1]["normalized"] == expected
    assert all(f["backend"] == "mltt" for f in r["actions"])
    assert all(
        "ε" not in (f["semantics"] or "") and "τ" not in (f["semantics"] or "")
        for f in r["actions"]
    )
    assert r["actions"][0]["nodes"][0]["requirements"] == ["?Ty(Prop)"]
    assert len({len(f["nodes"]) for f in r["actions"]}) > 1
    assert r["actions"][-1]["nodes"] == r["words"][-1]["nodes"]
    compiler = shutil.which("coqc")
    if compiler:
        source = tmp_path / "meaning.v"
        source.write_text(r["coq"])
        result = subprocess.run([compiler, str(source)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr


def test_lexical_decorations_are_native_before_root_composition():
    r = parse("a man walks.", "2026-english-mltt", trace=True)
    assert r.ok and isinstance(r.semantics, SemanticFormula)
    nodes = [n for tree in r.trace_trees for n in tree.values() if n.get_formula() is not None]
    assert nodes and all(isinstance(n.get_formula(), SemanticFormula) for n in nodes)
    assert all(isinstance(n.get_type(), SemanticType) for n in nodes)
    assert any(str(n.get_type()).startswith("Σ") for n in nodes)
    assert any(
        "π₁" in str(n.get_formula()) for step in r.action_steps for n in step.after_tree.values()
    )
    assert "Definition meaning" in r.to_coq()


def test_scope_is_explicit_witness_closure_and_both_readings_typecheck(tmp_path):
    narrow = run("every doctor examined a patient.")
    wide = run("every doctor examined a patient.", scope="wide")
    assert narrow["words"][-1]["normalized"].startswith("Π x:doctor. Σ")
    assert wide["words"][-1]["normalized"] == "Σ x:patient. Π x1:doctor. examine(x1, x)"
    assert narrow["words"][-1]["nodes"] == wide["words"][-1]["nodes"]
    compiler = shutil.which("coqc")
    if compiler:
        source = tmp_path / "wide.v"
        source.write_text(wide["coq"])
        result = subprocess.run([compiler, str(source)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "sentence,expected",
    [
        ("a man walks.", "walk(ε x0:e. man(x0))"),
        ("every man walks.", "walk(τ x0:e. man(x0))"),
        ("a black dog walks.", "walk(ε x0:e. (dog(x0) ∧ black(x0)))"),
        ("john likes mary.", "like(john, mary)"),
    ],
)
def test_classical_choice_terms_are_preserved(sentence, expected):
    r = run(sentence, "classical")
    assert r["complete"]
    assert r["words"][-1]["semantics"] == expected
    assert r["words"][0]["nodes"][0]["requirements"] == ["?Ty(t)"]
    assert r["coq"] is None


@pytest.mark.parametrize("punctuation", ["", "."])
def test_ill_typed_sentence_is_rejected_with_or_without_punctuation(punctuation):
    r = run("a stone shouts" + punctuation)
    assert not r["ok"] and not r["complete"]
    assert "predicate of human" in r["failure"]["message"]
    assert r["failure"]["token"] == "shouts"
    facade = parse("a stone shouts" + punctuation, "2026-english-mltt")
    assert not facade.ok and facade.semantics is None


def test_nominal_subtyping_and_function_variance_are_separate_from_slots():
    theory = {"subtyping": {"man": ["human"], "human": ["object"]}}
    assert subtype(name("man"), name("human"), theory)
    assert subtype(parse_expr("arrow(human,Prop)"), parse_expr("arrow(man,Prop)"), theory)
    assert not subtype(parse_expr("arrow(man,Prop)"), parse_expr("arrow(human,Prop)"), theory)
    assert parse_semantic_type("mltt:arrow(object,Prop)").accepts_requirement(
        parse_semantic_type("mltt:arrow(man,Prop)")
    )
    with pytest.raises(TypeError):
        apply_semantics(
            parse_semantic_formula("mltt:lam(x,man,shout(x))"),
            parse_semantic_type("mltt:arrow(man,Prop)"),
            parse_semantic_formula("mltt:john"),
            parse_semantic_type("mltt:human"),
            theory,
        )


def test_capture_avoiding_beta_reduction():
    term = parse_expr("app(lam(x,human,lam(y,human,like(x,y))),y)").normalize()
    assert term.name != "y"
    assert "y" in term.free()
    assert str(term) == "λ y1:human. like(y, y1)"


def test_backends_cannot_be_mixed():
    with pytest.raises(ValueError, match="classical"):
        parse_semantic_formula("mltt:eps(x,human,walk(x))")
    with pytest.raises(TypeError, match="backends"):
        apply_semantics(
            parse_semantic_formula("classical:lam(x,e,walk(x))"),
            parse_semantic_type("classical:arrow(e,t)"),
            parse_semantic_formula("mltt:john"),
            parse_semantic_type("mltt:human"),
            {},
        )


def test_adverb_is_recorded_as_link_tree_growth():
    r = run("john walks quickly.")
    assert any(e["kind"] == "link" for e in r["words"][-1]["edges"])
    assert any(f["label"] == "anticipation-link" for f in r["actions"])
    assert r["words"][-1]["semantics"] == "quickly(walk(john))"


def test_stream_emits_axiom_then_frames_then_matching_result():
    payload = {"sentence": "a man walks.", "grammar": "2026-english-mltt", "stream": True}
    worker = subprocess.run(
        [sys.executable, "-m", "dylan.workbench_api"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    events = [json.loads(line) for line in worker.stdout.splitlines()]
    assert events[0]["event"] == "start"
    assert len(events[0]["initial"]["nodes"]) == 1
    assert events[-1]["event"] == "result" and events[-1]["result"]["complete"]
    for channel in ["words", "actions"]:
        collected = [events[0]["initial"]] + [
            e["frame"] for e in events if e["event"] == "frame" and e["channel"] == channel
        ]
        assert collected == events[-1]["result"][channel]


def test_frontend_defaults_to_constructive_and_exposes_separate_modes():
    config = configuration()
    assert config["default_grammar"] == "2026-english-mltt"
    assert {s["id"] for s in config["systems"]} == {"mltt", "classical", "ttr"}


def test_native_axiom_survives_participant_and_sentence_reset():
    from dynamicsyntax import icp

    parser = icp("2026-english-mltt")
    try:
        parser.init_participants(["Dylan", "User"])
        assert str(parser.get_best_tuple().tree.get_root_node().get_required_type()) == "Prop"
        parser.new_sentence()
        assert parser.get_best_tuple().tree.semantic_profile["backend"] == "mltt"
        assert str(parser.get_best_tuple().tree.get_root_node().get_required_type()) == "Prop"
    finally:
        parser.close()


@pytest.mark.parametrize("determiner,choice", [("a", "ε"), ("every", "τ")])
def test_classical_dp_has_cn_restrictor_and_two_internal_daughters(determiner, choice):
    result = run(f"{determiner} man walks.", "classical")
    nodes = {n["id"]: n for n in result["words"][-1]["nodes"]}
    assert result["complete"] and len(nodes) == 7
    assert nodes["00"]["type"] == "e"
    assert nodes["001"]["type"] == "cn → e"
    assert nodes["001"]["formula"] == f"λ P:cn. {choice}(P)"
    assert nodes["000"]["type"] == "cn"
    assert nodes["000"]["formula"] == "(x0, man(x0))"
    assert nodes["0000"]["type"] == "e" and nodes["0000"]["formula"] == "x0"
    assert nodes["0001"]["type"] == "e → cn"
    assert nodes["0001"]["formula"] == "λ x:e. (x, man(x))"
    after_det = {n["id"]: n for n in result["words"][1]["nodes"]}
    assert after_det["0001"]["required_type"] == "e → cn"
    assert result["words"][1]["pointer"] == "0001"
    assert after_det["0000"]["formula"] == "x0"
    assert any(f["label"].startswith("freshput(") for f in result["operations"])


def test_classical_two_dps_use_distinct_fresh_restrictor_variables():
    result = run("a man knows a woman.", "classical")
    assert result["complete"]
    nodes = {n["id"]: n for n in result["words"][-1]["nodes"]}
    assert nodes["0000"]["formula"] == "x0"
    assert nodes["01000"]["formula"] == "x1"
    assert result["words"][-1]["semantics"] == "know(ε x0:e. man(x0), ε x1:e. woman(x1))"
    assert sum(n["type"] == "cn" for n in nodes.values()) == 2


def test_classical_adjective_preserves_cn_head_and_restrictor():
    result = run("a black dog walks.", "classical")
    nodes = {n["id"]: n for n in result["words"][-1]["nodes"]}
    assert nodes["000"]["type"] == "cn"
    assert nodes["000"]["formula"] == "(x0, (dog(x0) ∧ black(x0)))"
    assert nodes["0000"]["formula"] == "x0"
    assert nodes["0001"]["type"] == "e → cn"


@pytest.mark.parametrize("constructor", ["choice_eps", "choice_tau"])
def test_constructive_rejects_classical_cn_choice_closures(constructor):
    with pytest.raises(ValueError, match="classical"):
        parse_semantic_formula(f"mltt:{constructor}(cn(x,man(x)))")


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_lexical_adverb_symbol_and_embedded_attachment(backend, tmp_path):
    directory = Path(__file__).parents[1] / "src/dynamicsyntax/grammars" / f"2026-english-{backend}"
    target = tmp_path / "grammar"
    shutil.copytree(directory, target)
    lexicon = target / "lexicon.txt"
    lexicon.write_text(lexicon.read_text().replace("quietly adverb quietly\n", ""))
    result = parse("john thinks that mary walks quietly.", target, trace=True)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == "think(john, quietly(walk(mary)))"
    assert any(str(addr).endswith("1L") and len(str(addr)) > 3 for addr in result.tree)
    if backend == "mltt" and shutil.which("coqc"):
        source = tmp_path / "EmbeddedModifier.v"
        source.write_text(result.to_coq())
        check = subprocess.run([shutil.which("coqc"), str(source)], capture_output=True, text=True)
        assert check.returncode == 0, check.stderr


def test_adverb_implementation_has_no_lexical_constant():
    root = Path(__file__).parents[1] / "src/dylan"
    for path in [root / "action/atomic/semantic_effects.py", root / "formula/mltt/coq.py"]:
        assert "quickly" not in path.read_text()
    result = run("john walks quietly.")
    assert result["ok"] and result["complete"]
    assert result["words"][-1]["normalized"] == "quietly(walk(john))"
    assert "Parameter quietly : Prop -> Prop." in result["coq"]


@pytest.mark.parametrize("scope", ["narrow", "wide"])
@pytest.mark.parametrize("sentence", [
    "john knows every woman.",
    "every doctor examined every patient.",
    "a doctor examined every patient.",
    "john likes every black woman.",
])
def test_object_universal_composes_and_compiles(sentence, scope, tmp_path):
    result = run(sentence, scope=scope)
    assert result["ok"] and result["complete"]
    assert "Π" in result["words"][-1]["normalized"]
    if sentence.startswith("a doctor"):
        expected = "Π" if scope == "narrow" else "Σ"
        assert result["words"][-1]["normalized"].startswith(expected)
    if shutil.which("coqc"):
        source = tmp_path / "ObjectQuantifier.v"
        source.write_text(result["coq"])
        check = subprocess.run([shutil.which("coqc"), str(source)], capture_output=True, text=True)
        assert check.returncode == 0, check.stderr


def test_object_universal_checks_declared_domain_and_like_accepts_entities():
    with pytest.raises(TypeError, match="human.*dog"):
        apply_semantics(
            parse_semantic_formula("mltt:lam(y,human,lam(x,human,like(x,y)))"),
            parse_semantic_type("mltt:arrow(human,arrow(human,Prop))"),
            parse_semantic_formula("mltt:lam(P,arrow(dog,Prop),pi(x,dog,P(x)))"),
            parse_semantic_type("mltt:arrow(arrow(dog,Prop),Prop)"),
            {"subtyping": {"dog": ["animal"], "animal": ["object"], "human": ["animal"]}},
        )
    # The lexical signature for ordinary like now accepts entity objects.
    # The explicitly human-only function above must still reject dog.
    assert run("john likes every dog.")["complete"]
