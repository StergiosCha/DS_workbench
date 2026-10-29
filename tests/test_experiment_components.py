import math

import pytest

from dylan.experiments.api import run, validate
from dylan.experiments.contracts import Configuration, Observation
from dylan.experiments.host import Session
from dylan.experiments.measurement import Measurement
from dylan.experiments.memory import Memory
from dylan.experiments.registry import from_dict


def test_memory_recency_count_and_no_adaptation_have_different_predictions():
    cue = ("test", "a")
    counts, decay, none = Memory("count-v1"), Memory("exponential-v1", .5), Memory("none-v1")
    for m in (counts, decay, none):
        assert m.activation([cue]) == 0
        m.observe([cue, cue])
        m.observe([])
    assert counts.strength(cue) == 1
    assert decay.strength(cue) == .5
    assert none.activation([cue]) == 0
    decay.observe([cue])
    assert decay.strength(cue) == 1.25
    assert decay.activation([cue, cue]) == pytest.approx(math.log(2.25))


def test_observation_is_predicted_before_update_and_sessions_do_not_share_memory():
    config = Configuration(grammar="ccg-incremental-v1")
    first, second = Session(config), Session(config)
    try:
        observation = Observation("John walks")
        assert first.observe(observation)["activation"] == 0
        assert first.observe(observation)["activation"] > 0
        assert second.observe(observation)["activation"] == 0
        failure = first.observe(Observation("zzzz"))
        assert failure["activation"] is None
        assert failure["prediction"]["status"] == "unavailable"
        assert failure["memory_after"]["time"] == 3
    finally:
        first.close()
        second.close()


def test_lexical_control_is_available_without_claiming_a_supported_derivation():
    session = Session(Configuration(grammar="ccg-incremental-v1", representation="lexical"))
    try:
        result = session.observe(Observation("unknown words"))
        assert not result["analysis"]["supported"]
        assert result["activation"] == 0
        assert result["cue_count"] == 1
    finally:
        session.close()


def test_swapped_measurement_changes_response_scale_and_is_labelled_unfitted():
    a = Measurement("lognormal-v1").predict(1)
    b = Measurement("shifted-lognormal-v1").predict(1)
    assert b["mean_rt_ms"] - a["mean_rt_ms"] == pytest.approx(150)
    assert a["status"] == b["status"] == "illustrative"


@pytest.mark.parametrize("value", [{"grammar": "unknown"}, {"memory": []}, {"measurement": {}}, {"decay": float("nan")}, {"decay": True}, {"decay": 0}, {"semantics": "arbitrary"}, {"representation": "DS-tree"}])
def test_incompatible_or_invalid_configuration_is_rejected(value):
    with pytest.raises(ValueError):
        from_dict(value)


@pytest.mark.parametrize("payload", [None, {}, {"configurations": [{}]*5}, {"configurations": [{}], "prime":"John", "target":"Mary", "task":[]}, {"configurations": [{}], "prime":"John", "target":"Mary", "fillers":[{}]}, {"configurations": [{}], "mode":"study", "family":"f00", "condition":"matched", "lag":True}, {"configurations":[{}], "module":"os"}])
def test_api_rejects_bad_payloads_without_worker_crashes(payload):
    with pytest.raises(ValueError):
        validate(payload)


def test_api_runs_two_actual_memory_choices_on_identical_inputs():
    configs = [Configuration(grammar="ccg-incremental-v1", memory=m).to_dict() for m in ("none-v1", "count-v1")]
    result = run({"configurations":configs, "prime":"John walks", "target":"John walks"})
    assert result["runs"][0]["events"][-1]["activation"] == 0
    assert result["runs"][1]["events"][-1]["activation"] > 0
