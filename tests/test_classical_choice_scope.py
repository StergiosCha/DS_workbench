"""Choice scope checked against independent finite-model truth conditions."""

from itertools import product
from pathlib import Path

import pytest

from dynamicsyntax import icp
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.choice_scope import close_choices
from dylan.formula.mltt.semantics import parse_semantic_type
from dylan.formula.mltt.terms import Expr, parse_expr
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def reset_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def evaluate(term, environment, individuals):
    """Standard Hilbert epsilon picks a witness; tau picks a counterexample.

    This evaluator knows nothing about the parser's scope-resolution code.
    Changing enumeration order changes the choice function, not truth.
    """
    if term.kind == "name":
        return environment[term.name]
    if term.kind == "choice_scope":
        return evaluate(term.args[0], environment, individuals)
    if term.kind == "app":
        return evaluate(term.args[0], environment, individuals)(
            evaluate(term.args[1], environment, individuals))
    if term.kind in {"eps", "tau"}:
        values = [(x, evaluate(term.args[1], {**environment, term.name: x}, individuals))
                  for x in individuals]
        desired = term.kind == "eps"
        return next((x for x, holds in values if holds == desired), individuals[0])
    if term.kind == "and":
        return evaluate(term.args[0], environment, individuals) and evaluate(term.args[1], environment, individuals)
    if term.kind == "implies":
        return not evaluate(term.args[0], environment, individuals) or evaluate(term.args[1], environment, individuals)
    raise AssertionError(f"Unexpected logical constructor: {term.kind}")


def walk(term):
    yield term
    for arg in term.args:
        yield from walk(arg)


def parse_scoped(sentence, scope):
    parser = icp("2026-english-classical", strict=True, top_n=0)
    parser.semantic_profile["scope"] = scope
    try:
        result = parser.parse(sentence)
        assert result.ok and result.tree.is_complete()
        # The result is already constructed in the DS tree, before export.
        assert result.tree.get_root_node().get_formula().term == result.semantics.term
        return result.semantics.term
    finally:
        parser.close()


@pytest.mark.parametrize("order", [(0, 1, 2, 3), (3, 2, 1, 0)])
def test_actual_doctor_patient_readings_in_finite_models(order):
    narrow = parse_scoped("every doctor examined a patient.", "narrow")
    wide = parse_scoped("every doctor examined a patient.", "wide")
    assert narrow != wide
    assert all(node.kind not in {"forall", "pi", "sigma"} for term in (narrow, wide) for node in walk(term))
    # Include empty restrictors and the two-doctor/two-patient case. Every
    # possible examination relation between those doctors and patients is
    # checked; the expectations use Python quantification, not our compiler.
    edges = tuple(product((0, 1), (2, 3)))
    for doctors, patients, mask in product((set(), {0}, {0, 1}), (set(), {2}, {2, 3}), range(16)):
        examined = {edge for bit, edge in enumerate(edges) if mask & (1 << bit)}
        env = {"doctor": lambda x: x in doctors, "patient": lambda x: x in patients,
               "examine": lambda d: lambda p: (d, p) in examined}
        assert evaluate(narrow, env, order) == all(any((d, p) in examined for p in patients) for d in doctors)
        assert evaluate(wide, env, order) == any(all((d, p) in examined for d in doctors) for p in patients)


def test_narrow_patient_choice_contains_doctor_parameter():
    term = parse_scoped("every doctor examined a patient.", "narrow")
    universals = [node for node in walk(term) if node.kind == "tau"]
    assert universals
    doctor_choice = universals[0]
    patient_choices = [node for node in walk(doctor_choice.args[1]) if node.kind == "eps"]
    assert patient_choices and any(doctor_choice.name in patient.free() for patient in patient_choices)
    assert not (term.free() & {"c", "c1", "x0", "x1"})


def test_choice_closure_is_capture_avoiding_idempotent_and_serializable():
    raw = parse_expr("know(c,eps(x,e,patient(x)))")
    # Embed a universal without capturing the pre-existing parameter c.
    raw = Expr("and", args=(raw, parse_expr("walk(tau(x,e,doctor(x)))")))
    closed = close_choices(raw)
    assert "c" in closed.free()
    assert close_choices(closed, "wide") == closed
    assert parse_expr(closed.to_source()) == closed
    assert r"\tau" in closed.to_tex() and "choice_scope" not in str(closed)


def test_closed_complement_retains_its_scope():
    term = parse_scoped("a man thinks that every doctor examined a patient.", "wide")
    # The matrix subject remains an independent nominal choice. The embedded
    # patient choice cannot move out to take scope over think or that subject.
    assert term.kind == "choice_scope"
    matrix = term.args[0]
    assert matrix.kind == "app" and matrix.args[1].kind == "choice_scope"
    assert matrix.args[0].args[1].kind == "eps"
    assert matrix.args[1] == parse_scoped("every doctor examined a patient.", "wide")


@pytest.mark.parametrize("sentence", ["all people walk.", "all the people walk.", "john knows all people."])
def test_all_remains_individual_valued_in_the_tree(sentence):
    result = parse_request({"sentence": sentence, "grammar": "2026-english-classical",
                            "lexical_mode": "dictionary"})
    assert result["complete"]
    assert "τ" in result["words"][-1]["semantics"] and "∀" not in result["words"][-1]["semantics"]
    assert any(n["type"] == "cn → e" for frame in result["words"] for n in frame["nodes"])
    assert not parse_semantic_type("classical:e").accepts_requirement(
        parse_semantic_type("classical:arrow(arrow(e,t),t)"))


def test_generator_preserves_the_same_choice_template(tmp_path, monkeypatch):
    import importlib.util
    import shutil

    root = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location("everyday", root / "scripts/build_everyday_extensions.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    for language in ("english", "smg"):
        name = f"2026-{language}-classical"
        shutil.copytree(root / "src/dynamicsyntax/grammars" / name, tmp_path / name)
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    generator.build("classical")
    actions = (tmp_path / "2026-english-classical/lexical-actions.txt").read_text()
    for template in ("universal", "all-plural", "all-contextual"):
        body = generator.block(actions, template)
        assert "choice_tau(P)" in body and "forall(" not in body
        assert "Ty(classical:arrow(cn,e))" in body
