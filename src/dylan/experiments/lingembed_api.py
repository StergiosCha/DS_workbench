"""Optional export wrapper around the frozen experimental protocol API."""

import json
import sys

from dylan.experiments import api
from dylan.experiments.lingembed import export_analysis


def validate(payload):
    if not isinstance(payload, dict) or type(payload.get("export_lingembed", False)) is not bool:
        raise ValueError("export_lingembed must be a boolean in an experiment request")
    api.validate({key: value for key, value in payload.items() if key != "export_lingembed"})
    return payload


def run(payload):
    validate(payload)
    result = api.run({key: value for key, value in payload.items() if key != "export_lingembed"})
    if payload.get("export_lingembed"):
        for experiment in result["runs"]:
            for event in experiment["events"]:
                event["lingembed"] = export_analysis(event["analysis"])
    return result


def main():
    try:
        result = run(json.load(sys.stdin))
    except ValueError as exc:
        result = {"error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
