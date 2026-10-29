from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from dylan.experiments.contracts import Configuration, digest
from dylan.experiments.responses import import_sessions
from dylan.experiments.study import prepare, prototype, replay_schedule, schedule


def export_session(participant=0, count=None):
    study = prototype()
    value = schedule(study, participant)
    return {"schema":1, "data_kind":"rehearsal", **value,
            "events":[{**e, "rt_ms":500., "possible":True, "visibility_interrupted":False}
                      for e in value["events"][:count]]}


def test_counterbalancing_and_randomization_are_reproducible():
    study = prototype()
    cells = defaultdict(set)
    for participant in range(4):
        value = schedule(study, participant)
        targets = [e for e in value["events"] if e["role"] == "target"]
        assert len(targets) == len({e["family"] for e in targets}) == 24
        for event in targets:
            cells[event["family"]].add((event["condition"], event["lag"]))
    assert all(len(c) == 4 for c in cells.values())
    assert schedule(study, 19) == schedule(study, 19)
    assert schedule(study, 19)["events"] != schedule(study, 23)["events"]


@pytest.mark.parametrize("participant", [-1, 100000, True, "0", None])
def test_invalid_participant_codes_fail(participant):
    with pytest.raises(ValueError):
        schedule(prototype(), participant)


def test_common_support_requires_every_condition_and_filler():
    study = prototype()
    analyses, coverage = prepare(study, grammars=["ccg-incremental-v1", "ccg-original-v1"])
    assert len(coverage["grammars"]["ccg-incremental-v1"]["supported_families"]) == 24
    assert not coverage["common_families"]
    original_rows = replay_schedule(study, 0, Configuration(grammar="ccg-original-v1"), analyses["ccg-original-v1"])
    assert any(r["activation"] is None for r in original_rows)


def test_exports_preserve_choices_and_exclude_interrupted_targets():
    value = export_session()
    targets = [e for e in value["events"] if e["role"] == "target"]
    targets[0]["visibility_interrupted"] = True
    targets[1]["possible"] = False
    imported = import_sessions(prototype(), [value])
    assert len(imported["responses"]) == 23
    assert imported["responses"][0]["possible"] is False
    assert imported["sessions"][0]["complete"]
    partial = import_sessions(prototype(), [export_session(count=4)])
    assert not partial["sessions"][0]["complete"]


@pytest.mark.parametrize("change", ["study", "condition", "order", "missing_middle", "response", "nonfinite", "provenance"])
def test_tampered_exports_fail_before_comparison(change):
    value = export_session()
    if change == "study":
        value["study_sha256"] = "bad"
    elif change == "condition":
        value["events"][0]["condition"] = "different"
    elif change == "order":
        value["events"][1]["order"] = 0
    elif change == "missing_middle":
        del value["events"][1]
    elif change == "response":
        value["events"][0]["possible"] = "yes"
    elif change == "nonfinite":
        value["events"][0]["rt_ms"] = float("nan")
    else:
        value["data_kind"] = "synthetic"
    with pytest.raises(ValueError):
        import_sessions(prototype(), [value])


def test_duplicate_sessions_and_relabelling_are_rejected():
    value = export_session()
    with pytest.raises(ValueError):
        import_sessions(prototype(), [value, deepcopy(value)])
    with pytest.raises(ValueError):
        import_sessions(prototype(), [value], data_kind="human")


def test_exported_study_and_report_match_runtime_protocol():
    root = Path(__file__).resolve().parents[1] / "data/experiments"
    study = json.loads((root / "study-v1.json").read_text())
    report = json.loads((root / "pilot-report.json").read_text())
    assert study == prototype() == report["protocol"]["study"]
    assert report["protocol"]["study_sha256"] == digest(study)
    assert report["comparison"]["data_kind"] == "synthetic"
    assert len(report["comparison"]["models"]) == 18
    assert len(report["coverage"]["common_families"]) == 24
    assert report["recovery_summary"]["runs"] == 9
    source = root.parents[1] / "src/dylan"
    for path, expected in report["protocol"]["software_sha256"].items():
        assert hashlib.sha256((source / path).read_bytes()).hexdigest() == expected, path
