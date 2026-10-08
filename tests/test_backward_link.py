"""Inverse LINK creates a separate tree while preserving the clause address."""

from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.atomic.substitute import local_references
from dylan.tree.label.labels import label_factory_create
from dylan.tree.modality import Modality
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree
from dylan.workbench_api import tree_snapshot


def test_inverse_link_make_go_and_modal_paths_preserve_the_original_root():
    tree = Tree()
    assert EffectFactory.create(r"make(/\L)").exec_tuple_context(tree, None) is tree
    assert tree.pointer == NodeAddress("0")
    assert EffectFactory.create(r"go(/\L)").exec_tuple_context(tree, None) is tree
    topic = tree.pointer
    assert topic == NodeAddress("0B")
    assert label_factory_create(r"<\/L>Tn(0)").check_with_tuple_as_context(tree, None)
    assert EffectFactory.create(r"go(\/L)").exec_tuple_context(tree, None) is tree
    assert tree.pointer == NodeAddress("0")
    assert Modality.relating(tree.pointer, topic).reachable(tree.pointer, tree) == {topic}
    assert Modality.relating(topic, tree.pointer).reachable(topic, tree) == {tree.pointer}
    # Neither node is a syntactic daughter of the other.
    assert topic not in Modality.parse(r"<\/+>").reachable(tree.pointer, tree)
    assert tree.pointer not in Modality.parse(r"<\/+>").reachable(topic, tree)
    assert tree_snapshot(tree, None)["edges"] == [
        {"source": "0B", "target": "0", "path": "L", "kind": "link"},
    ]


def test_backward_link_referent_is_nonlocal_for_clause_substitution():
    tree = Tree()
    for effect in [r"make(/\L)", r"go(/\L)", "put(Fo(mltt:giorgos))",
                   r"go(\/L)", r"make(\/0)", r"go(\/0)"]:
        assert EffectFactory.create(effect).exec_tuple_context(tree, None) is tree
    assert "giorgos" not in local_references(tree)


def test_existing_forward_link_round_trip_is_preserved():
    tree = Tree()
    for effect in [r"make(\/L)", r"go(\/L)", r"go(/\L)"]:
        assert EffectFactory.create(effect).exec_tuple_context(tree, None) is tree
    assert tree.pointer == NodeAddress("0") and NodeAddress("0B") not in tree
