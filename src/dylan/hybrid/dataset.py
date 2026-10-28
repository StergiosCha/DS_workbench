"""Lossless experimental identifiers with explicit displayed-input reconstruction."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

MISSING = {"", "NA", "nan", "None", None}
EXPECTED = {1: (40, 2174), 2: (57, 2739), 3: (200, 11033), 4: (200, 11016)}


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value):
    if value in MISSING:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def identifier(value):
    return str(int(float(value)))


def quantile(values, probability):
    """R's default type-7 sample quantile, without a numerical dependency."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (position - lo) * (ordered[hi] - ordered[lo])


def participant_eligible(row):
    return (row.get("first_language", "english").strip().lower() == "english" and
            row.get("inattentive", "attentive") == "attentive")


def single_exclusion(row, cutoff):
    rt = number(row["RT"])
    if number(row["corr"]) == 0:
        return "incorrect"
    if rt is not None and rt < .2:
        return "quick"
    if rt is not None and rt > cutoff:
        return "slow"
    return "include"


def paired_exclusion(prime, target):
    for label in ("incorrect", "quick", "slow"):
        if label in (prime, target):
            return label
    return "include"


def displayed(text, pos, length=None):
    words, tags = text.split(), pos.split()
    if len(words) != len(tags):
        raise ValueError(f"Token/tag mismatch: {text!r} / {pos!r}")
    if length is not None:
        words, tags = words[:length], tags[:length]
    return " ".join(words), " ".join(tags)


def recover_history(directory, study, assignments):
    observations, issues = [], []
    for path in sorted(directory.glob("subjId*.csv")):
        subject = identifier(re.search(r"subjId(\d+)", path.name)[1])
        rows = read_csv(path)
        assignment = assignments.get(subject)
        if assignment is None:
            issues.append({"subject": subject, "issue": "missing list assignment"})
            continue
        for line, row in enumerate(rows, 2):
            order = number(row.get("trials.thisN"))
            if order is None:
                continue
            text = row.get(f"list{assignment}")
            if text in MISSING:
                issues.append({"subject": subject, "line": line, "issue": "missing display text"})
                continue
            tags = row.get("pos", "").split("|")
            types = row.get("stimType", "").split("|")
            tags = tags[min(int(assignment) - 1, len(tags) - 1)]
            kind = types[min(int(assignment) - 1, len(types) - 1)]
            length = None
            if study == 4:
                trial_type = row.get("trial_type")
                if trial_type not in {"threeword", "fourword"}:
                    issues.append({"subject": subject, "line": line,
                                   "issue": "unknown displayed length", "trial_type": trial_type})
                    continue
                length = 3 if trial_type == "threeword" else 4
            shown, pos = displayed(text, tags, length)
            observations.append({
                "id": f"s{study}:p{subject}:t{int(order)}", "study": study,
                "subject": subject, "order": int(order), "list": assignment,
                "item_id": identifier(row["itemId"]), "type": kind,
                "source_text": text, "text": shown, "pos": pos,
                "rt_seconds": number(row.get("response.rt")),
                "correct": number(row.get("response.corr")),
                "possible": row.get("corrAns") == "yes",
                "source_file": path.name, "source_line": line,
            })
    observations.sort(key=lambda x: (int(x["subject"]), x["order"]))
    keys = [x["id"] for x in observations]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate participant trial identifiers")
    return observations, issues


