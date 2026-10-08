"""Thesis LOFT triggers on partial trees and locally unfixed addresses."""

import pytest

from dylan.tree.basic_operator import BasicOperator
from dylan.tree.modality import Modality
from dylan.tree.node_address import NodeAddress
from dylan.action.atomic.go import Go
from dylan.action.atomic.if_then_else import IfThenElse
from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.meta.element import MetaElement, reset_all_meta_bindings
from dylan.action.meta.meta_modality import MetaModality
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node import Node
from dylan.tree.tree import Tree
from dylan.type.dstype import DSType


@pytest.fixture(autouse=True)
def clean_bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def add_node(tree, address, *labels):
    addr = NodeAddress(address)
    tree[addr] = Node(addr, [label_factory_create(s) for s in labels])
    return tree[addr]


def holds(tree, spec):
    pointer = tree.pointer
    result = label_factory_create(spec).check_with_tuple_as_context(tree, None)
    assert tree.pointer == pointer
    return result


@pytest.mark.parametrize(
    "path, expected",
    [
        (r"<\/1+>", {"01", "011"}),
        (r"<\/0+>", {"00", "000"}),
        (r"<\/+>", {"00", "000", "01", "011", "010", "0*", "0P"}),
        (r"<\/*>", {"0*"}),
        (r"<\/>", {"00", "01", "0*", "0P"}),
        (r"<\/1+\/0>", {"010"}),
    ],
)
def test_reachable_partial_tree(path, expected):
    addresses = map(NodeAddress, ["0", "00", "000", "01", "011", "010", "0*", "0P", "0L", "0L1"])
    assert {str(a) for a in Modality.parse(path).reachable(NodeAddress(), addresses)} == expected


def test_plus_is_nonreflexive_and_needs_existing_intermediate_nodes():
    mod = Modality.parse(r"<\/1+>")
    assert not mod.reachable(NodeAddress(), [NodeAddress("0"), NodeAddress("011")])
    assert Modality.parse(r"</\1+>").reachable(
        NodeAddress("011"), map(NodeAddress, ["0", "01", "011"])
    ) == {NodeAddress("0"), NodeAddress("01")}


@pytest.mark.parametrize(
    "target, matches",
    [("00", False), ("010", True), ("0110", True), ("0P", True), ("0U", False), ("0L10", False)],
)
def test_locally_unfixed_plus_excludes_subject_and_link(target, matches):
    assert NodeAddress("0P").subsumes(NodeAddress(target)) is matches
    assert not NodeAddress("0P").is_fixed()


def test_literal_path_binding_and_navigation_bounds():
    source, target = NodeAddress("0P"), NodeAddress("010")
    mod = Modality.relating(source, target)
    assert source.go_modality(mod) == target
    assert mod.inverse().relates(target, source)
    assert Modality.relating(source, source).relates(source, source)
    assert NodeAddress().up("0") is None
    assert NodeAddress().go_op(BasicOperator.parse(r"\/1+")) is None


def test_proclisis_box_is_vacuous_then_blocks_after_verb():
    tree = Tree()
    trigger = r"[\/1+]?Ty(x)"
    assert holds(tree, trigger)
    assert not holds(tree, r"<\/1+>?Ty(x)")
    add_node(tree, "01", "?Ty(e>t)")
    add_node(tree, "011", "?Ty(e>e>t)")
    add_node(tree, "010", "Ty(e)")
    assert holds(tree, trigger)
    add_node(tree, "011", "Ty(e>e>t)")
    assert not holds(tree, trigger)
    assert holds(tree, "¬" + trigger)
    tree.pointed_node.add_label(label_factory_create("Mood(Imp)"))
    assert holds(tree, f"({trigger} || Mood(Imp))")


def test_imperative_box_allows_unfixed_but_blocks_fixed_nodes():
    tree = Tree()
    trigger = r"[\/+]?Ex.Tn(x)"
    assert holds(tree, trigger)
    add_node(tree, "0*", "?Ex.Tn(x)", "Ty(e)")
    add_node(tree, "0P", "?Ex.Tn(x)", "Ty(e)")
    add_node(tree, "0L", "Ty(e)")
    assert holds(tree, trigger)
    add_node(tree, "01", "?Ty(e>t)")
    assert not holds(tree, trigger)


@pytest.mark.parametrize(
    "address, fixed", [("0", True), ("010", True), ("0*", False), ("0P0", False), ("0U", False)]
)
def test_tn_fixedness(address, fixed):
    tree = Tree(NodeAddress(address))
    assert holds(tree, "Ex.Tn(x)") is fixed


def test_type_wildcard_is_not_any_requirement_or_a_rule_meta():
    tree = Tree()
    assert holds(tree, "?Ty(x)")
    assert not holds(tree, "Ty(x)")
    tree.pointed_node.labels = [label_factory_create("?Ex.Tn(x)")]
    assert not holds(tree, "?Ty(x)")


def test_nested_disjunction_conjunction_and_negative_feature():
    tree = Tree()
    tree.pointed_node.add_label(label_factory_create("[+NEG]"))
    assert holds(tree, "+NEG")
    assert holds(tree, "(Mood(Imp) | ([+NEG] & ?Ty(x)))")
    assert not holds(tree, "¬([+NEG] | Mood(Imp))")
    assert holds(tree, r"[\/1+][\/0]?Ty(x)")
    add_node(tree, "01", "Ty(e>t)")
    add_node(tree, "010", "Ty(e)")
    assert not holds(tree, r"[\/1+][\/0]?Ty(x)")


