"""Terminal-punctuation tokenisation and sentence-final ``.`` (assert) parsing."""

from __future__ import annotations

import pytest

import dynamicsyntax as ds
from dylan.nlp.token_source import WhitespaceTokenSource
from dylan.nlp.types import utterance_from_text, whitespace_tokenize
from dylan.tree.label.labels import CompleteLabel, SpeakerLabel, label_factory_create


@pytest.mark.parametrize(
    ("name", "text", "expected"),
    [
        ("terminal-period", "a man knows you.", ["a", "man", "knows", "you", "."]),
        ("no-op-without-punctuation", "a man arrives", ["a", "man", "arrives"]),
        ("already-separated", "a man arrives .", ["a", "man", "arrives", "."]),
        ("bare-period-token", ".", ["."]),
        ("question-mark", "does a man arrive?", ["does", "a", "man", "arrive", "?"]),
        ("exclamation-mark", "go!", ["go", "!"]),
        ("comma", "yes, a man", ["yes", ",", "a", "man"]),
        ("stacked-punctuation", "what?!", ["what", "?", "!"]),
        ("word-internal-period-kept", "a 3.5 rating", ["a", "3.5", "rating"]),
        ("lowercasing-preserved", "A Man Arrives.", ["a", "man", "arrives", "."]),
        ("underscores-untouched", "not_a_real_word_zz", ["not_a_real_word_zz"]),
        ("whitespace-only", "   ", []),
        ("empty", "", []),
    ],
)
def test_whitespace_tokenize_splits_terminal_punctuation(
    name: str,
    text: str,
    expected: list[str],
) -> None:
    """Terminal ``. ? ! ,`` are detached into their own tokens; words stay intact."""
    assert whitespace_tokenize(text) == expected, name


def test_whitespace_token_source_matches_whitespace_tokenize() -> None:
    """``WhitespaceTokenSource`` goes through the same splitting."""
    assert WhitespaceTokenSource().tokenize("a man knows you.") == [
        "a",
        "man",
        "knows",
        "you",
        ".",
    ]


def test_utterance_from_text_detaches_terminal_period() -> None:
    """``utterance_from_text`` yields a separate ``.`` word with the utterance speaker."""
    utt = utterance_from_text("Alice", "a man arrives.")
    assert [w.word for w in utt.words] == ["a", "man", "arrives", "."]
    assert all(w.speaker == "Alice" for w in utt.words)


def test_label_factory_parses_complete_and_speaker() -> None:
    """``complete`` and ``Speaker(X)`` IF-conditions parse to real label classes."""
    assert isinstance(label_factory_create("complete"), CompleteLabel)
    assert isinstance(label_factory_create("Speaker(X)"), SpeakerLabel)


def test_parse_with_attached_terminal_period() -> None:
    """Sentence-final ``.`` attached to the last word parses via the assert action."""
    p = ds.parse("a man knows you.", "ttr")
    assert p.ok
    s = str(p.semantics)
    assert "man(" in s and "know" in s


def test_parse_without_period_still_ok() -> None:
    """The period-free sentence keeps parsing as before."""
    p = ds.parse("a man knows you", "ttr")
    assert p.ok


def test_parse_period_matches_space_separated_variant() -> None:
    """``a man arrives.`` parses; semantics equals the pre-tokenised ``a man arrives .``."""
    attached = ds.parse("a man arrives.", "ttr")
    separated = ds.parse("a man arrives .", "ttr")
    assert attached.ok
    assert separated.ok
    assert str(attached.semantics) == str(separated.semantics)


def test_parse_period_puts_assert_label_on_root() -> None:
    """The ``.`` assert lexical action decorates the completed tree with ``Assert``."""
    p = ds.parse("a man arrives.", "ttr")
    assert p.ok
    assert p.tree is not None
    labels = [str(lab) for node in p.tree.values() for lab in node.labels]
    assert any("assert" in lab.lower() for lab in labels)


def test_parse_terminal_question_mark() -> None:
    """Sentence-final ``?`` triggers the question lexical action."""
    p = ds.parse("does a man arrive?", "ttr")
    assert p.ok
    assert "question(" in str(p.semantics)
