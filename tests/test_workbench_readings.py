"""Complete alternative analyses retain their own semantics and calculus trace."""

import json
from pathlib import Path
import shutil

import pytest

from dylan import workbench_api
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq


@pytest.fixture(params=["mltt", "classical"])
def ambiguous(request, tmp_path, monkeypatch):
    reset_all_meta_bindings()
    source = Path(__file__).parents[1] / f"src/dynamicsyntax/grammars/2026-english-{request.param}"
    grammar = tmp_path / "grammar"
    shutil.copytree(source, grammar)
    with (grammar / "lexicon.txt").open("a") as out:
        out.write("bank proper john human\nbank proper john human\nbank proper mary human\n")
    config = workbench_api.configuration()
    config["grammars"].append(str(grammar))
    monkeypatch.setattr(workbench_api, "configuration", lambda: config)
    yield {"grammar": str(grammar), "sentence": "bank shouts.", "top_n": 0}
    reset_all_meta_bindings()


def test_n_best_deduplicates_and_replays_each_complete_analysis(ambiguous):
    first = workbench_api.parse_request(ambiguous)
    result = workbench_api.parse_request({**ambiguous, "n_best": 8, "reading_traces": True})
    assert result["complete"] and result["ok"]
    assert result["reading_search"]["exhausted"]
    assert {r["semantics"] for r in result["readings"]} == {"shout(john)", "shout(mary)"}
    for key in ("words", "actions", "operations", "templates", "stats", "coq"):
        assert result[key] == first[key]
    alternative = result["readings"][1]
    assert alternative["action_names"].count("bank") == 1
    trace = alternative["trace"]
    for channel in trace.values():
        assert len(channel[0]["nodes"]) == 1
        assert channel[0]["kind"] == "axiom"
        assert channel[-1]["complete"]
        assert channel[-1]["semantics"] == alternative["semantics"]
    assert [f["label"] for f in trace["words"] if f["kind"] == "word"] == ["bank", "shouts", "."]
    operations = [f for f in trace["operations"] if f["kind"] == "operation"]
    assert any(f["delta"]["created"] for f in operations)
    assert any(f["pointer_before"] != f["pointer"] for f in operations)
    assert any(f["conditions"] for f in operations)
    if result["backend"] == "mltt" and shutil.which("coqc"):
        for reading in result["readings"]:
            assert compile_coq(reading["coq"], {}) == "passed"
    json.dumps(result)


def test_reading_limit_does_not_claim_exhaustive_search(ambiguous):
    result = workbench_api.parse_request({**ambiguous, "n_best": 1})
    assert len(result["readings"]) == 1
    assert result["reading_search"]["stop_reason"] == "reading_limit"
    assert not result["reading_search"]["exhausted"]


def test_candidate_bound_is_distinct_from_exhaustion(ambiguous):
    from dynamicsyntax import icp
    from dylan.workbench_readings import collect_readings

    parser = icp(ambiguous["grammar"], top_n=0)
    try:
        result = parser.parse(ambiguous["sentence"])
        assert result.ok
        readings, search = collect_readings(parser, result.tree, [], ["bank", "shouts", "."],
                                            limit=8, max_candidates=1)
        assert len(readings) == 1
        assert search["stop_reason"] == "candidate_limit" and not search["exhausted"]
    finally:
        parser.close()


def test_failed_alternative_does_not_replace_primary(ambiguous):
    path = Path(ambiguous["grammar"]) / "lexicon.txt"
    path.write_text(path.read_text().replace("bank proper mary human", "bank proper mary stone"))
    result = workbench_api.parse_request({**ambiguous, "n_best": 8})
    # The constructive predicate rejects stone; classical e alone has no such distinction.
    if result["backend"] == "mltt":
        assert [r["semantics"] for r in result["readings"]] == ["shout(john)"]
    assert result["complete"] and result["failure"] is None
    assert result["words"][-1]["semantics"] == "shout(john)"


def test_lexical_limit_is_reported_separately_from_search_exhaustion(ambiguous):
    result = workbench_api.parse_request({**ambiguous, "top_n": 1, "n_best": 8})
    assert len(result["readings"]) == 1
    assert result["reading_search"]["exhausted"]
    # The nonrestrictive-relative extension also adds a second period entry.
    # Both losses must remain visible even though this sentence needs only one.
    assert result["reading_search"]["top_n_cuts"] == [("bank", 2), (".", 1)]


@pytest.mark.parametrize("sentence", ["a man", "unknown walks.", "a stone shouts."])
def test_unfinished_or_failed_parses_are_not_complete_readings(sentence):
    result = workbench_api.parse_request({"grammar": "2026-english-mltt", "sentence": sentence, "n_best": 3})
    assert not result["complete"] and not result["readings"]
    assert not result["reading_search"]["exhausted"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_shipped_attachment_ambiguity_records_link_and_both_meanings(backend):
    result = workbench_api.parse_request({"grammar": f"2026-english-{backend}",
        "sentence": "john thinks that mary walks quickly.", "n_best": 3, "reading_traces": True})
    assert result["complete"] and result["reading_search"]["exhausted"]
    assert {r["normalized"] for r in result["readings"]} == {
        "quickly(think(john, walk(mary)))", "think(john, quickly(walk(mary)))"}
    assert all(r["strategy"] == "link" for r in result["readings"])
    if backend == "mltt" and shutil.which("coqc"):
        for reading in result["readings"]:
            assert compile_coq(reading["coq"], {}) == "passed"


@pytest.mark.parametrize("value", [0, 9, True, 3.0, "3", None, [], {}])
def test_invalid_reading_limits_are_rejected(value):
    with pytest.raises(ValueError, match="n_best"):
        workbench_api.validate_request({"grammar": "2026-english-mltt", "sentence": "john walks.", "n_best": value})


def test_dialogue_does_not_silently_ignore_alternative_search():
    with pytest.raises(ValueError, match="dialogue"):
        workbench_api.validate_request({"grammar": "2026-english-mltt", "n_best": 3,
                                       "dialogue": [{"speaker": "A", "text": "john walks."}]})
