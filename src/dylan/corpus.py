"""Sourced corpus execution and coverage arithmetic. No model judgments."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPORA = [ROOT / "data/greek-clitics/corpus.jsonl", ROOT / "data/english/corpus.jsonl"]
STATUSES = {"licensed", "starred", "variable", "not_stated"}
INCONCLUSIVE = {"search_limit", "time_limit", "runtime_error", "grammar_gap"}


def read_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    ids = set()
    for row in rows:
        if row["id"] in ids:
            raise ValueError(f"Duplicate corpus id: {row['id']}")
        ids.add(row["id"])
        if row["judgment"]["status"] not in STATUSES:
            raise ValueError(f"Invalid judgment: {row['id']}")
        source = row["source"]
        if (
            not source.get("file")
            or not source.get("label")
            or not (source.get("line") or source.get("page"))
        ):
            raise ValueError(f"Missing source locator: {row['id']}")
        if not row.get("surface") or not row.get("phenomena") or not row.get("grammars"):
            raise ValueError(f"Missing surface, tags or grammar mapping: {row['id']}")
    return rows


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def compile_coq(source, cache):
    if not source:
        return "not_applicable"
    key = hashlib.sha256(source.encode()).hexdigest()
    if key in cache:
        return cache[key]
    compiler = shutil.which("coqc")
    if not compiler:
        return "unavailable"
    with tempfile.TemporaryDirectory(prefix="ds-corpus-coq-") as tmp:
        path = Path(tmp) / "meaning.v"
        path.write_text(source)
        try:
            run = subprocess.run([compiler, str(path)], capture_output=True, text=True, timeout=20)
            outcome = "passed" if run.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            outcome = "timeout"
    cache[key] = outcome
    return outcome


@contextmanager
def deadline(seconds):
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise TimeoutError("Corpus row exceeded its time limit")

    signal.signal(signal.SIGALRM, expired)
    timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    started = time.monotonic()
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if timer[0]:
            signal.setitimer(
                signal.ITIMER_REAL, max(0.001, timer[0] - (time.monotonic() - started)), timer[1]
            )


def run_row(row, grammar, *, top_n=3, timeout=30, coq_cache=None, isolate=True):
    """Use an isolated real workbench worker; failed infrastructure is inconclusive."""
    from dynamicsyntax import get_grammars

    result = None
    failure = None
    if grammar not in get_grammars():
        failure = {"kind": "grammar_gap", "message": "No executable grammar for this stage yet."}
    else:
        payload = {"sentence": row["surface"], "grammar": grammar, "top_n": top_n}
        if row["judgment"]["status"] == "variable":
            payload["n_best"] = 8
        try:
            if isolate or not hasattr(signal, "SIGALRM"):
                worker = subprocess.run(
                    [sys.executable, "-m", "dylan.workbench_api"],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                result = json.loads(worker.stdout)
                if worker.returncode or "error" in result:
                    failure = {
                        "kind": "runtime_error",
                        "message": result.get("error", "Worker failed"),
                    }
                    result = None
            else:
                from dylan.action.meta.element import reset_all_meta_bindings
                from dylan.workbench_api import parse_request

                reset_all_meta_bindings()
                with deadline(timeout):
                    result = parse_request(payload)
        except (subprocess.TimeoutExpired, TimeoutError):
            failure = {"kind": "time_limit", "message": f"Worker exceeded {timeout} seconds"}
        except (
            ValueError,
            OSError,
            RuntimeError,
            TypeError,
            RecursionError,
            NotImplementedError,
        ) as exc:
            failure = {"kind": "runtime_error", "message": str(exc)}
    result = result or {}
    frames = result.get("words", [])
    coverage = result.get("diagnostics", {}).get("lexical_coverage", [])
    record = {
        "id": row["id"],
        "grammar": grammar,
        "surface": row["surface"],
        "source": row["source"],
        "phenomena": row["phenomena"],
        "judgment": row["judgment"],
        "expected": row.get("expected", {}),
        "ok": result.get("ok", False),
        "complete": result.get("complete", False),
        "failure": failure or result.get("failure"),
        "cap_hit": result.get("cap_hit"),
        "executable": bool(coverage) and all(c["known"] for c in coverage),
        "semantics": (frames[-1].get("normalized") or frames[-1].get("semantics"))
        if frames
        else None,
        "stats": result.get("stats", {}),
        "top_n": top_n,
        "top_n_cuts": result.get("stats", {}).get("top_n_cuts", []),
        "ms": result.get("elapsed_ms"),
        "readings": result.get("readings", []),
        "reading_search": result.get("reading_search"),
        "coq": compile_coq(result.get("coq"), coq_cache if coq_cache is not None else {}),
        "backend": result.get("backend"),
        "templates": result.get("templates", []),
    }
    # Corpus records have the worker's JSON contract in both execution modes.
    # Nonempty search-cut tuples otherwise differ after a subprocess roundtrip.
    return json.loads(json.dumps(record, ensure_ascii=False))


def agrees(row):
    if (
        not row["executable"]
        or row.get("cap_hit")
        or (row.get("failure") or {}).get("kind") in INCONCLUSIVE
    ):
        return False
    status = row["judgment"]["status"]
    if status == "licensed":
        return row["ok"] and row["complete"]
    if status == "starred":
        return not row["complete"]
    if status == "variable":
        strategies = {r.get("strategy") for r in row.get("readings", []) if r.get("complete")}
        return len(strategies - {None}) >= 2
    return False


def summarize(records):
    groups = defaultdict(list)
    for row in records:
        for tag in ["all", *row["phenomena"]]:
            groups[f"{row['grammar']}:{tag}"].append(row)
    report = {}
    for key, rows in sorted(groups.items()):
        assessed = [r for r in rows if r["judgment"]["status"] != "not_stated"]
        executable = [r for r in assessed if r["executable"]]
        agreeing = [r for r in executable if agrees(r)]
        over = [r["id"] for r in assessed if r["judgment"]["status"] == "starred" and r["complete"]]
        under = [
            {"id": r["id"], "kind": (r.get("failure") or {}).get("kind", "incomplete")}
            for r in executable
            if r["judgment"]["status"] == "licensed" and not agrees(r)
        ]
        semantic = [
            r
            for r in agreeing
            if r["judgment"]["status"] == "licensed"
            and r.get("expected", {}).get("semantics_substrings")
        ]
        correct = [
            r
            for r in semantic
            if all(s in (r["semantics"] or "") for s in r["expected"]["semantics_substrings"])
            and (r["backend"] != "mltt" or r["coq"] == "passed")
        ]

        def median(field):
            values = [r.get("stats", {}).get(field) for r in rows]
            return (
                statistics.median(v for v in values if v is not None)
                if any(v is not None for v in values)
                else None
            )

        times = [r["ms"] for r in rows if r.get("ms") is not None]
        report[key] = {
            "rows": len(rows),
            "not_stated": len(rows) - len(assessed),
            "vocabulary": [len(executable), len(assessed)],
            "agreement": [len(agreeing), len(executable)],
            "semantic": [len(correct), len(semantic)],
            "semantic_unmeasured": sum(r["judgment"]["status"] == "licensed" for r in agreeing)
            - len(semantic),
            "overgeneration": over,
            "execution_errors": [
                r["id"]
                for r in rows
                if (r.get("failure") or {}).get("kind") in {"runtime_error", "time_limit"}
            ],
            "undergeneration": under,
            "inconclusive": [
                r["id"]
                for r in rows
                if r.get("cap_hit") or (r.get("failure") or {}).get("kind") in INCONCLUSIVE
            ],
            "matrix": "C"
            if len(executable) >= 3 and len(agreeing) / len(executable) >= 0.9
            else "P"
            if agreeing
            else "A",
            "median_tuples": median("tuples"),
            "median_backtracks": median("backtracks_called"),
            "median_ms": statistics.median(times) if times else None,
        }
    return report


def lock_counts(report):
    return {
        key: {name: value[name] for name in ("rows", "vocabulary", "agreement", "semantic")}
        for key, value in report.items()
    }


def check_lock(report, locked):
    errors = []
    for key, value in report.items():
        if value.get("execution_errors"):
            errors.append(f"{key}: execution errors {value['execution_errors']}")
        if value["overgeneration"]:
            errors.append(f"{key}: overgeneration {value['overgeneration']}")
        if any(
            kind in {"time_limit", "runtime_error"}
            for kind in (u["kind"] for u in value["undergeneration"])
        ):
            errors.append(f"{key}: execution failed")
    for key, baseline in locked.items():
        current = report.get(key)
        if current is None:
            errors.append(f"{key}: group disappeared")
            continue
        if current["rows"] < baseline["rows"]:
            errors.append(f"{key}: corpus rows disappeared")
        for name in ("vocabulary", "agreement", "semantic"):
            if current[name][0] < baseline[name][0]:
                errors.append(
                    f"{key}: {name} dropped from {baseline[name][0]} to {current[name][0]}"
                )
    return errors


def markdown(report):
    lines = [
        "# Measured coverage",
        "",
        "Rates show numerator/denominator. Unknown judgments and unmeasured semantic checks are kept separate.",
        "",
        "| Grammar:phenomenon | Vocabulary | Agreement | Semantics | Overgeneration | Matrix | Median tuples |",
        "|---|---:|---:|---:|---:|:---:|---:|",
    ]
    for key, row in report.items():

        def rate(name):
            return "/".join(map(str, row[name]))

        lines.append(
            f"| {key} | {rate('vocabulary')} | {rate('agreement')} | {rate('semantic')} | {len(row['overgeneration'])} | {row['matrix']} | {row['median_tuples']} |"
        )
    lines.extend(
        [
            "",
            "Coq compilation checks type correctness of the exported meaning; it does not establish truth or a proof of inhabitation.",
            "",
        ]
    )
    return "\n".join(lines)
