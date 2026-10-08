"""Structural ``__eq__``/``__hash__`` across the Formula hierarchy + parser safety-cap plumbing."""

from __future__ import annotations

from loguru import logger

import dynamicsyntax as ds
from dylan.formula.epsilon_term import EpsilonTerm
from dylan.formula.formula import Formula
from dylan.formula.predicate_argument import PredicateArgumentFormula
from dylan.formula.ttr_lambda import TTRLambdaAbstract
from dylan.formula.ttr_record_type import TTRRecordType
from dylan.parser.interactive_context_parser import InteractiveContextParser
from dylan.tree.tree import Tree

RECORD_STR = "[x : e|p==man(x) : t|head==x : e]"
LAMBDA_STR = "R1^(R1 ++ [e1==run : es|p2==subj(e1, x) : t|head==e1 : es])"
PRED_ARG_STR = "like(x, y)"

PROBE_SENTENCE = "a man knows you"
PROBE_SEMANTICS = (
    "[x1==you : e|e0==know : es|x0 : e|head==e0 : es|p0==man(x0) : t"
    "|p2==pres(e0) : t|p5==subj(e0, x0) : t|p4==obj(e0, x1) : t]"
)


# ---------------------------------------------------------------------------
# Formula hashing
# ---------------------------------------------------------------------------


def test_ttr_record_type_parsed_twice_is_eq_and_hash_equal() -> None:
    """Two independent parses of the same record string are ``==`` and hash-equal."""
    r1 = TTRRecordType.parse(RECORD_STR)
    r2 = TTRRecordType.parse(RECORD_STR)
    assert r1 is not r2
    assert r1 == r2
    assert hash(r1) == hash(r2)


def test_lambda_parsed_twice_is_eq_and_hash_equal() -> None:
    """Two independent parses of the same TTR lambda string are ``==`` and hash-equal."""
    f1 = Formula.create(LAMBDA_STR)
    f2 = Formula.create(LAMBDA_STR)
    assert isinstance(f1, TTRLambdaAbstract)
    assert f1 is not f2
    assert f1 == f2
    assert hash(f1) == hash(f2)


def test_predicate_argument_parsed_twice_is_eq_and_hash_equal() -> None:
    """Two independent parses of the same predicate-argument string are ``==`` and hash-equal."""
    f1 = Formula.create(PRED_ARG_STR)
    f2 = Formula.create(PRED_ARG_STR)
    assert isinstance(f1, PredicateArgumentFormula)
    assert f1 is not f2
    assert f1 == f2
    assert hash(f1) == hash(f2)


def test_epsilon_term_is_eq_and_hash_equal() -> None:
    """`EpsilonTerm` (dataclass subclass of `PredicateArgumentFormula`) hashes structurally."""
    r = TTRRecordType.parse(RECORD_STR)
    e1 = EpsilonTerm("epsilon", Formula.create("x"), r.clone())
    e2 = EpsilonTerm("epsilon", Formula.create("x"), r.clone())
    assert e1 == e2
    assert hash(e1) == hash(e2)


def test_unequal_formulas_differ() -> None:
    """Structurally different formulas are ``!=`` (and here hash-distinct)."""
    r = TTRRecordType.parse(RECORD_STR)
    other_record = TTRRecordType.parse("[x : e|p==woman(x) : t|head==x : e]")
    assert r != other_record
    assert hash(r) != hash(other_record)

    pa = Formula.create(PRED_ARG_STR)
    other_pa = Formula.create("like(y, x)")
    assert pa != other_pa
    assert hash(pa) != hash(other_pa)

    lam = Formula.create(LAMBDA_STR)
    assert lam != r
    assert pa != r


