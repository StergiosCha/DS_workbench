"""Import local task exports against a fixed schedule, retaining response provenance."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from dylan.experiments.contracts import digest
from dylan.experiments.study import prototype, schedule


def import_sessions(study, sessions, *, data_kind="rehearsal"):
    if data_kind not in ("rehearsal", "human"):
        raise ValueError("Task exports must explicitly identify rehearsal or human responses")
    responses, participants, audit = [], set(), []
    for session in sessions:
        if not isinstance(session, dict) or session.get("schema") != 1 or session.get("data_kind") != data_kind:
            raise ValueError("Invalid session schema or inconsistent response provenance")
        if session.get("study_id") != study["id"] or session.get("study_sha256") != digest(study):
            raise ValueError("Session does not match this frozen study")
        participant = session.get("participant")
        expected = schedule(study, participant)["events"]
        if participant in participants:
            raise ValueError("Duplicate participant session")
        participants.add(participant)
        events = session.get("events")
        if not isinstance(events, list) or not events or len(events) > len(expected):
            raise ValueError("Expected a nonempty consecutive prefix of the scheduled events")
        excluded = Counter()
        for index, event in enumerate(events):
            if not isinstance(event, dict) or any(event.get(k) != v for k, v in expected[index].items()):
                raise ValueError("Event identity, order or observation differs from the schedule")
            rt = event.get("rt_ms")
            if type(rt) not in (int, float) or not math.isfinite(rt) or rt <= 0:
                raise ValueError("Response time must be finite and positive")
            if type(event.get("possible")) is not bool or type(event.get("visibility_interrupted")) is not bool:
                raise ValueError("Expected explicit response and visibility flags")
            if event["role"] != "target":
                continue
            # A response is a participant judgment, not ground-truth accuracy.
            # Keep both choices; model RT conditional on the observed task.
            if event["visibility_interrupted"]:
                excluded["visibility_interrupted"] += 1
                continue
            responses.append({"participant": participant, "family": event["family"],
                              "rt_seconds": rt / 1000, "possible": event["possible"], "data_kind": data_kind})
        audit.append({"participant": participant, "events": len(events), "scheduled": len(expected),
                      "complete": len(events) == len(expected), "excluded_targets": dict(excluded),
                      "session_sha256": digest(session)})
    return {"schema": 1, "study_id": study["id"], "study_sha256": digest(study), "data_kind": data_kind,
            "responses": responses, "participants": sorted(participants), "sessions": audit,
            "policy": "Both response choices retained; interrupted targets excluded; RT <=150 ms excluded identically at comparison",
            "limitation": "Provenance is declared by the collector, not authenticated; rehearsal files cannot be relabelled by this importer"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    parser.add_argument("--data-kind", choices=("rehearsal", "human"), default="rehearsal")
    parser.add_argument("--output", type=Path, default=Path("build/experiments/responses.json"))
    parser.add_argument("--evaluate", action="store_true", help="Requires the research extra; uses the declared shared model comparison")
    args = parser.parse_args()
    study = prototype()
    imported = import_sessions(study, [json.loads(path.read_text()) for path in args.sessions], data_kind=args.data_kind)
    if args.evaluate:
        from dylan.experiments.evaluation import compare, feature_rows
        from dylan.experiments.study import prepare
        prepared, coverage = prepare(study)
        rows = feature_rows(study, prepared, imported["participants"])
        imported["comparison"] = compare(study, rows, coverage, imported["responses"], data_kind=args.data_kind)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(imported, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps({"output": str(args.output), "data_kind": args.data_kind, "responses": len(imported["responses"])}))


if __name__ == "__main__":
    main()
