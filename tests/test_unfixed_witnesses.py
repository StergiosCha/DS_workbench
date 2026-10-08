"""Nominal witnesses survive MERGE, address reuse and constructive export."""

import re
import shutil

import pytest

from dylan.action.atomic.merge import Merge
from dylan.action.atomic.semantic_effects import eliminate
from dylan.corpus import compile_coq
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType, apply_semantics
from dylan.formula.mltt.terms import parse_expr
from dylan.tree.label.labels import FormulaLabel, label_factory_create
from dylan.tree.modality import Modality
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


def add_dp(tree, address):
    for suffix, labels in {
        "": ["?Ty(mltt:object)", "?Ex.Tn(x)"],
        "0": ["Ty(mltt:CN)", "Fo(mltt:man)"],
        "1": ["Ty(mltt:arrow(CN,object))", "Fo(mltt:lam(A,CN,sigma(x,A,top)))"],
    }.items():
        addr = NodeAddress(address + suffix)
        tree[addr] = Node(addr, [label_factory_create(s) for s in labels])
    tree.pointer = NodeAddress(address)
    assert eliminate(tree) is tree
    return tree.pointed_node.get_formula(), tree.pointed_node.get_type()


def test_reused_unfixed_address_creates_two_distinct_witnesses_that_compile():
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt", "subtyping": {"man": ["object"]},
                             "predicates": {"see": ["object", "object"]}}
    first, first_type = add_dp(tree, "0*")
    assert re.fullmatch(r"[A-Za-z][A-Za-z_0-9]*", first.term.name)
    target = NodeAddress("00")
    tree[target] = Node(target, [label_factory_create("?Ty(mltt:object)")])
    tree.pointer = target
    assert Merge(Modality.relating(target, NodeAddress("0*"))).exec_tuple_context(tree, None)
    assert tree[target].get_formula().term == first.term
    second, second_type = add_dp(tree, "0*")
    assert first.term != second.term
    assert len({first.witnesses[0].variable, second.witnesses[0].variable}) == 2
    predicate = SemanticFormula(parse_expr("lam(y,object,lam(x,object,see(x,y)))"))
    typ = SemanticType(parse_expr("arrow(object,arrow(object,Prop))"))
    vp, vp_type = apply_semantics(predicate, typ, second, second_type, tree.semantic_profile)
    meaning, _ = apply_semantics(vp, vp_type, first, first_type, tree.semantic_profile)
    meaning = meaning.close_witnesses()
    meaning.theory = tree.semantic_profile
    assert not {first.term.name, second.term.name} & meaning.term.free()
    if shutil.which("coqc"):
        assert compile_coq(meaning.to_coq(), {}) == "passed"


@pytest.mark.parametrize("collision", ["free", "bound", "declared"])
def test_witness_name_avoids_existing_symbols(collision):
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    if collision == "declared":
        tree.semantic_profile["constants"] = {"p00": "object"}
    else:
        term = "p00" if collision == "free" else "lam(p00,object,p00)"
        tree.get_root_node().add_label(FormulaLabel(SemanticFormula(parse_expr(term))))
    formula, _ = add_dp(tree, "00")
    assert formula.term.name != "p00"
