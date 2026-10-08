"""Effects execute through the DS calculus, with faithful frozen trace states."""

import logging

import pytest

from dylan.action.action import Action
from dylan.action.atomic.effect_factory import EffectFactory
from dylan.action.atomic.if_then_else import IfThenElse
from dylan.action.atomic.lexical_macro import LexicalMacro
from dylan.action.execution_trace import capture_effects
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.tree import Tree
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def contents(tree):
    return str(tree.pointer), [
        (str(a), [str(label) for label in n.labels]) for a, n in tree.items()
    ]


def test_nested_then_else_and_macros_record_only_executed_primitives():
    macro = LexicalMacro(
        "build-child", [EffectFactory.create(r"make(\/0)"), EffectFactory.create(r"go(\/0)")]
    )
    nested = IfThenElse.from_lines(["IF Ty(e)", "THEN put(+wrong)", "ELSE put(?Ty(e))"])
    rule = Action("test", IfThenElse.from_lines(["IF ?Ty(t)", "THEN do_nothing", "ELSE abort"]))
    rule.effect.then_effects = [macro, nested]
    with capture_effects() as effects:
        result = rule.exec(Tree(), None)
    assert result is not None
    assert [e.operation for e in effects] == [r"make(\/0)", r"go(<\/0>)", "put(?Ty(e))"]
    assert effects[-1].conditions[-1]["branch"] == "ELSE"
    assert effects[-1].conditions[-1]["checks"] == [{"label": "Ty(e)", "passed": False}]
    assert effects[0].conditions[0]["branch"] == "THEN"
    assert all("wrong" not in e.operation for e in effects)


def test_failed_rule_discards_its_partial_trace():
    rule = Action(
        "fail", IfThenElse.from_lines(["IF ?Ty(t)", r"THEN make(\/0)", r"go(\/1)", "ELSE abort"])
    )
    with capture_effects() as effects:
        assert rule.exec(Tree(), None) is None
    assert effects == []


def test_observation_preserves_execution_and_freezes_old_decorations():
    rule = Action(
        "intro",
        IfThenElse.from_lines(
            [
                "IF ?Ty(t)",
                r"THEN make(\/0)",
                r"go(\/0)",
                "put(Ty(e))",
                "put(Fo(john))",
                "ELSE abort",
            ]
        ),
    )
    plain = rule.exec(Tree(), None)
    with capture_effects() as effects:
        observed = rule.exec(Tree(), None)
    assert contents(plain) == contents(observed)
    old = contents(effects[0].after_tree)
    observed.pointed_node.labels.clear()
    reset_all_meta_bindings()
    assert contents(effects[0].after_tree) == old
    assert effects[1].after_tree.pointed_node.get_type() is None
    assert str(effects[2].after_tree.pointed_node.get_type()) == "e"


@pytest.mark.parametrize(
    "grammar,sentence",
    [
        ("2026-english-mltt", "a man walks."),
        ("2026-english-classical", "a man walks."),
        ("2015-english-ttr", "a man knows you."),
    ],
)
def test_workbench_make_go_put_are_distinct_and_end_at_authoritative_word_state(
    grammar, sentence, caplog
):
    caplog.set_level(logging.CRITICAL)
    result = parse_request({"grammar": grammar, "sentence": sentence})
    assert result["complete"]
    ops = result["operations"]
    make, go, put = ops[1:4]
    assert make["label"].startswith("make(")
    assert make["delta"]["created"] == ["01"]
    assert make["pointer_before"] == make["pointer"] == "0"
    assert len(make["nodes"]) == 2
    assert next(n for n in make["nodes"] if n["id"] == "01")["labels"] == []
    assert go["label"].startswith("go(")
    assert go["pointer_before"] == "0" and go["pointer"] == "01"
    assert go["nodes"] == make["nodes"]
    assert put["label"].startswith("put(")
    assert put["delta"]["decorations"][0]["node"] == "01"
    assert put["pointer_before"] == put["pointer"] == "01"
    assert put["rule"] == "intro-pred"
    assert all(c["passed"] for c in put["conditions"][0]["checks"])
    assert ops[-1]["nodes"] == result["words"][-1]["nodes"]
    assert ops[-1]["pointer"] == result["words"][-1]["pointer"]
    assert len(ops) > len(result["actions"])


def test_link_macro_uses_make_go_put_and_thinning_uses_delete():
    result = parse_request({"grammar": "2026-english-mltt", "sentence": "john walks quickly."})
    assert result["complete"]
    ops = result["operations"]
    link = [f for f in ops if f.get("rule") == "quickly"]
    assert any(f["label"] == r"make(\/L)" for f in link)
    assert any(f["label"] == r"go(<\/L>)" for f in link)
    assert all(len(f["delta"]["created"]) <= 1 for f in link)
    assert any(f["label"].startswith("delete(?Ty(") for f in ops)
    assert result["words"][-1]["semantics"] == "quickly(walk(john))"


def test_operation_stream_frames_match_result_and_no_unknown_word_is_executed():
    events = []
    result = parse_request(
        {"grammar": "2026-english-mltt", "sentence": "a missing walks."}, events.append
    )
    assert not result["ok"]
    streamed = [events[0]["initial"]] + [
        e["frame"] for e in events if e["event"] == "frame" and e["channel"] == "operations"
    ]
    assert streamed == result["operations"]
    assert all(f["word_index"] <= 0 for f in streamed)
