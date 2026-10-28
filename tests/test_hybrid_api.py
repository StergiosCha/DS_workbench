import json

import pytest

from dylan.hybrid.api import EXAMPLES, analyse, validate


@pytest.mark.parametrize("payload", [None, {"text": "x", "extra": True}, {"text": "x", "complete": "false"},
    {"text": "word " * 41}, {"text": "John", "grammar": "../../outside"}, {"action": "draft", "word": "a b"},
    {"text": "John", "grammar": []}, {"text": "John", "framework": []}, {"action": []}])
def test_invalid_worker_inputs_are_rejected(payload):
    with pytest.raises(ValueError):
        validate(payload)


def test_live_drafting_requires_explicit_request():
    with pytest.raises(ValueError, match="Explicit live"):
        analyse({"action": "draft", "word": "glimmers"})


@pytest.mark.parametrize("example", EXAMPLES)
def test_frontend_examples_return_serializable_bounded_results(example):
    result = analyse({k: v for k, v in example.items() if k != "label"})
    assert result["modules"]
    json.dumps(result, allow_nan=False)
    if example["label"] == "Agreement conflict":
        assert result["modules"]["features"]["status"] == "conflict"
        assert result["modules"]["ds"]["status"] != "complete"
