"""Local correction uses the context DAG and preserves actual speaker history."""

import pytest

from dylan.nlp.types import utterance_from_text
from dynamicsyntax import icp
from dynamicsyntax._parse import _active_path_edges


def feed(parser, text, speaker="A"):
    return all(parser.parse_word(word) is not None for word in utterance_from_text(speaker, text))


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("punctuation", ["", "."])
@pytest.mark.parametrize("repairer", ["A", "B"])
def test_same_and_other_speaker_correct_last_word(backend, punctuation, repairer):
    parser = icp(f"2026-english-{backend}")
    try:
        parser.init_participants(["A", "B"])
        parser.new_sentence()
        assert feed(parser, "john likes mary" + punctuation)
        previous = parser.get_best_tuple()
        assert feed(parser, "sorry bill.", repairer)
        assert str(parser.get_best_tuple().tree.get_root_node().get_formula()) == "like(john, bill)"
        assert not parser.get_state().word_stack
        assert not parser.get_state().repair_processing_enabled()
        assert parser.context.get_who_has_floor() == repairer
        assert [(w.speaker, w.word) for w in parser.context.get_dialogue_history()][-3:] == [
            (repairer, "sorry"),
            (repairer, "bill"),
            (repairer, "."),
        ]
        assert "mary" not in [e.word.word for e in _active_path_edges(parser) if e.word]
        assert parser.get_state().contains_vertex(previous)  # Old branch survives.
    finally:
        parser.close()


@pytest.mark.parametrize(
    "boundary", ["grounded", "new_clause", "disabled", "no_context", "unknown"]
)
def test_failed_repair_cannot_cross_boundaries_or_lose_old_tree(boundary):
    parser = icp("2026-english-classical")
    try:
        parser.init_participants(["A", "B"])
        parser.new_sentence()
        if boundary != "no_context":
            assert feed(parser, "john likes mary")
        if boundary == "grounded":
            parser.get_state().get_parent_edge().ground_for("B")
        elif boundary == "new_clause":
            parser.new_sentence()
        elif boundary == "disabled":
            parser.max_repair_depth = 0
        before = parser.get_best_tuple()
        assert feed(parser, "sorry", "B")
        assert not feed(parser, "zzunknown" if boundary == "unknown" else "bill", "B")
        assert parser.get_best_tuple() is before
        assert not parser.get_state().word_stack
    finally:
        parser.close()


def test_new_tree_keeps_prior_dag_and_blocks_ordinary_backtracking_into_it():
    parser = icp("2026-english-classical")
    try:
        parser.init_participants(["A", "B"])
        parser.new_sentence()
        assert feed(parser, "john likes mary.")
        previous = parser.get_best_tuple()
        parser.new_sentence()
        new = parser.get_best_tuple()
        assert parser.get_state().contains_vertex(previous)
        assert new is not previous
        assert not feed(parser, "walks", "B")
        assert parser.get_best_tuple() is new
        assert str(previous.tree.get_root_node().get_formula()) == "like(john, mary)"
        assert feed(parser, "bill walks.", "B")
    finally:
        parser.close()
