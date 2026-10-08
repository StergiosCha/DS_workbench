"""E0.6: rules commented out with ``//* ... *//`` are reported, not silently dropped (wide-coverage-plan.md, M0)."""

from __future__ import annotations

from pathlib import Path

from dylan.action.grammar import Grammar

GRAMMARS = Path(__file__).resolve().parents[1] / "src" / "dynamicsyntax" / "grammars"


def test_2015_ttr_reports_its_three_disabled_rules() -> None:
    grammar = Grammar(GRAMMARS / "2015-english-ttr")
    assert len(grammar.disabled_rule_names) == 3
    assert grammar.disabled_rule_names[0] == "star-adjunction"
    assert all(name and " " not in name for name in grammar.disabled_rule_names)
    assert "star-adjunction" not in grammar


def test_native_grammar_has_no_disabled_rules() -> None:
    grammar = Grammar(GRAMMARS / "2026-english-mltt")
    assert grammar.disabled_rule_names == []
    assert len(grammar) > 0
