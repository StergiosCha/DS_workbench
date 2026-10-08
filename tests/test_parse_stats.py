"""E0.1: measure actual search, keeping replay and later parses independent."""

import pytest

from dynamicsyntax import icp
from dylan.parser.interactive_context_parser import InteractiveContextParser
from dylan.workbench_api import parse_request


def test_parse_stats_counts_children_and_backtracks():
    parser = icp("2026-smg-mltt")
    try:
        # Use an unambiguous clitic: τον and την also have article readings.
        result = parser.parse("αγαπά με.")
        stats = result.stats
        assert not result.ok
        assert stats.children_built_per_word == [1, 0, 0]
        assert stats.backtracks_called == 2 and stats.backtracks_ok == 0
        assert stats.traversed == 2  # accepted verb plus the final completion edge
        assert stats.tuples > 1 and stats.edges > 0
        assert stats.lexical_execs > 0 and stats.computational_execs > 0
        assert stats.pruned == 0
        snapshot = stats.to_dict()
        good = parser.parse("με αγαπά.")
        assert good.ok and good.stats.backtracks_called == 0
        assert stats.to_dict() == snapshot
        assert parser.parse(" ").stats.tuples == 0
    finally:
        parser.close()


def test_trace_replay_does_not_inflate_search_stats():
    parser = icp("2026-english-mltt")
    try:
        plain = parser.parse("every doctor examined a patient.")
        traced = parser.parse("every doctor examined a patient.", trace=True)
        assert plain.ok and traced.ok and traced.action_steps
        assert plain.stats == traced.stats
        assert traced.stats.children_built_per_word == [1] * 6
    finally:
        parser.close()


@pytest.mark.parametrize("top_n,expected", [(3, [("like", 1)]), (0, [])])
def test_stats_count_search_cuts_not_vocabulary_inspection(top_n, expected):
    parser = icp("2015-english-ttr", top_n=top_n)
    try:
        result = parser.parse("like")
        parser.lexicon.lookup("like")
        assert result.stats.top_n_cuts == expected
        assert parser.stats.top_n_cuts == expected
    finally:
        parser.close()


def test_stats_record_caps_and_reset_with_new_sentence():
    parser = InteractiveContextParser("2026-english-mltt", max_lexical_adjustment_pairs=1)
    try:
        result = parser.parse("every doctor examined a patient.")
        assert result.stats.cap_hits == [result.cap_hit]
        parser.new_sentence()
        assert parser.stats.cap_hits == [] and parser.stats.tuples == 1
        assert parser.stats.children_built_per_word == []
        assert result.stats.cap_hits == ["max_lexical_adjustment_pairs"]
    finally:
        parser.close()


def test_workbench_stats_include_every_dialogue_tree():
    result = parse_request({
        "grammar": "2026-english-mltt",
        "dialogue": [
            {"speaker": "Alice", "text": "john walks."},
            {"speaker": "Bob", "text": "mary walks.", "boundary": "new_tree"},
        ],
    })
    assert result["complete"]
    assert result["stats"] == result["diagnostics"]["stats"]
    assert result["stats"]["children_built_per_word"] == [1] * 6
    assert result["stats"]["tuples"] >= 8
    assert result["stats"]["cap_hits"] == []
