"""E0.3: exhausted search budgets are reported independently of grammaticality."""

import json

import pytest

import dynamicsyntax as ds
from dylan.action.computational_action import ComputationalAction
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.greek_workbench import CASES
from dylan.nlp.types import utterance_from_text
from dylan.parser.dag_parser import DAGParser
from dylan.parser.interactive_context_parser import InteractiveContextParser
from dylan.tree.tree import Tree
from dylan.workbench_api import parse_request

SENTENCE = "every doctor examined a patient."
CAPS = ["max_lexical_adjustment_pairs", "max_nonoptional_adjust_passes"]


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("trace", [False, True])
@pytest.mark.parametrize(
    "grammar,sentence",
    [
        ("2026-english-mltt", SENTENCE),
        ("2026-english-classical", SENTENCE),
        ("2015-english-ttr", "a man knows you."),
    ],
)
def test_parse_cap_is_reported_and_result_survives_parser_reuse(cap, trace, grammar, sentence):
    parser = InteractiveContextParser(grammar)
    default = getattr(parser, cap)
    setattr(parser, cap, 1)
    try:
        result = parser.parse(sentence, trace=trace)
        assert not result.ok and result.semantics is None
        assert result.cap_hit == parser.last_cap_hit == cap
        if trace:
            assert len(result.trace_step_labels) < len(utterance_from_text("Dylan", sentence).words)
        assert parser.parse(" ").cap_hit is None
        # Controls cannot turn a stopped parse into an accepted continuation.
        assert parser.parse_word(utterance_from_text("Dylan", parser.WAIT).words[0]) is None
        setattr(parser, cap, default)
        recovered = parser.parse(sentence, trace=trace)
        assert recovered.ok and recovered.cap_hit is None
        assert parser.last_cap_hit is None
        assert result.cap_hit == cap
        rejected = parser.parse("zzzunknown")
        assert not rejected.ok and rejected.cap_hit is None
    finally:
        parser.close()


@pytest.mark.parametrize("reset", ["init", "new_sentence", "init_participants"])
def test_explicit_parser_resets_clear_cap(reset):
    parser = InteractiveContextParser("2026-english-mltt", max_lexical_adjustment_pairs=1)
    try:
        assert parser.parse(SENTENCE).cap_hit == "max_lexical_adjustment_pairs"
        if reset == "init_participants":
            parser.init_participants(["Alice", "Bob"])
        else:
            getattr(parser, reset)()
        assert parser.last_cap_hit is None
    finally:
        parser.close()


@pytest.mark.timeout(3)
def test_completion_stops_after_nonoptional_cap_instead_of_restarting_the_loop():
    parser = DAGParser(Lexicon(), Grammar(), max_nonoptional_adjust_passes=1)
    parser.nonoptional_grammar["loop"] = ComputationalAction(
        "loop", ["IF ?Ty(t)", "THEN do_nothing", "ELSE abort"], True
    )
    actions, tree = parser.complete_tree(Tree())
    assert len(actions) == 1 and not tree.is_complete()
    assert parser.last_cap_hit == "max_nonoptional_adjust_passes"
    parser.init()
    assert parser.last_cap_hit is None


@pytest.mark.parametrize("factory", [
    lambda: InteractiveContextParser(max_completion_steps=1),
    lambda: InteractiveContextParser.from_loaded(Lexicon(), Grammar(), max_completion_steps=1),
])
def test_completion_budget_survives_loading_and_resets_after_a_parse(factory):
    parser = factory()
    try:
        parser.set_grammar("2026-smg-mltt")
        sentence = "Xtipise o Γiorγos to Γiani"
        limited = parser.parse(sentence)
        assert not limited.ok and limited.cap_hit == "max_completion_steps"
        assert limited.stats.cap_hits == ["max_completion_steps"]
        parser.max_completion_steps = 10_000
        recovered = parser.parse(sentence)
        assert recovered.ok and recovered.cap_hit is None
        assert limited.cap_hit == "max_completion_steps"
    finally:
        parser.close()


@pytest.mark.parametrize("cap", CAPS)
def test_workbench_reports_search_limit_without_overwriting_source_judgment(cap, monkeypatch):
    case = next(c for c in CASES if c["id"] == "cg-neg")
    payloads = [
        {"sentence": SENTENCE, "grammar": "2026-english-mltt"},
        {"sentence": case["reverse"], "grammar": "2026-cypriot-mltt"},
    ]
    judgments = [parse_request(payload)["diagnostics"]["judgment"] for payload in payloads]

    def limited_icp(grammar, **kwargs):
        return InteractiveContextParser(grammar, **kwargs, **{cap: 1})

    monkeypatch.setattr(ds, "icp", limited_icp)
    for payload, judgment in zip(payloads, judgments):
        result = parse_request(payload)
        assert not result["ok"] and not result["complete"] and result["coq"] is None
        assert result["cap_hit"] == result["diagnostics"]["cap_hit"] == cap
        assert result["failure"]["kind"] == "search_limit"
        assert result["failure"]["limit"] == 1
        assert result["diagnostics"]["judgment"] == judgment
        json.dumps(result)


@pytest.mark.parametrize("entrypoint", ["parse", "trace", "workbench", "dialogue_boundary"])
@pytest.mark.parametrize("cap", ["max_nonoptional_adjust_passes", "max_completion_steps"])
def test_cap_during_final_completion_is_reported_before_any_new_tree(entrypoint, cap, monkeypatch):
    # Lower the real budget only at completion, after all words have parsed successfully.
    def limited_completion_parser(grammar, **kwargs):
        parser = InteractiveContextParser(grammar, **kwargs)
        complete_tree = parser.complete_tree

        def complete(tree):
            setattr(parser, cap, 1)
            return complete_tree(tree)

        monkeypatch.setattr(parser, "complete_tree", complete)
        return parser

    sentence = SENTENCE.rstrip(".")
    if entrypoint in {"parse", "trace"}:
        parser = limited_completion_parser("2026-english-mltt")
        try:
            result = parser.parse(sentence, trace=entrypoint == "trace")
            assert not result.ok and result.cap_hit == cap and result.semantics is None
        finally:
            parser.close()
    else:
        monkeypatch.setattr(ds, "icp", limited_completion_parser)
        payload = {"sentence": sentence, "grammar": "2026-english-mltt"}
        if entrypoint == "dialogue_boundary":
            del payload["sentence"]
            payload["dialogue"] = [
                {"speaker": "Alice", "text": sentence},
                {"speaker": "Bob", "text": "john walks.", "boundary": "new_tree"},
            ]
        result = parse_request(payload)
        assert not result["ok"] and not result["complete"] and result["coq"] is None
        assert result["cap_hit"] == cap and result["failure"]["kind"] == "search_limit"
        assert result["failure"]["index"] == 4
        assert not result["context_trees"]
        assert not any(frame["label"] == "New tree" for frame in result["words"])
