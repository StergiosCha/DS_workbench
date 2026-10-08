"""Unfixed nominal positions and their eventual case-constrained MERGE."""

import json
from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.grammar import Grammar
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.tree import Tree

ROOT = Path(__file__).parents[1] / "src/dynamicsyntax/grammars"


@pytest.fixture(params=["mltt", "classical"])
def grammar(request, tmp_path):
    reset_all_meta_bindings()
    target = tmp_path / "grammar"
    shutil.copytree(ROOT / f"2026-smg-{request.param}", target)
    backend = request.param
    entity, prop = ("object", "Prop") if backend == "mltt" else ("e", "t")
    # Adapted names test the rules; these are not new shipped Greek lexical rows.
    with (target / "lexical-actions.txt").open("a") as out:
        for case, parent_type in (("nom", prop), ("acc", f"arrow({entity},{prop})")):
            out.write(rf'''

proper-{case}(NAME)
IF ?Ty({backend}:{entity})
   ¬[+FULL-DP]
THEN put(Ty({backend}:{entity}))
   put(Fo({backend}:NAME))
   put(Case({case}))
   put([+FULL-DP])
   put(?</\0>Ty({backend}:{parent_type}))
   gofirst((?Ty({backend}:{prop}) || Ty({backend}:{prop})))
ELSE abort
''')
    with (target / "lexicon.txt").open("a") as out:
        out.write("george proper-nom george\njohn proper-acc john\n")
    path = target / "semantics.json"
    theory = json.loads(path.read_text())
    theory["constants"].update(george="human", john="human")
    path.write_text(json.dumps(theory))
    yield target
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence", [
    "george agapa john.", "agapa george john.", "john agapa george.",
])
def test_word_order_fixes_names_at_their_case_positions(grammar, sentence):
    result = parse(sentence, grammar, strict=True)
    assert result.ok and result.tree.is_complete() and result.cap_hit is None
    assert str(result.semantics) == "love(george, john)"
    assert str(result.tree[NodeAddress("00")].get_formula()) == "george"
    assert str(result.tree[NodeAddress("010")].get_formula()) == "john"
    assert all(a.is_fixed() for a in result.tree)


@pytest.mark.parametrize("sentence", [
    "george agapa george.", "john agapa john.", "agapa john john.",
])
def test_case_or_duplicate_full_dp_cannot_be_erased_by_merge(grammar, sentence):
    result = parse(sentence, grammar, strict=True)
    assert not result.ok and result.cap_hit is None


def test_late_star_adjunction_builds_unfixed_daughter_under_typed_node(grammar):
    rules = Grammar(grammar, strict=True)
    tree = Tree()
    tree.pointer = NodeAddress("00")
    backend = json.loads((grammar / "semantics.json").read_text())["backend"]
    entity = "object" if backend == "mltt" else "e"
    tree[tree.pointer] = Node(tree.pointer, [label_factory_create(f"Ty({backend}:{entity})")])
    result = rules["late-star-adjunction"].exec(tree, None)
    assert result is not None and str(result.pointer) == "00*"
    assert str(result.pointed_node.get_required_type()) == entity
    assert result.pointed_node.contains(label_factory_create("?Ex.Tn(x)"))
    assert rules["late-star-adjunction"].exec(result, None) is None


def test_unmerged_unfixed_node_blocks_completion(grammar):
    rules = Grammar(grammar, strict=True)
    backend = json.loads((grammar / "semantics.json").read_text())["backend"]
    entity, prop = ("object", "Prop") if backend == "mltt" else ("e", "t")
    tree = Tree()
    tree.semantic_profile = {"backend": backend}
    for address, specs in {
        "0": [f"?Ty({backend}:{prop})"],
        "00": [f"Ty({backend}:{entity})", f"Fo({backend}:george)"],
        "01": [f"Ty({backend}:arrow({entity},{prop}))",
               f"Fo({backend}:lam(x,{entity},walk(x)))"],
        "0*": [f"Ty({backend}:{entity})", "?Ex.Tn(x)"],
    }.items():
        a = NodeAddress(address)
        tree[a] = Node(a, [label_factory_create(s) for s in specs])
    assert rules["elimination"].exec(tree.clone(), None) is None
    tree.pointer = NodeAddress("0*")
    assert rules["completion"].exec(tree.clone(), None) is None
    assert not tree.is_complete()
