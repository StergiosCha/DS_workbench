"""Decision stubs are neutral, logged and unable to activate live inference."""

from copy import deepcopy
import json

import pytest

from dylan.decision.client import DecisionClient, MODEL, content_hash, uniform_answers, validate_answers
from dylan.decision.questions.entry_v1 import questions


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live inference is forbidden in the test suite")
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)


def question_set():
    return questions([{"id": "e0", "template": "clitic", "params": ["him"]},
                      {"id": "e1", "template": "article", "params": ["acc"]}])


def test_log_record_has_required_fields(tmp_path):
    path = tmp_path / "audit.jsonl"
    client = DecisionClient("stub", log_path=path)
    record = client.decide({"next_word": "ton"}, question_set(), idea=1, deterministic_order=["e0", "e1"])
    assert json.loads(path.read_text()) == record
    assert set(record) >= {"model", "question_set_hash", "chunk_id", "answers", "latency_ms", "stub", "action_taken"}
    assert record["stub"] and record["action_taken"] == "none"
    assert set(record["answers"]["entry"]["probabilities"].values()) == {1 / 3}


def test_question_set_hash_changes_on_rewording():
    first = question_set()
    second = deepcopy(first)
    second["entry"]["instructions"] += " Consider the preceding word."
    assert content_hash(first) != content_hash(second)


def test_environment_and_key_cannot_activate_uncalibrated_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_DECISION_MODEL", MODEL)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-must-not-be-sent")
    record = DecisionClient(log_path=tmp_path / "audit.jsonl").decide({}, question_set(), idea=1)
    assert record["stub"] and record["gate"] == "unmeasured"
    assert record["model"] == "stub"


def test_off_does_not_create_a_log(tmp_path):
    path = tmp_path / "audit.jsonl"
    assert DecisionClient("off", log_path=path).decide({}, question_set(), idea=1) is None
    assert not path.exists()


@pytest.mark.parametrize("answer", [None, [], {"entry": None}, {"entry": {"type": "choice", "probabilities": None}}])
def test_malformed_answer_is_rejected(answer):
    with pytest.raises(ValueError):
        validate_answers(answer, question_set())


def test_primitive_probabilities_and_score_mean_are_validated():
    qs = {**question_set(), "distance": {"type": "score", "criteria": ["near", "middle", "far"]},
          "cluster": {"type": "noul", "instructions": "Has a clitic cluster"}}
    answers = uniform_answers(qs)
    assert validate_answers(answers, qs) == answers
    bad = deepcopy(answers)
    bad["distance"]["score"] = 0
    with pytest.raises(ValueError, match="weighted mean"):
        validate_answers(bad, qs)
    bad = deepcopy(answers)
    bad["entry"]["probabilities"]["e0"] = float("nan")
    with pytest.raises(ValueError):
        validate_answers(bad, qs)


@pytest.mark.parametrize("grammar,sentence", [
    ("2026-smg-mltt", "mas to edosa."),
    ("2026-smg-classical", "mas to edosa."),
    ("2026-smg-mltt", "to mas edosa."),
    ("2026-pontic-mltt", "edikse m esen."),
    ("2026-pontic-classical", "edeke m a."),
    ("2026-english-mltt", "john thinks that mary walks quietly."),
])
def test_stub_never_changes_corpus_outcomes(grammar, sentence, tmp_path):
    from dynamicsyntax import icp
    from dylan.action.meta.element import reset_all_meta_bindings

    values = []
    for mode in ("off", "stub"):
        reset_all_meta_bindings()
        parser = icp(grammar)
        parser.decision_client = DecisionClient(mode, log_path=tmp_path / f"{mode}.jsonl")
        try:
            result = parser.parse(sentence)
            values.append((result.ok, result.tree.is_complete(), str(result.semantics),
                           result.cap_hit, result.stats))
        finally:
            parser.close()
    assert values[0] == values[1]
    if grammar.startswith("2026-smg"):
        record = json.loads((tmp_path / "stub.jsonl").read_text().splitlines()[0])
        assert record["state"]["entries"][0]["params"]


def test_prior_breaks_only_a_completeness_tie():
    from dylan.dag.word_level_context_dag import WordLevelContextDAG
    from dylan.tree.tree import Tree

    dag = WordLevelContextDAG()
    parent = dag.get_current_tuple()
    first, second = dag.get_new_edge([], None), dag.get_new_edge([], None)
    dag.add_child_from(parent, dag.get_new_tuple(Tree()), first)
    dag.add_child_from(parent, dag.get_new_tuple(Tree()), second)
    assert dag.get_out_edges(parent) == [first, second]
    first.prior, second.prior = 0.1, 0.9
    assert dag.get_out_edges(parent) == [second, first]
    first.dst.tree.pointed_node.labels.clear()
    assert dag.get_out_edges(parent) == [first, second]


def test_audit_failure_cannot_fail_the_parse(tmp_path):
    from dynamicsyntax import icp

    path = tmp_path / "not_a_directory"
    path.write_text("x")
    parser = icp("2026-smg-mltt")
    parser.decision_client = DecisionClient("stub", log_path=path / "audit.jsonl")
    try:
        assert parser.parse("mas to edosa.").ok
    finally:
        parser.close()


def test_triage_cannot_change_results_or_leak_source_labels(tmp_path):
    from dylan.decision.triage import triage_result

    path = tmp_path / "audit.jsonl"
    client = DecisionClient("stub", log_path=path)
    result = {"id": "example", "grammar": "2026-smg-mltt", "surface": "test",
              "failure": {"kind": "unresolved_parse_failure"}, "ok": False,
              "judgment": {"status": "starred"}, "phenomena": ["pcc"],
              "gloss": "gold explanation", "expected": {"complete": False}}
    before = deepcopy(result)
    estimate = triage_result(result, client)
    assert result == before
    assert estimate["stub"] and not estimate["display"]
    assert estimate["route"] == "human_review"
    record = json.loads(path.read_text())
    assert not {"judgment", "phenomena", "gloss", "expected"} & record["state"].keys()
    assert "constraint_violation" not in record["questions"]["failure_kind_estimate"]["criteria"]
    result["failure"]["kind"] = "constraint_violation"
    assert triage_result(result, client) is None
    result["failure"]["kind"] = "construction_gap"
    result["cap_hit"] = "completion"
    assert triage_result(result, client) is None