def test_meta_modality_finds_witness_and_go_uses_binding():
    tree = Tree()
    add_node(tree, "00", "Ty(e)")
    add_node(tree, "01", "+Q")
    assert holds(tree, "<Z>+Q")
    frozen = Go(Modality.parse("<Z>")).instantiate()
    assert Go(Modality.parse("<Z>")).exec_tuple_context(tree, None) is tree
    assert str(tree.pointer) == "01"
    reset_all_meta_bindings()
    tree.pointer = tree.root_addr
    assert frozen.exec_tuple_context(tree, None) is tree
    assert str(tree.pointer) == "01"
    assert Go(Modality.parse("<Z>")).exec_tuple_context(tree, None) is None


def test_failed_candidates_and_negation_restore_meta_bindings():
    tree = Tree()
    add_node(tree, "00", "Ty(e)")
    add_node(tree, "01", "Ty(t)", "+Q")
    assert holds(tree, "<Z>(Ty(X) & +Q)")
    assert MetaElement.get("X", DSType).get_value() == DSType.t
    assert str(MetaModality.get("Z").instantiate()) == r"<\/1>"
    reset_all_meta_bindings()
    assert not holds(tree, "¬<Z>+Q")
    assert MetaModality.get("Z").get_meta().get_value() is None
    assert not holds(tree, "<Z>+absent")
    assert MetaModality.get("Z").get_meta().get_value() is None


def test_address_binding_and_box_failure_restore_earlier_bindings():
    tree = Tree()
    assert holds(tree, "Tn(a)")
    add_node(tree, "01", "Ty(e)")
    add_node(tree, "011", "Ty(t)")
    assert not holds(tree, r"[\/1+]Ty(X)")
    assert MetaElement.get("X", DSType).get_value() is None
    assert MetaElement.get("a", NodeAddress).get_value() == NodeAddress()
    tree.pointer = NodeAddress("0110")
    add_node(tree, "0110", "Ty(e)")
    assert holds(tree, r"</\0></\1+>Tn(a)")


def test_unsupported_trigger_warns_once(caplog):
    caplog.set_level("WARNING", logger="dylan.tree.label.labels")
    tree = Tree()
    for _ in range(2):
        assert not holds(tree, "UnknownLoftTest(foo)")
    assert sum("UnknownLoftTest" in r.message for r in caplog.records) == 1


def test_rule_backtracks_to_another_modality_witness():
    tree = Tree()
    add_node(tree, "00", "+candidate")
    add_node(tree, "01", "+candidate", "+chosen")
    rule = IfThenElse(
        [label_factory_create("<Z>+candidate"), label_factory_create("<Z>+chosen")],
        [EffectFactory.create("go(Z)")],
        [EffectFactory.create("abort")],
    )
    assert rule.exec_tuple_context(tree, None) is tree
    assert str(tree.pointer) == "01"


def test_failed_effects_restore_tree_before_trying_another_witness():
    tree = Tree()
    add_node(tree, "00", "+candidate")
    add_node(tree, "01", "+candidate", "+chosen")
    rule = IfThenElse.from_lines([
        "IF <Z>+candidate",
        "THEN go(Z)",
        r"make(\/0)",
        "put(+touched)",
        "IF +chosen",
        "THEN do_nothing",
        "ELSE abort",
        "ELSE abort",
    ])
    assert rule.exec_tuple_context(tree, None) is tree
    assert str(tree.pointer) == "01"
    assert NodeAddress("010") in tree
    assert NodeAddress("000") not in tree
    assert not tree[NodeAddress("00")].contains(label_factory_create("+touched"))
    assert tree[NodeAddress("01")].contains(label_factory_create("+touched"))


@pytest.mark.parametrize("spec", ["Case(acc)", "Person(1)", "person(2)", "Number(sg)", "Gender(fem)", "Aspect(perf)"])
def test_case_person_number_labels_are_unary_predicates(spec):
    from dylan.tree.label.labels import Requirement, UnaryPredicateLabel, generic_label_seen

    before = set(generic_label_seen)
    label = label_factory_create(spec)
    assert isinstance(label, UnaryPredicateLabel)
    requirement = label_factory_create("?" + spec)
    assert isinstance(requirement, Requirement)
    assert requirement.inner == label
    tree = Tree()
    tree.pointed_node.add_label(label)
    assert holds(tree, spec)
    assert generic_label_seen == before


@pytest.mark.parametrize("target,expected", [("010", True), ("0110", True), ("00", False)])
def test_subsumes_label_binds_witness_and_checks_address_pattern(target, expected):
    tree = Tree()
    add_node(tree, "0P", "?Ex.Tn(x)", "Ty(e)")
    for length in range(2, len(target)):
        add_node(tree, target[:length], "?Ty(e>t)")
    add_node(tree, target, "?Ty(e)")
    tree.pointer = NodeAddress(target)
    assert not holds(tree, "subsumes(Y)")
    assert holds(tree, "<Y>(?Ex.Tn(x) & Ty(e))")
    label = label_factory_create("subsumes(Y)")
    assert label.check_with_tuple_as_context(tree, None) is expected
    frozen = label.instantiate()
    reset_all_meta_bindings()
    assert frozen.check_with_tuple_as_context(tree, None) is expected
    assert tree.pointer == NodeAddress(target)
