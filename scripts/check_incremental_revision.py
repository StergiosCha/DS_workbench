"""Run explicit live integration probes; draft references never become model inputs."""

import argparse
import json
from pathlib import Path
import shutil

from dylan.corpus import compile_coq
from dylan.decision.client import content_hash
from dylan.decision.evaluation import write_json
from dylan.workbench_api import parse_request
from dylan.workbench_environment import load_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/lexical-revision/observations.json"))
    args = parser.parse_args()
    load_environment()
    probes = json.loads(Path("data/lexical-revision/probes.json").read_text())
    report = {"probe_hash": content_hash(probes), "scope": probes["scope"],
              "review_status": probes["review_status"], "observations": []}
    output = Path("build/lexical-revision/live")
    output.mkdir(parents=True, exist_ok=True)
    for backend in ("mltt", "classical"):
        for case in probes["cases"]:
            result = parse_request({"sentence": case["sentence"], "grammar": f"2026-english-{backend}",
                                    "lexical_mode": "jev", "n_best": 3, "reading_traces": True, "strict": True})
            assert result["complete"] and result["cap_hit"] is None, (case["id"], result["failure"])
            selection = result["lexical"]["selection"]
            assert selection["live_calls"] <= 8
            assert any(d["answers"] for d in selection["decisions"]), "No valid Jev answer"
            assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
            coq = compile_coq(result["coq"], {}) if result["coq"] and shutil.which("coqc") else None
            assert coq in {None, "passed"}, coq
            row = {"id": case["id"], "backend": backend, "complete": True, "model": selection["model"],
                   "live_calls": selection["live_calls"], "used": selection["used"], "coq": coq,
                   "path_updates": selection["path_updates"], "revisions": selection["revisions"],
                   "decisions": [{k: d[k] for k in ("word", "prefix", "phase", "status", "preferred", "answers", "cached")}
                                 for d in selection["decisions"]],
                   "readings": [r["normalized"] for r in result["readings"]]}
            report["observations"].append(row)
            write_json(args.output, report)
            write_json(output / f"{backend}-{case['id']}.json", result)
            print(json.dumps({"id": case["id"], "backend": backend, "used": selection["used"],
                              "revisions": [r["status"] for r in selection["revisions"]],
                              "live_calls": selection["live_calls"], "coq": coq}), flush=True)


if __name__ == "__main__":
    main()
