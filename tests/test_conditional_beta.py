"""Source structure, finite-situation semantics and boundaries of the beta."""

from itertools import product
from pathlib import Path

import pytest

from dynamicsyntax import icp
from dylan.action.atomic.conditional_beta import BETA_GRAMMAR, ConditionalBetaEffect
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.terms import name, parse_expr
from dylan.grammar_tools import lint_grammar
from dylan.workbench_api import configuration, parse_request, validate_request


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def parse(sentence, trace=False):
    return parse_request({"sentence": sentence, "grammar": BETA_GRAMMAR, "strict": True}, _trace=trace)


def semantic_parse(sentence):
    parser = icp(BETA_GRAMMAR, strict=True, top_n=0)
    try:
        result = parser.parse(sentence)
        assert result.ok and result.tree.is_complete()
        return result.tree
    finally:
        parser.close()


@pytest.mark.parametrize("sentence", [
    "If John cries, Mary laughs.", "If John cries Mary laughs.",
    "If John cries then Mary laughs.", "Mary laughs if John cries.",
    "If John cries, then Mary laughs.",
    "If John likes Mary, Bill greets Sue.", "Bill greets Sue if John likes Mary.",
    "If George arrives, Sue leaves.",
])
def test_both_orders_complete_with_a_shared_situation_term(sentence):
    tree = semantic_parse(sentence)
    host = tree[tree.root_addr.down0()]
    linked = tree[host.address.down_link()]
    assert str(host.get_type()) == str(linked.get_type()) == "es"
    assert host.get_formula().term == linked.get_formula().term
    assert host.get_formula().term.kind == "tau"
    assert host.get_formula().term.args[0] == name("es")
    assert all(node.is_complete() for node in tree.values())
    # The situation stays explicit even in the subject-saturated predicate.
    assert str(tree[tree.root_addr.down1()].get_type()) == "es → t"
    term = tree.get_root_node().get_formula().term
    assert "condition" not in term.free()
    assert parse_expr(term.to_source()) == term


def evaluate(term, environment, situations):
    """Independent finite model: tau selects a counterexample if one exists."""
    if term.kind == "name":
        return environment[term.name]
    if term.kind == "choice_scope":
        return evaluate(term.args[0], environment, situations)
    if term.kind == "app":
        return evaluate(term.args[0], environment, situations)(evaluate(term.args[1], environment, situations))
    if term.kind == "tau":
        assert term.args[0] == name("es")
        return next((s for s in situations if not evaluate(
            term.args[1], {**environment, term.name: s}, situations)), situations[0])
    if term.kind == "implies":
        return not evaluate(term.args[0], environment, situations) or evaluate(term.args[1], environment, situations)
    raise AssertionError(term.kind)


@pytest.mark.parametrize("situations", [(0, 1), (1, 0)])
def test_actual_output_matches_restricted_universal_over_situations(situations):
    initial = semantic_parse("If John cries, Mary laughs.").get_root_node().get_formula().term
    reset_all_meta_bindings()
    final = semantic_parse("Mary laughs if John cries.").get_root_node().get_formula().term
    for values in product((False, True), repeat=4):
        crying, laughing = values[:2], values[2:]
        env = {"john": "john", "mary": "mary",
               "cry": lambda person: lambda s: person == "john" and crying[s],
               "laugh": lambda person: lambda s: person == "mary" and laughing[s]}
        expected = all(not crying[s] or laughing[s] for s in situations)
        assert evaluate(initial, env, situations) == expected
        assert evaluate(final, env, situations) == expected
    # This includes an empty antecedent extension: John crying is not asserted.


@pytest.mark.parametrize("sentence", [
    "If John cries.", "If John, Mary laughs.", "If John cries Mary.",
    "If John likes, Mary laughs.", "If John cries, laughs.",
    "John cries if.", "John cries if Mary.", "John cries.",
    "If John cries, if Mary laughs, Bill walks.",
    "If John cries, Mary laughs if Bill walks.",
    "If John cries, , Mary laughs.",
    "If John cries then, Mary laughs.",
    "Mary laughs, if John cries.",       # peripheral strategy not provided
    "Mary laughs when John cries.", "Mary laughs because John cries.",
    "If he cries, Mary laughs.", "If a man cries, Mary laughs.",
])
def test_missing_content_and_unimplemented_routes_do_not_complete(sentence):
    result = parse(sentence)
    assert not result["complete"], sentence
    assert not result.get("error")


def test_word_and_operation_trace_show_restrictor_then_link_evaluation():
    events = []
    result = parse_request({"sentence": "If John cries, Mary laughs.", "grammar": BETA_GRAMMAR,
                            "strict": True}, on_event=events.append)
    assert result["complete"]
    after_if = result["words"][1]
    assert after_if["conditional_beta"] == "fixed-situation-v1"
    assert any(n["type"] == "cns → es" for n in after_if["nodes"])
    assert any(n["type"] == "t → cns" for n in after_if["nodes"])
    assert any("SITUATION-SHARED" in req for n in after_if["nodes"] for req in n["requirements"])
    ops = "\n".join(frame["label"] for frame in result["operations"])
    assert r"make(\/L)" in ops and "SharedFo(" in ops
    assert any(frame.get("rule") == "evaluate-conditional-link" or
               "evaluate-conditional-link" in str(frame) for frame in result["actions"])
    streamed = [event["frame"] for event in events if event["event"] == "frame" and event["channel"] == "operations"]
    assert streamed == result["operations"][1:]
    final = result["words"][-1]
    assert final["requirement_count"] == 0 and not final["type_errors"]
    assert "nonempty" in " ".join(final["context_assumptions"])


def test_beta_is_visible_but_not_the_default_and_loads_without_fallbacks():
    config = configuration()
    assert config["default_grammar"] != BETA_GRAMMAR
    assert BETA_GRAMMAR in next(s for s in config["systems"] if s["id"] == "classical")["grammars"]
    assert BETA_GRAMMAR not in config["lexical"]["grammars"]
    assert "Beta" in config["beta_grammars"][BETA_GRAMMAR]["label"]
    path = Path(__file__).parents[1] / "src/dynamicsyntax/grammars" / BETA_GRAMMAR
    report = lint_grammar(path)
    for key in ("strict_errors", "warnings", "undefined_templates", "arity_failures", "generic_labels"):
        assert not report[key], (key, report[key])


@pytest.mark.parametrize("extra", [
    {"lexical_mode": "assisted"}, {"lexical_mode": "dictionary"},
    {"decision_mode": "jev"}, {"experimental_rules": True},
    {"compare_jev": True}, {"grammar_pack": {"name": "unreviewed"}},
    {"paragraph": "If John cries, Mary laughs."},
    {"dialogue": [{"speaker": "A", "text": "If John cries, Mary laughs.", "boundary": "continue"}]},
])
def test_beta_rejects_unsupported_modes_before_model_or_extension_work(extra):
    payload = {"sentence": "If John cries, Mary laughs.", "grammar": BETA_GRAMMAR, **extra}
    if "paragraph" in extra or "dialogue" in extra:
        payload.pop("sentence")
    with pytest.raises(ValueError, match="beta"):
        validate_request(payload)


def test_beta_effects_cannot_modify_ordinary_grammars():
    parser = icp("2026-english-classical", strict=True)
    try:
        parser.init()
        tree = parser.get_best_tuple().tree
        before = tree.clone()
        for operation in ("conditional-beta-open", "conditional-beta-link"):
            assert ConditionalBetaEffect(operation).exec_tuple_context(tree, parser.context) is None
            assert tree == before
    finally:
        parser.close()
