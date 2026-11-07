"""Actual LINK/record composition and limits of the backward-laughter beta."""

from pathlib import Path
from contextlib import closing
import re

import pytest

from dynamicsyntax import icp
from dylan.action.atomic.ttr_laughter import BETA_GRAMMAR, TTRLaughter
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.ttr_record_type import TTRRecordType
from dylan.grammar_tools import lint_grammar
from dylan.workbench_api import configuration, parse_request, validate_request


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def parse(sentence, **options):
    return parse_request({"sentence": sentence, "grammar": BETA_GRAMMAR,
                          "strict": True, **options}, _trace=False)


@pytest.mark.parametrize("sentence,target,link", [
    ("John [laugh] walks.", "x0", "00L"),
    ("A man [laugh] arrives.", "x0", "00L"),
    ("John sees a telescope [laugh].", "x1", "010L"),
    ("John likes Mary. [laugh]", "e0", "0L"),
    ("A woman runs. [laugh]", "e0", "0L"),
])
def test_laughter_retains_referent_or_event_and_link(sentence, target, link):
    result = parse(sentence)
    assert result["complete"], result["failure"]
    final = result["words"][-1]
    assert final["backend"] == "ttr" and final["requirement_count"] == 0
    assert f"laughable({target})" in final["semantics"]
    linked = next(n for n in final["nodes"] if n["id"] == link)
    assert f"laughable({target})" in linked["formula"]
    assert "+LAUGHTER-BACKWARD" in linked["labels"]
    record = TTRRecordType.parse(final["semantics"])
    assert record is not None
    # Laughable's target must refer to a field in the result, not a new entity.
    assert target in {str(label) for label in record.get_labels()}
    assert str(record.head().manifest_type) == "e0"
    assert len(re.findall(r"laughable\(", final["semantics"])) == 1
    assert result["coq"] is None and final["speech_act"] is None


def test_object_and_situation_readings_remain_distinct():
    result = parse("John sees a telescope [laugh].", n_best=4)
    assert len(result["readings"]) == 2
    targets = {re.search(r"laughable\((\w+)\)", r["semantics"]).group(1)
               for r in result["readings"]}
    assert targets == {"x1", "e0"}
    for reading in result["readings"]:
        assert "obj(e0, x1)" in reading["semantics"]
        assert "subj(e0, x0)" in reading["semantics"]
        assert "telescope(x1)" in reading["semantics"]


@pytest.mark.parametrize("text", ["[laugh]", "[laugh] John walks.",
    "a [laugh] man arrives.", "John likes [laugh] Mary.",
    "John walks. [laugh] [laugh]", "John walks. [laugh] because Mary runs."])
def test_unimplemented_sites_do_not_become_complete(text):
    result = parse(text)
    assert not result["complete"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_pending_sentence_stays_pending_after_nominal_laughter():
    result = parse("a man [laugh]")
    assert result["ok"] and not result["complete"]
    final = result["words"][-1]
    assert final["requirement_count"] > 0
    assert any(n["id"] == "00L" for n in final["nodes"])


def test_two_targets_do_not_reuse_laughter_field():
    result = parse("John [laugh] likes Mary [laugh].")
    assert result["complete"]
    meaning = result["words"][-1]["semantics"]
    assert "laughter0==laughable(x0)" in meaning
    assert "laughter1==laughable(x1)" in meaning


def test_dialogue_continues_same_tree_and_exposes_actual_contributor():
    result = parse_request({"grammar": BETA_GRAMMAR, "dialogue": [
        {"speaker": "A", "text": "a man"},
        {"speaker": "B", "text": "[laugh]"},
        {"speaker": "A", "text": "arrives."}]}, _trace=False)
    assert result["complete"] and not result["context_trees"]
    assert result["token_metadata"][2]["speaker"] == "B"
    assert "laughable(x0)" in result["words"][-1]["semantics"]
    assert not result["words"][-1]["feedback_events"]  # No inferred grounding.


def test_live_operations_show_link_then_computational_evaluation():
    events = []
    result = parse_request({"grammar": BETA_GRAMMAR,
                            "sentence": "John likes Mary. [laugh]"}, on_event=events.append)
    assert result["complete"]
    assert any(f["label"] == r"make(\/L)" for f in result["operations"])
    assert any(f["label"] == "link-evaluation" for f in result["actions"])
    streamed = [e["frame"] for e in events if e.get("event") == "frame" and e["channel"] == "operations"]
    assert streamed == result["operations"][1:]


def test_action_cannot_mutate_a_native_semantic_tree():
    with closing(icp("2026-english-mltt", strict=True, top_n=0)) as parser:
        tree = parser.parse("john walks.").tree
        before = str(tree)
        assert TTRLaughter().exec_tuple_context(tree, parser.context) is None
        assert str(tree) == before


def test_beta_grammar_is_strict_and_every_declared_word_is_loaded():
    directory = Path(__file__).parents[1] / "src/dynamicsyntax/grammars" / BETA_GRAMMAR
    report = lint_grammar(directory)
    for key in ("strict_errors", "warnings", "undefined_templates", "arity_failures", "generic_labels"):
        assert not report[key], (key, report[key])
    with closing(icp(BETA_GRAMMAR, strict=True, top_n=0)) as parser:
        assert parser.lexicon.load_stats.words_failed == 0
        for row in (directory / "lexicon.txt").read_text().splitlines():
            assert parser.lexicon.get(row.split()[0])
    config = configuration()
    assert BETA_GRAMMAR in next(s for s in config["systems"] if s["id"] == "ttr")["grammars"]
    assert config["default_grammar"] != BETA_GRAMMAR


@pytest.mark.parametrize("option", [
    {"paragraph": "John walks."}, {"lexical_mode": "assisted"},
    {"decision_mode": "jev"}, {"experimental_rules": True}, {"grammar_pack": "x"},
])
def test_unsupported_modes_are_rejected_at_request_boundary(option):
    with pytest.raises(ValueError, match="laughter beta"):
        validate_request({"grammar": BETA_GRAMMAR, "sentence": "John walks.", **option})
