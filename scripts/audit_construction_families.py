"""Probe combinations of English construction families, with every failure retained.

An authored engineering matrix, not unseen-text accuracy. No model calls.
Add families and vocabulary here before changing implementation or coverage claims.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dylan.lexical_dictionary import configuration
from dylan.paragraph_workbench import time_budget, SentenceDeadline
from dylan.workbench_api import parse_request

FAMILIES = {
    "copular noun phrases": [
        "{name} is a person.",
        "{name} was a doctor.",
        "{name} is not a doctor.",
    ],
    "noun-relative adjectives": [
        "{name} is a great person.",
        "{name} is a good doctor.",
        "{name} was a skilled doctor.",
        "{name} is not a great person.",
        "{name} is a great black dog.",
        "{name} is a black great dog.",
    ],
    "bare predicative adjectives": [
        "{name} is great.",
        "{name} is very good.",
        "{name} is not great.",
    ],
    "modified quantifiers": [
        "a great person walks.",
        "every good doctor walks.",
        "all great people walk.",
        "all the good people walk.",
    ],
    "objects and PPs": [
        "{name} likes a great person.",
        "{name} reads a good book in a library.",
        "{name} walks with mary.",
        "{name} relies on mary.",
    ],
    "coordination": ["{name} walks and mary reads a good book."],
    "finite clauses": [
        "{name} thinks that mary is a good doctor.",
        "{name} walks because mary arrived.",
        "{name} walks when mary arrives.",
        "{name} walks although mary sleeps.",
    ],
    "relative clauses": [
        "a good doctor who mary knows walks.",
        "{name}, who mary knows, is a good doctor.",
    ],
}
NEGATIVES = [
    "john is a.",
    "john is good doctor.",
    "john is a a good doctor.",
    "john walks with with mary.",
]
# "good" also has a noun reading (a good/commodity); don't label that string
# ungrammatical merely because an adjective-only analysis would be incomplete.
EXPLORATORY = [
    "john is a very good doctor.",
    "john has been a good doctor.",
    "the good doctor was praised by mary.",
    "john is a former doctor.",
    "john met the doctor whose patient arrived.",
    "john is a good.",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not configuration()["installed"]:
        raise SystemExit(
            "The pinned WordNet index is required; no missing-source cases are silently skipped."
        )
    cases = []
    for family, patterns in FAMILIES.items():
        for pattern in patterns:
            for name in ["john", "mary", "george"] if "{name}" in pattern else ["john"]:
                cases.append((family, pattern.format(name=name), True))
    cases += [("negative contrasts", s, False) for s in NEGATIVES] + [
        ("exploratory gaps", s, None) for s in EXPLORATORY
    ]
    rows = []
    for backend in ["mltt", "classical"]:
        for family, sentence, expected in cases:
            try:
                with time_budget(3):
                    r = parse_request(
                        {
                            "sentence": sentence,
                            "grammar": "2026-english-" + backend,
                            "lexical_mode": "dictionary",
                            "allow_model_fallback": False,
                        },
                        _trace=False,
                    )
                known = all(x["known"] for x in r["diagnostics"]["lexical_coverage"])
                row = {
                    "family": family,
                    "backend": backend,
                    "sentence": sentence,
                    "expected_complete": expected,
                    "complete": r["complete"],
                    "meaning": r["words"][-1].get("normalized"),
                    "failure": r["failure"],
                    "all_tokens_known": known,
                }
                row["matches_expectation"] = (
                    None
                    if expected is None or (expected is False and not known)
                    else r["complete"] == expected
                )
                if r["failure"] and r["failure"]["kind"] == "search_limit":
                    row["matches_expectation"] = None
                    row["inconclusive"] = "Search limit"
            except (SentenceDeadline, ValueError, TypeError) as e:
                row = {
                    "family": family,
                    "backend": backend,
                    "sentence": sentence,
                    "expected_complete": expected,
                    "complete": False,
                    "inconclusive": str(e) or "Search deadline",
                    "matches_expectation": None,
                }
            rows.append(row)
    summary = {}
    for family in [*FAMILIES, "negative contrasts", "exploratory gaps"]:
        subset = [r for r in rows if r["family"] == family]
        summary[family] = {
            "cases": len(subset),
            "complete": sum(r["complete"] for r in subset),
            "expectations_matched": sum(r["matches_expectation"] is True for r in subset),
            "expectations_failed": sum(r["matches_expectation"] is False for r in subset),
            "expectations_inconclusive": sum(
                r["expected_complete"] is not None and r["matches_expectation"] is None
                for r in subset
            ),
        }
    report = {
        "scope": "Authored English construction/vocabulary combinations in two native backends. Not an accuracy estimate; no LLM requests. Exploratory gaps have no passing expectation.",
        "summary": summary,
        "cases": rows,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if any(
        r["expected_complete"] is not None and r["matches_expectation"] is not True for r in rows
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
