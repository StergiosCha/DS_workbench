"""Maintenance tools expose malformed resources without inventing reachability."""

import shutil
from pathlib import Path
from dylan.grammar_tools import diff_grammars, lint_grammar

FIXTURES = Path(__file__).parent / "fixtures/validation"


def test_lint_reports_missing_templates_and_duplicate_rules():
    missing = lint_grammar(FIXTURES / "missing_template")
    assert missing["strict_errors"]
    assert missing["undefined_templates"] == {"ghost_template": 2}
    assert missing["dynamic_status"] == "unmeasured"
    assert missing["templates_not_seen_on_success"] is None
    duplicate = lint_grammar(FIXTURES / "dup_rule")
    assert any("dup-rule" in error for error in duplicate["strict_errors"])


def test_diff_ignores_inline_comments_but_reports_rule_changes(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    shutil.copytree(FIXTURES / "dup_rule", left)
    shutil.copytree(left, right)
    source = right / "computational-actions.txt"
    source.write_text(
        source.read_text().replace("THEN do_nothing", "THEN do_nothing // explanation")
    )
    assert not diff_grammars(left, right)
    source.write_text(source.read_text().replace("THEN do_nothing", "THEN abort"))
    assert "THEN abort" in diff_grammars(left, right)
