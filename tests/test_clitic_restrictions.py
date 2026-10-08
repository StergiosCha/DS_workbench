"""PCC failures arise from incompatible decorations at a shared address."""

import pytest

from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.atomic.put import Put
from dylan.action.atomic.if_then_else import IfThenElse
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.formula import Formula
from dylan.formula.formula_metavariable import FormulaMetavariable
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree
from dylan.tree.label.labels import label_factory_create


def build_clitic(tree, edge, formula):
    tree.pointer = tree.root_addr
    for spec in (f"make(\\/{edge})", f"go(\\/{edge})", "put(Ty(e))", f"put(Fo({formula}))"):
        if EffectFactory.create(spec).exec_tuple_context(tree, None) is None:
            return None
    return tree


@pytest.mark.parametrize(
    "name, restriction", [("U_Sp'", "Sp'"), ("V_Hr'", "Hr'"), ("U_x", "x"), ("U1", None)]
)
def test_restricted_metavariables_parse_and_round_trip(name, restriction):
    f = Formula.create(name)
    assert isinstance(f, FormulaMetavariable)
    assert f.restriction == restriction
    assert str(f) == name
    assert Formula.create(str(f)) == f
    assert hash(Formula.create(str(f))) == hash(f)


@pytest.mark.parametrize("edge", ["P", "10"])
def test_incompatible_clitics_on_same_unfixed_or_fixed_address_abort(edge):
    tree = Tree()
    assert build_clitic(tree, edge, "U_Sp'") is tree
    before = len(tree)
    assert build_clitic(tree, edge, "V_Hr'") is None
    assert len(tree) == before
    assert str(tree.pointed_node.get_formula()) == "U_Sp'"


@pytest.mark.parametrize("second_edge", ["*", "10"])
def test_distinct_address_types_coexist(second_edge):
    tree = Tree()
    assert build_clitic(tree, "P", "U_Sp'") is tree
    assert build_clitic(tree, second_edge, "V_Hr'") is tree
    assert str(tree[NodeAddress("0P")].get_formula()) == "U_Sp'"
    assert str(tree[NodeAddress("0" + second_edge)].get_formula()) == "V_Hr'"


@pytest.mark.parametrize("second", ["V_Sp'", "U1"])
def test_compatible_collapse_keeps_existing_restriction(second):
    tree = Tree()
    assert build_clitic(tree, "P", "U_Sp'") is tree
    assert build_clitic(tree, "P", second) is tree
    assert str(tree.pointed_node.get_formula()) == "U_Sp'"
    assert len(tree) == 2


def test_unrestricted_metavariable_can_gain_restriction():
    tree = Tree()
    assert build_clitic(tree, "P", "U1") is tree
    assert Put.parse("put(Fo(U_Sp'))").exec_tuple_context(tree, None) is tree
    assert tree.pointed_node.get_formula().restriction == "Sp'"


def test_case_decorations_clash_on_the_same_collapsed_node():
    tree = Tree()
    assert build_clitic(tree, "P", "U_Sp'") is tree
    assert Put.parse("put(Case(gen))").exec_tuple_context(tree, None) is tree
    assert Put.parse("put(Case(acc))").exec_tuple_context(tree, None) is None
    assert tree.pointed_node.contains(label_factory_create("Case(gen)"))
    assert not tree.pointed_node.contains(label_factory_create("Case(acc)"))


def test_put_freezes_the_captured_address_before_next_rule_reset():
    reset_all_meta_bindings()
    tree = Tree()
    assert label_factory_create("Tn(a)").check_with_tuple_as_context(tree, None)
    assert Put.parse(r"put(</\0></\1+>Tn(a))").exec_tuple_context(tree, None) is tree
    reset_all_meta_bindings()
    assert any(str(lab) == r"</\0></\1+>Tn(0)" for lab in tree.pointed_node.labels)


def clitic_rule(kind, formula, *, gsg=False):
    """Minimal projections of thesis entries (3.64), (3.100), (3.102/104)."""
    indicative = r"[\/+]?Ex.Tn(x)" if kind == "dat" else r"[\/1+]?Ty(x)"
    imperative = r"(Mood(Imp) & [\/1+][\/0]?Ty(x))" if gsg and kind == "dat" else "Mood(Imp)"
    structure = (
        [r"make(\/P)", r"go(\/P)", "put(?Ex.Tn(x))"]
        if kind == "dat"
        else [r"make(\/1)", r"go(\/1)", "put(?Ty(e>t))", r"make(\/0)", r"go(\/0)"]
    )
    return IfThenElse.from_lines(
        [
            "IF ?Ty(t)",
            f"({indicative} || {imperative})",
            "THEN " + structure[0],
            *structure[1:],
            "put(Ty(e))",
            f"put(Fo({formula}))",
            "put(?Ex.Fo(x))",
            "gofirst(?Ty(t))",
            "ELSE abort",
        ]
    )


def imperative_rule():
    return IfThenElse.from_lines(
        [
            "IF ?Ty(t)",
            r"[\/+]?Ex.Tn(x)",
            "THEN put(Mood(Imp))",
            r"make(\/1)",
            r"go(\/1)",
            "put(Ty(e>t))",
            r"go(/\1)",
            "ELSE abort",
        ]
    )


def test_indicative_dat_acc_order_and_imperative_proclisis_block():
    dat, acc = clitic_rule("dat", "U_Sp'"), clitic_rule("acc", "U_x")
    tree = Tree()
    assert dat.exec_tuple_context(tree, None) is tree
    assert acc.exec_tuple_context(tree, None) is tree
    assert imperative_rule().exec_tuple_context(tree, None) is None
    reverse = Tree()
    assert acc.exec_tuple_context(reverse, None) is reverse
    assert dat.exec_tuple_context(reverse, None) is None


@pytest.mark.parametrize("order", [("dat", "acc"), ("acc", "dat")])
def test_smg_imperative_permits_both_clitic_orders(order):
    tree = Tree()
    assert imperative_rule().exec_tuple_context(tree, None) is tree
    for kind in order:
        rule = clitic_rule(kind, "U_Sp'" if kind == "dat" else "U_x")
        assert rule.exec_tuple_context(tree, None) is tree


def test_gsg_imperative_blocks_acc_dat_order():
    tree = Tree()
    assert imperative_rule().exec_tuple_context(tree, None) is tree
    assert clitic_rule("acc", "U_x").exec_tuple_context(tree, None) is tree
    assert clitic_rule("dat", "U_Sp'", gsg=True).exec_tuple_context(tree, None) is None


def test_two_local_clitics_fail_with_incompatible_persons():
    tree = Tree()
    assert clitic_rule("dat", "U_Sp'").exec_tuple_context(tree, None) is tree
    assert clitic_rule("dat", "V_Hr'").exec_tuple_context(tree, None) is None
    assert str(tree[NodeAddress("0P")].get_formula()) == "U_Sp'"
