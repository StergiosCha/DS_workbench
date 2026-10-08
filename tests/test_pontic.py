"""Pontic cluster entries preserve postverbal placement and argument structure."""

from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1] / "src/dynamicsyntax/grammars"


@pytest.fixture(params=["mltt", "classical"])
def grammar(request, tmp_path):
    reset_all_meta_bindings()
    target = tmp_path / "grammar"
    shutil.copytree(ROOT / f"2026-pontic-{request.param}", target)
    with (target / "lexicon.txt").open("a") as out:
        # Unsourced adaptation used only to test the monotransitive valency guard.
        out.write("agapa verb-finite love pro 3 sg\n")
    assert Grammar(target, strict=True)
    assert Lexicon(target, strict=True).load_stats.words_failed == 0
    yield target
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence,meaning", [
    ("edikse m esen.", "show(pro, hearer, speaker)"),
    ("edikse m ese.", "show(pro, hearer, speaker)"),
    ("edeke m a.", "give(pro, theme, speaker)"),
])
def test_pontic_m_esen_single_entry(grammar, sentence, meaning):
    result = parse(sentence, grammar, trace=True)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == meaning
    first = next(step for step in result.action_steps if step.word == "m")
    assert str(first.after_tree[NodeAddress("0110")].get_formula()) == "U_speaker"
    assert NodeAddress("0P") in first.after_tree
    tail = next(step for step in result.action_steps if step.word in {"esen", "ese", "a"})
    assert set(tail.before_tree) == set(tail.after_tree)
    assert first.after_tree.get_root_node().get_formula() is None


@pytest.mark.parametrize("sentence", [
    "m esen edikse.", "edikse me se.", "edikse aton ato.", "edikse m.",
    "edikse m aton.", "edikse m esen esen.", "agapa m esen.",
])
def test_pontic_cluster_controls(grammar, sentence):
    result = parse(sentence, grammar)
    assert not result.ok
    assert result.cap_hit is None
