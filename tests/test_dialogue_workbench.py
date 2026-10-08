"""Dialogue frames retain speakers, repaired paths and explicit tree boundaries."""

import json
import subprocess
import sys

import pytest

from dylan.dialogue_workbench import configuration
from dylan.workbench_api import parse_request, validate_request


def request(turns, backend="classical"):
    return parse_request({"dialogue": turns, "grammar": f"2026-english-{backend}"})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("example", configuration()["examples"], ids=lambda example: example["id"])
def test_dialogue_presets_run_in_native_backends(example, backend):
    result = parse_request(
        {"dialogue": example["turns"], "grammar": f"2026-{example['family']}-{backend}"}
    )
    assert result["complete"], result["failure"]
    assert result["backend"] == backend
    assert result["dialogue"]
    assert all(w["known"] for w in result["diagnostics"]["lexical_coverage"])
    for frame in result["operations"]:
        assert frame["pointer"] in {n["id"] for n in frame["nodes"]}
    json.dumps(result)


def test_speaker_switch_keeps_the_object_requirement():
    result = request(
        [{"speaker": "Alice", "text": "john likes"}, {"speaker": "Bob", "text": "mary."}]
    )
    before = next(f for f in result["words"] if f["label"] == "likes")
    assert before["speaker"] == "Alice" and before["pointer"] == "010"
    assert next(n for n in before["nodes"] if n["id"] == "010")["required_type"] == "e"
    after = next(f for f in result["words"] if f["label"] == "mary")
    assert after["speaker"] == "Bob" and after["addressee"] == "Alice"
    assert len([f for f in result["words"] if f["kind"] == "axiom"]) == 1
    assert result["words"][-1]["semantics"] == "like(john, mary)"


def test_repair_frames_restore_the_real_open_slot_and_keep_old_words():
    result = request(
        [{"speaker": "A", "text": "john likes mary."}, {"speaker": "B", "text": "sorry bill."}]
    )
    repair = result["repairs"][0]
    assert repair["replaced"] == [2, 3] and repair["replacement"] == 5
    frames = result["operations"]
    rollback = next(f for f in frames if f["kind"] == "repair")
    assert rollback["pointer"] == "010" and rollback["pointer_before"] == "0"
    assert rollback["active_words"] == [0, 1]
    assert next(n for n in rollback["nodes"] if n["id"] == "010")["formula"] is None
    assert next(f for f in result["words"] if f["label"] == "mary")["nodes"] != rollback["nodes"]
    assert result["tokens"] == ["john", "likes", "mary", ".", "sorry", "bill", "."]
    assert result["words"][-1]["active_words"] == [0, 1, 5, 6]
    assert result["words"][-1]["semantics"] == "like(john, bill)"
    assert result["diagnostics"]["lexical_coverage"][4]["source"] == "parser_control"
    assert any(
        f["kind"] == "operation" and f["word_index"] == 5 and "bill" in f["label"] for f in frames
    )


def test_new_tree_preserves_the_previous_interpretation():
    result = request(
        [
            {"speaker": "A", "text": "john likes mary."},
            {"speaker": "B", "text": "bill walks.", "boundary": "new_tree"},
        ]
    )
    assert result["context_trees"][0]["semantics"] == "like(john, mary)"
    assert result["words"][-1]["semantics"] == "walk(bill)"
    assert result["words"][-1]["clause_index"] == 1
    assert result["words"][-1]["active_words"] == [4, 5, 6]


@pytest.mark.parametrize(
    "turns, kind",
    [
        ([{"speaker": "A", "text": "sorry bill."}], "missing_context"),
        (
            [
                {"speaker": "A", "text": "john likes mary."},
                {"speaker": "B", "text": "sorry walks."},
            ],
            "repair_unavailable",
        ),
        (
            [
                {"speaker": "A", "text": "john likes mary."},
                {"speaker": "B", "text": "sorry zzunknown."},
            ],
            "lexicon_gap",
        ),
        (
            [{"speaker": "A", "text": "john likes mary."}, {"speaker": "B", "text": "bill walks."}],
            "context_boundary",
        ),
    ],
)
def test_distinguish_context_gaps_and_failed_repairs_from_grammaticality(turns, kind):
    result = request(turns)
    assert not result["ok"] and result["failure"]["kind"] == kind
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_incomplete_turn_and_pending_repair_stay_incomplete():
    result = request([{"speaker": "A", "text": "john likes"}])
    assert result["ok"] and not result["complete"]
    pending = request([{"speaker": "A", "text": "john likes mary. sorry"}])
    assert pending["ok"] and not pending["complete"] and pending["pending_repair"]
    assert pending["diagnostics"]["parse_status"] == "incomplete"


@pytest.mark.parametrize(
    "dialogue",
    [
        None,
        [],
        [{}],
        ["hello"],
        [{"speaker": "A", "text": ""}],
        [{"speaker": "A", "text": "john", "boundary": "guess"}],
        [{"speaker": str(i), "text": "john"} for i in range(3)],
        [{"speaker": "A", "text": "john"}] * 13,
        [{"speaker": "A", "text": "john " * 81}],
    ],
)
def test_invalid_dialogue_is_rejected(dialogue):
    with pytest.raises(ValueError):
        validate_request({"dialogue": dialogue, "grammar": "2026-english-classical"})


def test_streamed_dialogue_matches_its_final_channels():
    payload = {
        "dialogue": [
            {"speaker": "A", "text": "john likes mary."},
            {"speaker": "B", "text": "sorry bill."},
        ],
        "grammar": "2026-english-mltt",
        "stream": True,
    }
    worker = subprocess.run(
        [sys.executable, "-m", "dylan.workbench_api"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    events = [json.loads(line) for line in worker.stdout.splitlines()]
    result = events[-1]["result"]
    assert result["complete"]
    assert events[0]["dialogue"] == result["dialogue"]
    for channel in ("words", "actions", "operations"):
        frames = [events[0]["initial"]] + [
            e["frame"] for e in events if e.get("channel") == channel
        ]
        assert frames == result[channel]
