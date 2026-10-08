"""MERGE moves complete nominal subtrees and checks every overlapping node."""

import pytest

from dylan.action.atomic.merge import Merge
from dylan.tree.label.labels import label_factory_create
from dylan.tree.modality import Modality
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


def sample(specs):
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    for address, labels in specs.items():
        addr = NodeAddress(address)
        tree[addr] = Node(addr, [label_factory_create(s) for s in labels])
    tree.pointer = NodeAddress("00")
    return tree, Merge(Modality.relating(tree.pointer, NodeAddress("0*")))


@pytest.mark.parametrize("target,source", [
    (["Fo(mltt:john)"], ["Fo(mltt:mary)"]),
    (["Ty(mltt:CN)"], ["Ty(mltt:Prop)"]),
    (["Case(nom)"], ["Case(acc)"]),
])
def test_descendant_conflict_leaves_entire_tree_unchanged(target, source):
    tree, effect = sample({"00": ["?Ty(mltt:object)"],
                           "0*": ["Ty(mltt:object)", "?Ex.Tn(x)"],
                           "000": target, "0*0": source,
                           "0*1": ["Ty(mltt:CN)"]})
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


def test_descendant_union_preserves_destination_requirements_and_more_specific_values():
    tree, effect = sample({"00": ["?Ty(mltt:object)"],
                           "0*": ["Ty(mltt:object)", "?Ex.Tn(x)"],
                           "000": ["Ty(mltt:human)", "Fo(mltt:john)", "?[+CHECK]"],
                           "0*0": ["Ty(mltt:object)", "Fo(U_x)", "?Ex.Fo(x)"]})
    assert effect.exec_tuple_context(tree, None) is tree
    node = tree[NodeAddress("000")]
    assert str(node.get_type()) == "human" and str(node.get_formula()) == "john"
    assert node.contains(label_factory_create("?[+CHECK]"))
    assert not node.contains(label_factory_create("?Ex.Fo(x)"))


def test_moves_cn_link_and_locally_unfixed_plus_descendants():
    tree, effect = sample({"00": ["?Ty(mltt:object)"],
                           "0*": ["Ty(mltt:object)", "?Ex.Tn(x)"],
                           "0*0": ["Ty(mltt:CN)"],
                           "0*00": ["Fo(mltt:man)"],
                           "0*L": ["?Ty(mltt:Prop)"],
                           "0*P": ["Ty(mltt:object)", "?Ex.Tn(x)"],
                           "0*P0": ["?Ex.Fo(x)"]})
    assert NodeAddress("0*P") in {n.address for n in tree.get_unfixed_nodes()}
    assert NodeAddress("0*P") in {n.address for n in tree.get_daughters(tree[NodeAddress("0*")])}
    assert effect.exec_tuple_context(tree, None) is tree
    assert set(map(str, tree)) == {"0", "00", "000", "0000", "00L", "00P", "00P0"}
    assert str(tree[NodeAddress("0000")].get_formula()) == "man"
    assert tree[NodeAddress("00P")].contains(label_factory_create("?Ex.Tn(x)"))
    assert tree[NodeAddress("00P0")].contains(label_factory_create("?Ex.Fo(x)"))


@pytest.mark.parametrize("terminal,children", [("00", "0*"), ("0*", "00")])
def test_terminal_restriction_blocks_dp_daughters_in_either_direction(terminal, children):
    tree, effect = sample({"00": ["Ty(mltt:object)"], "0*": ["Ty(mltt:object)"]})
    tree[NodeAddress(terminal)].add_label(label_factory_create("!"))
    child = NodeAddress(children + "0")
    tree[child] = Node(child, [label_factory_create("Ty(mltt:CN)")])
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


def test_terminal_restriction_still_allows_link_daughter():
    tree, effect = sample({"00": ["Ty(mltt:object)", "!"],
                           "0*": ["Ty(mltt:object)"], "0*L": ["?Ty(mltt:Prop)"]})
    assert effect.exec_tuple_context(tree, None) is tree
    assert NodeAddress("00L") in tree
