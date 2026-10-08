"""Real parser contracts for the workbench, including failure and trace fidelity."""

import json
import subprocess
import sys

import pytest

from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.tree import Tree
from dylan.workbench_api import EXAMPLES, parse_request, tree_snapshot, validate_request


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("example", EXAMPLES)
def test_starter_examples_produce_complete_real_derivations(example):
    result = parse_request({"sentence": example["sentence"], "grammar": "2015-english-ttr"})
    assert result["ok"] and result["complete"]
    assert result["words"][0]["nodes"][0]["requirements"] == ["?Ty(t)"]
    final = result["words"][-1]
    assert final["pointer"] == "0"
    assert final["requirement_count"] == 0
    assert final["semantics"]
    assert len(result["actions"]) > len(result["words"])
    assert result["actions"][-1]["nodes"] == final["nodes"]
    for frame in result["words"] + result["actions"]:
        ids = {node["id"] for node in frame["nodes"]}
        assert frame["pointer"] in ids
        assert all(edge["source"] in ids and edge["target"] in ids for edge in frame["edges"])
    json.dumps(result)


def test_unknown_word_stops_before_unparsed_remainder():
    result = parse_request({"sentence": "a zzzunknown arrives", "grammar": "2015-english-ttr"})
    assert not result["ok"]
    assert result["failure"]["index"] == 1
    assert "not in this grammar" in result["failure"]["message"]
    assert [frame["label"] for frame in result["words"]] == ["Axiom", "a"]
    assert not any(frame["word_index"] > 0 for frame in result["actions"])


def test_incomplete_sentence_is_distinct_from_a_failed_parse():
    result = parse_request({"sentence": "a man", "grammar": "2015-english-ttr"})
    assert result["ok"] and not result["complete"]
    assert result["failure"] is None
    assert result["words"][-1]["requirement_count"] > 0


def test_snapshot_does_not_decorate_its_input_tree():
    tree = Tree()
    before = [(str(a), [str(label) for label in n.labels]) for a, n in tree.items()]
    tree_snapshot(tree, None)
    after = [(str(a), [str(label) for label in n.labels]) for a, n in tree.items()]
    assert before == after


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"sentence": " "},
        {"sentence": "hello", "grammar": "/tmp"},
        {"sentence": "x" * 501, "grammar": "2015-english-ttr"},
        {"sentence": "a " * 41, "grammar": "2015-english-ttr"},
    ],
)
def test_api_rejects_invalid_or_unbounded_requests(payload):
    with pytest.raises(ValueError):
        validate_request(payload)


@pytest.mark.parametrize(
    "option,value",
    [("top_n", value) for value in [-1, 21, True, False, "3", 3.0, None, [], {}]]
    + [("strict", value) for value in [0, 1, "true", None, [], {}]],
)
def test_api_rejects_invalid_parser_options(option, value):
    with pytest.raises(ValueError, match=option):
        validate_request({"sentence": "a man arrives", "grammar": "2015-english-ttr", option: value})


def test_worker_returns_json_without_stdout_log_pollution():
    worker = subprocess.run(
        [sys.executable, "-m", "dylan.workbench_api"],
        input=json.dumps({"sentence": "a man arrives.", "grammar": "2015-english-ttr"}),
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert json.loads(worker.stdout)["complete"]
