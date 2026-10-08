"""Recorded preferences preserve backtracking, readings and reference isolation."""

from copy import deepcopy
import json

import pytest

from dylan.decision.client import DecisionClient, uniform_answers
from dylan.decision.evaluation import decision_items, run_case, score_group, answers_for_replay
from dylan.decision.gates import family_hash, grammar_hash, measured_gate, qualifies, evaluation_summary
from dylan.decision.provider import DIRECT_MODEL


@pytest.fixture(autouse=True)
def no_live_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline replay must never call a provider")
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)
    monkeypatch.setenv("DS_DECISION_PROVIDER", "typesafe")


def reverse_answers(records, idea):
    answers = {}
    for record in records:
        if record["idea"] != idea:
            continue
        values = uniform_answers(record["questions"])
        answer = next(iter(values.values()))
        choice = record["deterministic_order"][-1]
        answer.update(choice=choice, confidence=0.8)
        answer["probabilities"] = {key: 0.9 if key == choice else 0.1 / (len(answer["probabilities"]) - 1)
                                   for key in answer["probabilities"]}
        answers[record["cache_key"]] = values
    return answers


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("idea", [1, 2])
def test_wrong_preference_can_backtrack_to_success(backend, idea, tmp_path):
    # Keep the original clitic ambiguity: Greek-script τον now also has a
    # definite-DP branch which changes the endpoint-completeness tie breaks.
    case = {"grammar": f"2026-smg-{backend}", "surface": "ton agapa."}
    baseline = run_case(case, DecisionClient("stub", log_path=tmp_path / "base.jsonl"))
    answers = reverse_answers(baseline["records"], idea)
    assert answers
    replay = run_case(case, DecisionClient("stub", recorded=answers, log_path=tmp_path / "replay.jsonl"))
    assert replay["outcome"] == baseline["outcome"] and replay["outcome"]["ok"]
    assert any(r.get("recorded") for r in replay["records"])
    assert replay["stats"]["backtracks_ok"] > baseline["stats"]["backtracks_ok"]
    assert replay["stats"]["pruned"] == 0 and not replay["stats"]["top_n_cuts"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_all_exhausted_readings_survive_changed_order(backend, tmp_path):
    case = {"grammar": f"2026-smg-{backend}", "surface": "o γiorγos xtipise to γiani."}
    baseline = run_case(case, DecisionClient("stub", log_path=tmp_path / "base.jsonl"), enumerate_readings=True)
    answers = reverse_answers(baseline["records"], 2)
    replay = run_case(case, DecisionClient("stub", recorded=answers, log_path=tmp_path / "replay.jsonl"),
                      enumerate_readings=True)
    assert baseline["readings"]["exhausted"] and replay["readings"]["exhausted"]
    assert len(baseline["readings"]["analyses"]) >= 3
    assert replay["readings"] == baseline["readings"]
    assert replay["stats"]["pruned"] == 0


def test_duplicate_prefixes_keep_conflicting_reference_labels_out_of_state(tmp_path):
    case = {"id": "first", "grammar": "2026-smg-mltt", "surface": "τον αγαπά."}
    case["baseline"] = run_case(case, DecisionClient("stub", log_path=tmp_path / "audit.jsonl"))
    clone = deepcopy(case)
    clone["id"] = "second"
    original = next(r for r in case["baseline"]["records"] if r["idea"] == 1)
    alternative = next(r for r in clone["baseline"]["records"] if r["cache_key"] == original["cache_key"])
    alternative["reference_choices"] = [original["deterministic_order"][-1]]
    items = decision_items([case, clone])
    item = next(i for i in items if i["cache_key"] == original["cache_key"])
    assert len(item["reference_choices"]) == 2
    assert item["state"]["tokens_so_far"] == []
    assert item["state"]["next_word"] == "τον"
    assert "αγαπά" not in json.dumps(item["state"], ensure_ascii=False)
    assert not {"reference_choices", "source", "surface", "judgment", "case_ids"} & item["state"].keys()
    score = score_group([item], {})
    assert score["ambiguous"] == 1 and score["n"] == 0


def test_reference_response_identity_is_validated(tmp_path):
    case = {"id": "case", "grammar": "2026-smg-mltt", "surface": "τον αγαπά."}
    case["baseline"] = run_case(case, DecisionClient("stub", log_path=tmp_path / "audit.jsonl"))
    items = decision_items([case])
    item = next(i for i in items if i["idea"] == 1)
    record = next(r for r in case["baseline"]["records"] if r["cache_key"] == item["cache_key"])
    response = {**record, "stub": False, "model": "wrong-version"}
    with pytest.raises(ValueError, match="frozen request"):
        answers_for_replay({"items": items}, {item["cache_key"]: response}, 1)


def test_runtime_gate_requires_versioned_benefit_and_parity(monkeypatch, tmp_path):
    grammar = "2026-smg-mltt"
    evidence = {"model": DIRECT_MODEL, "provider": "typesafe", "n": 40, "agreement": 0.95,
                "gain": 0.2, "parity": True, "backtracks_reduced": True, "replay_hits": 50,
                "family_hash": family_hash(1), "grammar_hash": grammar_hash(grammar)}
    path = tmp_path / "gates.json"
    monkeypatch.setenv("DS_DECISION_GATES", str(path))
    path.write_text(json.dumps({f"{grammar}:1": evidence}))
    assert measured_gate(grammar, 1, DIRECT_MODEL)
    for key, value in [("parity", False), ("backtracks_reduced", False), ("missing", 1),
                       ("replay_hits", 0), ("agreement", 0.8), ("n", 39)]:
        assert not qualifies({**evidence, key: value}, 1)
    path.write_text(json.dumps({f"{grammar}:1": {**evidence, "family_hash": "stale"}}))
    assert not measured_gate(grammar, 1, DIRECT_MODEL)


def test_evaluation_summary_omits_stale_and_private_fields(monkeypatch, tmp_path):
    grammar = "2026-smg-mltt"
    monkeypatch.setenv("DS_DECISION_GATES", str(tmp_path / "calibration.json"))
    row = {"model": DIRECT_MODEL, "provider": "typesafe", "n": 17, "agreement": 0.4,
           "gain": -0.6, "parity": True, "baseline_backtracks": 109, "replay_backtracks": 113,
           "eligible": False, "family_hash": family_hash(1), "grammar_hash": grammar_hash(grammar),
           "private_test_field": "must not be public"}
    path = tmp_path / "evaluation.json"
    path.write_text(json.dumps({f"{grammar}:1": row}))
    summary = evaluation_summary(grammar, DIRECT_MODEL, "typesafe")
    assert summary["1"]["n"] == 17 and "must not be public" not in json.dumps(summary)
    assert evaluation_summary(grammar, "other-model", "typesafe") == {}
    path.write_text("[]")
    assert evaluation_summary(grammar, DIRECT_MODEL, "typesafe") == {}
