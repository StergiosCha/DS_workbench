"""General MERGE refines addresses and types without losing obligations."""

import pytest

from dylan.action.atomic.merge import Merge
from dylan.tree.label.labels import label_factory_create
from dylan.tree.modality import Modality
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


def pair(target, source, *, address="00", unfixed="0*"):
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt", "subtyping": {"human": ["object"]}}
    for a, specs in ((address, target), (unfixed, source)):
        addr = NodeAddress(a)
        tree[addr] = Node(addr, [label_factory_create(s) for s in specs])
    tree.pointer = NodeAddress(address)
    return tree, Merge(Modality.relating(tree.pointer, NodeAddress(unfixed)))


@pytest.mark.parametrize("target,source", [
    (["Ty(mltt:Prop)"], ["Ty(mltt:object)"]),
    (["?Ty(mltt:Prop)"], ["Ty(mltt:human)"]),
    (["Ty(mltt:object)"], ["?Ty(mltt:Prop)"]),
    (["Ty(classical:e)"], ["Ty(mltt:object)"]),
])
def test_merge_rejects_type_conflicts_before_mutation(target, source):
    tree, effect = pair(target, source)
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


@pytest.mark.parametrize("target,source", [
    (["Ty(mltt:human)"], ["Ty(mltt:object)"]),
    (["Ty(mltt:object)"], ["Ty(mltt:human)"]),
    (["?Ty(mltt:object)"], ["Ty(mltt:human)"]),
])
def test_merge_preserves_the_more_specific_type(target, source):
    tree, effect = pair(target, source + ["?Ex.Tn(x)", "?Ex.Fo(x)"])
    assert effect.exec_tuple_context(tree, None) is tree
    assert str(tree.pointed_node.get_type()) == "human"
    assert tree.pointed_node.contains(label_factory_create("?Ex.Fo(x)"))
    assert not tree.pointed_node.contains(label_factory_create("?Ex.Tn(x)"))
    assert NodeAddress("0*") not in tree


def test_locally_unfixed_object_cannot_merge_into_subject_even_without_rule_guard():
    tree, effect = pair(["?Ty(mltt:object)"], ["Ty(mltt:object)"], unfixed="0P")
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


@pytest.mark.parametrize("old,new", [
    ("Person(1)", "Person(3)"), ("Number(sg)", "Number(pl)"), ("Gender(m)", "Gender(f)"),
])
def test_merge_cannot_erase_nominal_agreement_features(old, new):
    tree, effect = pair(["Ty(mltt:object)", old], ["Ty(mltt:object)", new])
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


@pytest.mark.parametrize("feature,value", [("gender", "masc"), ("number", "pl"), ("person", 1)])
def test_concrete_formula_must_satisfy_clitic_reference_class(feature, value):
    tree, effect = pair(["Ty(mltt:object)", "Fo(U_her)"],
                        ["Ty(mltt:object)", "Fo(mltt:alex)"])
    tree.semantic_profile.update({
        "reference_classes": {"her": {"gender": "fem", "number": "sg", "person": 3}},
        "referents": {"alex": {feature: value}},
    })
    before = tree.clone()
    assert effect.exec_tuple_context(tree, None) is None
    assert tree == before


def test_declared_clitic_gender_accepts_equivalent_nominal_feature_spelling():
    tree, effect = pair(["Ty(mltt:object)", "Fo(U_her)"],
                        ["Ty(mltt:object)", "Fo(mltt:alex)", "Gender(f)"])
    tree.semantic_profile["reference_classes"] = {"her": {"gender": "fem"}}
    assert effect.exec_tuple_context(tree, None) is tree
