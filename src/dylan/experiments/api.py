"""Bounded local experiment endpoints with independently selected engine workers."""

import json
import sys

from dylan.experiments.contracts import Observation
from dylan.experiments.host import Session
from dylan.experiments.registry import catalog, from_dict
from dylan.experiments.study import interactive_demo, prototype, schedule
from dylan.workbench_paths import data_path


def resource(name, *, participant=0):
    if name == "catalog":
        return catalog()
    if name == "study":
        return prototype()
    if name == "schedule":
        return schedule(prototype(), participant)
    if name == "report":
        path = data_path("experiments/pilot-report.json")
        return json.loads(path.read_text()) if path.exists() else {"status": "not_built"}
    if name == "references":
        return json.loads(data_path("experiments/references-v1.json").read_text())
    raise KeyError("Unknown experiment resource")


def validate(payload):
    allowed = {"configurations", "mode", "prime", "target", "prime_context", "target_context", "task", "fillers", "family", "condition", "lag"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError("Unknown experiment request fields")
    configs = payload.get("configurations")
    if not isinstance(configs, list) or not 1 <= len(configs) <= 4:
        raise ValueError("Select one to four configurations")
    for config in configs:
        from_dict(config)
    mode = payload.get("mode", "pair")
    if mode not in ("pair", "study"):
        raise ValueError("Unknown experiment mode")
    if mode == "study":
        if payload.get("family") not in [f["id"] for f in prototype()["families"]]:
            raise ValueError("Unknown study family")
        if payload.get("condition") not in ("matched", "shifted_boundary") or type(payload.get("lag")) is not int or payload["lag"] not in (0, 2):
            raise ValueError("Unknown experimental condition")
    else:
        for field in ("prime", "target", "prime_context", "target_context"):
            if not isinstance(payload.get(field, ""), str) or len(payload.get(field, "")) > 1000:
                raise ValueError("Invalid observed text")
        for role in ("prime", "target"):
            Observation(payload.get(role, ""), payload.get(role + "_context", ""), payload.get("task", "fragment"))
        fillers = payload.get("fillers", [])
        if not isinstance(fillers, list) or len(fillers) > 2:
            raise ValueError("At most two intervening observations")
        for filler in fillers:
            if not isinstance(filler, dict) or set(filler) - {"text", "left_context", "task"}:
                raise ValueError("Invalid intervening observation")
            try:
                Observation(**filler)
            except TypeError:
                raise ValueError("Incomplete intervening observation") from None
    return payload


def run(payload):
    validate(payload)
    runs = []
    for value in payload["configurations"]:
        config = from_dict(value)
        if payload.get("mode") == "study":
            runs.append(interactive_demo(prototype(), config, payload["family"], payload["condition"], payload["lag"]))
            continue
        session = Session(config)
        try:
            session.observe(Observation(payload["prime"], payload.get("prime_context", ""), payload.get("task", "fragment")))
            for filler in payload.get("fillers", []):
                session.observe(Observation(**filler))
            session.observe(Observation(payload["target"], payload.get("target_context", ""), payload.get("task", "fragment")))
            runs.append({"configuration": config.to_dict(), "events": session.events})
        finally:
            session.close()
    return {"runs": runs, "scope": "Unfitted component demonstration. See the synthetic pilot for fitted model comparisons."}


def main():
    try:
        result = run(json.load(sys.stdin))
    except ValueError as exc:
        result = {"error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
