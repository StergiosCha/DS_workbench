"""Copy and extend native grammars without changing installed package files.

Run with --output /path/to/new-directory. No network or model key is used.
"""

import argparse
from hashlib import sha256
from importlib.resources import as_file, files
import json
from pathlib import Path
import shutil

import dynamicsyntax as ds


def extend(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    report = {"distribution_version": ds.__version__, "ai_used": False, "grammars": []}
    for backend in ("classical", "mltt"):
        grammar_id = f"2026-english-{backend}"
        target = output / grammar_id
        with as_file(files("dynamicsyntax") / "grammars" / grammar_id) as source:
            shutil.copytree(source, target)
        profile_path = target / "semantics.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["predicates"]["dance"] = ["human"]
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        with (target / "lexicon.txt").open("a", encoding="utf-8") as stream:
            stream.write("\n// Community tutorial: a new predicate in existing frames.\n"
                         "dances intransitive dance human\n"
                         "dance intransitive-base dance human\n")
        cases = [
            ("John dances.", "dance(john)"),
            ("Mary dances.", "dance(mary)"),
            ("John does not dance.", "¬(dance(john))"),
            ("John, who Mary knows, dances.", "(dance(john) ∧ know(mary, john))"),
            ("John dances Mary.", None),
            ("John dances because.", None),
        ]
        checks = []
        for sentence, expected in cases:
            result = ds.parse(sentence, target, strict=True, trace=True, top_n=0)
            complete = bool(result.ok and result.tree and result.tree.is_complete())
            assert result.cap_hit is None, (sentence, result.cap_hit)
            meaning = str(result.semantics) if result.semantics is not None else None
            assert complete == (expected is not None), (sentence, meaning)
            if expected is not None:
                assert meaning == expected, (sentence, meaning, expected)
            checks.append({"sentence": sentence, "complete": complete, "meaning": meaning,
                           "expected_meaning": expected, "cap_hit": result.cap_hit})
        hashes = {p.name: sha256(p.read_bytes()).hexdigest()
                  for p in sorted(target.iterdir()) if p.is_file()}
        report["grammars"].append({"grammar": grammar_id, "files_sha256": hashes,
                                   "checks": checks})
    (output / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = extend(args.output.resolve())
    print(json.dumps({"output": str(args.output), "checks_passed": sum(
        len(g["checks"]) for g in report["grammars"]), "ai_used": False}))
