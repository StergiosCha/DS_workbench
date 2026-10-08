"""Tree / node address invariants."""

from __future__ import annotations

from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


def test_tree_has_axiom_requirement() -> None:
    t = Tree()
    assert t.root_addr == NodeAddress()
    assert any("?" in str(lab) for lab in t.pointed_node.labels)


def test_clone_is_distinct() -> None:
    a = Tree()
    b = a.clone()
    assert a is not b
    assert a.pointer == b.pointer


def test_locally_unfixed_plus_node_unifies_with_indirect_object():
    from dylan.tree.node import Node
    from dylan.tree.label.labels import label_factory_create

    def node(address, typ="e"):
        return Node(NodeAddress(address), [label_factory_create(f"Ty({typ})")])

    unfixed = node("0P")
    assert unfixed.is_unifiable(node("010"))
    assert unfixed.is_unifiable(node("0110"))
    assert not unfixed.is_unifiable(node("00"))
    assert not unfixed.is_unifiable(node("010", "t"))


def test_native_projection_never_runs_ttr_implicit_merge(monkeypatch):
    from dynamicsyntax import parse

    def forbidden(self):
        raise AssertionError("Native projection must not merge implicitly")

    monkeypatch.setattr(Tree, "merge_unfixed", forbidden)
    result = parse("john walks.", "2026-english-mltt")
    assert result.ok
    assert str(result.tree.get_maximal_semantics()) == "walk(john)"
