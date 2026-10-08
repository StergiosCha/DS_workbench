"""Maintained SMG action programs and the placement gates of the thesis."""

from pathlib import Path

import pytest

from dynamicsyntax import parse
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1] / "src/dynamicsyntax/grammars"


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_accusative_clitic_uses_object_guard_without_global_flag(backend):
    grammar = ROOT / f"2026-smg-{backend}"
    assert "CLITIC" not in (grammar / "lexical-actions.txt").read_text()
    result = parse("τον αγαπά.", grammar)
    assert result.ok and result.tree.is_complete()
    obj = result.tree[NodeAddress("010")]
    assert obj.contains(label_factory_create("Case(acc)"))
    assert obj.contains(label_factory_create("Person(3)"))
    assert not parse("το τον ξέρω.", grammar).ok


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_smg_approved_gerund_prohibitive_and_future_templates(backend):
    target = ROOT / f"2026-smg-{backend}"
    assert Lexicon(target, strict=True).load_stats.words_failed == 0
    for text in ["γράφοντας το.", "μην το γράφει.", "θα το γράψει."]:
        result = parse(text, target)
        assert result.ok and result.tree.is_complete(), text
    for text in ["το γράφοντας.", "μη γράφε το.", "θα γράψει το."]:
        assert not parse(text, target).ok, text


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_shipped_clitic_resolves_to_supplied_dialogue_referent(backend):
    from dynamicsyntax import icp
    from dylan.context.referent import Referent
    from dylan.nlp.types import utterance_from_text

    parser = icp(f"2026-smg-{backend}", strict=True)
    try:
        parser.context.referents = [Referent("mary", "human", gender="fem", number="sg"),
                                   *parser.context.referents]
        assert parser.parse_utterance(utterance_from_text("A", "την ξέρω."))
        assert str(parser.get_final_semantics()) == "know(speaker, mary)"
        assert parser.get_state().get_current_tuple().tree.is_complete()
    finally:
        parser.close()