def normalize_study(root, study):
    directory = root / f"study{study}" / "Data and analysis"
    raw = read_csv(directory / "Data" / f"S{study}_data.csv")
    pre = read_csv(directory / "Data" / f"S{study}_data_preprocessed.csv")
    stimuli = read_csv(directory / "Data" / f"S{study}_stimuli.csv")
    assignments = {identifier(r["subjId"]): identifier(r["list"]) for r in pre}
    observations, issues = recover_history(directory / "PsychoPy data", study, assignments)
    by_pair = defaultdict(dict)
    for event in observations:
        role = "target" if event["type"] == "target" else "prime" if "prime" in event["type"].lower() else None
        # Later studies label the primes by condition without a 'Prime' suffix.
        if role is None and event["type"] in {"experimental", "control", "reverse", "exp", "con", "rev"}:
            role = "prime"
        if role:
            by_pair[(event["subject"], event["item_id"])][role] = event
    cutoff_data = [number(r["RT"]) for r in raw if participant_eligible(r)]
    if any(x is None for x in cutoff_data):
        raise ValueError("Missing RT in upstream cutoff population")
    cutoff = quantile(cutoff_data, .75) + 3 * (quantile(cutoff_data, .75) - quantile(cutoff_data, .25))
    exclusions = defaultdict(dict)
    for r in raw:
        exclusions[(identifier(r["subjId"]), identifier(r["itemId"]))][r["type"]] = single_exclusion(r, cutoff)
    trials, mismatches = [], []
    for row in pre:
        subject, item = identifier(row["subjId"]), identifier(row["itemId"])
        events = by_pair.get((subject, item), {})
        actual = exclusions[(subject, item)]
        reason = paired_exclusion(actual["prime"], actual["target"])
        if reason != row["exclusion"] or abs(cutoff - float(row["cutoff"])) > 1e-6:
            mismatches.append({"subject": subject, "item": item, "computed": reason,
                               "published": row["exclusion"]})
        pattern = row.get("pattern", "")
        lengths = [3 if p == "part" else 4 for p in pattern.split("_")] if study == 4 else [None, None]
        prime, pos_prime = displayed(row["item_prime"], row["pos_prime"], lengths[0])
        target, pos_target = displayed(row["item_target"], row["pos_target"], lengths[1])
        history_ok = all(role in events for role in ("prime", "target"))
        if history_ok:
            history_ok = (events["prime"]["text"] == prime and events["target"]["text"] == target and
                          events["target"]["order"] == events["prime"]["order"] + 1)
        if not history_ok:
            issues.append({"subject": subject, "item": item, "issue": "pair/history mismatch"})
        rt = float(row["RT"])
        if "target" in events and events["target"]["rt_seconds"] is not None:
            if abs(events["target"]["rt_seconds"] - rt) > 1e-6:
                issues.append({"subject": subject, "item": item, "issue": "target RT mismatch"})
                history_ok = False
        trials.append({
            "id": f"s{study}:p{subject}:i{item}", "study": study,
            "subject": subject, "item_id": item, "family": f"s{study}:i{item}",
            "list": assignments[subject], "condition": row["condition"], "pattern": pattern,
            "constituent": row.get("constituent"), "isi_seconds": number(row.get("ISI")),
            "soa_seconds": number(row.get("SOA")),
            "prime": prime, "target": target, "pos_prime": pos_prime, "pos_target": pos_target,
            "source_prime": row["item_prime"], "source_target": row["item_target"],
            "rt_seconds": rt, "correct": int(float(row["correct"])),
            "exclusion": row["exclusion"], "participant_eligible": participant_eligible(row),
            "included": participant_eligible(row) and row["exclusion"] == "include",
            "cutoff_seconds": cutoff, "history_verified": history_ok,
            "prime_order": events.get("prime", {}).get("order"),
            "target_order": events.get("target", {}).get("order"),
        })
    included = [r for r in trials if r["included"]]
    counts = (len({r["subject"] for r in included}), len(included))
    groups = defaultdict(list)
    for row in included:
        groups[f"{row['pattern']}:{row['condition']}".strip(":")].append(row["rt_seconds"] * 1000)
    summary = {
        "study": study, "participants": counts[0], "included_pairs": counts[1],
        "expected_participants": EXPECTED[study][0], "expected_pairs": EXPECTED[study][1],
        "counts_match_publication": counts == EXPECTED[study], "cutoff_seconds": cutoff,
        "preprocessing_mismatches": mismatches, "history_issues": issues,
        "observations": len(observations), "history_verified_pairs": sum(r["history_verified"] for r in trials),
        "exclusions": dict(Counter(r["exclusion"] for r in trials if r["participant_eligible"])),
        "raw_descriptive_means_ms": {k: {"n": len(v), "mean": statistics.mean(v),
                                        "median": statistics.median(v)} for k, v in groups.items()},
        "interpretation": "Preprocessing reproduction and sample descriptives; not Bayesian posterior estimates.",
    }
    return trials, observations, stimuli, summary


def write_jsonl(path, records):
    with Path(path).open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def normalize(root: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    summaries, all_trials, all_observations, all_stimuli = [], [], [], []
    for study in range(1, 5):
        trials, observations, stimuli, summary = normalize_study(root, study)
        all_trials.extend(trials)
        all_observations.extend(observations)
        all_stimuli.extend({"study": study, **s} for s in stimuli)
        summaries.append(summary)
    write_jsonl(output / "trials.jsonl", all_trials)
    write_jsonl(output / "observations.jsonl", all_observations)
    write_jsonl(output / "stimuli.jsonl", all_stimuli)
    report = {"schema": 1, "studies": summaries,
              "source_manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()}
    (output / "preprocessing-report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("build/hybrid/sources"))
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/data"))
    args = parser.parse_args()
    report = normalize(args.sources, args.output)
    for study in report["studies"]:
        print({k: study[k] for k in ("study", "participants", "included_pairs", "counts_match_publication", "history_verified_pairs")})
    if any(s["preprocessing_mismatches"] or not s["counts_match_publication"] or s["history_issues"] for s in report["studies"]):
        raise SystemExit("Audit differences are recorded in preprocessing-report.json; resolve before comparison.")


if __name__ == "__main__":
    main()
