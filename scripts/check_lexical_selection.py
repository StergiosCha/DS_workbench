"""Explicit live check of Jev lexical selection, native derivations and cache reuse."""

import argparse
import json
from pathlib import Path
import shutil

from dylan.corpus import compile_coq
from dylan.workbench_api import parse_request
from dylan.workbench_environment import load_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    args = parser.parse_args()
    assert args.live
    load_environment()
    output = Path("build/lexical-selection/live")
    output.mkdir(parents=True, exist_ok=True)
    for backend in ("mltt", "classical"):
        for label, sentence in (("double-object", "john lends mary a book."),
                                ("to-recipient", "john lends a book to mary.")):
            payload = {"grammar": f"2026-english-{backend}", "sentence": sentence,
                       "lexical_mode": "jev", "strict": True, "n_best": 2, "reading_traces": True}
            result = parse_request(payload)
            assert result["complete"] and result["cap_hit"] is None, result["failure"]
            assert not result["stats"]["top_n_cuts"] and result["stats"]["pruned"] == 0
            selection = result["lexical"]["selection"]
            assert any(d["answers"] for d in selection["decisions"]), "No successful Jev answer"
            assert selection["used"] and all("lend_" in entry["symbol"] for entry in selection["used"])
            assert all(d["prefix"] == ["john"] for d in selection["decisions"])
            assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
            assert len({frame["pointer"] for frame in result["operations"]}) > 2
            coq = "not_applicable"
            if backend == "mltt":
                coq = compile_coq(result["coq"], {}) if shutil.which("coqc") else "not_installed"
                assert coq in {"passed", "not_installed"}, coq
            cached = parse_request(payload)
            assert cached["lexical"]["selection"]["live_calls"] == 0
            assert cached["words"][-1]["normalized"] == result["words"][-1]["normalized"]
            (output / f"{backend}-{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"backend": backend, "frame": label, "complete": True,
                              "used": selection["used"], "live_calls": selection["live_calls"],
                              "cached_live_calls": 0, "coq": coq,
                              "readings": len(result["readings"]), "operations": len(result["operations"])}), flush=True)


if __name__ == "__main__":
    main()
