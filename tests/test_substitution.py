"""Context substitution respects lexical restrictions, locality and active dialogue paths."""

import pytest

from dynamicsyntax import icp
from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.atomic.substitute import Substitute
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.context.context import Context
from dylan.context.referent import Referent
from dylan.dag.word_level_context_dag import WordLevelContextDAG
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree


@pytest.fixture(autouse=True)
def reset():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def sample(restriction="x", address="010"):
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt", "subtyping": {"human": ["object"]}}
    tree.pointer = NodeAddress(address)
    tree[tree.pointer] = Node(tree.pointer, [label_factory_create(s) for s in
                             ["Ty(mltt:object)", f"Fo(U_{restriction})", "?Ex.Fo(x)"]])
    context = Context(WordLevelContextDAG())
    context.referents = [Referent("mary", "human"), Referent("speaker", "human", 1),
                        Referent("hearer", "human", 2)]
    return tree, context


@pytest.mark.parametrize("restriction,symbol", [("Sp'", "speaker"), ("Hr'", "hearer"), ("x", "mary")])
def test_substitute_respects_person_restriction(restriction, symbol):
    tree, context = sample(restriction)
    assert EffectFactory.create("substitute").exec_tuple_context(tree, context) is tree
    assert str(tree.pointed_node.get_formula()) == symbol
    assert str(tree.pointed_node.get_type()) == "human"
    assert tree.pointed_node.is_complete()


def test_substitute_anti_locality():
    tree, context = sample()
    address = NodeAddress("00")
    tree[address] = Node(address, [label_factory_create("Fo(mltt:mary)")])
    assert Substitute.candidates(tree, context) == []
    assert Substitute().exec_tuple_context(tree, context) is None
    assert context.last_reference_failure["kind"] == "missing_context"
    assert str(tree.pointed_node.get_formula()) == "U_x"


def test_no_referent_is_missing_context():
    tree, context = sample()
    context.referents = []
    assert Substitute().exec_tuple_context(tree, context) is None
    assert context.last_reference_failure["kind"] == "missing_context"


def test_unfixed_reference_waits_until_its_position_is_known():
    tree, context = sample(address="0P")
    assert Substitute().exec_tuple_context(tree, context) is None
    assert context.last_reference_failure is None


def test_named_reference_class_resolves_to_context_before_its_default():
    tree, context = sample("her")
    tree.semantic_profile["reference_classes"] = {"her": {
        "person": 3, "gender": "fem", "number": "sg", "default": "her",
    }}
    context.referents = [Referent("john", "human", gender="masc", number="sg"),
                        Referent("mary", "human", gender="fem", number="sg"),
                        Referent("her", "human", gender="fem", number="sg", source="grammar")]
    assert [r.symbol for r in Substitute.candidates(tree, context)] == ["mary", "her"]
    assert Substitute().exec_tuple_context(tree, context) is tree
    assert str(tree.pointed_node.get_formula()) == "mary"


def test_reference_class_cannot_override_conflicting_lexical_features():
    tree, context = sample("her")
    tree.semantic_profile["reference_classes"] = {"her": {"gender": "fem"}}
    tree.pointed_node.add_label(label_factory_create("Gender(masc)"))
    assert Substitute.candidates(tree, context) == []


@pytest.mark.parametrize("restriction,person,symbol", [
    ("Sp'", 1, "speaker"), ("Hr'", 2, "hearer"), ("x", 2, "hearer"),
    ("x", 3, "mary"), ("Sp'", 2, None), ("Hr'", 3, None),
])
def test_substitute_person_label_and_restriction_agree(restriction, person, symbol):
    tree, context = sample(restriction)
    tree.pointed_node.add_label(label_factory_create(f"Person({person})"))
    result = Substitute().exec_tuple_context(tree, context)
    if symbol:
        assert result is tree
        assert str(tree.pointed_node.get_formula()) == symbol
    else:
        assert result is None
        assert tree.pointed_node.contains(label_factory_create("?Ex.Fo(x)"))


def test_dialogue_names_are_newest_first_and_reset_clears_context():
    parser = icp("2026-english-mltt")
    try:
        from dylan.nlp.types import utterance_from_text

        assert parser.parse_utterance(utterance_from_text("A", "john walks."))
        assert parser.context.referents[0].symbol == "john"
        parser.new_sentence()
        assert parser.parse_utterance(utterance_from_text("B", "mary walks."))
        assert [r.symbol for r in parser.context.referents[:2]] == ["mary", "john"]
        parser.init()
        assert all(r.source == "grammar" for r in parser.context.referents)
    finally:
        parser.close()


def test_context_references_survive_a_new_sentence_but_not_reset():
    parser = icp("2026-english-mltt")
    try:
        parser.context.referents = [Referent("external", "human")]
        parser.new_sentence()
        assert parser.context.referents[0].symbol == "external"
        parser.init()
        assert "external" not in [r.symbol for r in parser.context.referents]
    finally:
        parser.close()


def test_repaired_names_are_removed_from_active_context():
    from dylan.nlp.types import utterance_from_text

    parser = icp("2026-english-mltt", repairing=True)
    try:
        assert parser.parse_utterance(utterance_from_text("A", "john likes mary."))
        assert parser.parse_utterance(utterance_from_text("B", "sorry bill."))
        active = [r.symbol for r in parser.context.referents if r.source == "context"]
        assert active == ["bill", "john"]
    finally:
        parser.close()


def test_substituent_declaration_is_confined_to_the_result_tree():
    tree, context = sample()
    original = tree.clone()
    assert Substitute().exec_tuple_context(tree, context) is tree
    assert tree.semantic_profile["constants"]["mary"] == "human"
    assert "constants" not in original.semantic_profile


def test_substitution_completion_rule_executes_in_a_real_parse(tmp_path):
    import json
    from pathlib import Path
    import shutil
    from dynamicsyntax import parse

    source = Path(__file__).parents[1] / "src/dynamicsyntax/grammars/2026-smg-mltt"
    target = tmp_path / "grammar"
    shutil.copytree(source, target)
    lexical = target / "lexical-actions.txt"
    lexical.write_text(lexical.read_text().replace("put(Fo(mltt:REF))", "put(Fo(U_x))\n      put(?Ex.Fo(x))"))
    with (target / "computational-actions.txt").open("a") as out:
        out.write("\nsubstitution\n!completion\nIF Ex.fo(x)\n   ?Ex.Fo(x)\nTHEN substitute\nELSE abort\n")
    result = parse("ton agapa.", target, trace=True)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == "love(pro, him)"
    assert any(step.action_name == "substitution" for step in result.action_steps)
    theory = target / "semantics.json"
    profile = json.loads(theory.read_text())
    profile["constants"] = {}
    theory.write_text(json.dumps(profile))
    failed = parse("ton agapa.", target)
    assert not failed.ok
    assert failed.parser.context.last_reference_failure["kind"] == "missing_context"
