from copy import deepcopy

import pytest

from dylan.experiments.lingembed_api import run, validate
from dylan.experiments.contracts import Observation
from dylan.experiments.lingembed import export_analysis
from dylan.experiments.registry import create_engine


def analyse(grammar, text, context="", task="fragment"):
    engine = create_engine(grammar)
    try:
        return engine.analyse(Observation(text, context, task))
    finally:
        engine.close()


@pytest.mark.parametrize("grammar", ["ds-english-v1", "ccg-incremental-v1"])
def test_prefix_exports_are_independent_of_later_words(grammar):
    short = export_analysis(analyse(grammar, "John likes"))
    long = export_analysis(analyse(grammar, "John likes Mary"))
    assert short["frames"] == long["frames"][:2]
    assert long["tokens"][-1] == {"index": 2, "text": "mary", "context": False}


def test_ccg_exports_real_typed_derivations_and_ordered_spans():
    original = analyse("ccg-incremental-v1", "likes Mary", "John")
    exported = export_analysis(original)
    assert exported["tokens"][0]["context"]
    assert len(exported["frames"][0]["structures"]) == 2  # NP and raised NP
    final = exported["frames"][-1]["structures"][0]
    assert final["nodes"][0]["type"] == "S"
    assert final["nodes"][0]["meaning"] == original.meanings[0]
    assert final["nodes"][0]["span"] == [0, 3]
    leaves = {e["source"] for e in final["edges"]}
    assert sorted(node["span"] for node in final["nodes"] if node["id"] not in leaves) == [[0, 1], [1, 2], [2, 3]]
    assert all(node["span"][1] <= index + 1 for index, frame in enumerate(exported["frames"])
               for structure in frame["structures"] for node in structure["nodes"])


def test_ccg_replay_checks_lexicon_and_native_states():
    original = analyse("ccg-incremental-v1", "John likes Mary").to_dict()
    changed = deepcopy(original)
    changed["provenance"]["lexicon_sha256"] = "stale"
    with pytest.raises(ValueError, match="lexicon"):
        export_analysis(changed)
    changed = deepcopy(original)
    changed["states"][0]["after"]["categories"] = ["invented"]
    with pytest.raises(ValueError, match="output state"):
        export_analysis(changed)


@pytest.mark.parametrize("grammar,text", [("ds-english-v1", "John likes Mary"),
                                         ("ds-greek-v1", "ο άνθρωπος περπατάει")])
def test_ds_preserves_labels_and_explicit_completion_without_invented_alignment(grammar, text):
    original = analyse(grammar, text, task="sentence")
    exported = export_analysis(original)
    words = [f for f in exported["frames"] if f["stage"] == "word"]
    assert len(words) == len(original.states)
    for source, frame in zip(original.states, words):
        assert source["after"] == frame["native_state"]
        assert [(n["address"], n["labels"]) for n in source["after"]["nodes"]] == [
            (n["id"], n["labels"]) for n in frame["structures"][0]["nodes"]]
        assert all(n["span"] is None for n in frame["structures"][0]["nodes"])
    assert exported["frames"][-1]["stage"] == "completion"
    assert exported["frames"][-1]["native_state"] == original.provenance["native_state"]
    assert exported["frames"][-1]["observed"] == words[-1]["observed"]


@pytest.mark.parametrize("grammar", ["ds-english-v1", "ccg-incremental-v1"])
def test_unknown_words_remain_coverage_failures(grammar):
    result = export_analysis(analyse(grammar, "John zzzzz"))
    assert not result["supported"]
    assert result["status"] == "unsupported_lexicon"
    assert not result["complete"]


def test_missing_full_span_derivation_is_not_filled_with_future_structure():
    result = export_analysis(analyse("ccg-application-v1", "John likes Mary"))
    assert result["frames"][1]["structures"] == []
    assert result["frames"][1]["native_state"]["chart_cells"]
    assert result["frames"][2]["structures"]


def test_export_is_optional_and_does_not_change_experiment_results():
    payload = {"configurations": [{"grammar": "ccg-incremental-v1"}], "prime": "John walks", "target": "Mary walks"}
    ordinary = run(payload)
    enriched = run({**payload, "export_lingembed": True})
    for result in enriched["runs"]:
        for event in result["events"]:
            assert event.pop("lingembed")["schema"] == "lingembed.analysis.v1"
    assert ordinary == enriched
    with pytest.raises(ValueError, match="boolean"):
        validate({**payload, "export_lingembed": "yes"})
