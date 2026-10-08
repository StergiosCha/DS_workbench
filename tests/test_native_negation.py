"""Constructive negation, including witness refutation, and minimal theory export."""

import shutil
import subprocess

import pytest

from dynamicsyntax import parse
from dylan.action.atomic.effect_factory import EffectFactory
from dylan.formula.mltt.semantics import parse_semantic_formula
from dylan.formula.mltt.terms import parse_expr
from dylan.tree.label.labels import label_factory_create
from dylan.tree.tree import Tree


def compile_formula(formula, tmp_path):
    if shutil.which("coqc"):
        source = tmp_path / "Negation.v"
        source.write_text(formula.to_coq())
        proc = subprocess.run([shutil.which("coqc"), str(source)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_negate_is_an_action_on_a_typed_proposition(backend, tmp_path):
    result = parse("john walks.", f"2026-english-{backend}")
    tree = result.tree.clone()
    effect = EffectFactory.create("semantic-negate")
    assert effect.exec_tuple_context(tree, None) is tree
    assert str(tree.get_root_node().get_formula()) == "¬(walk(john))"
    assert tree.get_root_node().get_type() == result.tree.get_root_node().get_type()
    if backend == "mltt":
        formula = tree.get_root_node().get_formula()
        assert "(~ (walk john))" in formula.to_coq()
        compile_formula(formula, tmp_path)


def test_negation_closes_existential_witnesses_under_its_scope(tmp_path):
    tree = parse("a man walks.", "2026-english-mltt").tree.clone()
    assert EffectFactory.create("semantic-negate").exec_tuple_context(tree, None)
    formula = tree.get_root_node().get_formula()
    assert formula.term.kind == "neg" and formula.term.args[0].kind == "sigma"
    assert not formula.witnesses
    assert "-> False" in formula.to_coq()
    compile_formula(formula, tmp_path)


def test_negate_rejects_a_nominal_decoration():
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    tree.pointed_node.labels = [label_factory_create("Ty(mltt:human)"), label_factory_create("Fo(mltt:john)")]
    assert EffectFactory.create("semantic-negate").exec_tuple_context(tree, None) is None


def test_minimal_export_keeps_only_reachable_declarations_and_ancestors(tmp_path):
    formula = parse("john walks quietly.", "2026-english-mltt").semantics
    minimal = formula.to_coq()
    assert "Parameter quietly" in minimal and "Parameter walk" in minimal
    assert "Record human" in minimal and "Record animal" in minimal
    assert "Parameter object" in minimal
    assert "Parameter mary" not in minimal and "Record dog" not in minimal
    assert "Parameter quickly" not in minimal and "Parameter think" not in minimal
    assert "Parameter mary" in formula.to_coq(minimal=False)
    compile_formula(formula, tmp_path)


def test_negation_term_parsing_binding_and_tex():
    term = parse_expr("neg(pi(x,human,walk(x)))")
    assert term.free() == {"human", "walk"}
    assert r"\neg" in term.to_tex()
    assert str(term).startswith("¬(Π")
    assert parse_semantic_formula("mltt:neg(walk(john))").term.kind == "neg"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence,meaning", [
    ("john does not walk.", "¬(walk(john))"),
    ("john does not know mary.", "¬(know(john, mary))"),
    ("john thinks that mary does not walk.", "think(john, ¬(walk(mary)))"),
    ("john does not think that mary walks.", "¬(think(john, walk(mary)))"),
])
def test_do_support_negates_the_local_clause(backend, sentence, meaning, tmp_path):
    result = parse(sentence, f"2026-english-{backend}", strict=True, trace=True)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == meaning
    assert any(step.action_name == "negation" for step in result.action_steps)
    if backend == "mltt":
        compile_formula(result.semantics, tmp_path)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "john does not walks.", "john not walks.", "john does not not walk.",
    "john does does walk.", "john does not.",
])
def test_do_support_retains_bare_predicate_requirement(backend, sentence):
    result = parse(sentence, f"2026-english-{backend}", strict=True)
    assert not result.ok and result.cap_hit is None


def test_surface_negation_respects_witness_scope(tmp_path):
    from dynamicsyntax import icp

    narrow = parse("a man does not walk.", "2026-english-mltt").semantics
    parser = icp("2026-english-mltt")
    parser.semantic_profile["scope"] = "wide"
    try:
        wide = parser.parse("a man does not walk.").semantics
    finally:
        parser.close()
    assert narrow.term.kind == "neg" and narrow.term.args[0].kind == "sigma"
    assert wide.term.kind == "sigma" and wide.term.args[-1].kind == "neg"
    compile_formula(narrow, tmp_path)
    compile_formula(wide, tmp_path)
