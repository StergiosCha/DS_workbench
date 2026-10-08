"""Load-time validation of grammar directories (duplicate rules, missing templates, arity)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from loguru import logger

from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.parser.dag_parser import DAGParser

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "validation"
BUNDLED_2026 = Path(__file__).resolve().parents[1] / "resources" / "2026-english-ttr"


@pytest.fixture
def warning_sink() -> Iterator[list[str]]:
    """Collect loguru WARNING+ messages emitted while the test body runs."""
    messages: list[str] = []
    handler_id = logger.add(
        lambda m: messages.append(str(m)),
        level="WARNING",
        format="{message}",
    )
    yield messages
    logger.remove(handler_id)


def test_duplicate_rule_warns_and_keeps_first(warning_sink: list[str]) -> None:
    """Duplicate computational-action name warns (rule + file) and the first block wins."""
    grammar = Grammar(FIXTURES / "dup_rule")
    assert set(grammar) == {"dup-rule", "unique-rule"}
    # First occurrence was starred (*dup-rule); the plain redefinition must be ignored.
    assert grammar["dup-rule"].is_always_good()
    joined = "\n".join(warning_sink)
    assert "dup-rule" in joined
    assert "computational-actions.txt" in joined


def test_missing_template_warns_per_template_and_skips_rows(warning_sink: list[str]) -> None:
    """One warning per distinct missing template, with the affected-row count; rows skipped."""
    lex = Lexicon(FIXTURES / "missing_template")
    assert "test" in lex
    assert "ghosta" not in lex and "ghostb" not in lex
    assert lex.load_stats.words_failed == 2
    ghost_warnings = [m for m in warning_sink if "ghost_template" in m]
    assert len(ghost_warnings) == 1
    assert "2 row(s)" in ghost_warnings[0]
    assert "lexical-actions.txt" in ghost_warnings[0]


def test_arity_mismatch_warns_and_skips_row(warning_sink: list[str]) -> None:
    """A row with fewer columns than the template's parameters warns and is skipped."""
    lex = Lexicon(FIXTURES / "arity")
    assert "good" in lex
    assert "short" not in lex
    joined = "\n".join(warning_sink)
    assert "'short'" in joined
    assert "expected 1" in joined and "found 0" in joined


def test_strict_duplicate_rule_raises() -> None:
    """``strict=True`` on Grammar raises instead of warning."""
    with pytest.raises(ValueError, match="dup-rule"):
        Grammar(FIXTURES / "dup_rule", strict=True)


def test_strict_missing_template_raises() -> None:
    """``strict=True`` on Lexicon raises on a row naming an unknown template."""
    with pytest.raises(ValueError, match="ghost_template"):
        Lexicon(FIXTURES / "missing_template", strict=True)


def test_strict_arity_mismatch_raises() -> None:
    """``strict=True`` on Lexicon raises on a column-count mismatch."""
    with pytest.raises(ValueError, match="expected 1"):
        Lexicon(FIXTURES / "arity", strict=True)


def test_from_resource_dir_plumbs_strict() -> None:
    """`DAGParser.from_resource_dir` forwards *strict* to Grammar and Lexicon."""
    with pytest.raises(ValueError, match="dup-rule"):
        DAGParser.from_resource_dir(FIXTURES / "dup_rule", strict=True)
    parser = DAGParser.from_resource_dir(FIXTURES / "dup_rule")
    assert "dup-rule" in parser.nonoptional_grammar


@pytest.mark.parametrize(
    "entrypoint",
    [
        "constructor", "from_resource_dir", "icp", "deferred", "from_loaded",
        "parse", "batch", "workbench",
    ],
)
def test_icp_plumbs_strict_and_top_n(entrypoint, tmp_path, monkeypatch) -> None:
    """Only the fourth entry succeeds; strict validation reaches both resource loaders."""
    import dynamicsyntax as ds
    from dylan import workbench_api
    from dylan.parser.interactive_context_parser import InteractiveContextParser

    (tmp_path / "computational-actions.txt").write_text("*trp\nabort\n", encoding="utf-8")
    (tmp_path / "lexical-actions.txt").write_text(
        "*fail(NAME)\nIF ?Ty(t)\nTHEN abort\nELSE abort\n\n"
        "*finish(NAME)\nIF ?Ty(t)\nTHEN put(Ty(t))\n"
        "     put(Fo(NAME))\n     delete(?Ty(t))\nELSE abort\n",
        encoding="utf-8",
    )
    (tmp_path / "lexicon.txt").write_text(
        "test fail one\ntest fail two\ntest fail three\ntest finish success\n",
        encoding="utf-8",
    )
    # The production workbench still permits only bundled ids. Allow these test resources.
    monkeypatch.setattr(
        workbench_api,
        "configuration",
        lambda: {"grammars": [str(tmp_path), *(str(p) for p in FIXTURES.iterdir())]},
    )

    def run(path, **options):
        if entrypoint == "workbench":
            result = workbench_api.parse_request(
                {"sentence": "test", "grammar": str(path), **options}
            )
            return result["ok"] and result["complete"]
        if entrypoint in {"parse", "batch"}:
            results = ds.parse(
                ["test", "test"] if entrypoint == "batch" else "test", path, **options
            )
            results = results if isinstance(results, list) else [results]
            try:
                return all(result.ok for result in results)
            finally:
                results[0].parser.close()
        if entrypoint in {"deferred", "from_loaded"}:
            parser = (
                ds.icp(**options)
                if entrypoint == "deferred"
                else InteractiveContextParser.from_loaded(
                    Lexicon(None, options.get("top_n", 3)),
                    Grammar(None),
                    strict=options.get("strict", False),
                )
            )
        else:
            factory = {
                "constructor": InteractiveContextParser,
                "from_resource_dir": InteractiveContextParser.from_resource_dir,
                "icp": ds.icp,
            }[entrypoint]
            parser = factory(path, **options)
        try:
            # Reloading must preserve the options, including for an initially unloaded parser.
            parser.set_grammar(path)
            return parser.parse("test").ok
        finally:
            parser.close()

    for options, succeeds in [
        ({}, False),
        ({"strict": True}, False),
        ({"top_n": 0, "strict": True}, True),
        ({"top_n": 1, "strict": True}, False),
        ({"top_n": 3}, False),
        ({"top_n": 20, "strict": True}, True),
    ]:
        assert run(tmp_path, **options) is succeeds, options
    # Permissive remains the default: malformed rows warn without raising on load.
    run(FIXTURES / "missing_template")
    for fixture, message in [
        ("dup_rule", "dup-rule"),
        ("missing_template", "ghost_template"),
        ("arity", "expected 1"),
    ]:
        with pytest.raises(ValueError, match=message):
            run(FIXTURES / fixture, strict=True)


def test_bundled_2026_grammar_warns_and_still_parses(warning_sink: list[str]) -> None:
    """The bundled 2026-english-ttr triggers validation warnings but loads and parses."""
    import dynamicsyntax as ds

    lex = Lexicon(BUNDLED_2026)
    assert "arrives" in lex
    joined = "\n".join(warning_sink)
    # Dead ditransitive rows reference templates absent from lexical-actions.txt.
    assert "v_ditran_fin" in joined
    assert "not found in lexical-actions.txt" in joined
    result = ds.parse("a man arrives", "2026-english-ttr")
    assert result.ok
