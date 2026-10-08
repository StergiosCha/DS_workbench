"""E0.2: the Lexicon top_n cut is recorded, never silent (docs/design/wide-coverage-plan.md, M0)."""

from __future__ import annotations

from pathlib import Path

from dylan.action.lexicon import Lexicon

TTR = Path(__file__).resolve().parents[1] / "resources" / "2015-english-ttr"


def _multi_entry_word(lex: Lexicon) -> tuple[str, int]:
    for word in sorted(lex.keys()):
        n = len(lex.lookup_all(word))
        if n > 3:
            return word, n
    raise AssertionError("2015-english-ttr should have a word with more than three entries")


def test_top_n_cut_is_reported_not_silent() -> None:
    lex = Lexicon(TTR, 3)
    word, total = _multi_entry_word(lex)
    assert lex.cut_log == []
    assert len(lex.lookup(word)) == 3
    assert lex.cut_log == [(word, total - 3)]
    assert len(lex.lookup_all(word)) == total


def test_top_n_zero_never_cuts() -> None:
    lex = Lexicon(TTR, 0)
    word, total = _multi_entry_word(lex)
    assert len(lex.lookup(word)) == total
    assert lex.cut_log == []
