"""Person-case restrictions arise from node collapse and output filters."""

import json
from pathlib import Path

import pytest

from dynamicsyntax import parse
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1] / "src/dynamicsyntax/grammars"


@pytest.fixture(params=["mltt", "classical"])
def grammar(request):
    reset_all_meta_bindings()
    yield ROOT / f"2026-smg-{request.param}"
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence", ["me agapa.", "se agapa."])
def test_single_acc12_fixes_as_object_and_discharges_case(grammar, sentence):
    result = parse(sentence, grammar, trace=True)
    assert result.ok and result.tree.is_complete()
    assert NodeAddress("0P") not in result.tree
    assert str(result.tree[NodeAddress("010")].get_formula()) == (
        "speaker" if sentence.startswith("me") else "hearer")


@pytest.mark.parametrize("sentence", ["mu se agapa.", "su me agapa.", "tu me agapa.", "tis se agapa.", "dos mu se.", "dos se mu."])
def test_strong_pcc_clashes_even_inside_postverbal_chunk(grammar, sentence, caplog):
    import logging

    with caplog.at_level(logging.DEBUG, logger="dylan.action.atomic.put"):
        result = parse(sentence, grammar)
    assert not result.ok
    assert "incompatible clitic restrictions" in caplog.text


def test_mu_to_is_licensed(grammar):
    assert parse("dos mu to.", grammar).ok


@pytest.mark.parametrize("sentence", ["mu me agapa.", "su se agapa."])
def test_identical_person_cannot_collapse_accusative_and_genitive(grammar, sentence):
    # Same-person counterexamples are discussed on thesis PDF p.267.
    assert not parse(sentence, grammar).ok


def test_case_filter_rejects_acc12_as_indirect_object(grammar):
    # The accusative `to` fills 010, leaving only 0110 for the unfixed acc12.
    result = parse("dos to me.", grammar)
    assert not result.ok and not result.tree.is_complete()


def test_chunk_templates_disable_computation_between_clitics(grammar):
    from dylan.action.lexicon import Lexicon

    lexicon = Lexicon(grammar, strict=True)
    for word in ("mu", "to", "me"):
        clitics = [action for action in lexicon.lookup_all(word)
                   if action.action_type.startswith("clitic")]
        assert clitics
        assert all(not action.requires_left_adjustment() for action in clitics)
    # The same surface form can also introduce a name, outside a clitic chunk.
    article = next(action for action in lexicon.lookup_all("to")
                   if action.action_type == "article-name")
    assert article.requires_left_adjustment()
    assert json.loads((grammar / "semantics.json").read_text())["fragment"] == "thesis"
