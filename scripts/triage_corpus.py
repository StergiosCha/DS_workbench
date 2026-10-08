"""Write separate backlog estimates from corpus results. Runtime is off or stub."""

import argparse
import json
from pathlib import Path

from dylan.corpus import write_rows
from dylan.decision.client import DecisionClient
from dylan.decision.triage import triage_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--mode", choices=["off", "stub"], default="stub")
    parser.add_argument("--output", type=Path, default=Path("build/decision/triage.jsonl"))
    parser.add_argument("--log", type=Path, default=Path("build/decision/triage-audit.jsonl"))
    args = parser.parse_args()
    client = DecisionClient(args.mode, log_path=args.log)
    estimates = []
    for path in args.results:
        for line in path.read_text().splitlines():
            result = json.loads(line)
            estimate = triage_result(result, client)
            if estimate is not None:
                estimates.append({"id": result["id"], "grammar": result["grammar"],
                                  "model_estimate": estimate})
    write_rows(args.output, estimates)
    print(f"{len(estimates)} separate estimates; calibration unmeasured; no corpus fields changed.")


if __name__ == "__main__":
    main()
