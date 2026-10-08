"""Semantic regressions: independent argument records must not share field labels."""

import pytest

from dylan.action.atomic.ttr_fresh_put import TTRFreshPut
from dylan.context.context import Context
from dylan.dag.word_level_context_dag import WordLevelContextDAG
from dylan.formula.predicate_argument import PredicateArgumentFormula
from dylan.formula.formula import Formula
from dylan.formula.atomic_formula import AtomicFormula
from dylan.formula.variable import Variable
from dylan.action.meta.meta_formula import MetaFormula
from dylan.formula.ttr_field import TTRField
from dylan.formula.ttr_label import TTRLabel
from dylan.formula.ttr_record_type import TTRRecordType
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.workbench_api import parse_request


def role(record, predicate):
    matches = [f.manifest_type for f in record.get_fields()
               if isinstance(f.manifest_type, PredicateArgumentFormula)
               and str(f.manifest_type.predicate) == predicate]
    assert len(matches) == 1, (predicate, str(record))
    return matches[0].arguments[-1]


@pytest.mark.parametrize("grammar", ["2015-english-ttr", "2026-english-ttr", "2026-english-ttr-2"])
@pytest.mark.parametrize("sentence,subject_name,object_name", [
    ("a man knows you.", None, "you"),
    ("john likes mary.", "john", "mary"),
    ("mary likes john.", "mary", "john"),
    ("john likes john.", "john", "john"),
    ("a man likes a woman.", None, None),
])
def test_distinct_arguments_survive_ttr_composition(grammar, sentence, subject_name, object_name):
    result = parse_request({"grammar": grammar, "sentence": sentence}, _trace=False)
    assert result["complete"], result["failure"]
    record = TTRRecordType.parse(result["words"][-1]["semantics"])
    subject, obj = role(record, "subj"), role(record, "obj")
    assert subject != obj, str(record)
    sf, of = record.get_field(TTRLabel(str(subject))), record.get_field(TTRLabel(str(obj)))
    assert sf is not None and of is not None
    if subject_name:
        assert str(sf.manifest_type) == subject_name
    else:
        assert role(record, "man") == subject
    if object_name:
        assert str(of.manifest_type) == object_name
    else:
        assert role(record, "woman") == obj


def test_runtime_ttrput_freshens_the_branch_without_mutating_context_or_template():
    context = Context(WordLevelContextDAG(), None, "A", "B")
    source = context.get_current_tuple().tree
    branch = source.clone()
    template = TTRRecordType.parse("[x:e|head==x:e]")
    action = TTRFreshPut(template)
    for addr in ("00", "010"):
        address = NodeAddress(addr)
        branch[address] = Node(address)
        branch.set_pointer(address)
        assert action.exec_tuple_context(branch, context) is branch
    subject = branch[NodeAddress("00")].get_formula()
    obj = branch[NodeAddress("010")].get_formula()
    assert subject.get_head_field().label != obj.get_head_field().label
    assert not source._entity_pool
    assert str(template) == "[x : e|head==x : e]"
    replay = source.clone()
    replay.set_pointer(replay.root_addr)
    action.exec_tuple_context(replay, context)
    assert replay.pointed_node.get_formula() == subject


def test_freshening_rejects_contexts_that_cannot_allocate_branch_local_names():
    template = TTRRecordType.parse("[x:e|head==x:e]")
    context = Context(WordLevelContextDAG(), None, "A", "B")
    with pytest.raises(TypeError, match="receiving Tree"):
        template.freshen_vars(context)
    with pytest.raises(TypeError, match="receiving Tree"):
        template.freshen_vars_tree(context)


@pytest.mark.parametrize("name", ["A", "B", "Alice", "speaker_B"])
def test_participant_constants_survive_ttr_record_roundtrip(name):
    record = TTRRecordType.parse(f"[x0=={name}:e|head==x0:e]")
    assert record is not None
    assert record.get_field(TTRLabel("x0")).manifest_type == AtomicFormula(name)
    assert TTRRecordType.parse(str(record)) == record
    assert isinstance(Formula.create("X"), MetaFormula)
    assert isinstance(Formula.create("R1"), Variable)


def test_invalid_manifest_cannot_silently_become_an_unconstrained_field():
    assert TTRField.parse("x0==???:e") is None
    assert TTRRecordType.parse("[x0==???:e|head==x0:e]") is None
    with pytest.raises(ValueError, match="supported TTR formula"):
        TTRFreshPut.parse("ttrput([x0==???:e|head==x0:e])")


@pytest.mark.parametrize("grammar", ["2015-english-ttr", "2026-english-ttr", "2026-english-ttr-2"])
def test_ttr_semantics_are_stable_across_replay_and_requests(grammar):
    payload = {"grammar": grammar, "sentence": "a man knows you."}
    recorded = parse_request(payload, _trace=False)
    traced = parse_request(payload)
    repeated = parse_request(payload, _trace=False)
    expected = recorded["words"][-1]["semantics"]
    assert traced["complete"] and repeated["complete"]
    assert repeated["words"][-1]["semantics"] == expected
    for channel in ("words", "actions", "operations"):
        assert traced[channel][-1]["semantics"] == expected


@pytest.mark.parametrize("grammar", ["2015-english-ttr", "2026-english-ttr", "2026-english-ttr-2"])
def test_speaker_change_resolves_you_without_overwriting_the_subject(grammar):
    result = parse_request({"grammar": grammar, "dialogue": [
        {"speaker": "A", "text": "john likes"},
        {"speaker": "B", "text": "you."},
    ]})
    assert result["complete"]
    record = TTRRecordType.parse(result["words"][-1]["semantics"])
    subject, obj = role(record, "subj"), role(record, "obj")
    assert subject != obj
    assert str(record.get_field(TTRLabel(str(subject))).manifest_type) == "john"
    assert str(record.get_field(TTRLabel(str(obj))).manifest_type) == "A"


@pytest.mark.parametrize("grammar", ["2015-english-ttr", "2026-english-ttr", "2026-english-ttr-2"])
def test_repair_preserves_subject_and_original_contribution(grammar):
    result = parse_request({"grammar": grammar, "dialogue": [
        {"speaker": "A", "text": "john likes mary."},
        {"speaker": "B", "text": "sorry bill."},
    ]})
    assert result["complete"]
    before = next(f for f in result["words"] if f["label"] == ".")
    for snapshot, expected in ((before, "mary"), (result["words"][-1], "bill")):
        record = TTRRecordType.parse(snapshot["semantics"])
        subject, obj = role(record, "subj"), role(record, "obj")
        assert subject != obj
        assert str(record.get_field(TTRLabel(str(subject))).manifest_type) == "john"
        assert str(record.get_field(TTRLabel(str(obj))).manifest_type) == expected
