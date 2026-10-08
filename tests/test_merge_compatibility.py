"""MERGE must not destroy conflicting decorations or lose resolved reference."""

import pytest

from dylan.action.atomic.merge import Merge
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.label.labels import label_factory_create
from dylan.tree.modality import Modality
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


@pytest.fixture(autouse=True)
def reset():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def sample(old, new):
    tree = Tree()
    for address, formula in [("010", old), ("0P", new)]:
        addr = NodeAddress(address)
        labels = [label_factory_create("Ty(e)"), label_factory_create(f"Fo({formula})")]
        if address == "0P":
            labels += [label_factory_create("?Ex.Tn(x)"), label_factory_create("?Ex.Fo(x)")]
        tree[addr] = Node(addr, labels)
    tree.pointer = NodeAddress("010")
    return tree, Merge(Modality.relating(tree.pointer, NodeAddress("0P")))


@pytest.mark.parametrize("old,new", [("U_Sp'", "V_Hr'"), ("john", "mary"), ("mltt:john", "mltt:mary")])
def test_merge_blocks_incompatible_formula_restrictions(old, new):
    tree, merge = sample(old, new)
    before = tree.clone()
    assert merge.exec_tuple_context(tree, None) is None
    assert tree == before


def test_merge_blocks_incompatible_cases_without_mutation():
    tree, merge = sample("U_x", "U_x")
    tree.pointed_node.add_label(label_factory_create("Case(acc)"))
    tree[NodeAddress("0P")].add_label(label_factory_create("Case(gen)"))
    before = tree.clone()
    assert merge.exec_tuple_context(tree, None) is None
    assert tree == before


@pytest.mark.parametrize("old,new,expected", [("john", "U_x", "john"), ("U_x", "john", "john"),
                                            ("U_Sp'", "U1", "U_Sp'"), ("U1", "V_Hr'", "V_Hr'")])
def test_merge_keeps_most_informative_compatible_formula(old, new, expected):
    tree, merge = sample(old, new)
    assert merge.exec_tuple_context(tree, None) is tree
    assert NodeAddress("0P") not in tree
    assert str(tree.pointed_node.get_formula()) == expected
    assert not tree.pointed_node.contains(label_factory_create("?Ex.Tn(x)"))
    if expected == "john":
        assert not tree.pointed_node.contains(label_factory_create("?Ex.Fo(x)"))
