from copy import deepcopy
import json
import subprocess

import pytest

from dylan.experiments import diagnostic
from dylan.experiments.contracts import Analysis, Observation
from dylan.experiments.diagnostic_report import render


def items(suite="number_prep"):
    return [{"id": f"{suite}:1/{name}", "family": f"{suite}:1", "suite": suite,
             "shared_frame": "lexical-frame:1", "condition": name, "gold": gold,
             "text": text} for name, gold, text in [
        ("match_sing", True, "the student near the sailors is good"),
        ("mismatch_sing", False, "the student near the sailors are good"),
        ("match_plural", True, "the students near the sailor are good"),
        ("mismatch_plural", False, "the students near the sailor is good"),
    ]]


def test_no_derivation_does_not_earn_negative_credit():
    observation = Observation("the student glorp", task="sentence")
    for status in ("no_derivation", "unsupported_lexicon", "search_limit", "constraint_rejection"):
        result = diagnostic.compact(Analysis("test", observation, status, False, False))
        assert result["decision"] is None
    rows = items()
    records = {i["id"]: {"status": "unsupported_lexicon", "decision": None} for i in rows}
    score = diagnostic.metrics(rows, records)
    assert score["evaluable_conditions"] == score["evaluable_families"] == score["correct_families"] == 0
    assert score["condition_accuracy"] is None and score["negative_rejection"] is None


def test_accept_all_is_half_correct_but_passes_no_family():
    rows = items()
    score = diagnostic.metrics(rows, {i["id"]: {"status": "complete", "decision": True} for i in rows})
    assert score["condition_accuracy"] == .5 and score["evaluable_families"] == 1
    assert score["correct_families"] == 0 and score["negative_rejection"] == 0


def test_scoring_rejects_missing_conditions_duplicate_or_extra_results_and_nonboolean_decisions():
    rows = items()
    records = {i["id"]: {"status": "complete", "decision": True} for i in rows}
    with pytest.raises(ValueError, match="exactly"):
        diagnostic.metrics(rows, dict(list(records.items())[:-1]))
    with pytest.raises(ValueError, match="four"):
        diagnostic.metrics(rows[:-1], dict(list(records.items())[:-1]))
    records[rows[0]["id"]]["decision"] = 1
    with pytest.raises(ValueError, match="booleans"):
        diagnostic.metrics(rows, records)


def test_partial_coverage_does_not_pass_a_family_or_enter_the_shared_sample():
    rows = items()
    correct = {i["id"]: {"status": "test", "decision": i["gold"]} for i in rows}
    partial = deepcopy(correct)
    partial[rows[0]["id"]]["decision"] = None
    result = diagnostic.summarize(
        {"items": rows, "protocol": {"selection": {"number_prep": {}}}},
        {"ccg-feature-head-v1": correct, "ds-english-v1": partial})
    assert result["engines"]["ds-english-v1"]["overall"]["evaluable_conditions"] == 3
    assert result["engines"]["ds-english-v1"]["overall"]["evaluable_families"] == 0
    assert result["intersections"]["all_configurations"]["families"] == 0
    assert result["intersections"]["feature_ablations"]["families"] == 1


def test_real_worker_runs_new_engine_in_this_checkout_and_gold_is_irrelevant():
    rows = items()
    results = diagnostic.run_engine("ccg-feature-head-v1", rows)
    assert [results[i["id"]]["decision"] for i in rows] == [True, False, True, False]
    altered = [dict(i, gold=not i["gold"], condition="unrelated") for i in rows]
    assert diagnostic.run_engine("ccg-feature-head-v1", altered) == results


def test_worker_timeout_cannot_be_reported_as_rejection(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 1)
    monkeypatch.setattr(diagnostic.subprocess, "run", timeout)
    result = diagnostic.run_engine("ds-english-v1", items())
    assert all(r == {"status": "worker_timeout", "decision": None} for r in result.values())


def test_prepare_keeps_regions_predictions_and_shared_frame_identity(tmp_path, monkeypatch):
    protocol = {"selection": {"number_prep": {"items": [1], "critical_region": 6},
                              "reflexive_prep_masc": {"items": [1], "critical_region": 7}}}
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    monkeypatch.setattr(diagnostic, "data_path", lambda _: path)

    def suite(name, *args, **kwargs):
        conditions = [{"name": c, "regions": [
            {"number": 1, "label": "intro", "content": " The "},
            {"number": 2, "label": "subject", "content": "student"},
            {"number": 3, "label": "gap", "content": ""},
            {"number": 6, "label": "verb", "content": "is"},
            {"number": 7, "label": "end", "content": "good"},
        ]} for c in diagnostic.CONDITIONS]
        return {"source": {"id": name}, "predictions": [{"formula": "source formula"}],
                "critical_regions": [6], "meta": {}, "families": [
                    {"item_number": 1, "id": name + ":1", "conditions": conditions}]}
    monkeypatch.setattr(diagnostic, "syntaxgym", suite)
    result = diagnostic.prepare(tmp_path)
    assert len(result["items"]) == 8
    assert len({i["shared_frame"] for i in result["items"]}) == 1
    assert result["items"][0]["regions"][0]["content"] == " The "
    assert result["items"][0]["regions"][2]["content"] == ""
    assert result["sources"][0]["predictions"] == [{"formula": "source formula"}]


def test_report_does_not_execute_markup_from_imported_sources():
    report = {"text": "</script><script>alert(1)</script>&"}
    html = render(report)
    assert "</script><script>alert(1)" not in html
    payload = html.split('id="report-data">', 1)[1].split("</script>", 1)[0]
    assert json.loads(payload) == report
