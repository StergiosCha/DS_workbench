"""Thesis topic-copy strategy with approved names and disclosed verb adaptations."""

from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree
from dylan.workbench_api import parse_request

ROOT = Path(__file__).parents[1]


@pytest.fixture(params=["mltt", "classical"])
def grammar(request):
    reset_all_meta_bindings()
    yield f"2026-smg-{request.param}"
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence", [
    "o γiorγos ton ksero.", "o γiorγos, ton ksero.",
    "ο γιώργος, τον ξέρω.", "o γiorγos, xtipise to γiani.",
])
def test_topic_is_a_separate_nominative_tree_with_a_matching_clause_referent(grammar, sentence):
    # (2.95), with the already approved ksero replacing source gnorizo;
    # the last example uses the source (2.50) vocabulary under (2.101).
    result = parse(sentence, grammar, strict=True, trace=True)
    assert result.ok and result.tree.is_complete() and result.cap_hit is None
    topic = result.tree[NodeAddress("0B")]
    assert topic.contains(label_factory_create("Case(nom)"))
    assert str(topic.get_formula()) == "giorgos"
    referent = result.tree[NodeAddress("00" if "xtipise" in sentence else "010")]
    assert str(referent.get_formula()) == "giorgos"
    if "xtipise" not in sentence:
        assert referent.contains(label_factory_create("Case(acc)"))
        assert str(result.semantics) == "know(speaker, giorgos)"
    else:
        assert str(result.semantics) == "hit(giorgos, giannis)"
    assert result.action_steps[-1].after_tree == result.tree
    if result.semantics.backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result.semantics.to_coq(), {}) == "passed"


@pytest.mark.parametrize("sentence", [
    "o γiorγos, tin ksero.", "o γiorγos, tus ksero.",
    "o γiorγos, ksero ton γiani.", "o γiorγos, ksero.",
    "o γiorγos,", "o γiorγos, , ton ksero.", ", ton ksero.",
])
def test_copy_agreement_and_incomplete_topic_controls(grammar, sentence):
    result = parse_request({"sentence": sentence, "grammar": grammar, "strict": True})
    assert not result["complete"] and result["cap_hit"] is None


def test_svo_has_both_subject_merge_and_topic_link_with_independent_playback(grammar):
    result = parse_request({"sentence": "o γiorγos xtipise to γiani.", "grammar": grammar,
                            "n_best": 8, "reading_traces": True})
    assert result["complete"]
    merged = next(r for r in result["readings"] if r["strategies"] == ["star-adjunction"])
    linked = next(r for r in result["readings"] if r["strategies"] == ["link"])
    assert merged["normalized"] == linked["normalized"] == "hit(giorgos, giannis)"
    assert not any(n["id"] == "0B" for n in merged["tree"]["nodes"])
    assert {"source": "0B", "target": "0", "kind": "link", "path": "L"} in linked["tree"]["edges"]
    operations = linked["trace"]["operations"]
    assert any(frame["label"] == r"make(/\L)" and frame["delta"]["created"] == ["0B"]
               for frame in operations if "delta" in frame)
    assert any(frame.get("pointer_before") == "0" and frame["pointer"] == "0B" for frame in operations)
    assert any("SharedFo" in label for frame in operations for node in frame["nodes"]
               for label in node["requirements"])
    assert operations[-1]["nodes"] == linked["tree"]["nodes"]
    assert not any(frame.get("trace_note") for frame in operations)


def test_topic_copy_requirement_ignores_its_source_and_unfixed_or_context_occurrences():
    tree = Tree()
    tree.semantic_profile = {"backend": "mltt"}
    condition = label_factory_create("?SharedFo(mltt:giorgos)")
    tree.pointed_node.labels = [label_factory_create("Ty(mltt:Prop)"), condition]
    for address in ("0B", "0*", "0C"):
        addr = NodeAddress(address)
        tree[addr] = Node(addr, [label_factory_create("Fo(mltt:giorgos)")])
    thin = EffectFactory.create("semantic-thin")
    assert thin.exec_tuple_context(tree, None) is None
    # A formula in a further forward-LINKed tree can satisfy D in (2.94).
    addr = NodeAddress("0L0")
    tree[addr] = Node(addr, [label_factory_create("Fo(mltt:giorgos)")])
    assert thin.exec_tuple_context(tree, None) is tree
    assert condition not in tree.pointed_node.labels
