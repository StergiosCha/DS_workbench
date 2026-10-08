"""Approved proper-name NPs use case filters and visible tree actions."""

from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1]


@pytest.fixture(params=["mltt", "classical"])
def grammar(request):
    reset_all_meta_bindings()
    yield ROOT / f"src/dynamicsyntax/grammars/2026-smg-{request.param}"
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence,meaning", [
    ("o γiorγos xtipise to γiani.", "hit(giorgos, giannis)"),
    ("xtipise o γiorγos to γiani.", "hit(giorgos, giannis)"),
    ("to γiani xtipise o γiorγos.", "hit(giorgos, giannis)"),
    ("ο γιώργος χτύπησε τον γιάννη.", "hit(giorgos, giannis)"),
    ("χτύπησε ο γιώργος τον γιάννη.", "hit(giorgos, giannis)"),
    ("τον γιάννη χτύπησε ο γιώργος.", "hit(giorgos, giannis)"),
    ("to γiani xtipise.", "hit(pro, giannis)"),
    ("ton xtipise ton γiani.", "hit(pro, giannis)"),
    ("to γiani ton xtipise.", "hit(pro, giannis)"),
    ("o γiorγos ton xtipise.", "hit(giorgos, him)"),
])
def test_name_case_word_order_and_clitic_coreference(grammar, sentence, meaning):
    # (2.50)-(2.52), with disclosed order and spelling adaptations in the review.
    result = parse(sentence, grammar, strict=True, trace=True)
    assert result.ok and result.tree.is_complete() and result.cap_hit is None
    assert str(result.semantics) == meaning
    assert all(a.is_fixed() for a in result.tree)
    assert any(step.action_name == "merge-general" for step in result.action_steps)
    if result.semantics.backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result.semantics.to_coq(), {}) == "passed"
    if "giannis" in meaning:
        assert str(result.tree[NodeAddress("010")].get_formula()) == "giannis"


@pytest.mark.parametrize("sentence", [
    "to γiorγos xtipise ton γiani.", "o γiani xtipise ton γiani.",
    "o γiorγos xtipise o γiorγos.", "ton γiani xtipise ton γiani.",
    "o xtipise ton γiani.",
    "o γiorγos ksero ton γiani.",
    "tin xtipise ton γiani.",
    "ton γiani tin xtipise.",
])
def test_case_mismatch_or_missing_name_cannot_complete(grammar, sentence):
    result = parse(sentence, grammar, strict=True)
    assert not result.ok and result.cap_hit is None


@pytest.mark.parametrize("sentence", ["O Γiorγos xtipise to Γiani", "Xtipise o Γiorγos to Γiani"])
@pytest.mark.parametrize("trace", [False, True])
def test_source_examples_complete_without_added_punctuation(grammar, sentence, trace):
    result = parse(sentence, grammar, strict=True, trace=trace)
    assert result.ok and result.tree.is_complete() and result.cap_hit is None
    assert str(result.semantics) == "hit(giorgos, giannis)"
    if trace:
        assert result.action_steps[-1].after_tree == result.tree
        assert result.action_steps[-1].word is None
    if result.semantics.backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result.semantics.to_coq(), {}) == "passed"


def test_workbench_completion_replays_only_the_successful_path(grammar):
    from dylan.workbench_api import parse_request

    result = parse_request({"sentence": "Xtipise o Γiorγos to Γiani", "grammar": grammar.name})
    assert result["ok"] and result["complete"] and result["cap_hit"] is None
    assert result["actions"][-1]["nodes"] == result["words"][-1]["nodes"]
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", ["tu me edika.", "mu se edika.", "su me edika."])
def test_sourced_grico_pcc_controls_with_approved_verb(backend, sentence):
    result = parse(sentence, ROOT / f"src/dynamicsyntax/grammars/2026-grico-{backend}", strict=True)
    assert not result.ok and result.cap_hit is None
