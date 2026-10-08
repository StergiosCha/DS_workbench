"""Search revisions must not appear as two lexical readings on one derivation."""

import json
from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.meta.element import reset_all_meta_bindings


@pytest.fixture
def ambiguous_grammar(tmp_path):
    reset_all_meta_bindings()
    target = tmp_path / "grammar"
    source = Path(__file__).parents[1] / "src/dynamicsyntax/grammars/2026-english-mltt"
    shutil.copytree(source, target)
    with (target / "lexicon.txt").open("a") as out:
        out.write("bank proper rock stone\nbank proper john human\n")
    path = target / "semantics.json"
    profile = json.loads(path.read_text())
    profile["constants"]["rock"] = "stone"
    path.write_text(json.dumps(profile))
    yield target
    reset_all_meta_bindings()


def test_final_action_trace_excludes_abandoned_lexical_reading(ambiguous_grammar):
    result = parse("bank shouts.", ambiguous_grammar, trace=True)
    assert result.ok and str(result.semantics) == "shout(john)"
    assert result.stats.backtracks_ok > 0
    banks = [step for step in result.action_steps if step.action_name == "bank"]
    assert len(banks) == 1
    assert str(banks[0].after_tree.pointed_node.get_formula()) == "john"
    assert not any("rock" in str(step.after_tree.pointed_node.get_formula())
                   for step in result.action_steps)


def test_workbench_shows_a_return_to_the_branch_point(ambiguous_grammar, monkeypatch):
    from dylan import workbench_api

    config = workbench_api.configuration()
    config["grammars"].append(str(ambiguous_grammar))
    monkeypatch.setattr(workbench_api, "configuration", lambda: config)
    result = workbench_api.parse_request({"sentence": "bank shouts.", "grammar": str(ambiguous_grammar)})
    assert result["ok"] and result["complete"]
    assert result["stats"]["backtracks_ok"] > 0
    for channel in ("words", "actions", "operations"):
        rollback = next(frame for frame in result[channel] if frame["kind"] == "backtrack")
        assert rollback["pointer"] == "0"
        assert rollback["nodes"][0]["formula"] is None
    assert result["words"][-1]["normalized"] == "shout(john)"