def test_formula_set_and_dict_round_trip() -> None:
    """Formulas survive set membership and dict-key lookup via a re-parsed equal key."""
    first = [
        TTRRecordType.parse(RECORD_STR),
        Formula.create(LAMBDA_STR),
        Formula.create(PRED_ARG_STR),
    ]
    second = [
        TTRRecordType.parse(RECORD_STR),
        Formula.create(LAMBDA_STR),
        Formula.create(PRED_ARG_STR),
    ]
    as_set = set(first)
    assert len(as_set) == 3
    for f in second:
        assert f in as_set
    as_dict = {f: str(f) for f in first}
    for f in second:
        assert as_dict[f] == str(f)


def test_parsed_tree_is_hashable() -> None:
    """`Tree.__hash__` is total once formula labels hash (workaround removal precondition)."""
    result = ds.parse(PROBE_SENTENCE, "ttr")
    assert result.ok
    tree = result.tree
    assert isinstance(tree, Tree)
    assert tree in {tree}
    assert hash(tree) == hash(tree)


def test_parse_semantics_string_unchanged() -> None:
    """Hashing preserves the corrected record, including distinct argument fields."""
    result = ds.parse(PROBE_SENTENCE, "ttr")
    assert result.ok
    assert str(result.semantics) == PROBE_SEMANTICS


# ---------------------------------------------------------------------------
# Parser safety caps
# ---------------------------------------------------------------------------


class _AlwaysFiringAction:
    """Minimal computational-action stub whose ``exec`` always succeeds."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def exec(self, tree: Tree, context: object) -> Tree:
        self.calls += 1
        return tree

    def instantiate(self) -> _AlwaysFiringAction:
        return self


def test_max_nonoptional_adjust_passes_kwarg_reaches_loop_bound() -> None:
    """The constructor cap bounds ``adjust_with_non_optional_grammar`` exactly, with a debug log."""
    parser = InteractiveContextParser(max_nonoptional_adjust_passes=7)
    assert parser.max_nonoptional_adjust_passes == 7
    stub = _AlwaysFiringAction("stub")
    parser.nonoptional_grammar[stub.name] = stub
    captured: list[str] = []
    hid = logger.add(lambda m: captured.append(m.record["message"]), level="DEBUG")
    try:
        actions, _ = parser.adjust_with_non_optional_grammar(([], Tree()))
    finally:
        logger.remove(hid)
        parser.close()
    assert stub.calls == 7
    assert len(actions) == 7
    assert any("cap hit: max_nonoptional_adjust_passes=7" in msg for msg in captured)


def test_max_lexical_adjustment_pairs_kwarg_reaches_expansion_loop() -> None:
    """A zero pairs cap stops lexical left-adjustment expansion and logs the cap hit."""
    parser = InteractiveContextParser("ttr", max_lexical_adjustment_pairs=0)
    assert parser.max_lexical_adjustment_pairs == 0
    captured: list[str] = []
    hid = logger.add(lambda m: captured.append(m.record["message"]), level="DEBUG")
    try:
        parser.parse(PROBE_SENTENCE)
    finally:
        logger.remove(hid)
        parser.close()
    assert any("cap hit: max_lexical_adjustment_pairs=0" in msg for msg in captured)


def test_cap_defaults_and_max_repair_depth_kwarg() -> None:
    """Defaults match the module constants; ``max_repair_depth`` is per-instance configurable."""
    from dylan.parser.dag_parser import _MAX_NONOPTIONAL_ADJUST_PASSES
    from dylan.parser.interactive_context_parser import (
        _MAX_LEXICAL_ADJUSTMENT_PAIRS,
        MAX_REPAIR_DEPTH,
    )

    default_parser = InteractiveContextParser()
    assert default_parser.max_lexical_adjustment_pairs == _MAX_LEXICAL_ADJUSTMENT_PAIRS
    assert default_parser.max_nonoptional_adjust_passes == _MAX_NONOPTIONAL_ADJUST_PASSES
    assert default_parser.max_repair_depth == MAX_REPAIR_DEPTH
    default_parser.close()

    custom = InteractiveContextParser(max_repair_depth=3)
    assert custom.max_repair_depth == 3
    custom.close()
