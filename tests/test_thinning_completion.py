"""Regression: *thinning metavariable binding and completion-related tree state."""

from __future__ import annotations

from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.label.labels import MetaLabel, Requirement, TypeLabel, label_factory_create
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree
from dylan.type.dstype import DSType


def test_label_factory_meta_label_for_v_to_z_and_meta() -> None:
    """Uppercase ``V``–``Z`` (optional digits) and ``META`` become side-effecting :class:`MetaLabel`."""
    assert isinstance(label_factory_create("X"), MetaLabel)
    assert isinstance(label_factory_create("V0"), MetaLabel)
    assert isinstance(label_factory_create("META"), MetaLabel)
    assert not isinstance(label_factory_create("x"), MetaLabel)


def test_thinning_deletes_requirement_when_pattern_matches() -> None:
    """``*thinning`` IF ``?X`` + ``X`` must bind ``X`` to an on-node label and ``delete(?X)`` drops the requirement."""
    reset_all_meta_bindings()
    lines = [
        "IF      ?X",
        "        X",
        "THEN    delete(?X)",
        "ELSE    abort",
    ]
    eff = EffectFactory.create_lines(lines)
    addr = NodeAddress()
    node = Node(
        addr,
        [Requirement(TypeLabel(DSType.t)), TypeLabel(DSType.t)],
    )
    t: Tree = Tree.__new__(Tree)
    dict.__init__(t)
    t.root_addr = addr
    t.pointer = addr
    t._entity_pool = []
    t._event_pool = []
    t._proposition_pool = []
    t._record_type_pool = []
    t._predicate_pool = []
    t[addr] = node

    out = eff.exec_tuple_context(t, None)
    assert out is not None
    assert not any(isinstance(lab, Requirement) for lab in out.pointed_node.labels)
    assert out.is_complete()
    reset_all_meta_bindings()


def test_requirement_instantiate_propagates_inner() -> None:
    """Bound metavar inside ``?`` must resolve via :meth:`Requirement.instantiate`."""
    reset_all_meta_bindings()
    try:
        z = MetaLabel.get("Z")
        assert z == TypeLabel(DSType.e)
        req = Requirement(z)
        inst = req.instantiate()
        assert isinstance(inst, Requirement)
        assert isinstance(inst.inner, TypeLabel)
        assert inst.inner.type == DSType.e
    finally:
        reset_all_meta_bindings()


def test_completion_grammar_declared_not_hardcoded(tmp_path):
    from dylan.action.grammar import Grammar
    from dylan.action.lexicon import Lexicon
    from dylan.parser.interactive_context_parser import InteractiveContextParser

    (tmp_path / "computational-actions.txt").write_text(
        "merge-local\n!completion\nIF ?Ty(t)\nTHEN abort\nELSE abort\n\n"
        "completion\nIF ?Ty(t)\nTHEN abort\nELSE abort\n\n"
        "anticipation0\nIF ?Ty(t)\nTHEN abort\nELSE abort\n"
    )
    grammar = Grammar(tmp_path, strict=True)
    parser = InteractiveContextParser.from_loaded(Lexicon(), grammar)
    assert set(parser.completion_grammar) == {"merge-local"}
    actions = [grammar["completion"], grammar["anticipation0"], grammar["merge-local"]]
    assert parser._index_of_trp(actions) == 2
    assert grammar["merge-local"].instantiate().completion
    assert not grammar["completion"].completion

    grammar["merge-local"].completion = False
    legacy = InteractiveContextParser.from_loaded(Lexicon(), grammar)
    assert set(legacy.completion_grammar) == {"completion", "anticipation0"}
    assert legacy._index_of_trp(actions) == 0


def test_modal_case_filter_is_thinned_after_merge():
    from dylan.action.atomic.merge import Merge

    reset_all_meta_bindings()
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    labels = {
        "0": ["Ty(mltt:Prop)"],
        "01": ["Ty(mltt:arrow(object,Prop))"],
        "010": ["?Ty(mltt:object)"],
        "0P": ["Ty(mltt:object)", "Fo(mltt:speaker)", "?Ex.Tn(x)",
               r"?</\0>Ty(mltt:arrow(object,Prop))"],
    }
    for address, values in labels.items():
        addr = NodeAddress(address)
        tree[addr] = Node(addr, [label_factory_create(value) for value in values])
    assert not tree.is_complete()
    tree.pointer = NodeAddress("0P")
    assert EffectFactory.create("semantic-thin").exec_tuple_context(tree, None) is None
    tree.pointer = NodeAddress("010")
    assert Merge.parse(r"merge(/\0/\1\/P)").exec_tuple_context(tree, None) is tree
    thin = EffectFactory.create("semantic-thin")
    while thin.exec_tuple_context(tree, None) is not None:
        pass
    tree.pointer = tree.root_addr
    assert tree.is_complete()
    reset_all_meta_bindings()


def test_modal_case_filter_is_not_deleted_when_parent_has_wrong_type():
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    tree[tree.root_addr] = Node(tree.root_addr, [label_factory_create("Ty(mltt:Prop)")])
    tree.pointer = NodeAddress("00")
    tree[tree.pointer] = Node(tree.pointer, [label_factory_create(s) for s in
        ["Ty(mltt:object)", r"?</\0>Ty(mltt:arrow(object,Prop))"]])
    assert EffectFactory.create("semantic-thin").exec_tuple_context(tree, None) is None
    tree.pointer = tree.root_addr
    assert not tree.is_complete()


def test_parent_type_inference_keeps_formula_and_false_case_requirements():
    reset_all_meta_bindings()
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt", "constants": {"john": "object"},
                             "predicates": {"walk": ["object"]}}
    values = {
        "0": ["?Ty(mltt:Prop)"],
        "00": ["Ty(mltt:object)", "Fo(mltt:john)", r"?</\0>Ty(mltt:arrow(object,Prop))"],
        "01": ["Ty(mltt:arrow(object,Prop))", "Fo(mltt:lam(x,object,walk(x)))"],
    }
    for address, specs in values.items():
        a = NodeAddress(address)
        tree[a] = Node(a, [label_factory_create(s) for s in specs])
    tree.pointer = NodeAddress("00")
    effect = EffectFactory.create("semantic-project-parent-type")
    assert effect.exec_tuple_context(tree, None) is tree
    assert str(tree.get_root_node().get_type()) == "Prop"
    assert tree.get_root_node().get_formula() is None
    assert tree.get_root_node().contains(label_factory_create("?Ex.Fo(x)"))
    assert EffectFactory.create("semantic-thin").exec_tuple_context(tree, None) is None
    tree.pointer = tree.root_addr
    assert not tree.is_complete()
    reset_all_meta_bindings()


def test_formula_thinning_does_not_discharge_a_different_formula():
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    tree[tree.root_addr] = Node(tree.root_addr, [label_factory_create(s) for s in
        ["Ty(mltt:object)", "Fo(mltt:mary)", "?Ex.Fo(mltt:john)"]])
    assert EffectFactory.create("semantic-thin").exec_tuple_context(tree, None) is None
    assert not tree.is_complete()
